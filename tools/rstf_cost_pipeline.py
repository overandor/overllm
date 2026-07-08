#!/usr/bin/env python3
"""Run the full RSTF comparative cost pipeline.

This pipeline combines the three RSTF cost views into one reproducible report:

1. UTF-8 byte upper-bound proxy (`tools/rstf_token_cost.py`).
2. OverLLM's repo-trained BPE tokenizer (`tools/rstf_bpe_token_cost.py`).
3. OpenAI tiktoken model/encoding-specific counts (`tools/rstf_tiktoken_cost.py`).

The report is intentionally truth-labeled. It demonstrates tokenizer-aware cost
observability on the synthetic RSTF corpus; it does not guarantee savings on
arbitrary production traffic or final provider invoices.

Usage:

  python tools/rstf_cost_pipeline.py
  python tools/rstf_cost_pipeline.py --out benchmark/rstf/comparative_cost_report.json --out-md benchmark/rstf/comparative_cost_report.md
  python tools/rstf_cost_pipeline.py --tiktoken-model gpt-4o --price gpt-4o=2.50 --price gpt-4o-mini=0.15
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from rstf_bpe_token_cost import DEFAULT_VOCAB_DIR, run_bpe_token_cost_benchmark
from rstf_token_cost import run_token_cost_benchmark
from rstf_tiktoken_cost import run_tiktoken_cost_benchmark

REPORT_VERSION = "rstf-comparative-cost-v0.1"
REPORT_TRUTH_LABEL = "synthetic_rstf_corpus_multi_tokenizer_cost_observability_not_production_traffic_guarantee"
DEFAULT_TIKTOKEN_MODELS = ["gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "benchmark" / "rstf" / "comparative_cost_report.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "benchmark" / "rstf" / "comparative_cost_report.md"


def parse_price_args(values: list[str]) -> dict[str, float]:
    prices: dict[str, float] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --price value {value!r}; expected model=price_per_1m")
        model, price_text = value.split("=", 1)
        model = model.strip()
        if not model:
            raise ValueError(f"Invalid --price value {value!r}; missing model name")
        prices[model] = float(price_text)
    return prices


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def summarize_tiktoken(report: dict[str, Any]) -> dict[str, Any]:
    overall = report["overall"]
    cost = report.get("cost_estimate", {})
    model = report.get("model_requested") or report.get("encoding_resolved")
    return {
        "model": model,
        "tokenizer": f"tiktoken ({report['encoding_resolved']})",
        "raw_tokens": overall["raw_tokens_total"],
        "canonical_tokens": overall["canonical_tokens_total"],
        "tokens_saved": overall["tokens_saved_total"],
        "savings_ratio": overall["token_savings_ratio"],
        "savings_percent": pct(overall["token_savings_ratio"]),
        "estimated_cost_saved_usd": cost.get("input_cost_saved_usd"),
        "pricing_per_1m_tokens": cost.get("input_price_per_1m_tokens"),
        "pricing_source": cost.get("truth_label"),
        "truth_label": report["truth_label"],
    }


def summarize_byte_proxy(report: dict[str, Any]) -> dict[str, Any]:
    overall = report["overall"]
    return {
        "model": "Tokenizer unavailable/offline fallback",
        "tokenizer": "UTF-8 byte length upper-bound proxy",
        "raw_bytes": overall["raw_bytes_total"],
        "canonical_bytes": overall["canonical_bytes_total"],
        "bytes_saved": overall["raw_bytes_total"] - overall["canonical_bytes_total"],
        "savings_ratio": overall["byte_savings_ratio"],
        "savings_percent": pct(overall["byte_savings_ratio"]),
        "note": "Offline byte-length reduction proxy, not a model-specific token count.",
        "truth_label": report["truth_label"],
    }


def summarize_bpe(report: dict[str, Any]) -> dict[str, Any]:
    overall = report["overall"]
    return {
        "model": "OverLLM BPE reference implementation",
        "tokenizer": "OverLLM BPE small repo-trained vocab",
        "raw_tokens": overall["raw_tokens_total"],
        "canonical_tokens": overall["canonical_tokens_total"],
        "tokens_saved": overall["raw_tokens_total"] - overall["canonical_tokens_total"],
        "savings_ratio": overall["token_savings_ratio"],
        "savings_percent": pct(overall["token_savings_ratio"]),
        "vocab_size": report.get("tokenizer_vocab_size"),
        "merge_count": report.get("tokenizer_merge_count"),
        "note": "Real local BPE tokenizer measurement, not production-provider billing.",
        "truth_label": report["truth_label"],
    }


def transform_breakdown(
    byte_report: dict[str, Any],
    bpe_report: dict[str, Any],
    tiktoken_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    transforms = sorted(byte_report["per_transform"].keys())
    out: dict[str, Any] = {}
    for transform in transforms:
        tiktok_values = [r["per_transform"][transform]["token_savings_ratio"] for r in tiktoken_reports]
        out[transform] = {
            "byte_proxy_savings": pct(byte_report["per_transform"][transform]["byte_savings_ratio"]),
            "bpe_savings": pct(bpe_report["per_transform"][transform]["token_savings_ratio"]),
            "tiktoken_savings_min": pct(min(tiktok_values)),
            "tiktoken_savings_max": pct(max(tiktok_values)),
            "tiktoken_savings_range": f"{pct(min(tiktok_values))}-{pct(max(tiktok_values))}",
        }
    return out


def build_key_findings(report: dict[str, Any]) -> list[str]:
    tiktoken_models = [m for m in report["models_tested"] if str(m.get("tokenizer", "")).startswith("tiktoken")]
    tiktok_min = min(m["savings_ratio"] for m in tiktoken_models)
    tiktok_max = max(m["savings_ratio"] for m in tiktoken_models)
    byte_model = next(m for m in report["models_tested"] if m["tokenizer"].startswith("UTF-8"))
    bpe_model = next(m for m in report["models_tested"] if m["model"].startswith("OverLLM BPE"))
    return [
        (
            "On the synthetic 160-example RSTF corpus, selected tiktoken encodings "
            f"show {pct(tiktok_min)}-{pct(tiktok_max)} input-token reduction after canonicalization."
        ),
        (
            "The OverLLM repo-trained BPE reference shows "
            f"{bpe_model['savings_percent']} token reduction; this is a real local tokenizer result, not production-provider billing."
        ),
        (
            "The UTF-8 byte view shows "
            f"{byte_model['savings_percent']} byte-length reduction; this is an offline upper-bound proxy, not exact tokenization."
        ),
        "Upside-down and homoglyph transforms produce the largest reductions because multi-byte/rare glyphs collapse to ordinary canonical text.",
        "Reversed text shows token savings for real tokenizers even though byte length is unchanged, because BPE merges are learned from forward-reading text.",
        "Cost estimates are calculated only when caller-supplied per-1M-token input pricing is provided.",
    ]


def run_pipeline(
    tiktoken_models: list[str],
    prices_per_1m: dict[str, float],
    vocab_dir: Path,
) -> dict[str, Any]:
    byte_report = run_token_cost_benchmark()
    bpe_report = run_bpe_token_cost_benchmark(vocab_dir)
    tiktoken_reports = [
        run_tiktoken_cost_benchmark(
            model=model,
            input_price_per_1m=prices_per_1m.get(model),
        )
        for model in tiktoken_models
    ]

    models_tested = [summarize_tiktoken(r) for r in tiktoken_reports]
    models_tested.append(summarize_byte_proxy(byte_report))
    models_tested.append(summarize_bpe(bpe_report))

    report = {
        "report_type": "RSTF Cost Reduction Comparison",
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_corpus": "160 synthetic RSTF adversarial examples (reversed, upside_down, homoglyph, bidi_override)",
        "models_tested": models_tested,
        "transform_breakdown": transform_breakdown(byte_report, bpe_report, tiktoken_reports),
        "truth_labels": {
            "report": REPORT_TRUTH_LABEL,
            "tiktoken": "real_tiktoken_count_for_selected_model_or_encoding_not_provider_bill",
            "byte_proxy": byte_report["truth_label"],
            "bpe": bpe_report["truth_label"],
        },
        "pricing_disclaimer": (
            "Cost estimates use caller-supplied pricing, not live provider pricing. "
            "Actual bills depend on cached input, output tokens, tools usage, batching mode, priority mode, and current provider pricing tables."
        ),
        "production_disclaimer": (
            "These results demonstrate tokenizer-aware cost observability on a synthetic RSTF corpus. "
            "They do not guarantee savings on arbitrary production traffic."
        ),
    }
    report["key_findings"] = build_key_findings(report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['report_type']}",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Truth label: `{report['truth_labels']['report']}`",
        "",
        f"Corpus: {report['test_corpus']}",
        "",
        "## Key findings",
        "",
    ]
    for finding in report["key_findings"]:
        lines.append(f"- {finding}")

    lines += [
        "",
        "## Models tested",
        "",
        "| Model | Tokenizer | Raw | Canonical | Saved | Savings | Cost saved | Truth label |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for model in report["models_tested"]:
        raw = model.get("raw_tokens", model.get("raw_bytes"))
        canonical = model.get("canonical_tokens", model.get("canonical_bytes"))
        saved = model.get("tokens_saved", model.get("bytes_saved"))
        cost = model.get("estimated_cost_saved_usd")
        cost_text = "" if cost is None else f"${cost:.8f}"
        lines.append(
            f"| {model['model']} | {model['tokenizer']} | {raw} | {canonical} | {saved} | "
            f"{model['savings_percent']} | {cost_text} | `{model['truth_label']}` |"
        )

    lines += [
        "",
        "## Transform breakdown",
        "",
        "| Transform | Byte proxy | OverLLM BPE | tiktoken range |",
        "|---|---:|---:|---:|",
    ]
    for transform, stats in sorted(report["transform_breakdown"].items()):
        lines.append(
            f"| `{transform}` | {stats['byte_proxy_savings']} | {stats['bpe_savings']} | {stats['tiktoken_savings_range']} |"
        )

    lines += [
        "",
        "## Disclaimers",
        "",
        report["pricing_disclaimer"],
        "",
        report["production_disclaimer"],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full RSTF comparative cost pipeline")
    parser.add_argument("--tiktoken-model", action="append", dest="tiktoken_models", default=[], help="Model to benchmark; repeatable")
    parser.add_argument("--price", action="append", default=[], help="Caller-supplied input price per 1M tokens, format model=price")
    parser.add_argument("--vocab-dir", default=str(DEFAULT_VOCAB_DIR), help="OverLLM BPE tokenizer data directory")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT_JSON), help="Write comparative JSON report")
    parser.add_argument("--out-md", default=str(DEFAULT_OUTPUT_MD), help="Write comparative Markdown report")
    parser.add_argument("--summary-only", action="store_true", help="Print report without per-example nested data")
    args = parser.parse_args()

    models = args.tiktoken_models or DEFAULT_TIKTOKEN_MODELS
    report = run_pipeline(
        tiktoken_models=models,
        prices_per_1m=parse_price_args(args.price),
        vocab_dir=Path(args.vocab_dir),
    )

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(render_markdown(report), encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
