#!/usr/bin/env python3
"""RSTF dogfood scan: run the fingerprint module against this repository's
own real text (README/docs prose and Python source), not synthetic
benchmark fixtures.

This is not a customer pilot — nobody outside this repo supplied the input
data, so it doesn't satisfy "someone tested it on their own real inputs."
What it does provide that the synthetic benchmarks can't: real, naturally
occurring text that nobody constructed to make RSTF look good or bad,
scanned line-by-line the way "Pilot 1: GitHub Repo Scanner" (scan READMEs,
docs, code comments for transformed content) was described.

Every RSTF-related file (the module itself, its docs, its benchmarks/tests)
legitimately contains crafted example glyphs like "ʇsǝʇ" or "аpple.com" -
those are expected true positives, not findings. Results are split into
"within RSTF's own files" (expected) and "elsewhere in the repo" (the
actual signal: did anything real, unrelated to this feature, get flagged).

Usage:

  python tools/rstf_dogfood_scan.py
  python tools/rstf_dogfood_scan.py --out-md benchmark/rstf/dogfood_report.md
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

try:
    from api.semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint
except Exception:
    from semantic_fingerprint import FINGERPRINT_VERSION, compute_fingerprint  # type: ignore

REPORT_VERSION = "rstf-dogfood-scan-v0.1"

SCAN_EXTENSIONS = {".md", ".py"}
EXCLUDE_DIR_NAMES = {".git", "node_modules", "__pycache__", "dist", "build", "ui"}

RSTF_OWN_PATHS_PREFIXES = (
    "api/semantic_fingerprint.py",
    "tools/rstf_benchmark.py",
    "tools/rstf_token_cost.py",
    "tools/rstf_adversarial_eval.py",
    "tools/rstf_dogfood_scan.py",
    "docs/SEMANTIC_TRANSFORM_FINGERPRINT.md",
    "benchmark/rstf/",
    "tests/test_semantic_fingerprint.py",
    "tests/test_rstf_benchmark.py",
    "tests/test_rstf_token_cost.py",
    "tests/test_rstf_adversarial_eval.py",
    "tests/test_rstf_dogfood_scan.py",
    "tools/bpe_tokenizer.py",
    "tools/bpe_parity_check.py",
    "tools/rstf_bpe_token_cost.py",
    "tests/test_bpe_tokenizer.py",
    "tests/test_bpe_parity_check.py",
    "tests/test_rstf_bpe_token_cost.py",
    "cpp/rstf/",
    "docs/OVERLLM_UNDERWRITING_PACKAGE.md",
    "docs/RSTF_TRAINING_BOOTCAMP.md",
    "tools/rstf_tiktoken_cost.py",
    "tools/rstf_cost_pipeline.py",
    "tools/rstf_real_corpus_cost.py",
    "tools/rstf_memory_efficient.py",
    "tools/rstf_unified_cost_benchmark.py",
    "tests/test_rstf_tiktoken_cost.py",
    "tests/test_rstf_cost_pipeline.py",
    "tests/test_rstf_real_corpus_cost.py",
    "docs/RSTF_TIKTOKEN_COST.md",
    "docs/RSTF_COST_PIPELINE.md",
    "docs/RSTF_RAM_COMPRESSION.md",
    "docs/RSTF_REAL_CORPUS_COST.md",
    "docs/SERVERLESS_FUNCTIONS.md",
)


def _iter_scan_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in SCAN_EXTENSIONS:
            continue
        if any(part in EXCLUDE_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        yield path


def _is_rstf_own_file(rel_path: str) -> bool:
    return any(rel_path == p or rel_path.startswith(p) for p in RSTF_OWN_PATHS_PREFIXES)


def run_scan(root: Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    hits: list[dict[str, Any]] = []
    files_scanned = 0
    lines_scanned = 0

    for path in sorted(_iter_scan_files(root)):
        rel_path = str(path.relative_to(root))
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            lines_scanned += 1
            fp = compute_fingerprint(stripped)
            if fp["transform_detected"]:
                hits.append({
                    "file": rel_path,
                    "line": line_no,
                    "text": stripped[:200],
                    "transform_receipt": fp["transform_receipt"],
                    "within_rstf_own_files": _is_rstf_own_file(rel_path),
                })

    expected_hits = [h for h in hits if h["within_rstf_own_files"]]
    unexpected_hits = [h for h in hits if not h["within_rstf_own_files"]]

    return {
        "report_version": REPORT_VERSION,
        "fingerprint_version": FINGERPRINT_VERSION,
        "files_scanned": files_scanned,
        "lines_scanned": lines_scanned,
        "total_hits": len(hits),
        "expected_hits_within_rstf_own_files": len(expected_hits),
        "unexpected_hits_elsewhere": len(unexpected_hits),
        "hits": hits,
        "truth_label": "real_repo_text_not_a_customer_pilot_no_external_input_data",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# RSTF dogfood scan ({report['report_version']})",
        "",
        f"Fingerprint version: `{report['fingerprint_version']}`",
        "",
        "Scanned this repository's own `.md` and `.py` files line-by-line - real "
        "text, not synthetic benchmark fixtures. This is not a customer pilot: "
        "nobody outside this repo supplied the input.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Files scanned | {report['files_scanned']} |",
        f"| Non-blank lines scanned | {report['lines_scanned']} |",
        f"| Total hits | {report['total_hits']} |",
        f"| Expected hits (within RSTF's own module/docs/benchmark/test files) | {report['expected_hits_within_rstf_own_files']} |",
        f"| **Unexpected hits (elsewhere in the repo)** | **{report['unexpected_hits_elsewhere']}** |",
        "",
    ]

    unexpected = [h for h in report["hits"] if not h["within_rstf_own_files"]]
    if unexpected:
        lines += ["## Unexpected hits — needs review", "",
                   "| file | line | text | transform_receipt |", "|---|---|---|---|"]
        for h in unexpected:
            lines.append(f"| {h['file']} | {h['line']} | {h['text']!r} | `{h['transform_receipt']}` |")
    else:
        lines.append("No unexpected hits outside RSTF's own files.")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RSTF dogfood scan against this repo's own text")
    parser.add_argument("--out", help="Write the full JSON report to this path")
    parser.add_argument("--out-md", help="Write a human-readable Markdown report to this path")
    args = parser.parse_args()

    report = run_scan()

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(render_markdown(report), encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "hits"}, indent=2, sort_keys=True))
    print(f"\n{len(report['hits'])} total hits (see --out for detail)", file=sys.stderr)


if __name__ == "__main__":
    main()
