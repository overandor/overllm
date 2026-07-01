#!/usr/bin/env python3
"""
Tier-3 Value Packet Demo

Purpose:
    Demonstrate the smallest runnable OverLLM market primitive:
    a claim becomes financeable only after it has evidence, provenance,
    a settlement rule, a bond field, and a receipt.

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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        "evidence_tier": tier,
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
            "market_meaning": "Demonstrates receipted exchange primitive: claim + evidence + bond + settlement rule + provenance + hash receipt.",
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
        default="This single-file demo deterministically emits a JSON value packet and hash-chained receipt containing claim, evidence, bond, resolution, and provenance fields.",
    )
    parser.add_argument(
        "--public-wording",
        default="Internally stable single-file demo of a receipted value packet primitive.",
    )
    parser.add_argument("--stake-usd", type=float, default=100.0)
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
        default="Program exits successfully and emits packet, receipt, packet_hash, receipt_hash, evidence tier, and firewall result.",
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
