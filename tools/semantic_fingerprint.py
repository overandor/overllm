#!/usr/bin/env python3
"""Reversible Semantic Transform Fingerprint (RSTF) CLI for OverLLM.

Examples:

  python tools/semantic_fingerprint.py compute --text "test"
  python tools/semantic_fingerprint.py compute --file some_prompt.txt
  python tools/semantic_fingerprint.py compare --text-a "test" --text-b "ʇsǝʇ"

See docs/SEMANTIC_TRANSFORM_FINGERPRINT.md for what this does and does not
detect.
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
    from api.semantic_fingerprint import compare_fingerprints, compute_fingerprint
except Exception:
    from semantic_fingerprint import compare_fingerprints, compute_fingerprint  # type: ignore


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


def _read_text(args: argparse.Namespace, text_attr: str, file_attr: str) -> str:
    file_value = getattr(args, file_attr, None)
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    text_value = getattr(args, text_attr, None)
    if text_value is None:
        raise SystemExit(f"provide --{text_attr.replace('_', '-')} or --{file_attr.replace('_', '-')}")
    return text_value


def cmd_compute(args: argparse.Namespace) -> None:
    text = _read_text(args, "text", "file")
    print_json(compute_fingerprint(text))


def cmd_compare(args: argparse.Namespace) -> None:
    text_a = _read_text(args, "text_a", "file_a")
    text_b = _read_text(args, "text_b", "file_b")
    print_json(compare_fingerprints(text_a, text_b))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OverLLM reversible semantic transform fingerprint CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    compute = sub.add_parser("compute", help="Compute raw/canonical hashes and transform receipt for text")
    compute.add_argument("--text")
    compute.add_argument("--file")
    compute.set_defaults(func=cmd_compute)

    compare = sub.add_parser("compare", help="Compare two texts for canonical-message equality")
    compare.add_argument("--text-a", dest="text_a")
    compare.add_argument("--file-a", dest="file_a")
    compare.add_argument("--text-b", dest="text_b")
    compare.add_argument("--file-b", dest="file_b")
    compare.set_defaults(func=cmd_compare)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
