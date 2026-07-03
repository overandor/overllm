#!/usr/bin/env python3
"""
Tier-3 Value Packet Demo

Purpose:
    Demonstrate the smallest runnable OverLLM market primitive:
    a claim becomes financeable only after it has evidence, provenance,
    a settlement rule, a bond field, a measurable underwriting score, and
    a receipt.

Honest evidence label:
    Tier 3 candidate: stable internal proof.

This file deliberately does not claim breakthrough status. A breakthrough
requires prior-art review, baselines, falsification, reproducibility, and
external verification. This demo only produces a deterministic, hash-chained
value packet that can be shown, inspected, and re-run locally.

Run:
    python3 tools/value_packet_demo.py

Optional:
    python3 tools/value_packet_demo.py --claim "My claim" --stake-usd 100
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List


EVIDENCE_WEIGHTS: Dict[str, int] = {
    "implementation": 10,
    "clean_build": 10,
    "unit_tests": 10,
    "smoke_test": 15,
    "baseline_comparison": 15,
    "ablation": 15,
    "repeated_seeds": 10,
    "real_world_task": 10,
    "external_reproduction": 5,
}

TIER_LADDER: List[Dict[str, Any]] = [
    {"tier": 0, "name": "concept", "required": None},
    {"tier": 1, "name": "implemented", "required": "implementation"},
    {"tier": 2, "name": "runs", "required": "clean_build"},
    {"tier": 3, "name": "stable_internal_proof", "required": "smoke_test"},
    {"tier": 4, "name": "baseline_beating", "required": "baseline_comparison"},
    {"tier": 5, "name": "ablation_supported", "required": "ablation"},
    {"tier": 6, "name": "reproducible_internal", "required": "repeated_seeds"},
    {"tier": 7, "name": "generalized", "required": "real_world_task"},
    {"tier": 8, "name": "externally_verified", "required": "external_reproduction"},
]

BLOCKED_TERMS: Dict[str, int] = {
    "breakthrough": 8,
    "revolutionary": 8,
    "world-first": 8,
    "world first": 8,
    "frontier": 8,
    "state of the art": 4,
    "state-of-the-art": 4,
    "beats": 4,
    "outperforms": 4,
    "proven": 5,
    "validated": 6,
}


@dataclasses.dataclass(frozen=True)
class Evidence:
    kind: str
    description: str
    receipt: str
    created_at: str


@dataclasses.dataclass(frozen=True)
class Bond:
    stake_usd: float
    claimant: str
    counterparty: str
    forfeiture_condition: str
    settlement_currency: str = "USD"


@dataclasses.dataclass(frozen=True)
class ResolutionRule:
    resolver: str
    resolution_date: str
    procedure: str
    pass_condition: str
    fail_condition: str


@dataclasses.dataclass(frozen=True)
class HotTensorInput:
    evidence_score: float
    evidence_tier: int
    stake_usd: float
    claimed_value_usd: float
    prior_art_risk: float
    adjudication_cost_usd: float
    reproducibility_runs: int
    external_reproductions: int
    claim_specificity: float
    resolution_clarity: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_object(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def evidence_score(evidence: List[Evidence]) -> int:
    present = {item.kind for item in evidence}
    return sum(EVIDENCE_WEIGHTS.get(kind, 0) for kind in present)


def evidence_tier(evidence: List[Evidence]) -> Dict[str, Any]:
    present = {item.kind for item in evidence}
    current = TIER_LADDER[0]
    for tier in TIER_LADDER[1:]:
        required = tier["required"]
        if required in present:
            current = tier
        else:
            break
    return {"tier": current["tier"], "name": current["name"]}


def evidence_entropy(evidence: List[Evidence]) -> float:
    """Normalized Shannon entropy over evidence-kind weights.

    More diverse evidence kinds produce a higher entropy value. Repeating the
    same evidence type should not create a false sense of underwriting depth.
    """
    weights = [EVIDENCE_WEIGHTS[item.kind] for item in evidence if item.kind in EVIDENCE_WEIGHTS]
    total = sum(weights)
    if total <= 0 or len(weights) <= 1:
        return 0.0
    probs = [w / total for w in weights]
    entropy = -sum(p * math.log(p, 2) for p in probs if p > 0)
    max_entropy = math.log(len(weights), 2)
    return round(clamp(entropy / max_entropy), 6)


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def hot_tensor_underwrite(inp: HotTensorInput) -> Dict[str, Any]:
    """Deterministic underwriting math for a bondable claim.

    This is not ML and not a scientific result. It is a transparent scoring
    kernel that turns claim evidence into an inspectable financeability score.

    Vector x:
        x0 = evidence_score / 100
        x1 = evidence_tier / 8
        x2 = min(stake / claimed_value, 1)
        x3 = 1 - prior_art_risk
        x4 = 1 - min(adjudication_cost / stake, 1)
        x5 = log1p(reproducibility_runs) / log1p(10)
        x6 = min(external_reproductions / 3, 1)
        x7 = claim_specificity
        x8 = resolution_clarity

    Heat H is a bounded weighted sum. Risk R penalizes vague, expensive,
    weakly reproduced, high-prior-art-risk claims. Final underwrite score U
    is the bounded difference H - R.
    """
    stake_coverage = clamp(safe_ratio(inp.stake_usd, inp.claimed_value_usd))
    adjudication_efficiency = 1.0 - clamp(safe_ratio(inp.adjudication_cost_usd, max(inp.stake_usd, 1.0)))
    reproducibility_signal = clamp(math.log1p(max(inp.reproducibility_runs, 0)) / math.log1p(10))
    external_signal = clamp(inp.external_reproductions / 3.0)

    x = {
        "evidence_strength": clamp(inp.evidence_score / 100.0),
        "tier_strength": clamp(inp.evidence_tier / 8.0),
        "stake_coverage": stake_coverage,
        "novelty_safety": 1.0 - clamp(inp.prior_art_risk),
        "adjudication_efficiency": adjudication_efficiency,
        "reproducibility_signal": reproducibility_signal,
        "external_signal": external_signal,
        "claim_specificity": clamp(inp.claim_specificity),
        "resolution_clarity": clamp(inp.resolution_clarity),
    }

    weights = {
        "evidence_strength": 0.18,
        "tier_strength": 0.14,
        "stake_coverage": 0.12,
        "novelty_safety": 0.10,
        "adjudication_efficiency": 0.10,
        "reproducibility_signal": 0.12,
        "external_signal": 0.08,
        "claim_specificity": 0.08,
        "resolution_clarity": 0.08,
    }

    heat = sum(x[k] * weights[k] for k in weights)
    heat = clamp(heat)

    risk_terms = {
        "prior_art_risk": 0.22 * clamp(inp.prior_art_risk),
        "weak_stake": 0.18 * (1.0 - stake_coverage),
        "adjudication_drag": 0.16 * (1.0 - adjudication_efficiency),
        "low_reproducibility": 0.16 * (1.0 - reproducibility_signal),
        "no_external_reproduction": 0.10 * (1.0 - external_signal),
        "claim_vagueness": 0.09 * (1.0 - clamp(inp.claim_specificity)),
        "resolution_vagueness": 0.09 * (1.0 - clamp(inp.resolution_clarity)),
    }
    risk = clamp(sum(risk_terms.values()))
    underwrite_score = clamp(heat - 0.55 * risk)

    if underwrite_score >= 0.75:
        decision = "underwritable_subject_to_review"
    elif underwrite_score >= 0.50:
        decision = "conditionally_underwritable"
    elif underwrite_score >= 0.30:
        decision = "weak_underwriting_candidate"
    else:
        decision = "not_underwritable_yet"

    return {
        "schema": "overllm.hot_tensor_underwriting.v1",
        "input_vector": x,
        "weights": weights,
        "heat": round(heat, 6),
        "risk_terms": {k: round(v, 6) for k, v in risk_terms.items()},
        "risk": round(risk, 6),
        "underwrite_score": round(underwrite_score, 6),
        "decision": decision,
        "formula": "U = clamp(sum_i(w_i*x_i) - 0.55*sum_j(r_j), 0, 1)",
        "interpretation": "Transparent deterministic scoring, not a learned model and not external validation.",
    }


def firewall(wording: str, tier: int) -> Dict[str, Any]:
    lower = wording.lower()
    violations = []
    for term, required_tier in BLOCKED_TERMS.items():
        if term in lower and tier < required_tier:
            violations.append(
                {
                    "term": term,
                    "required_tier": required_tier,
                    "current_tier": tier,
                }
            )
    return {"allowed": len(violations) == 0, "violations": violations}


def build_value_packet(args: argparse.Namespace) -> Dict[str, Any]:
    created_at = utc_now()

    evidence = [
        Evidence(
            kind="implementation",
            description="Single-file implementation exists and constructs a value packet.",
            receipt="self:file_present",
            created_at=created_at,
        ),
        Evidence(
            kind="clean_build",
            description="The file runs with the standard Python interpreter and no third-party dependencies.",
            receipt=f"python:{platform.python_version()}",
            created_at=created_at,
        ),
        Evidence(
            kind="smoke_test",
            description="The demo constructed a claim, bond, resolution rule, evidence list, packet hash, and receipt hash in one execution.",
            receipt="runtime:self_smoke_pass",
            created_at=created_at,
        ),
    ]

    score = evidence_score(evidence)
    tier = evidence_tier(evidence)
    entropy = evidence_entropy(evidence)

    bond = Bond(
        stake_usd=args.stake_usd,
        claimant=args.claimant,
        counterparty=args.counterparty,
        forfeiture_condition="Stake is forfeited if the resolution procedure fails under the stated pass condition.",
    )

    resolution = ResolutionRule(
        resolver=args.resolver,
        resolution_date=args.resolution_date,
        procedure=args.procedure,
        pass_condition=args.pass_condition,
        fail_condition=args.fail_condition,
    )

    hot_tensor = hot_tensor_underwrite(
        HotTensorInput(
            evidence_score=score,
            evidence_tier=tier["tier"],
            stake_usd=args.stake_usd,
            claimed_value_usd=args.claimed_value_usd,
            prior_art_risk=args.prior_art_risk,
            adjudication_cost_usd=args.adjudication_cost_usd,
            reproducibility_runs=args.reproducibility_runs,
            external_reproductions=args.external_reproductions,
            claim_specificity=args.claim_specificity,
            resolution_clarity=args.resolution_clarity,
        )
    )

    public_wording = args.public_wording
    claim_firewall = firewall(public_wording, tier["tier"])

    packet_body = {
        "schema": "overllm.value_packet.v1",
        "packet_id": "vp_" + uuid.uuid4().hex[:16],
        "created_at": created_at,
        "honest_label": "Tier-3 candidate: stable internal proof, not breakthrough status.",
        "claim": {
            "name": args.claim_name,
            "plain_claim": args.claim,
            "technical_claim": args.technical_claim,
            "allowed_public_wording": public_wording if claim_firewall["allowed"] else None,
            "blocked_public_wording": public_wording if not claim_firewall["allowed"] else None,
            "claim_firewall": claim_firewall,
        },
        "bond": dataclasses.asdict(bond),
        "resolution_rule": dataclasses.asdict(resolution),
        "evidence": [dataclasses.asdict(item) for item in evidence],
        "evidence_score": score,
        "evidence_entropy": entropy,
        "evidence_tier": tier,
        "hot_tensor_underwriting": hot_tensor,
        "provenance": {
            "runtime": "python",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "argv_hash": sha256_text(" ".join(sys.argv)),
            "generated_by": "tools/value_packet_demo.py",
        },
        "limitations": [
            "This is an internal smoke artifact, not external validation.",
            "No prior-art search was performed by this file.",
            "No baseline comparison was performed by this file.",
            "No ablation or repeated-seed study was performed by this file.",
            "HotTensor underwriting is deterministic scoring, not a learned model.",
            "No public scientific breakthrough claim is allowed from this evidence tier.",
        ],
    }

    packet_hash = hash_object(packet_body)
    receipt = {
        "schema": "overllm.value_packet_receipt.v1",
        "packet_id": packet_body["packet_id"],
        "packet_hash": packet_hash,
        "receipt_id": "receipt_" + uuid.uuid4().hex[:16],
        "created_at": utc_now(),
        "chain": [
            {"step": "claim", "hash": hash_object(packet_body["claim"])},
            {"step": "bond", "hash": hash_object(packet_body["bond"])},
            {"step": "resolution_rule", "hash": hash_object(packet_body["resolution_rule"])},
            {"step": "evidence", "hash": hash_object(packet_body["evidence"])},
            {"step": "hot_tensor_underwriting", "hash": hash_object(packet_body["hot_tensor_underwriting"])},
            {"step": "packet", "hash": packet_hash},
        ],
    }

    receipt["receipt_hash"] = hash_object(receipt)

    return {
        "packet": packet_body,
        "receipt": receipt,
        "appraisal_note": {
            "status": "runnable_demo_artifact",
            "tier": tier,
            "market_meaning": "Demonstrates receipted exchange primitive: claim + evidence + bond + settlement rule + provenance + HotTensor underwriting + hash receipt.",
            "not_allowed_claim": "This file is not a scientific breakthrough.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an OverLLM Tier-3 value packet demo.")
    parser.add_argument("--claim-name", default="Bondable Claim Receipt Demo")
    parser.add_argument(
        "--claim",
        default="A claim becomes more financeable when bundled with evidence, provenance, a settlement rule, a bond field, and a receipt.",
    )
    parser.add_argument(
        "--technical-claim",
        default="This single-file demo deterministically emits a JSON value packet and hash-chained receipt containing claim, evidence, bond, resolution, HotTensor underwriting, and provenance fields.",
    )
    parser.add_argument(
        "--public-wording",
        default="Internally stable single-file demo of a receipted value packet primitive with deterministic HotTensor underwriting.",
    )
    parser.add_argument("--stake-usd", type=float, default=100.0)
    parser.add_argument("--claimed-value-usd", type=float, default=1000.0)
    parser.add_argument("--prior-art-risk", type=float, default=0.50)
    parser.add_argument("--adjudication-cost-usd", type=float, default=25.0)
    parser.add_argument("--reproducibility-runs", type=int, default=1)
    parser.add_argument("--external-reproductions", type=int, default=0)
    parser.add_argument("--claim-specificity", type=float, default=0.82)
    parser.add_argument("--resolution-clarity", type=float, default=0.88)
    parser.add_argument("--claimant", default="claimant")
    parser.add_argument("--counterparty", default="counterparty")
    parser.add_argument("--resolver", default="human reviewer using the stated procedure")
    parser.add_argument("--resolution-date", default="2026-07-08")
    parser.add_argument(
        "--procedure",
        default="Run the file with Python 3, inspect the JSON output, verify packet_hash and receipt_hash by recomputing canonical SHA-256 hashes.",
    )
    parser.add_argument(
        "--pass-condition",
        default="Program exits successfully and emits packet, receipt, packet_hash, receipt_hash, evidence tier, HotTensor underwriting, and firewall result.",
    )
    parser.add_argument(
        "--fail-condition",
        default="Program crashes, omits required packet fields, or produces hashes that cannot be recomputed from canonical JSON.",
    )
    return parser.parse_args()


def main() -> int:
    start = time.time()
    args = parse_args()
    output = build_value_packet(args)
    output["runtime_ms"] = round((time.time() - start) * 1000, 3)
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
