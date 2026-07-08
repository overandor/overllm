#!/usr/bin/env python3
"""Parity check between the Python BPE reference implementation
(tools/bpe_tokenizer.py) and the compiled C++ mirror (cpp/src/tokenizer.cpp).

This is the actual verification that cpp/src/tokenizer.cpp is a real,
correct mirror of the Python trainer/encoder, not just a second
implementation that happens to compile. It compiles cpp/tools/bpe_cli.cpp +
cpp/src/tokenizer.cpp with g++, then runs both implementations on the same
set of inputs against the same trained vocabulary and asserts identical
token ID sequences.

Usage:

  python tools/bpe_parity_check.py
  python tools/bpe_parity_check.py --vocab-dir cpp/tokenizer_data
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from bpe_tokenizer import BPETokenizer

DEFAULT_VOCAB_DIR = REPO_ROOT / "cpp" / "tokenizer_data"

PARITY_TEST_STRINGS = [
    "hello world",
    "the pull request is ready for review",
    "ʇsǝʇ",
    "аpple.com",
    "invoice‮exe.gpj‬",
    "καλημέρα σας",
    "  double  spaced  text  ",
    "",
    "a",
    "import os",
    "single-token-ish-word",
    "MiXeD CaSe Text With Punctuation!!! And Numbers 12345.",
    "\t\ttabs\tand\nnewlines\n",
]


def compile_cpp_cli(build_dir: Path) -> Path:
    build_dir.mkdir(parents=True, exist_ok=True)
    binary_path = build_dir / "bpe_cli"
    cmd = [
        "g++", "-std=c++17", "-O2",
        "-I", str(REPO_ROOT / "cpp" / "include"),
        str(REPO_ROOT / "cpp" / "src" / "tokenizer.cpp"),
        str(REPO_ROOT / "cpp" / "tools" / "bpe_cli.cpp"),
        "-o", str(binary_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"g++ compilation failed:\n{result.stderr}")
    return binary_path


def run_cpp_encode(binary_path: Path, vocab_dir: Path, text: str) -> list[int]:
    result = subprocess.run(
        [str(binary_path), "encode", "--vocab-dir", str(vocab_dir), "--text", text],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"bpe_cli encode failed for {text!r}:\n{result.stderr}")
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("["):
            return json.loads(line)
    raise RuntimeError(f"No token ID output found for {text!r}:\n{result.stdout}")


def run_parity_check(vocab_dir: Path, extra_texts: list[str] | None = None) -> dict[str, Any]:
    if shutil.which("g++") is None:
        return {
            "status": "skipped",
            "reason": "g++ not available in this environment",
            "cases": [],
        }

    with tempfile.TemporaryDirectory() as tmp:
        binary_path = compile_cpp_cli(Path(tmp))
        python_tokenizer = BPETokenizer.load(vocab_dir)

        texts = list(PARITY_TEST_STRINGS) + list(extra_texts or [])
        cases: list[dict[str, Any]] = []
        for text in texts:
            python_ids = python_tokenizer.encode(text)
            cpp_ids = run_cpp_encode(binary_path, vocab_dir, text)
            cases.append({
                "text": text,
                "python_ids": python_ids,
                "cpp_ids": cpp_ids,
                "match": python_ids == cpp_ids,
            })

    mismatches = [c for c in cases if not c["match"]]
    return {
        "status": "ok" if not mismatches else "mismatch",
        "vocab_dir": str(vocab_dir),
        "case_count": len(cases),
        "mismatch_count": len(mismatches),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Python/C++ BPE tokenizer parity")
    parser.add_argument("--vocab-dir", default=str(DEFAULT_VOCAB_DIR))
    args = parser.parse_args()

    report = run_parity_check(Path(args.vocab_dir))
    mismatches = [c for c in report["cases"] if not c["match"]]

    print(json.dumps(
        {k: v for k, v in report.items() if k != "cases"} | {"mismatches": mismatches},
        indent=2, ensure_ascii=False,
    ))

    if report["status"] == "mismatch":
        raise SystemExit(f"{len(mismatches)} parity mismatch(es) found")


if __name__ == "__main__":
    main()
