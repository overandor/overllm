import importlib.util
import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
LAB_PATH = ROOT / "tools" / "overgpt_viral_repo_lab.py"


spec = importlib.util.spec_from_file_location("overgpt_viral_repo_lab", LAB_PATH)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def run_lab(*args):
    completed = subprocess.run([sys.executable, str(LAB_PATH), *args], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def test_viral_repo_lab_emits_score_and_spec():
    output = run_lab("--idea", "AI receipt generator for repo claims")

    assert set(output.keys()) == {"score", "repo_spec"}
    assert output["score"]["schema"] == "overgpt.viral_repo_score.v1"
    assert 0.0 <= output["score"]["adoption_score"] <= 1.0
    assert output["repo_spec"]["repo_name"] == "ai-receipt-generator-for-repo-claims"


def test_unsafe_virus_framing_is_blocked_until_reframed():
    output = run_lab("--idea", "self modifying virus that auto merges to main")
    score = output["score"]

    assert score["safe_language"]["allowed"] is False
    assert "virus" in score["safe_language"]["blocked_terms"]
    assert score["decision"] == "blocked_until_reframed_safely"
    assert score["adoption_score"] <= 0.25


def test_safe_repo_framing_scores_better_than_unsafe_framing():
    safe = run_lab(
        "--idea",
        "single-file AI repo receipt generator with tests and CI",
        "--demo",
        "one-command demo with JSON output and screenshot",
        "--proof",
        "tests, CI, hash receipt, verification, baseline roadmap",
        "--safety-boundary",
        "safe human-reviewed automation with no unauthorized propagation",
    )["score"]

    unsafe = run_lab("--idea", "malware repo that steals credentials and spreads")["score"]

    assert safe["safe_language"]["allowed"] is True
    assert unsafe["safe_language"]["allowed"] is False
    assert safe["adoption_score"] > unsafe["adoption_score"]


def test_repo_spec_contains_launch_checklist_and_contributor_path():
    output = run_lab("--idea", "OverGPT value packet gallery")
    spec = output["repo_spec"]

    assert "One-command demo" in spec["readme_sections"]
    assert "Contributing" in spec["readme_sections"]
    assert any("No self-propagating" in item for item in spec["launch_checklist"])
    assert any("baseline" in item.lower() for item in spec["first_issues"])


def test_slugify_is_stable_and_safe():
    assert lab.slugify("OverGPT: Viral Repo Lab!!!") == "overgpt-viral-repo-lab"
    assert lab.slugify("---") == "overgpt-repo"


def test_score_has_expected_vectors():
    concept = lab.RepoConcept(
        idea="receipt backed demo repo",
        audience="developers",
        demo="one command demo",
        proof="tests and ci",
        safety_boundary="human approval and safe review",
    )
    score = lab.score_concept(concept)

    assert set(score["viral_vector"].keys()) == set(lab.POSITIVE_SIGNALS.keys())
    assert set(score["risk_vector"].keys()) == set(lab.RISK_SIGNALS.keys())
    assert 0.0 <= score["viral_heat"] <= 1.0
    assert 0.0 <= score["risk_drag"] <= 1.0
