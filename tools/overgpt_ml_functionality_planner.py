#!/usr/bin/env python3
"""
OverGPT ML Functionality Planner

A safe ML-assisted repo-evolution layer.

It scores candidate functionality and merge readiness, then emits a reviewable
plan. It does not self-modify the repository, bypass CI, or merge changes.

The intended control loop is:

    proposal -> ML score -> value packet -> tests -> PR -> CI -> human review -> merge

Run:
    python3 tools/overgpt_ml_functionality_planner.py

Optional:
    python3 tools/overgpt_ml_functionality_planner.py --input proposals.json
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence


RISK_TERMS = {
    "auto_merge",
    "self_modify",
    "bypass_review",
    "bypass_ci",
    "credential",
    "secret",
    "token",
    "exfiltrate",
    "virus",
    "worm",
    "malware",
    "persistence",
    "stealth",
}

SAFE_TERMS = {
    "test",
    "ci",
    "receipt",
    "diligence",
    "human_approval",
    "review",
    "documentation",
    "baseline",
    "ablation",
    "sandbox",
    "dry_run",
    "proposal",
}

FEATURES = [
    "value_density",
    "testability",
    "receiptability",
    "ci_compatibility",
    "human_approval_safety",
    "complexity_penalty",
    "blast_radius_penalty",
    "risk_term_penalty",
    "documentation_support",
    "baseline_support",
]


@dataclasses.dataclass(frozen=True)
class Proposal:
    name: str
    description: str
    expected_value: float
    complexity: float
    blast_radius: float
    test_plan: str
    files: List[str]
    requires_human_approval: bool = True


@dataclasses.dataclass(frozen=True)
class MLPWeights:
    hidden: List[List[float]]
    hidden_bias: List[float]
    output: List[float]
    output_bias: float


VALUE_MODEL = MLPWeights(
    hidden=[
        [0.42, 0.32, 0.28, 0.20, 0.24, -0.38, -0.40, -0.55, 0.16, 0.18],
        [0.18, 0.40, 0.35, 0.38, 0.30, -0.20, -0.25, -0.45, 0.26, 0.30],
        [0.35, 0.25, 0.42, 0.18, 0.22, -0.18, -0.22, -0.35, 0.36, 0.20],
        [0.26, 0.34, 0.20, 0.42, 0.40, -0.30, -0.38, -0.65, 0.18, 0.25],
    ],
    hidden_bias=[0.03, 0.02, 0.01, 0.04],
    output=[0.28, 0.26, 0.22, 0.24],
    output_bias=0.02,
)

MERGE_MODEL = MLPWeights(
    hidden=[
        [0.12, 0.46, 0.28, 0.44, 0.55, -0.48, -0.50, -0.72, 0.20, 0.24],
        [0.18, 0.38, 0.30, 0.36, 0.50, -0.35, -0.45, -0.68, 0.22, 0.18],
        [0.10, 0.42, 0.24, 0.48, 0.60, -0.42, -0.58, -0.80, 0.18, 0.20],
    ],
    hidden_bias=[0.01, 0.02, 0.03],
    output=[0.34, 0.30, 0.36],
    output_bias=-0.08,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def relu(x: float) -> float:
    return max(0.0, x)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_object(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def tokenize(text: str) -> List[str]:
    lowered = text.lower()
    for char in ",.;:/\\()[]{}\n\t-|":
        lowered = lowered.replace(char, " ")
    return [part.strip() for part in lowered.split() if part.strip()]


def term_score(tokens: Iterable[str], terms: set[str]) -> float:
    token_set = set(tokens)
    if not token_set:
        return 0.0
    hits = sum(1 for term in terms if term in token_set)
    return clamp(hits / max(1, len(terms) ** 0.5))


def path_complexity(files: Sequence[str]) -> float:
    if not files:
        return 0.0
    weighted = 0.0
    for path in files:
        parts = pathlib.PurePosixPath(path).parts
        weighted += min(1.0, len(parts) / 6.0)
        if path.startswith(".github/"):
            weighted += 0.15
        if path.endswith(".go") or path.endswith(".py"):
            weighted += 0.10
    return clamp(weighted / len(files))


def proposal_features(proposal: Proposal) -> Dict[str, float]:
    text = " ".join([proposal.name, proposal.description, proposal.test_plan, " ".join(proposal.files)])
    tokens = tokenize(text)
    risk = term_score(tokens, RISK_TERMS)
    safe = term_score(tokens, SAFE_TERMS)
    has_tests = any("test" in path.lower() for path in proposal.files) or "test" in proposal.test_plan.lower()
    has_ci = any(path.startswith(".github/workflows/") for path in proposal.files) or "ci" in proposal.test_plan.lower()
    has_docs = any(path.lower().startswith("docs/") or path.lower().endswith(".md") for path in proposal.files)
    has_receipts = "receipt" in text.lower() or "hash" in text.lower() or "manifest" in text.lower()
    baseline = "baseline" in text.lower() or "ablation" in text.lower() or "comparison" in text.lower()

    return {
        "value_density": clamp(proposal.expected_value),
        "testability": clamp(0.75 * float(has_tests) + 0.25 * safe),
        "receiptability": clamp(0.8 * float(has_receipts) + 0.2 * safe),
        "ci_compatibility": clamp(0.8 * float(has_ci) + 0.2 * safe),
        "human_approval_safety": 1.0 if proposal.requires_human_approval else 0.0,
        "complexity_penalty": clamp(0.55 * proposal.complexity + 0.45 * path_complexity(proposal.files)),
        "blast_radius_penalty": clamp(proposal.blast_radius),
        "risk_term_penalty": risk,
        "documentation_support": 1.0 if has_docs else 0.0,
        "baseline_support": 1.0 if baseline else 0.0,
    }


def mlp_score(features: Dict[str, float], weights: MLPWeights) -> float:
    x = [features[name] for name in FEATURES]
    hidden = []
    for row, bias in zip(weights.hidden, weights.hidden_bias):
        hidden.append(relu(sum(w * xi for w, xi in zip(row, x)) + bias))
    raw = sum(w * hi for w, hi in zip(weights.output, hidden)) + weights.output_bias
    return round(sigmoid(raw), 6)


def safety_gate(features: Dict[str, float], proposal: Proposal) -> Dict[str, Any]:
    blocks = []
    if features["risk_term_penalty"] > 0.0:
        blocks.append("proposal_contains_high_risk_terms")
    if not proposal.requires_human_approval:
        blocks.append("human_approval_required_for_repo_evolution")
    if features["blast_radius_penalty"] > 0.75:
        blocks.append("blast_radius_too_large_for_autonomous_merge")
    if features["ci_compatibility"] < 0.35:
        blocks.append("ci_or_test_plan_too_weak")
    return {
        "allowed_to_generate_plan": len(blocks) == 0 or blocks == ["ci_or_test_plan_too_weak"],
        "allowed_to_auto_merge": False,
        "merge_requires_human_review": True,
        "blocks": blocks,
    }


def recommendation(value_score: float, merge_score: float, safety: Dict[str, Any]) -> str:
    if safety["blocks"]:
        return "revise_before_pr"
    if value_score >= 0.62 and merge_score >= 0.62:
        return "draft_pr_candidate"
    if value_score >= 0.55:
        return "write_spec_and_tests_first"
    return "backlog_candidate"


def score_proposal(proposal: Proposal) -> Dict[str, Any]:
    features = proposal_features(proposal)
    value_score = mlp_score(features, VALUE_MODEL)
    merge_score = mlp_score(features, MERGE_MODEL)
    safety = safety_gate(features, proposal)
    output = {
        "proposal": dataclasses.asdict(proposal),
        "features": features,
        "value_score": value_score,
        "merge_readiness_score": merge_score,
        "safety_gate": safety,
        "recommendation": recommendation(value_score, merge_score, safety),
    }
    output["proposal_hash"] = sha256_object(output)
    return output


def default_proposals() -> List[Proposal]:
    return [
        Proposal(
            name="Baseline comparison for OverGPT value packets",
            description="Compare the current value packet against a plain unreceipted claim JSON baseline.",
            expected_value=0.86,
            complexity=0.38,
            blast_radius=0.22,
            test_plan="Add tests, CI output, and a baseline receipt artifact.",
            files=[
                "tools/overgpt_baseline_compare.py",
                "tests/test_overgpt_baseline_compare.py",
                "docs/OVERGPT_DILIGENCE_ROADMAP.md",
            ],
        ),
        Proposal(
            name="Ablation harness for claim-underwriting components",
            description="Remove bond, resolution, firewall, receipts, and HotTensor fields one at a time and measure score loss.",
            expected_value=0.82,
            complexity=0.52,
            blast_radius=0.25,
            test_plan="Run deterministic ablations and assert expected score degradation.",
            files=["tools/overgpt_ablation_harness.py", "tests/test_overgpt_ablation_harness.py"],
        ),
        Proposal(
            name="Unsafe self-modifying auto-merge loop",
            description="Let the repo change itself and merge without review or CI.",
            expected_value=0.20,
            complexity=0.90,
            blast_radius=0.98,
            test_plan="No reliable test plan.",
            files=[".github/workflows/auto_merge.yml"],
            requires_human_approval=False,
        ),
    ]


def load_proposals(path: str) -> List[Proposal]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    proposals = raw.get("proposals", raw)
    return [
        Proposal(
            name=item["name"],
            description=item.get("description", ""),
            expected_value=float(item.get("expected_value", 0.5)),
            complexity=float(item.get("complexity", 0.5)),
            blast_radius=float(item.get("blast_radius", 0.5)),
            test_plan=item.get("test_plan", ""),
            files=list(item.get("files", [])),
            requires_human_approval=bool(item.get("requires_human_approval", True)),
        )
        for item in proposals
    ]


def build_report(proposals: List[Proposal]) -> Dict[str, Any]:
    scored = [score_proposal(proposal) for proposal in proposals]
    scored.sort(key=lambda item: (item["recommendation"] != "draft_pr_candidate", -item["value_score"], -item["merge_readiness_score"]))
    return {
        "schema": "overgpt.ml_functionality_planner.v1",
        "created_at": utc_now(),
        "model_type": "deterministic_tiny_mlp",
        "safety_posture": "ML may recommend specs or draft PR candidates, but cannot auto-merge or bypass review.",
        "feature_order": FEATURES,
        "ranked_proposals": scored,
        "next_best_safe_action": next_best_safe_action(scored),
        "report_hash": sha256_object(scored),
    }


def next_best_safe_action(scored: List[Dict[str, Any]]) -> str:
    for item in scored:
        if item["recommendation"] == "draft_pr_candidate":
            return "Create a human-reviewed PR for: " + item["proposal"]["name"]
    for item in scored:
        if item["recommendation"] == "write_spec_and_tests_first":
            return "Write spec and tests first for: " + item["proposal"]["name"]
    return "Keep proposals in backlog until safety, tests, and receipts improve."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank safe repo functionality proposals with a tiny deterministic MLP.")
    parser.add_argument("--input", help="Optional JSON file containing a list or {'proposals': [...]} object.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    proposals = load_proposals(args.input) if args.input else default_proposals()
    report = build_report(proposals)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
