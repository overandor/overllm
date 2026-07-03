#!/usr/bin/env python3
"""
OverGPT ViralRepoLab

Safe goal:
    Teach an algorithm to design repos that people want to star, fork, run,
    share, and contribute to.

Unsafe non-goal:
    This is not malware, not a worm, not self-modifying code, not unauthorized
    propagation, and not an auto-merge bot. "Viral" here means adoption,
    clarity, usefulness, and shareability.

Run:
    python3 tools/overgpt_viral_repo_lab.py --idea "AI receipt generator for repo claims"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


SAFE_BLOCKLIST = [
    "virus",
    "worm",
    "malware",
    "self modifying",
    "self-modifying",
    "steal",
    "credential",
    "token exfiltration",
    "exfiltrate",
    "ransomware",
    "unauthorized",
    "auto merge to main",
    "bypass ci",
    "disable security",
]

POSITIVE_SIGNALS = {
    "instant_demo": 0.14,
    "clear_problem": 0.12,
    "low_install_friction": 0.12,
    "visual_output": 0.10,
    "receipt_or_proof": 0.10,
    "developer_utility": 0.10,
    "novel_framing": 0.09,
    "safe_automation": 0.08,
    "good_name": 0.07,
    "shareable_story": 0.05,
    "contributor_path": 0.03,
}

RISK_SIGNALS = {
    "overclaiming": 0.22,
    "unclear_use_case": 0.18,
    "high_setup_friction": 0.16,
    "no_demo": 0.16,
    "security_ambiguity": 0.14,
    "no_tests": 0.08,
    "no_license_or_terms": 0.06,
}


@dataclass(frozen=True)
class RepoConcept:
    idea: str
    audience: str
    demo: str
    proof: str
    safety_boundary: str


@dataclass(frozen=True)
class ViralVector:
    instant_demo: float
    clear_problem: float
    low_install_friction: float
    visual_output: float
    receipt_or_proof: float
    developer_utility: float
    novel_framing: float
    safe_automation: float
    good_name: float
    shareable_story: float
    contributor_path: float


@dataclass(frozen=True)
class RiskVector:
    overclaiming: float
    unclear_use_case: float
    high_setup_friction: float
    no_demo: float
    security_ambiguity: float
    no_tests: float
    no_license_or_terms: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:64] or "overgpt-repo"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safety_check(text: str) -> Dict[str, Any]:
    lower = text.lower()
    hits = [term for term in SAFE_BLOCKLIST if term in lower]
    return {
        "allowed": len(hits) == 0,
        "blocked_terms": hits,
        "boundary": "Viral means adoption and shareability, never unauthorized propagation.",
    }


def phrase_score(text: str, phrases: Tuple[str, ...]) -> float:
    lower = text.lower()
    hits = sum(1 for phrase in phrases if phrase in lower)
    return clamp(hits / max(1, len(phrases)))


def estimate_vectors(concept: RepoConcept) -> Tuple[ViralVector, RiskVector]:
    joined = " ".join(asdict(concept).values()).lower()
    idea_len = len(concept.idea.strip())
    demo_len = len(concept.demo.strip())
    proof_len = len(concept.proof.strip())

    viral = ViralVector(
        instant_demo=clamp(0.25 + phrase_score(joined, ("demo", "run", "one command", "screenshot", "json"))),
        clear_problem=clamp(0.35 + min(0.45, idea_len / 180.0)),
        low_install_friction=clamp(0.35 + phrase_score(joined, ("single-file", "no dependencies", "python", "local", "cli"))),
        visual_output=clamp(0.25 + phrase_score(joined, ("dashboard", "chart", "graph", "screenshot", "visual", "json"))),
        receipt_or_proof=clamp(0.30 + phrase_score(joined, ("receipt", "proof", "hash", "test", "ci", "verification"))),
        developer_utility=clamp(0.30 + phrase_score(joined, ("repo", "developer", "ci", "github", "pull request", "api"))),
        novel_framing=clamp(0.35 + phrase_score(joined, ("overgpt", "hot tensor", "underwriting", "value packet", "claim"))),
        safe_automation=clamp(0.45 + phrase_score(concept.safety_boundary.lower(), ("approval", "safe", "human", "no unauthorized", "review"))),
        good_name=clamp(0.25 + min(0.55, len(slugify(concept.idea)) / 64.0)),
        shareable_story=clamp(0.30 + phrase_score(joined, ("viral", "share", "star", "fork", "launch", "market"))),
        contributor_path=clamp(0.25 + phrase_score(joined, ("good first issue", "plugin", "template", "roadmap", "contribute"))),
    )

    risk = RiskVector(
        overclaiming=phrase_score(joined, ("breakthrough", "world first", "revolutionary", "guaranteed", "3m")),
        unclear_use_case=1.0 - viral.clear_problem,
        high_setup_friction=1.0 - viral.low_install_friction,
        no_demo=clamp(1.0 - min(1.0, demo_len / 80.0)),
        security_ambiguity=0.75 if not safety_check(joined)["allowed"] else 0.10,
        no_tests=0.15 if any(w in joined for w in ["test", "ci", "verify"]) else 0.75,
        no_license_or_terms=0.25 if any(w in joined for w in ["license", "terms", "safe"]) else 0.70,
    )
    return viral, risk


def weighted_sum(values: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(values[k] * weights[k] for k in weights)


def score_concept(concept: RepoConcept) -> Dict[str, Any]:
    safety = safety_check(" ".join(asdict(concept).values()))
    viral, risk = estimate_vectors(concept)
    viral_dict = asdict(viral)
    risk_dict = asdict(risk)
    viral_heat = weighted_sum(viral_dict, POSITIVE_SIGNALS)
    risk_drag = weighted_sum(risk_dict, RISK_SIGNALS)
    adoption_score = clamp(sigmoid(4.0 * (viral_heat - risk_drag) - 0.5))

    if not safety["allowed"]:
        adoption_score = min(adoption_score, 0.25)
        decision = "blocked_until_reframed_safely"
    elif adoption_score >= 0.75:
        decision = "strong_viral_repo_candidate"
    elif adoption_score >= 0.55:
        decision = "promising_repo_candidate"
    elif adoption_score >= 0.35:
        decision = "needs_positioning_and_demo"
    else:
        decision = "weak_candidate"

    return {
        "schema": "overgpt.viral_repo_score.v1",
        "created_at": utc_now(),
        "concept": asdict(concept),
        "safe_language": safety,
        "viral_vector": viral_dict,
        "risk_vector": risk_dict,
        "viral_heat": round(viral_heat, 6),
        "risk_drag": round(risk_drag, 6),
        "adoption_score": round(adoption_score, 6),
        "decision": decision,
        "receipt_hash": sha256_text(json.dumps(asdict(concept), sort_keys=True)),
    }


def repo_spec(concept: RepoConcept, score: Dict[str, Any]) -> Dict[str, Any]:
    name = slugify(concept.idea)
    return {
        "repo_name": name,
        "tagline": f"{concept.idea.strip()} — runnable, safe, receipt-backed.",
        "readme_sections": [
            "What it does",
            "One-command demo",
            "Example output",
            "Why it is safe",
            "How it works",
            "Tests and receipts",
            "Roadmap",
            "Contributing",
        ],
        "first_issues": [
            "Add screenshot or terminal GIF",
            "Add baseline comparison",
            "Add sample output receipts",
            "Add docs for contributors",
            "Add security and claim-boundary notes",
        ],
        "launch_checklist": [
            "One-command run works",
            "README explains the problem in first 5 lines",
            "Demo output committed or uploaded as CI artifact",
            "Tests pass",
            "No unsupported breakthrough claims",
            "No self-propagating or unauthorized behavior",
            "License and safety boundary are clear",
        ],
        "positioning": {
            "audience": concept.audience,
            "demo": concept.demo,
            "proof": concept.proof,
            "score_decision": score["decision"],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score and package a safe viral repo concept.")
    parser.add_argument("--idea", required=True)
    parser.add_argument("--audience", default="developers, founders, and AI builders")
    parser.add_argument("--demo", default="one-command local CLI demo with JSON output")
    parser.add_argument("--proof", default="tests, CI, hash receipt, and sample output")
    parser.add_argument(
        "--safety-boundary",
        default="No unauthorized propagation, no credential access, no self-modifying behavior, human-reviewed merges only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    concept = RepoConcept(
        idea=args.idea,
        audience=args.audience,
        demo=args.demo,
        proof=args.proof,
        safety_boundary=args.safety_boundary,
    )
    score = score_concept(concept)
    output = {
        "score": score,
        "repo_spec": repo_spec(concept, score),
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
