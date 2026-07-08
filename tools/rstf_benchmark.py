#!/usr/bin/env python3
"""RSTF benchmark: measures detection/recovery accuracy of the reversible
semantic transform fingerprint module against synthetic examples.

For each source sentence in benchmark/rstf/corpus.json, this generates one
transformed variant per implemented transform class (reversed, upside_down,
bidi_override, homoglyph), runs compute_fingerprint on the transformed text,
and measures:

- raw_hash divergence: did the transform actually change the bytes (it
  should, almost always).
- detection rate: did transform_receipt correctly flag the transform class.
- exact recovery rate: does canonical_text exactly match the expected
  recovered text (original text for reversed/bidi/homoglyph; lowercased
  original for upside_down, since that transform is case-lossy by design).

This is a v0.1 benchmark: 40 source sentences x 4 transform classes = 160
examples. It is not a claim of exhaustive adversarial-text coverage — see
docs/SEMANTIC_TRANSFORM_FINGERPRINT.md for the module's documented limits.

Usage:

  python tools/rstf_benchmark.py
  python tools/rstf_benchmark.py --out benchmark/rstf/report.json
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
    from api.semantic_fingerprint import (
        FINGERPRINT_VERSION,
        compute_fingerprint,
        encode_bidi_override,
        encode_homoglyph,
        encode_reversed,
        encode_upside_down,
    )
except Exception:
    from semantic_fingerprint import (  # type: ignore
        FINGERPRINT_VERSION,
        compute_fingerprint,
        encode_bidi_override,
        encode_homoglyph,
        encode_reversed,
        encode_upside_down,
    )

CORPUS_PATH = REPO_ROOT / "benchmark" / "rstf" / "corpus.json"
BENCHMARK_VERSION = "rstf-benchmark-v0.1"


def _generate_examples(sentences: list[str]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for idx, sentence in enumerate(sentences):
        examples.append({
            "source_id": idx,
            "source_text": sentence,
            "transform": "reversed",
            "transformed_text": encode_reversed(sentence),
            "expected_canonical_text": sentence,
        })
        examples.append({
            "source_id": idx,
            "source_text": sentence,
            "transform": "upside_down",
            "transformed_text": encode_upside_down(sentence),
            "expected_canonical_text": sentence.lower(),
        })
        # Reverse the middle third of the sentence inside an RLO/PDF span,
        # simulating a Trojan-Source-style bidi override in the middle of
        # otherwise plain text.
        span_start = len(sentence) // 3
        span_end = 2 * len(sentence) // 3
        examples.append({
            "source_id": idx,
            "source_text": sentence,
            "transform": "bidi_override",
            "transformed_text": encode_bidi_override(sentence, span_start, span_end),
            "expected_canonical_text": sentence,
        })
        examples.append({
            "source_id": idx,
            "source_text": sentence,
            "transform": "homoglyph",
            "transformed_text": encode_homoglyph(sentence),
            "expected_canonical_text": sentence,
        })
    return examples


def run_benchmark() -> dict[str, Any]:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    examples = _generate_examples(corpus["sentences"])

    per_transform: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for example in examples:
        transform = example["transform"]
        fp = compute_fingerprint(example["transformed_text"])

        raw_diverged = fp["raw_hash"] != _raw_hash_of(example["source_text"])
        detected = fp["transform_receipt"].get(_receipt_key(transform), False)
        recovered_exact = fp["canonical_text"] == example["expected_canonical_text"]

        bucket = per_transform.setdefault(transform, {
            "count": 0, "raw_diverged": 0, "detected": 0, "recovered_exact": 0,
        })
        bucket["count"] += 1
        bucket["raw_diverged"] += int(raw_diverged)
        bucket["detected"] += int(detected)
        bucket["recovered_exact"] += int(recovered_exact)

        results.append({
            "source_id": example["source_id"],
            "transform": transform,
            "raw_diverged": raw_diverged,
            "detected": detected,
            "recovered_exact": recovered_exact,
            "canonical_text": fp["canonical_text"],
            "expected_canonical_text": example["expected_canonical_text"],
        })

    summary = {}
    for transform, bucket in per_transform.items():
        count = bucket["count"]
        summary[transform] = {
            "count": count,
            "raw_hash_divergence_rate": round(bucket["raw_diverged"] / count, 3),
            "detection_rate": round(bucket["detected"] / count, 3),
            "exact_recovery_rate": round(bucket["recovered_exact"] / count, 3),
        }

    total = len(results)
    overall = {
        "count": total,
        "raw_hash_divergence_rate": round(sum(r["raw_diverged"] for r in results) / total, 3),
        "detection_rate": round(sum(r["detected"] for r in results) / total, 3),
        "exact_recovery_rate": round(sum(r["recovered_exact"] for r in results) / total, 3),
    }

    return {
        "benchmark_version": BENCHMARK_VERSION,
        "fingerprint_version": FINGERPRINT_VERSION,
        "corpus_version": corpus.get("corpus_version"),
        "overall": overall,
        "per_transform": summary,
        "examples": results,
        "truth_label": "synthetic_generated_examples_not_real_world_traffic",
    }


def _receipt_key(transform: str) -> str:
    return {
        "reversed": "reversed",
        "upside_down": "upside_down",
        "bidi_override": "bidi_override",
        "homoglyph": "homoglyph_substitution",
    }[transform]


def _raw_hash_of(text: str) -> str:
    from api.semantic_fingerprint import _sha256_text  # local import: private helper
    return _sha256_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RSTF benchmark")
    parser.add_argument("--out", help="Write the full JSON report to this path")
    parser.add_argument("--summary-only", action="store_true", help="Print only the aggregate summary, not per-example results")
    args = parser.parse_args()

    report = run_benchmark()

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if args.summary_only:
        report = {k: v for k, v in report.items() if k != "examples"}

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
