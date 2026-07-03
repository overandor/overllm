#!/usr/bin/env python3
"""
OverGPT Enterprise Diligence Gate

This tool reads a value packet JSON file and produces a strict valuation-readiness
report. It does not assert that the repository is worth a target amount. It
measures the evidence gap between the current artifact and a target valuation.

Run:
    python3 tools/value_packet_demo.py > value_packet_output.json
    python3 tools/overgpt_diligence_gate.py value_packet_output.json --target-valuation-usd 3000000
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class Gate:
    name: str
    weight: float
    score: float
    reason: str
    missing: Tuple[str, ...]


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def load_json(path: str) -> Dict[str, Any]:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_packet(doc: Dict[str, Any]) -> Dict[str, Any]:
    if "packet" in doc and isinstance(doc["packet"], dict):
        return doc["packet"]
    return doc


def has_path(obj: Dict[str, Any], path: str) -> bool:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def count_present(packet: Dict[str, Any], paths: List[str]) -> int:
    return sum(1 for path in paths if has_path(packet, path))


def value_packet_gate(packet: Dict[str, Any]) -> Gate:
    required = [
        "claim",
        "bond",
        "resolution_rule",
        "evidence",
        "evidence_score",
        "evidence_tier",
        "hot_tensor_underwriting",
        "provenance",
        "limitations",
    ]
    present = count_present(packet, required)
    missing = tuple(path for path in required if not has_path(packet, path))
    score = present / len(required)
    return Gate(
        name="value_packet_integrity",
        weight=0.14,
        score=score,
        reason=f"{present}/{len(required)} required value-packet sections are present.",
        missing=missing,
    )


def receipt_gate(doc: Dict[str, Any]) -> Gate:
    receipt = doc.get("receipt", {})
    required = ["schema", "packet_id", "packet_hash", "receipt_id", "created_at", "chain", "receipt_hash"]
    present = count_present(receipt, required)
    chain = receipt.get("chain", []) if isinstance(receipt, dict) else []
    chain_steps = {entry.get("step") for entry in chain if isinstance(entry, dict)}
    required_steps = {"claim", "bond", "resolution_rule", "evidence", "hot_tensor_underwriting", "packet"}
    chain_score = len(chain_steps & required_steps) / len(required_steps)
    field_score = present / len(required)
    score = 0.55 * field_score + 0.45 * chain_score
    missing_fields = [path for path in required if not has_path(receipt, path)]
    missing_steps = [f"chain.{step}" for step in sorted(required_steps - chain_steps)]
    return Gate(
        name="receipt_verifiability",
        weight=0.14,
        score=score,
        reason=f"Receipt fields score {field_score:.2f}; receipt chain score {chain_score:.2f}.",
        missing=tuple(missing_fields + missing_steps),
    )


def evidence_gate(packet: Dict[str, Any]) -> Gate:
    evidence_score = float(packet.get("evidence_score", 0.0)) / 100.0
    tier = packet.get("evidence_tier", {}).get("tier", 0)
    tier_score = float(tier) / 8.0
    entropy = float(packet.get("evidence_entropy", 0.0))
    score = clamp(0.45 * evidence_score + 0.35 * tier_score + 0.20 * entropy)
    missing = []
    if tier < 4:
        missing.append("baseline_comparison")
    if tier < 5:
        missing.append("ablation")
    if tier < 6:
        missing.append("repeated_runs")
    if tier < 8:
        missing.append("external_reproduction")
    return Gate(
        name="evidence_strength",
        weight=0.14,
        score=score,
        reason=f"Evidence score={packet.get('evidence_score', 0)}, tier={tier}, entropy={entropy}.",
        missing=tuple(missing),
    )


def underwriting_gate(packet: Dict[str, Any]) -> Gate:
    hot = packet.get("hot_tensor_underwriting", {})
    underwrite_score = float(hot.get("underwrite_score", 0.0))
    decision = hot.get("decision", "unknown")
    missing = []
    if underwrite_score < 0.50:
        missing.append("underwrite_score_above_0_50")
    if underwrite_score < 0.75:
        missing.append("underwrite_score_above_0_75_for_enterprise_grade")
    return Gate(
        name="underwriting_readiness",
        weight=0.12,
        score=clamp(underwrite_score),
        reason=f"HotTensor decision={decision}; score={underwrite_score}.",
        missing=tuple(missing),
    )


def runtime_gate(doc: Dict[str, Any]) -> Gate:
    runtime_ms = doc.get("runtime_ms")
    packet = get_packet(doc)
    runtime_present = runtime_ms is not None
    provenance_present = has_path(packet, "provenance.python_version") and has_path(packet, "provenance.generated_by")
    ci_present = bool(doc.get("ci", False))
    score = 0.45 * float(runtime_present) + 0.35 * float(provenance_present) + 0.20 * float(ci_present)
    missing = []
    if not runtime_present:
        missing.append("runtime_ms")
    if not provenance_present:
        missing.append("runtime_provenance")
    if not ci_present:
        missing.append("ci_attestation_in_packet_or_report")
    return Gate(
        name="runtime_proof",
        weight=0.10,
        score=score,
        reason=f"Runtime present={runtime_present}; provenance present={provenance_present}; CI attestation present={ci_present}.",
        missing=tuple(missing),
    )


def commercial_gate(packet: Dict[str, Any]) -> Gate:
    commercial = packet.get("commercial", {})
    required = ["users", "revenue_usd", "retention", "pipeline_usd", "signed_counterparties"]
    present = count_present(commercial, required) if isinstance(commercial, dict) else 0
    score = present / len(required)
    return Gate(
        name="commercial_evidence",
        weight=0.14,
        score=score,
        reason=f"{present}/{len(required)} commercial evidence fields are present.",
        missing=tuple(path for path in required if not has_path(commercial, path)),
    )


def legal_gate(packet: Dict[str, Any]) -> Gate:
    legal = packet.get("legal", {})
    required = ["license", "ip_assignment", "privacy_review", "security_review", "terms"]
    present = count_present(legal, required) if isinstance(legal, dict) else 0
    score = present / len(required)
    return Gate(
        name="legal_transferability",
        weight=0.10,
        score=score,
        reason=f"{present}/{len(required)} legal-transfer fields are present.",
        missing=tuple(path for path in required if not has_path(legal, path)),
    )


def deployment_gate(packet: Dict[str, Any]) -> Gate:
    deployment = packet.get("deployment", {})
    required = ["live_url", "healthcheck", "version", "logs", "rollback_plan"]
    present = count_present(deployment, required) if isinstance(deployment, dict) else 0
    score = present / len(required)
    return Gate(
        name="deployment_evidence",
        weight=0.12,
        score=score,
        reason=f"{present}/{len(required)} deployment evidence fields are present.",
        missing=tuple(path for path in required if not has_path(deployment, path)),
    )


def enterprise_score(gates: List[Gate]) -> float:
    total_weight = sum(g.weight for g in gates)
    if total_weight <= 0:
        return 0.0
    return clamp(sum(g.weight * g.score for g in gates) / total_weight)


def valuation_ceiling_usd(score: float, target_valuation_usd: float) -> float:
    # Convex evidence penalty: early proof helps, but enterprise pricing requires
    # much higher proof density than artifact pricing. This intentionally prevents
    # thin evidence from producing a target-level valuation.
    return target_valuation_usd * math.pow(clamp(score), 2.35)


def readiness_label(score: float) -> str:
    if score >= 0.90:
        return "enterprise_diligence_ready"
    if score >= 0.75:
        return "strategic_review_candidate"
    if score >= 0.55:
        return "serious_builder_asset"
    if score >= 0.35:
        return "prototype_asset"
    return "pre_diligence_artifact"


def build_report(doc: Dict[str, Any], target_valuation_usd: float) -> Dict[str, Any]:
    packet = get_packet(doc)
    gates = [
        value_packet_gate(packet),
        receipt_gate(doc),
        evidence_gate(packet),
        underwriting_gate(packet),
        runtime_gate(doc),
        commercial_gate(packet),
        legal_gate(packet),
        deployment_gate(packet),
    ]
    score = enterprise_score(gates)
    ceiling = valuation_ceiling_usd(score, target_valuation_usd)
    missing = sorted({item for gate in gates for item in gate.missing})
    return {
        "schema": "overgpt.enterprise_diligence_report.v1",
        "target_valuation_usd": target_valuation_usd,
        "enterprise_score": round(score, 6),
        "readiness_label": readiness_label(score),
        "evidence_based_valuation_ceiling_usd": round(ceiling, 2),
        "target_gap_usd": round(max(0.0, target_valuation_usd - ceiling), 2),
        "gates": [
            {
                "name": gate.name,
                "weight": gate.weight,
                "score": round(gate.score, 6),
                "reason": gate.reason,
                "missing": list(gate.missing),
            }
            for gate in gates
        ],
        "missing_to_defend_target": missing,
        "claim_limit": "This report does not establish market value; it establishes evidence readiness for diligence.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score OverGPT value-packet diligence readiness.")
    parser.add_argument("packet_json", help="Path to value packet JSON, or - for stdin.")
    parser.add_argument("--target-valuation-usd", type=float, default=3_000_000.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    doc = load_json(args.packet_json)
    report = build_report(doc, args.target_valuation_usd)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
