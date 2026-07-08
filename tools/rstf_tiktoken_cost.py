#!/usr/bin/env python3
"""RSTF token-cost benchmark using OpenAI's tiktoken package.

This complements the existing RSTF cost tools:

- tools/rstf_token_cost.py: offline UTF-8 byte upper-bound proxy when real
  tokenizers are unavailable.
- tools/rstf_bpe_token_cost.py: real token counts under OverLLM's small,
  repo-trained BPE tokenizer.
- this file: real tiktoken counts for a selected OpenAI model or encoding when
  tiktoken is installed and its encoding data is available.

Scope honesty: tiktoken counts are real tokenizer counts for the selected
OpenAI model/encoding, not a universal provider bill. Actual API cost depends
on current provider pricing, model, request mode, cached-input treatment,
output tokens, tools, batching, and other deployment details. Cost estimation
therefore uses caller-supplied per-1M-token input pricing and is truth-labeled
as user-supplied pricing.

Usage:

  python tools/rstf_tiktoken_cost.py --summary-only
  python tools/rstf_tiktoken_cost.py --model gpt-4o-mini
  python tools/rstf_tiktoken_cost.py --encoding cl100k_base
  python tools/rstf_tiktoken_cost.py --input-price-per-1m 0.15 --out-md benchmark/rstf/tiktoken_cost_report.md
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
    import tiktoken
except Exception as exc:  # pragma: no cover - exercised only when dependency is absent
    tiktoken = None  # type: ignore[assignment]
    TIKTOKEN_IMPORT_ERROR = exc
else:
    TIKTOKEN_IMPORT_ERROR = None

try:
    from api.semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint
except Exception:
    from semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint  # type: ignore

try:
    from tools.rstf_benchmark import CORPUS_PATH, _generate_examples
except Exception:
    from rstf_benchmark import CORPUS_PATH, _generate_examples  # type: ignore

REPORT_VERSION = "rstf-tiktoken-cost-v0.1"
DEFAULT_ENCODING = "cl100k_base"


def get_tiktoken_encoding(model: str | None = None, encoding_name: str = DEFAULT_ENCODING):
    """Return a tiktoken encoding for the selected model or fallback encoding."""
    if tiktoken is None:
        raise RuntimeError(
            "tiktoken is not installed or could not be imported. "
            "Install it with `pip install tiktoken`, or use tools/rstf_token_cost.py "
            "for the offline UTF-8 byte proxy."
        ) from TIKTOKEN_IMPORT_ERROR

    if model:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            # Some new/unknown model names may not be mapped by the installed
            # tiktoken version. Fallback is explicit and recorded in the report.
            pass
    return tiktoken.get_encoding(encoding_name)


def estimate_input_cost_savings(tokens_saved: int, input_price_per_1m: float | None) -> dict[str, Any]:
    if input_price_per_1m is None:
        return {
            "tokens_saved": tokens_saved,
            "input_price_per_1m_tokens": None,
            "input_cost_saved_usd": None,
            "truth_label": "no_price_supplied_no_cost_claim",
        }
    return {
        "tokens_saved": tokens_saved,
        "input_price_per_1m_tokens": input_price_per_1m,
        "input_cost_saved_usd": round((tokens_saved / 1_000_000) * input_price_per_1m, 8),
        "truth_label": "user_supplied_price_not_live_provider_pricing",
    }


def run_tiktoken_cost_benchmark(
    model: str | None = None,
    encoding_name: str = DEFAULT_ENCODING,
    input_price_per_1m: float | None = None,
) -> dict[str, Any]:
    encoding = get_tiktoken_encoding(model=model, encoding_name=encoding_name)
    resolved_encoding = getattr(encoding, "name", encoding_name)

    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    examples = _generate_examples(corpus["sentences"])

    per_transform: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for example in examples:
        transform = example["transform"]
        raw_text = example["transformed_text"]
        fp = compute_fingerprint(raw_text)
        canonical_text = fp["canonical_text"]

        raw_tokens = len(encoding.encode(raw_text))
        canonical_tokens = len(encoding.encode(canonical_text))
        tokens_saved = raw_tokens - canonical_tokens

        bucket = per_transform.setdefault(transform, {
            "count": 0,
            "raw_tokens": 0,
            "canonical_tokens": 0,
        })
        bucket["count"] += 1
        bucket["raw_tokens"] += raw_tokens
        bucket["canonical_tokens"] += canonical_tokens

        results.append({
            "source_id": example["source_id"],
            "transform": transform,
            "raw_tokens": raw_tokens,
            "canonical_tokens": canonical_tokens,
            "tokens_saved": tokens_saved,
            "token_savings_ratio": round(tokens_saved / raw_tokens, 4) if raw_tokens else 0.0,
        })

    summary: dict[str, dict[str, Any]] = {}
    for transform, bucket in per_transform.items():
        raw_total = bucket["raw_tokens"]
        canonical_total = bucket["canonical_tokens"]
        summary[transform] = {
            "count": bucket["count"],
            "raw_tokens_total": raw_total,
            "canonical_tokens_total": canonical_total,
            "token_savings_ratio": round((raw_total - canonical_total) / raw_total, 4) if raw_total else 0.0,
        }

    raw_grand_total = sum(r["raw_tokens"] for r in results)
    canonical_grand_total = sum(r["canonical_tokens"] for r in results)
    total_tokens_saved = raw_grand_total - canonical_grand_total
    overall = {
        "count": len(results),
        "raw_tokens_total": raw_grand_total,
        "canonical_tokens_total": canonical_grand_total,
        "tokens_saved_total": total_tokens_saved,
        "token_savings_ratio": round(total_tokens_saved / raw_grand_total, 4) if raw_grand_total else 0.0,
    }

    return {
        "report_version": REPORT_VERSION,
        "fingerprint_version": FINGERPRINT_VERSION,
        "metric": "tiktoken_token_count",
        "model_requested": model,
        "encoding_requested": encoding_name,
        "encoding_resolved": resolved_encoding,
        "metric_note": (
            "Real token counts from OpenAI's tiktoken package for the selected "
            "model or encoding. These counts are tokenizer-specific and are not "
            "a universal provider bill. Use the exact production model/encoding "
            "and current provider pricing before making a cost claim."
        ),
        "overall": overall,
        "per_transform": summary,
        "examples": results,
        "cost_estimate": estimate_input_cost_savings(total_tokens_saved, input_price_per_1m),
        "truth_label": "real_tiktoken_count_for_selected_model_or_encoding_not_provider_bill",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# RSTF tiktoken token-cost report ({report['report_version']})",
        "",
        f"Fingerprint version: `{report['fingerprint_version']}` | "
        f"Requested model: `{report['model_requested']}` | "
        f"Resolved encoding: `{report['encoding_resolved']}`",
        "",
        f"**Metric: `{report['metric']}`.** {report['metric_note']}",
        "",
        "## Overall",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Examples | {report['overall']['count']} |",
        f"| Raw tokens (total) | {report['overall']['raw_tokens_total']} |",
        f"| Canonical tokens (total) | {report['overall']['canonical_tokens_total']} |",
        f"| Tokens saved (total) | {report['overall']['tokens_saved_total']} |",
        f"| Token savings ratio | {report['overall']['token_savings_ratio']:.1%} |",
        "",
        "## Cost estimate",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Input price per 1M tokens | {report['cost_estimate']['input_price_per_1m_tokens']} |",
        f"| Estimated input cost saved (USD) | {report['cost_estimate']['input_cost_saved_usd']} |",
        f"| Cost truth label | `{report['cost_estimate']['truth_label']}` |",
        "",
        "## Per-transform",
        "",
        "| Transform | Count | Raw tokens | Canonical tokens | Token savings ratio |",
        "|---|---|---|---|---|",
    ]
    for transform, stats in sorted(report["per_transform"].items()):
        lines.append(
            f"| `{transform}` | {stats['count']} | {stats['raw_tokens_total']} "
            f"| {stats['canonical_tokens_total']} | {stats['token_savings_ratio']:.1%} |"
        )
    lines += [
        "",
        "Truth label: " + f"`{report['truth_label']}`",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RSTF tiktoken token-cost benchmark")
    parser.add_argument("--model", default=None, help="OpenAI model name for tiktoken.encoding_for_model")
    parser.add_argument("--encoding", default=DEFAULT_ENCODING, help="Fallback tiktoken encoding name")
    parser.add_argument("--input-price-per-1m", type=float, default=None, help="Caller-supplied input price per 1M tokens")
    parser.add_argument("--out", help="Write the full JSON report to this path")
    parser.add_argument("--out-md", help="Write a human-readable Markdown report to this path")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = run_tiktoken_cost_benchmark(
        model=args.model,
        encoding_name=args.encoding,
        input_price_per_1m=args.input_price_per_1m,
    )

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(render_markdown(report), encoding="utf-8")

    if args.summary_only:
        report = {k: v for k, v in report.items() if k != "examples"}

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
