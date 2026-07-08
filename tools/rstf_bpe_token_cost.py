#!/usr/bin/env python3
"""RSTF token-cost benchmark using OverLLM's real, trained BPE tokenizer.

tools/rstf_token_cost.py measures UTF-8 byte length as a proxy, because no
production tokenizer (tiktoken, Hugging Face) is reachable from this
environment's network policy. This script instead uses OverLLM's own
tokenizer (tools/bpe_tokenizer.py, trained on this repo's own docs, mirrored
in cpp/src/tokenizer.cpp and parity-checked by tools/bpe_parity_check.py) to
get real, measured token counts - not a proxy - for canonicalization's
effect on token count.

Important scope honesty: this measures OverLLM's own small, repo-trained
BPE tokenizer, not GPT-4/Claude/Llama's production tokenizer. Absolute
token counts here do not represent what a production API would bill.
What is real: the algorithm (byte-level BPE, the same technique those
tokenizers use) and the measurement (canonical text really does tokenize
to fewer tokens under this real, working tokenizer).

Usage:

  python tools/rstf_bpe_token_cost.py
  python tools/rstf_bpe_token_cost.py --out-md benchmark/rstf/bpe_token_cost_report.md
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

from bpe_tokenizer import BPETokenizer
from rstf_benchmark import CORPUS_PATH, _generate_examples

REPORT_VERSION = "rstf-bpe-token-cost-v0.1"
DEFAULT_VOCAB_DIR = REPO_ROOT / "cpp" / "tokenizer_data"


def run_bpe_token_cost_benchmark(vocab_dir: Path) -> dict[str, Any]:
    tokenizer = BPETokenizer.load(vocab_dir)
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    examples = _generate_examples(corpus["sentences"])

    per_transform: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for example in examples:
        transform = example["transform"]
        raw_text = example["transformed_text"]
        fp = compute_fingerprint(raw_text)
        canonical_text = fp["canonical_text"]

        raw_tokens = len(tokenizer.encode(raw_text))
        canonical_tokens = len(tokenizer.encode(canonical_text))
        tokens_saved = raw_tokens - canonical_tokens

        bucket = per_transform.setdefault(transform, {
            "count": 0, "raw_tokens": 0, "canonical_tokens": 0,
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

    summary = {}
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
    overall = {
        "count": len(results),
        "raw_tokens_total": raw_grand_total,
        "canonical_tokens_total": canonical_grand_total,
        "token_savings_ratio": round((raw_grand_total - canonical_grand_total) / raw_grand_total, 4) if raw_grand_total else 0.0,
    }

    return {
        "report_version": REPORT_VERSION,
        "fingerprint_version": FINGERPRINT_VERSION,
        "tokenizer_vocab_size": tokenizer.vocab and len(tokenizer.vocab),
        "tokenizer_merge_count": len(tokenizer.merge_rank),
        "metric": "overllm_bpe_token_count",
        "metric_note": (
            "Real token counts from OverLLM's own trained BPE tokenizer "
            "(tools/bpe_tokenizer.py, C++ mirror in cpp/src/tokenizer.cpp, "
            "parity-verified by tools/bpe_parity_check.py). This is OverLLM's "
            "own tokenizer trained on this repo's own docs (a few tens of KB), "
            "not GPT-4/Claude/Llama's production tokenizer - absolute counts "
            "do not represent production API billing, but the measurement "
            "method (a real, working byte-level BPE tokenizer) is genuine, "
            "not a byte-length proxy."
        ),
        "overall": overall,
        "per_transform": summary,
        "examples": results,
        "truth_label": "real_tokenizer_measurement_small_repo_trained_vocab_not_production_scale",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# RSTF real-BPE token-cost report ({report['report_version']})",
        "",
        f"Fingerprint version: `{report['fingerprint_version']}` | "
        f"Tokenizer vocab size: `{report['tokenizer_vocab_size']}` | "
        f"Merges: `{report['tokenizer_merge_count']}`",
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
        f"| Token savings ratio | {report['overall']['token_savings_ratio']:.1%} |",
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
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RSTF real-BPE token-cost benchmark")
    parser.add_argument("--vocab-dir", default=str(DEFAULT_VOCAB_DIR))
    parser.add_argument("--out", help="Write the full JSON report to this path")
    parser.add_argument("--out-md", help="Write a human-readable Markdown report to this path")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = run_bpe_token_cost_benchmark(Path(args.vocab_dir))

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(render_markdown(report), encoding="utf-8")

    if args.summary_only:
        report = {k: v for k, v in report.items() if k != "examples"}

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
