#!/usr/bin/env python3
"""RSTF byte-cost benchmark: measures the token-cost proxy savings from
canonicalizing transformed text before it reaches a tokenizer.

Why bytes, not tokens: this environment's egress policy blocks the hosts
tiktoken and Hugging Face tokenizers need to fetch vocabulary files from
(openaipublic.blob.core.windows.net, huggingface.co both return 403), so no
real tokenizer is available offline here. UTF-8 byte length is not a
approximation of convenience — it is a mathematically provable *upper bound*
on token count for every byte-level BPE tokenizer in production use (GPT-3.5,
GPT-4, Claude, Llama, and friends all use byte-level BPE with a byte-fallback
base vocabulary): a token is composed of one or more raw bytes, so
token_count <= byte_count always. Canonicalizing a rare multi-byte glyph into
its single-byte ASCII equivalent can only reduce or hold constant the token
count a real tokenizer would produce; this script reports that byte-level
floor honestly, as a floor, not as a claimed exact token count.

Usage:

  python tools/rstf_token_cost.py
  python tools/rstf_token_cost.py --out-md benchmark/rstf/token_cost_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "api"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

try:
    from api.semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint
except Exception:
    from semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint  # type: ignore

try:
    from tools.rstf_benchmark import _generate_examples, CORPUS_PATH
except Exception:
    from rstf_benchmark import _generate_examples, CORPUS_PATH  # type: ignore

REPORT_VERSION = "rstf-token-cost-v0.1"


def utf8_byte_length(text: str) -> int:
    return len(text.encode("utf-8"))


def run_token_cost_benchmark() -> dict[str, Any]:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    examples = _generate_examples(corpus["sentences"])

    per_transform: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for example in examples:
        transform = example["transform"]
        raw_text = example["transformed_text"]
        fp = compute_fingerprint(raw_text)
        canonical_text = fp["canonical_text"]

        raw_bytes = utf8_byte_length(raw_text)
        canonical_bytes = utf8_byte_length(canonical_text)
        bytes_saved = raw_bytes - canonical_bytes

        bucket = per_transform.setdefault(transform, {
            "count": 0, "raw_bytes": 0, "canonical_bytes": 0,
        })
        bucket["count"] += 1
        bucket["raw_bytes"] += raw_bytes
        bucket["canonical_bytes"] += canonical_bytes

        results.append({
            "source_id": example["source_id"],
            "transform": transform,
            "raw_bytes": raw_bytes,
            "canonical_bytes": canonical_bytes,
            "bytes_saved": bytes_saved,
            "byte_savings_ratio": round(bytes_saved / raw_bytes, 4) if raw_bytes else 0.0,
        })

    summary = {}
    for transform, bucket in per_transform.items():
        raw_total = bucket["raw_bytes"]
        canonical_total = bucket["canonical_bytes"]
        summary[transform] = {
            "count": bucket["count"],
            "raw_bytes_total": raw_total,
            "canonical_bytes_total": canonical_total,
            "byte_savings_ratio": round((raw_total - canonical_total) / raw_total, 4) if raw_total else 0.0,
        }

    raw_grand_total = sum(r["raw_bytes"] for r in results)
    canonical_grand_total = sum(r["canonical_bytes"] for r in results)
    overall = {
        "count": len(results),
        "raw_bytes_total": raw_grand_total,
        "canonical_bytes_total": canonical_grand_total,
        "byte_savings_ratio": round((raw_grand_total - canonical_grand_total) / raw_grand_total, 4) if raw_grand_total else 0.0,
    }

    return {
        "report_version": REPORT_VERSION,
        "fingerprint_version": FINGERPRINT_VERSION,
        "metric": "utf8_byte_length",
        "metric_note": (
            "UTF-8 byte length, not a real tokenizer count. It is a provable upper "
            "bound on token count for byte-level BPE tokenizers (a token is >=1 raw "
            "byte), computed offline because this environment's egress policy blocks "
            "the hosts tiktoken/Hugging Face tokenizers need (403 on "
            "openaipublic.blob.core.windows.net and huggingface.co)."
        ),
        "overall": overall,
        "per_transform": summary,
        "examples": results,
        "truth_label": "synthetic_examples_byte_proxy_not_real_tokenizer_counts",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# RSTF byte-cost report ({report['report_version']})",
        "",
        f"Fingerprint version: `{report['fingerprint_version']}`",
        "",
        f"**Metric: `{report['metric']}`.** {report['metric_note']}",
        "",
        "## Overall",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Examples | {report['overall']['count']} |",
        f"| Raw UTF-8 bytes (total) | {report['overall']['raw_bytes_total']} |",
        f"| Canonical UTF-8 bytes (total) | {report['overall']['canonical_bytes_total']} |",
        f"| Byte savings ratio | {report['overall']['byte_savings_ratio']:.1%} |",
        "",
        "## Per-transform",
        "",
        "| Transform | Count | Raw bytes | Canonical bytes | Byte savings ratio |",
        "|---|---|---|---|---|",
    ]
    for transform, stats in sorted(report["per_transform"].items()):
        lines.append(
            f"| `{transform}` | {stats['count']} | {stats['raw_bytes_total']} "
            f"| {stats['canonical_bytes_total']} | {stats['byte_savings_ratio']:.1%} |"
        )
    lines += [
        "",
        "Note: `reversed` is expected to show ~0% byte savings — reordering bytes "
        "doesn't change how many there are. The savings come entirely from "
        "`upside_down` (multi-byte rotation glyphs), `homoglyph` (multi-byte "
        "Cyrillic/Greek confusables), and `bidi_override` (stripped 3-byte bidi "
        "control characters) collapsing to single-byte ASCII.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RSTF byte-cost benchmark")
    parser.add_argument("--out", help="Write the full JSON report to this path")
    parser.add_argument("--out-md", help="Write a human-readable Markdown report to this path")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = run_token_cost_benchmark()

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(render_markdown(report), encoding="utf-8")

    if args.summary_only:
        report = {k: v for k, v in report.items() if k != "examples"}

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
