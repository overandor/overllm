#!/usr/bin/env python3
"""RSTF real-corpus cost scanner.

Unlike tools/rstf_benchmark.py and the comparative synthetic pipeline, this
script does not generate transformed examples. It scans real input text as-is,
runs the production RSTF detector, and measures token/byte change only for
items where RSTF actually canonicalizes something.

The expected result on ordinary clean corpora may be near-zero savings. That is
not a failure: the point is to measure real prevalence and real cost impact, not
to replay synthetic attacks.

This scanner also includes RAM/storage compression A/B metrics:

- raw UTF-8 bytes
- canonical UTF-8 bytes
- compact receipt JSON bytes
- compressed raw bytes
- compressed canonical bytes
- compressed canonical+receipt bytes
- hot-path and audit-path delta ratios

Supported input modes:

  --input-file path.txt              one record per non-empty line by default
  --input-file records.jsonl         JSONL records; text read from --text-field
  --input-dir docs --glob "*.md"     recursively scan text files

Examples:

  python tools/rstf_real_corpus_cost.py --input-dir docs --glob "*.md"
  python tools/rstf_real_corpus_cost.py --input-file data/messages.jsonl --text-field message
  python tools/rstf_real_corpus_cost.py --input-file data/prompts.txt --tokenizer tiktoken --model gpt-4o
  python tools/rstf_real_corpus_cost.py --input-file data/prompts.txt --compressor zlib --include-examples
"""

from __future__ import annotations

import argparse
import json
import sys
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "api"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

try:
    from api.semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint
except Exception:
    from semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint  # type: ignore

from rstf_token_cost import utf8_byte_length

try:
    from rstf_tiktoken_cost import get_tiktoken_encoding
except Exception:  # pragma: no cover - optional dependency path
    get_tiktoken_encoding = None  # type: ignore[assignment]

try:
    import zstandard as zstd  # type: ignore
except Exception:  # pragma: no cover - optional dependency path
    zstd = None  # type: ignore[assignment]

REPORT_VERSION = "rstf-real-corpus-cost-v0.2"
REPORT_TRUTH_LABEL = "non_synthetic_real_input_rtf_scan_not_generated_attack_corpus"
COMPRESSION_TRUTH_LABEL = "lossless_ram_compression_ab_probe_not_os_memory_compressor_exact_model"


@dataclass
class TextRecord:
    source_id: str
    text: str


def iter_text_file(path: Path) -> Iterable[TextRecord]:
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        text = line.strip("\n")
        if text.strip():
            yield TextRecord(source_id=f"{path}:{line_no}", text=text)


def iter_jsonl_file(path: Path, text_field: str) -> Iterable[TextRecord]:
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        text = str(obj.get(text_field, ""))
        if text.strip():
            source_id = str(obj.get("id") or obj.get("source_id") or f"{path}:{line_no}")
            yield TextRecord(source_id=source_id, text=text)


def iter_input_records(input_file: Path | None, input_dir: Path | None, glob_pattern: str, text_field: str) -> list[TextRecord]:
    records: list[TextRecord] = []
    if input_file is not None:
        if input_file.suffix.lower() == ".jsonl":
            records.extend(iter_jsonl_file(input_file, text_field=text_field))
        else:
            records.extend(iter_text_file(input_file))
    if input_dir is not None:
        for path in sorted(input_dir.rglob(glob_pattern)):
            if path.is_file():
                records.extend(iter_text_file(path))
    return records


def token_counter(tokenizer: str, model: str | None, encoding_name: str):
    if tokenizer == "bytes":
        return utf8_byte_length, "utf8_byte_length", "utf8_byte_count_not_tokenizer"
    if tokenizer == "tiktoken":
        if get_tiktoken_encoding is None:
            raise RuntimeError("tiktoken helper unavailable; install tiktoken or use --tokenizer bytes")
        encoding = get_tiktoken_encoding(model=model, encoding_name=encoding_name)
        resolved = getattr(encoding, "name", encoding_name)
        return (lambda text: len(encoding.encode(text))), f"tiktoken:{resolved}", "real_tiktoken_count_for_selected_model_or_encoding_not_provider_bill"
    raise ValueError(f"Unknown tokenizer: {tokenizer}")


def compressor_fn(compressor: str):
    if compressor == "none":
        return (lambda data: data), "none"
    if compressor == "zlib":
        return (lambda data: zlib.compress(data, level=6)), "zlib_level_6"
    if compressor == "zstd":
        if zstd is None:
            raise RuntimeError("zstandard package unavailable; install zstandard or use --compressor zlib")
        zstd_compressor = zstd.ZstdCompressor(level=3)
        return zstd_compressor.compress, "zstd_level_3"
    raise ValueError(f"Unknown compressor: {compressor}")


def transform_names(receipt: dict[str, Any]) -> list[str]:
    names: list[str] = []
    if receipt.get("bidi_override"):
        names.append("bidi_override")
    if receipt.get("upside_down"):
        names.append("upside_down")
    if receipt.get("reversed"):
        names.append("reversed")
    if receipt.get("homoglyph_substitution"):
        names.append("homoglyph")
    return names or ["none"]


def compact_receipt(fp: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_hash": fp["raw_hash"],
        "canonical_hash": fp["canonical_hash"],
        "transform_receipt": fp["transform_receipt"],
        "lossless": fp["lossless"],
        "truth_label": fp["truth_label"],
    }


def utf8_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def ratio(saved: int, base: int) -> float:
    return round(saved / base, 4) if base else 0.0


def scan_records(
    records: list[TextRecord],
    tokenizer: str,
    model: str | None,
    encoding_name: str,
    include_examples: bool,
    compressor: str = "zlib",
) -> dict[str, Any]:
    count_fn, metric_name, metric_truth_label = token_counter(tokenizer, model, encoding_name)
    compress, compressor_resolved = compressor_fn(compressor)

    total_raw_units = 0
    total_canonical_units = 0
    transformed_raw_units = 0
    transformed_canonical_units = 0
    transformed_count = 0
    per_transform: dict[str, dict[str, Any]] = {}
    examples: list[dict[str, Any]] = []

    raw_utf8_bytes_total = 0
    canonical_utf8_bytes_total = 0
    receipt_json_bytes_total = 0
    compressed_raw_bytes_total = 0
    compressed_canonical_bytes_total = 0
    compressed_canonical_plus_receipt_bytes_total = 0

    for record in records:
        fp = compute_fingerprint(record.text)
        canonical = fp["canonical_text"]
        receipt = compact_receipt(fp)
        receipt_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")

        raw_bytes = utf8_bytes(record.text)
        canonical_bytes = utf8_bytes(canonical)
        canonical_plus_receipt_bytes = canonical_bytes + b"\n" + receipt_bytes

        raw_utf8_bytes_total += len(raw_bytes)
        canonical_utf8_bytes_total += len(canonical_bytes)
        receipt_json_bytes_total += len(receipt_bytes)
        compressed_raw_bytes_total += len(compress(raw_bytes))
        compressed_canonical_bytes_total += len(compress(canonical_bytes))
        compressed_canonical_plus_receipt_bytes_total += len(compress(canonical_plus_receipt_bytes))

        raw_units = count_fn(record.text)
        canonical_units = count_fn(canonical)
        delta = raw_units - canonical_units

        total_raw_units += raw_units
        total_canonical_units += canonical_units

        detected = bool(fp["transform_detected"])
        names = transform_names(fp["transform_receipt"])
        if detected:
            transformed_count += 1
            transformed_raw_units += raw_units
            transformed_canonical_units += canonical_units
            for name in names:
                if name == "none":
                    continue
                bucket = per_transform.setdefault(name, {"count": 0, "raw_units": 0, "canonical_units": 0})
                bucket["count"] += 1
                bucket["raw_units"] += raw_units
                bucket["canonical_units"] += canonical_units

        if include_examples and detected:
            examples.append({
                "source_id": record.source_id,
                "transforms": [n for n in names if n != "none"],
                "raw_units": raw_units,
                "canonical_units": canonical_units,
                "units_saved": delta,
                "savings_ratio": ratio(delta, raw_units),
                "raw_utf8_bytes": len(raw_bytes),
                "canonical_utf8_bytes": len(canonical_bytes),
                "receipt_json_bytes": len(receipt_bytes),
                "compressed_raw_bytes": len(compress(raw_bytes)),
                "compressed_canonical_bytes": len(compress(canonical_bytes)),
                "compressed_canonical_plus_receipt_bytes": len(compress(canonical_plus_receipt_bytes)),
                "raw_preview": record.text[:160],
                "canonical_preview": canonical[:160],
                "truth_label": fp["truth_label"],
            })

    for stats in per_transform.values():
        raw = stats["raw_units"]
        canonical = stats["canonical_units"]
        stats["units_saved"] = raw - canonical
        stats["savings_ratio"] = ratio(raw - canonical, raw)

    total_saved = total_raw_units - total_canonical_units
    transformed_saved = transformed_raw_units - transformed_canonical_units
    total_count = len(records)
    utf8_saved = raw_utf8_bytes_total - canonical_utf8_bytes_total
    compressed_hot_saved = compressed_raw_bytes_total - compressed_canonical_bytes_total
    compressed_audit_delta = compressed_raw_bytes_total - compressed_canonical_plus_receipt_bytes_total
    return {
        "report_type": "RSTF Real Corpus Cost Scan",
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint_version": FINGERPRINT_VERSION,
        "metric": metric_name,
        "metric_truth_label": metric_truth_label,
        "overall": {
            "records_scanned": total_count,
            "records_with_transform_detected": transformed_count,
            "transform_prevalence_ratio": round(transformed_count / total_count, 4) if total_count else 0.0,
            "raw_units_total": total_raw_units,
            "canonical_units_total": total_canonical_units,
            "units_saved_total": total_saved,
            "overall_savings_ratio": ratio(total_saved, total_raw_units),
        },
        "transformed_only": {
            "records": transformed_count,
            "raw_units_total": transformed_raw_units,
            "canonical_units_total": transformed_canonical_units,
            "units_saved_total": transformed_saved,
            "savings_ratio": ratio(transformed_saved, transformed_raw_units),
        },
        "ram_compression": {
            "compressor": compressor_resolved,
            "raw_utf8_bytes": raw_utf8_bytes_total,
            "canonical_utf8_bytes": canonical_utf8_bytes_total,
            "utf8_bytes_saved": utf8_saved,
            "utf8_savings_ratio": ratio(utf8_saved, raw_utf8_bytes_total),
            "receipt_json_bytes": receipt_json_bytes_total,
            "compressed_raw_bytes": compressed_raw_bytes_total,
            "compressed_canonical_bytes": compressed_canonical_bytes_total,
            "compressed_canonical_plus_receipt_bytes": compressed_canonical_plus_receipt_bytes_total,
            "hot_path_compressed_bytes_saved": compressed_hot_saved,
            "hot_path_compressed_savings_ratio": ratio(compressed_hot_saved, compressed_raw_bytes_total),
            "audit_path_compressed_delta_bytes": compressed_audit_delta,
            "audit_path_compressed_delta_ratio": ratio(compressed_audit_delta, compressed_raw_bytes_total),
            "hot_path_policy": "canonical_text_only",
            "audit_path_policy": "canonical_text_plus_compact_receipt_raw_text_cold_storage_if_required",
            "truth_label": COMPRESSION_TRUTH_LABEL,
        },
        "per_transform": per_transform,
        "examples": examples,
        "truth_label": REPORT_TRUTH_LABEL,
        "scope_note": (
            "This scan uses real input records as-is. It does not generate attack examples. "
            "Low or zero savings on clean corpora is expected and should be interpreted as low observed prevalence, not detector failure. "
            "RAM compression metrics are an A/B probe using the selected lossless compressor, not an exact model of any OS memory compressor."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    ram = report["ram_compression"]
    lines = [
        f"# {report['report_type']}",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Metric: `{report['metric']}`",
        f"Truth label: `{report['truth_label']}`",
        "",
        "## Overall",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Records scanned | {report['overall']['records_scanned']} |",
        f"| Records with transform detected | {report['overall']['records_with_transform_detected']} |",
        f"| Transform prevalence | {report['overall']['transform_prevalence_ratio']:.2%} |",
        f"| Raw units | {report['overall']['raw_units_total']} |",
        f"| Canonical units | {report['overall']['canonical_units_total']} |",
        f"| Units saved | {report['overall']['units_saved_total']} |",
        f"| Overall savings ratio | {report['overall']['overall_savings_ratio']:.2%} |",
        "",
        "## RAM compression A/B",
        "",
        f"Compressor: `{ram['compressor']}`",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Raw UTF-8 bytes | {ram['raw_utf8_bytes']} |",
        f"| Canonical UTF-8 bytes | {ram['canonical_utf8_bytes']} |",
        f"| UTF-8 bytes saved | {ram['utf8_bytes_saved']} |",
        f"| UTF-8 savings ratio | {ram['utf8_savings_ratio']:.2%} |",
        f"| Receipt JSON bytes | {ram['receipt_json_bytes']} |",
        f"| Compressed raw bytes | {ram['compressed_raw_bytes']} |",
        f"| Compressed canonical bytes | {ram['compressed_canonical_bytes']} |",
        f"| Compressed canonical+receipt bytes | {ram['compressed_canonical_plus_receipt_bytes']} |",
        f"| Hot-path compressed bytes saved | {ram['hot_path_compressed_bytes_saved']} |",
        f"| Hot-path compressed savings ratio | {ram['hot_path_compressed_savings_ratio']:.2%} |",
        f"| Audit-path compressed delta bytes | {ram['audit_path_compressed_delta_bytes']} |",
        f"| Audit-path compressed delta ratio | {ram['audit_path_compressed_delta_ratio']:.2%} |",
        "",
        "## Transformed records only",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Records | {report['transformed_only']['records']} |",
        f"| Units saved | {report['transformed_only']['units_saved_total']} |",
        f"| Savings ratio | {report['transformed_only']['savings_ratio']:.2%} |",
        "",
        "## Per transform",
        "",
        "| Transform | Count | Raw units | Canonical units | Units saved | Savings ratio |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, stats in sorted(report["per_transform"].items()):
        lines.append(
            f"| `{name}` | {stats['count']} | {stats['raw_units']} | {stats['canonical_units']} | "
            f"{stats['units_saved']} | {stats['savings_ratio']:.2%} |"
        )
    lines += ["", "## Scope", "", report["scope_note"], ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a non-synthetic corpus with RSTF")
    parser.add_argument("--input-file", type=Path, default=None, help="Text or JSONL input file")
    parser.add_argument("--input-dir", type=Path, default=None, help="Directory of text files to scan")
    parser.add_argument("--glob", default="*.md", help="Glob for --input-dir, default *.md")
    parser.add_argument("--text-field", default="text", help="JSONL field containing text")
    parser.add_argument("--tokenizer", choices=["bytes", "tiktoken"], default="bytes")
    parser.add_argument("--model", default=None, help="Model for tiktoken.encoding_for_model")
    parser.add_argument("--encoding", default="cl100k_base", help="Fallback tiktoken encoding")
    parser.add_argument("--compressor", choices=["none", "zlib", "zstd"], default="zlib", help="Lossless compressor for RAM/storage A/B metrics")
    parser.add_argument("--include-examples", action="store_true", help="Include detected example previews")
    parser.add_argument("--out", default="benchmark/rstf/real_corpus_cost_report.json")
    parser.add_argument("--out-md", default="benchmark/rstf/real_corpus_cost_report.md")
    args = parser.parse_args()

    if args.input_file is None and args.input_dir is None:
        raise SystemExit("Provide --input-file or --input-dir")

    records = iter_input_records(args.input_file, args.input_dir, args.glob, args.text_field)
    report = scan_records(
        records=records,
        tokenizer=args.tokenizer,
        model=args.model,
        encoding_name=args.encoding,
        include_examples=args.include_examples,
        compressor=args.compressor,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(report), encoding="utf-8")

    summary = {k: v for k, v in report.items() if k != "examples"}
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
