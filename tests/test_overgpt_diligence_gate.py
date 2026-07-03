import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO_PATH = ROOT / "tools" / "value_packet_demo.py"
GATE_PATH = ROOT / "tools" / "overgpt_diligence_gate.py"


spec = importlib.util.spec_from_file_location("overgpt_diligence_gate", GATE_PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def run_demo():
    completed = subprocess.run([sys.executable, str(DEMO_PATH)], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def run_gate(doc, target=3_000_000):
    with tempfile.NamedTemporaryFile("w+", suffix=".json", encoding="utf-8") as f:
        json.dump(doc, f)
        f.flush()
        completed = subprocess.run(
            [sys.executable, str(GATE_PATH), f.name, "--target-valuation-usd", str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    return json.loads(completed.stdout)


def test_gate_emits_enterprise_report_shape():
    doc = run_demo()
    report = run_gate(doc)

    assert report["schema"] == "overgpt.enterprise_diligence_report.v1"
    assert report["target_valuation_usd"] == 3_000_000.0
    assert 0.0 <= report["enterprise_score"] <= 1.0
    assert report["readiness_label"] in {
        "enterprise_diligence_ready",
        "strategic_review_candidate",
        "serious_builder_asset",
        "prototype_asset",
        "pre_diligence_artifact",
    }
    assert 0.0 <= report["evidence_based_valuation_ceiling_usd"] <= 3_000_000.0
    assert "gates" in report
    assert "missing_to_defend_target" in report


def test_current_demo_does_not_magically_reach_three_million():
    doc = run_demo()
    report = run_gate(doc, target=3_000_000)

    assert report["evidence_based_valuation_ceiling_usd"] < 3_000_000.0
    assert report["target_gap_usd"] > 0.0
    assert "This report does not establish market value" in report["claim_limit"]


def test_commercial_legal_and_deployment_evidence_raise_score():
    base_doc = run_demo()
    base_report = run_gate(base_doc)

    stronger_doc = json.loads(json.dumps(base_doc))
    packet = stronger_doc["packet"]
    packet["commercial"] = {
        "users": 25,
        "revenue_usd": 12000,
        "retention": "measured",
        "pipeline_usd": 75000,
        "signed_counterparties": 2,
    }
    packet["legal"] = {
        "license": "defined",
        "ip_assignment": "documented",
        "privacy_review": "complete",
        "security_review": "complete",
        "terms": "drafted",
    }
    packet["deployment"] = {
        "live_url": "https://example.invalid",
        "healthcheck": "passing",
        "version": "demo",
        "logs": "available",
        "rollback_plan": "documented",
    }
    stronger_doc["ci"] = True

    stronger_report = run_gate(stronger_doc)

    assert stronger_report["enterprise_score"] > base_report["enterprise_score"]
    assert stronger_report["evidence_based_valuation_ceiling_usd"] > base_report["evidence_based_valuation_ceiling_usd"]
    assert len(stronger_report["missing_to_defend_target"]) < len(base_report["missing_to_defend_target"])


def test_gate_weights_cover_expected_diligence_categories():
    doc = run_demo()
    report = run_gate(doc)
    gate_names = {g["name"] for g in report["gates"]}

    assert gate_names == {
        "value_packet_integrity",
        "receipt_verifiability",
        "evidence_strength",
        "underwriting_readiness",
        "runtime_proof",
        "commercial_evidence",
        "legal_transferability",
        "deployment_evidence",
    }


def test_valuation_ceiling_is_convex_and_bounded():
    target = 3_000_000.0
    low = gate.valuation_ceiling_usd(0.25, target)
    mid = gate.valuation_ceiling_usd(0.50, target)
    high = gate.valuation_ceiling_usd(0.85, target)

    assert 0 <= low < mid < high < target
    assert gate.valuation_ceiling_usd(1.0, target) == target
    assert gate.valuation_ceiling_usd(2.0, target) == target
    assert gate.valuation_ceiling_usd(-1.0, target) == 0.0
