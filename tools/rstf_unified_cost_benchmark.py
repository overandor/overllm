#!/usr/bin/env python3
"""Unified RSTF cost benchmark runner for long-duration monitoring.

Runs all three RSTF cost views in a single execution:
- tools/rstf_token_cost.py: UTF-8 byte upper-bound proxy
- tools/rstf_bpe_token_cost.py: OverLLM BPE tokenizer
- tools/rstf_tiktoken_cost.py: OpenAI tiktoken for selected models

Supports continuous monitoring mode with configurable intervals for
long-duration testing and trend analysis.

Usage:

  # Single run, all cost views
  python tools/rstf_unified_cost_benchmark.py

  # Continuous monitoring every 60 seconds
  python tools/rstf_unified_cost_benchmark.py --continuous --interval 60

  # Continuous with specific GPT model and pricing
  python tools/rstf_unified_cost_benchmark.py --continuous --interval 300 \
    --model gpt-4o --input-price-per-1m 2.50

  # Run for specific duration then stop
  python tools/rstf_unified_cost_benchmark.py --continuous --interval 60 \
    --duration 3600
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "api"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

try:
    from api.semantic_fingerprint import FINGERPRINT_VERSION
except Exception:
    from semantic_fingerprint import FINGERPRINT_VERSION  # type: ignore

try:
    from tools.rstf_token_cost import run_token_cost_benchmark as run_byte_proxy
except Exception:
    from rstf_token_cost import run_token_cost_benchmark as run_byte_proxy  # type: ignore

try:
    from tools.rstf_bpe_token_cost import (
        DEFAULT_VOCAB_DIR,
        run_bpe_token_cost_benchmark as run_bpe,
    )
except Exception:
    from rstf_bpe_token_cost import (  # type: ignore
        DEFAULT_VOCAB_DIR,
        run_bpe_token_cost_benchmark as run_bpe,
    )

try:
    from tools.rstf_tiktoken_cost import run_tiktoken_cost_benchmark
    run_tiktoken = run_tiktoken_cost_benchmark
except Exception:
    try:
        from rstf_tiktoken_cost import run_tiktoken_cost_benchmark  # type: ignore
        run_tiktoken = run_tiktoken_cost_benchmark
    except Exception:
        run_tiktoken = None

REPORT_VERSION = "rstf-unified-cost-v0.1"


def run_unified_benchmark(
    model: str | None = None,
    encoding_name: str = "cl100k_base",
    input_price_per_1m: float | None = None,
) -> dict[str, Any]:
    """Run all three RSTF cost views and consolidate results."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Run byte proxy (always available)
    byte_report = run_byte_proxy()

    # Run BPE tokenizer (may fail if vocab missing)
    try:
        bpe_report = run_bpe(DEFAULT_VOCAB_DIR)
        bpe_status = "ok"
        bpe_error = None
    except Exception as e:
        bpe_report = None
        bpe_status = "failed"
        bpe_error = str(e)

    # Run tiktoken (may fail if tiktoken not installed)
    if run_tiktoken is None:
        tiktoken_report = None
        tiktoken_status = "unavailable"
        tiktoken_error = "tiktoken module not available"
    else:
        try:
            tiktoken_report = run_tiktoken(
                model=model,
                encoding_name=encoding_name,
                input_price_per_1m=input_price_per_1m,
            )
            tiktoken_status = "ok"
            tiktoken_error = None
        except Exception as e:
            tiktoken_report = None
            tiktoken_status = "failed"
            tiktoken_error = str(e)

    return {
        "report_version": REPORT_VERSION,
        "fingerprint_version": FINGERPRINT_VERSION,
        "timestamp": timestamp,
        "model_requested": model,
        "encoding_requested": encoding_name,
        "input_price_per_1m": input_price_per_1m,
        "byte_proxy": {
            "status": "ok",
            "report": byte_report,
        },
        "bpe_tokenizer": {
            "status": bpe_status,
            "error": bpe_error,
            "report": bpe_report,
        },
        "tiktoken": {
            "status": tiktoken_status,
            "error": tiktoken_error,
            "report": tiktoken_report,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# RSTF Unified Cost Benchmark ({report['report_version']})",
        "",
        f"Timestamp: `{report['timestamp']}`",
        f"Fingerprint version: `{report['fingerprint_version']}`",
        f"Model requested: `{report['model_requested']}`",
        f"Encoding requested: `{report['encoding_requested']}`",
        "",
        "## Byte Proxy (UTF-8)",
        "",
        f"Status: `{report['byte_proxy']['status']}`",
    ]

    if report["byte_proxy"]["report"]:
        br = report["byte_proxy"]["report"]
        lines.extend([
            f"| Metric | Value |",
            f"|---|---|",
            f"| Examples | {br['overall']['count']} |",
            f"| Raw bytes (total) | {br['overall']['raw_bytes_total']} |",
            f"| Canonical bytes (total) | {br['overall']['canonical_bytes_total']} |",
            f"| Byte savings ratio | {br['overall']['byte_savings_ratio']:.1%} |",
            "",
        ])

    lines.extend([
        "## BPE Tokenizer (OverLLM)",
        "",
        f"Status: `{report['bpe_tokenizer']['status']}`",
    ])

    if report["bpe_tokenizer"]["error"]:
        lines.append(f"Error: `{report['bpe_tokenizer']['error']}`")
    elif report["bpe_tokenizer"]["report"]:
        bpr = report["bpe_tokenizer"]["report"]
        lines.extend([
            f"| Metric | Value |",
            f"|---|---|",
            f"| Examples | {bpr['overall']['count']} |",
            f"| Raw tokens (total) | {bpr['overall']['raw_tokens_total']} |",
            f"| Canonical tokens (total) | {bpr['overall']['canonical_tokens_total']} |",
            f"| Token savings ratio | {bpr['overall']['token_savings_ratio']:.1%} |",
            f"| Vocab size | {bpr.get('tokenizer_vocab_size', 'N/A')} |",
            "",
        ])

    lines.extend([
        "## Tiktoken (OpenAI)",
        "",
        f"Status: `{report['tiktoken']['status']}`",
    ])

    if report["tiktoken"]["error"]:
        lines.append(f"Error: `{report['tiktoken']['error']}`")
    elif report["tiktoken"]["report"]:
        tr = report["tiktoken"]["report"]
        lines.extend([
            f"| Metric | Value |",
            f"|---|---|",
            f"| Examples | {tr['overall']['count']} |",
            f"| Raw tokens (total) | {tr['overall']['raw_tokens_total']} |",
            f"| Canonical tokens (total) | {tr['overall']['canonical_tokens_total']} |",
            f"| Token savings ratio | {tr['overall']['token_savings_ratio']:.1%} |",
            f"| Encoding resolved | `{tr.get('encoding_resolved', 'N/A')}` |",
        ])

        if tr.get("cost_estimate"):
            ce = tr["cost_estimate"]
            lines.extend([
                f"| Input price per 1M tokens | {ce.get('input_price_per_1m_tokens', 'N/A')} |",
                f"| Estimated cost saved (USD) | {ce.get('input_cost_saved_usd', 'N/A')} |",
                f"| Cost truth label | `{ce.get('truth_label', 'N/A')}` |",
            ])

    lines.append("")
    return "\n".join(lines) + "\n"


def run_continuous_monitoring(
    interval: int,
    duration: int | None = None,
    model: str | None = None,
    encoding_name: str = "cl100k_base",
    input_price_per_1m: float | None = None,
    output_dir: Path | None = None,
) -> None:
    """Run unified benchmark continuously at specified intervals."""
    start_time = time.time()
    run_count = 0

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting continuous RSTF cost monitoring (interval: {interval}s)")
    if duration:
        print(f"Will stop after {duration}s ({duration/60:.1f} minutes)")
    print("-" * 60)

    while True:
        run_count += 1
        elapsed = time.time() - start_time

        # Check duration limit
        if duration and elapsed >= duration:
            print(f"\nDuration limit reached ({duration}s). Stopping.")
            break

        print(f"\n[Run #{run_count}] Elapsed: {elapsed:.1f}s")
        print("-" * 60)

        try:
            report = run_unified_benchmark(
                model=model,
                encoding_name=encoding_name,
                input_price_per_1m=input_price_per_1m,
            )

            # Print summary
            print(f"Byte proxy: {report['byte_proxy']['status']}")
            if report["byte_proxy"]["report"]:
                br = report["byte_proxy"]["report"]["overall"]
                print(f"  Savings: {br['byte_savings_ratio']:.1%}")

            print(f"BPE tokenizer: {report['bpe_tokenizer']['status']}")
            if report["bpe_tokenizer"]["report"]:
                bpr = report["bpe_tokenizer"]["report"]["overall"]
                print(f"  Savings: {bpr['token_savings_ratio']:.1%}")

            print(f"Tiktoken: {report['tiktoken']['status']}")
            if report["tiktoken"]["report"]:
                tr = report["tiktoken"]["report"]["overall"]
                print(f"  Savings: {tr['token_savings_ratio']:.1%}")
                if report["tiktoken"]["report"].get("cost_estimate"):
                    ce = report["tiktoken"]["report"]["cost_estimate"]
                    if ce.get("input_cost_saved_usd"):
                        print(f"  Cost saved: ${ce['input_cost_saved_usd']:.6f}")

            # Save to file if output_dir specified
            if output_dir:
                timestamp_safe = report["timestamp"].replace(":", "-").replace(".", "-")
                output_file = output_dir / f"rstf_unified_{timestamp_safe}.json"
                output_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"Saved: {output_file}")

        except Exception as e:
            print(f"Error in run #{run_count}: {e}")

        # Wait for next interval
        sleep_time = max(0, interval - (time.time() - start_time - elapsed))
        if sleep_time > 0:
            time.sleep(sleep_time)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run unified RSTF cost benchmark (all three cost views)"
    )
    parser.add_argument("--model", help="OpenAI model name for tiktoken")
    parser.add_argument("--encoding", default="cl100k_base", help="tiktoken encoding name")
    parser.add_argument("--input-price-per-1m", type=float, help="Input price per 1M tokens")
    parser.add_argument("--out", help="Write JSON report to this path")
    parser.add_argument("--out-md", help="Write Markdown report to this path")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds (default: 60)")
    parser.add_argument("--duration", type=int, help="Stop after N seconds")
    parser.add_argument("--output-dir", help="Directory for continuous output files")
    args = parser.parse_args()

    if args.continuous:
        output_dir = Path(args.output_dir) if args.output_dir else None
        run_continuous_monitoring(
            interval=args.interval,
            duration=args.duration,
            model=args.model,
            encoding_name=args.encoding,
            input_price_per_1m=args.input_price_per_1m,
            output_dir=output_dir,
        )
        return

    report = run_unified_benchmark(
        model=args.model,
        encoding_name=args.encoding,
        input_price_per_1m=args.input_price_per_1m,
    )

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(render_markdown(report), encoding="utf-8")

    if args.summary_only:
        # Strip examples arrays for cleaner output
        if report["byte_proxy"]["report"]:
            report["byte_proxy"]["report"].pop("examples", None)
        if report["bpe_tokenizer"]["report"]:
            report["bpe_tokenizer"]["report"].pop("examples", None)
        if report["tiktoken"]["report"]:
            report["tiktoken"]["report"].pop("examples", None)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
