import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
PLANNER_PATH = ROOT / "tools" / "overgpt_ml_functionality_planner.py"


spec = importlib.util.spec_from_file_location("overgpt_ml_functionality_planner", PLANNER_PATH)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


def run_planner(*args):
    completed = subprocess.run([sys.executable, str(PLANNER_PATH), *args], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def test_default_planner_emits_ranked_report():
    report = run_planner()

    assert report["schema"] == "overgpt.ml_functionality_planner.v1"
    assert report["model_type"] == "deterministic_tiny_mlp"
    assert "cannot auto-merge" in report["safety_posture"]
    assert len(report["ranked_proposals"]) >= 3
    assert report["next_best_safe_action"]
    assert report["report_hash"]


def test_all_scores_are_bounded():
    report = run_planner()

    for item in report["ranked_proposals"]:
        assert 0.0 <= item["value_score"] <= 1.0
        assert 0.0 <= item["merge_readiness_score"] <= 1.0
        for value in item["features"].values():
            assert 0.0 <= value <= 1.0


def test_unsafe_self_modifying_auto_merge_is_blocked():
    report = run_planner()
    unsafe = next(item for item in report["ranked_proposals"] if item["proposal"]["name"] == "Unsafe self-modifying auto-merge loop")

    assert unsafe["safety_gate"]["allowed_to_auto_merge"] is False
    assert unsafe["safety_gate"]["merge_requires_human_review"] is True
    assert "human_approval_required_for_repo_evolution" in unsafe["safety_gate"]["blocks"]
    assert "proposal_contains_high_risk_terms" in unsafe["safety_gate"]["blocks"]
    assert unsafe["recommendation"] == "revise_before_pr"


def test_safe_baseline_proposal_scores_above_unsafe_proposal():
    report = run_planner()
    by_name = {item["proposal"]["name"]: item for item in report["ranked_proposals"]}

    safe = by_name["Baseline comparison for OverGPT value packets"]
    unsafe = by_name["Unsafe self-modifying auto-merge loop"]

    assert safe["value_score"] > unsafe["value_score"]
    assert safe["merge_readiness_score"] > unsafe["merge_readiness_score"]
    assert safe["safety_gate"]["blocks"] == []


def test_custom_input_file_is_supported():
    payload = {
        "proposals": [
            {
                "name": "Receipt quality dashboard",
                "description": "Add documentation, CI, and tests for receipt quality review.",
                "expected_value": 0.74,
                "complexity": 0.30,
                "blast_radius": 0.20,
                "test_plan": "Unit tests and CI smoke test.",
                "files": ["tools/receipt_dashboard.py", "tests/test_receipt_dashboard.py", "docs/RECEIPTS.md"],
                "requires_human_approval": True,
            }
        ]
    }
    with tempfile.NamedTemporaryFile("w+", suffix=".json", encoding="utf-8") as f:
        json.dump(payload, f)
        f.flush()
        report = run_planner("--input", f.name)

    assert len(report["ranked_proposals"]) == 1
    item = report["ranked_proposals"][0]
    assert item["proposal"]["name"] == "Receipt quality dashboard"
    assert item["safety_gate"]["allowed_to_auto_merge"] is False
    assert item["safety_gate"]["merge_requires_human_review"] is True


def test_proposal_hash_changes_when_inputs_change():
    p1 = planner.Proposal(
        name="A",
        description="Add tests and receipts",
        expected_value=0.5,
        complexity=0.3,
        blast_radius=0.2,
        test_plan="CI test",
        files=["tests/test_a.py"],
    )
    p2 = planner.Proposal(
        name="B",
        description="Add tests and receipts",
        expected_value=0.5,
        complexity=0.3,
        blast_radius=0.2,
        test_plan="CI test",
        files=["tests/test_a.py"],
    )

    assert planner.score_proposal(p1)["proposal_hash"] != planner.score_proposal(p2)["proposal_hash"]
