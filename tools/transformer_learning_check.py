#!/usr/bin/env python3
"""Compiles and runs cpp/tools/train_language_model.cpp - the real
transformer training experiment - and checks its loss actually decreases.

This exists because two things that looked like "training" already existed
in this repo and neither proved learning actually happens:

- cpp/test_overllm.cpp checks that a single DPO/RL/backward/AdamW step
  "completes" and produces a plausible-looking loss value, never checking
  it over multiple steps.
- cpp/train_online.cpp's training loop feeds uniformly random tokens as
  chosen/rejected DPO pairs, which has no learnable signal by construction
  (both sequences are random draws from the same distribution), so it can
  run for any number of steps without ever proving gradient descent works.

This compiles cpp/tools/train_language_model.cpp (real BPE-tokenized text,
real next-token cross-entropy loss, real backward pass + AdamW, through
the same -O3 -ffast-math build settings the rest of this repo's C++ CMake
project uses) and asserts the loss curve actually decreases - mechanically
checked, not eyeballed from console output.

Building this also found and fixed a real bug: training diverged to NaN
around epoch 15 under -O3 -ffast-math with no gradient clipping (a standard
safeguard that cpp/src/model.cpp had never had). overllm_clip_gradients()
was added to fix it - see that function's docstring in model.cpp.

Usage:

  python tools/transformer_learning_check.py
  python tools/transformer_learning_check.py --out benchmark/transformer_learning/report.json
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def compile_trainer(build_dir: Path) -> Path:
    build_dir.mkdir(parents=True, exist_ok=True)
    binary_path = build_dir / "train_language_model"
    cmd = [
        "g++", "-std=c++17", "-O3", "-ffast-math",
        "-I", str(REPO_ROOT / "cpp" / "include"),
        str(REPO_ROOT / "cpp" / "src" / "model.cpp"),
        str(REPO_ROOT / "cpp" / "src" / "tensor_ops.cpp"),
        str(REPO_ROOT / "cpp" / "src" / "tokenizer.cpp"),
        str(REPO_ROOT / "cpp" / "tools" / "train_language_model.cpp"),
        "-o", str(binary_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"g++ compilation failed:\n{result.stderr}")
    return binary_path


def run_training(binary_path: Path, epochs: int, context_window: int, sentence_limit: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        out_json = Path(tmp) / "report.json"
        cmd = [
            str(binary_path),
            "--vocab-dir", str(REPO_ROOT / "cpp" / "tokenizer_data"),
            "--corpus", str(REPO_ROOT / "benchmark" / "rstf" / "corpus.json"),
            "--epochs", str(epochs),
            "--context-window", str(context_window),
            "--sentence-limit", str(sentence_limit),
            "--out-json", str(out_json),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        if result.returncode != 0:
            raise RuntimeError(f"train_language_model failed:\n{result.stderr}")
        return json.loads(out_json.read_text(encoding="utf-8"))


def check_report(report: dict[str, Any]) -> list[str]:
    problems = []
    losses = report["epoch_losses"]
    if any(math.isnan(loss) for loss in losses):
        problems.append("loss went NaN during training")
    if losses[-1] >= losses[0]:
        problems.append(f"loss did not decrease: first={losses[0]}, last={losses[-1]}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and verify the real transformer training experiment")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--context-window", type=int, default=24)
    parser.add_argument("--sentence-limit", type=int, default=6)
    parser.add_argument("--out", help="Write the JSON report to this path")
    args = parser.parse_args()

    if shutil.which("g++") is None:
        print(json.dumps({"status": "skipped", "reason": "g++ not available"}, indent=2))
        return

    with tempfile.TemporaryDirectory() as tmp:
        binary_path = compile_trainer(Path(tmp))
        report = run_training(binary_path, args.epochs, args.context_window, args.sentence_limit)

    problems = check_report(report)
    report["status"] = "ok" if not problems else "failed"
    report["problems"] = problems

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    if problems:
        raise SystemExit(f"Transformer learning check failed: {problems}")


if __name__ == "__main__":
    main()
