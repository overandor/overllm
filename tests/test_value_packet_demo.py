import importlib.util
import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO_PATH = ROOT / "tools" / "value_packet_demo.py"


spec = importlib.util.spec_from_file_location("value_packet_demo", DEMO_PATH)
value_packet_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(value_packet_demo)


def run_demo(*args):
    command = [sys.executable, str(DEMO_PATH), *args]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def test_demo_emits_packet_receipt_and_appraisal_note():
    output = run_demo()

    assert set(output.keys()) >= {"packet", "receipt", "appraisal_note", "runtime_ms"}
    assert output["packet"]["schema"] == "overllm.value_packet.v1"
    assert output["receipt"]["schema"] == "overllm.value_packet_receipt.v1"
    assert output["appraisal_note"]["not_allowed_claim"] == "This file is not a scientific breakthrough."


def test_packet_has_required_financeability_sections():
    output = run_demo("--stake-usd", "150", "--claimed-value-usd", "1000")
    packet = output["packet"]

    required = {
        "claim",
        "bond",
        "resolution_rule",
        "evidence",
        "evidence_score",
        "evidence_entropy",
        "evidence_tier",
        "hot_tensor_underwriting",
        "provenance",
        "limitations",
    }
    assert required.issubset(packet.keys())
    assert packet["bond"]["stake_usd"] == 150.0
    assert packet["evidence_tier"]["tier"] == 3
    assert packet["evidence_tier"]["name"] == "stable_internal_proof"


def test_receipt_hashes_are_recomputable():
    output = run_demo()
    packet = output["packet"]
    receipt = output["receipt"]

    expected_packet_hash = value_packet_demo.hash_object(packet)
    assert receipt["packet_hash"] == expected_packet_hash

    receipt_without_hash = dict(receipt)
    actual_receipt_hash = receipt_without_hash.pop("receipt_hash")
    expected_receipt_hash = value_packet_demo.hash_object(receipt_without_hash)
    assert actual_receipt_hash == expected_receipt_hash

    chain = {entry["step"]: entry["hash"] for entry in receipt["chain"]}
    assert chain["claim"] == value_packet_demo.hash_object(packet["claim"])
    assert chain["bond"] == value_packet_demo.hash_object(packet["bond"])
    assert chain["resolution_rule"] == value_packet_demo.hash_object(packet["resolution_rule"])
    assert chain["evidence"] == value_packet_demo.hash_object(packet["evidence"])
    assert chain["hot_tensor_underwriting"] == value_packet_demo.hash_object(packet["hot_tensor_underwriting"])
    assert chain["packet"] == expected_packet_hash


def test_claim_firewall_blocks_overclaiming():
    output = run_demo("--public-wording", "This is a breakthrough world-first result")
    claim = output["packet"]["claim"]

    assert claim["allowed_public_wording"] is None
    assert claim["blocked_public_wording"] == "This is a breakthrough world-first result"
    assert claim["claim_firewall"]["allowed"] is False
    blocked_terms = {v["term"] for v in claim["claim_firewall"]["violations"]}
    assert "breakthrough" in blocked_terms
    assert "world-first" in blocked_terms


def test_claim_firewall_allows_tier_appropriate_wording():
    output = run_demo("--public-wording", "Internally stable receipt demo")
    claim = output["packet"]["claim"]

    assert claim["allowed_public_wording"] == "Internally stable receipt demo"
    assert claim["blocked_public_wording"] is None
    assert claim["claim_firewall"]["allowed"] is True


def test_hot_tensor_underwriting_is_bounded_and_deterministic_shape():
    output = run_demo(
        "--stake-usd",
        "100",
        "--claimed-value-usd",
        "1000",
        "--prior-art-risk",
        "0.5",
        "--adjudication-cost-usd",
        "25",
        "--reproducibility-runs",
        "1",
        "--external-reproductions",
        "0",
        "--claim-specificity",
        "0.82",
        "--resolution-clarity",
        "0.88",
    )
    hot = output["packet"]["hot_tensor_underwriting"]

    assert hot["schema"] == "overllm.hot_tensor_underwriting.v1"
    assert 0.0 <= hot["heat"] <= 1.0
    assert 0.0 <= hot["risk"] <= 1.0
    assert 0.0 <= hot["underwrite_score"] <= 1.0
    assert hot["decision"] in {
        "underwritable_subject_to_review",
        "conditionally_underwritable",
        "weak_underwriting_candidate",
        "not_underwritable_yet",
    }
    assert set(hot["input_vector"].keys()) == {
        "evidence_strength",
        "tier_strength",
        "stake_coverage",
        "novelty_safety",
        "adjudication_efficiency",
        "reproducibility_signal",
        "external_signal",
        "claim_specificity",
        "resolution_clarity",
    }


def test_hot_tensor_rewards_stronger_claim_conditions():
    weak = run_demo(
        "--stake-usd",
        "25",
        "--claimed-value-usd",
        "1000",
        "--prior-art-risk",
        "0.9",
        "--adjudication-cost-usd",
        "200",
        "--reproducibility-runs",
        "0",
        "--external-reproductions",
        "0",
        "--claim-specificity",
        "0.35",
        "--resolution-clarity",
        "0.40",
    )["packet"]["hot_tensor_underwriting"]

    stronger = run_demo(
        "--stake-usd",
        "500",
        "--claimed-value-usd",
        "1000",
        "--prior-art-risk",
        "0.2",
        "--adjudication-cost-usd",
        "25",
        "--reproducibility-runs",
        "5",
        "--external-reproductions",
        "1",
        "--claim-specificity",
        "0.90",
        "--resolution-clarity",
        "0.95",
    )["packet"]["hot_tensor_underwriting"]

    assert stronger["heat"] > weak["heat"]
    assert stronger["risk"] < weak["risk"]
    assert stronger["underwrite_score"] > weak["underwrite_score"]


def test_evidence_entropy_is_bounded():
    output = run_demo()
    entropy = output["packet"]["evidence_entropy"]
    assert 0.0 <= entropy <= 1.0


def test_cli_accepts_custom_claim_inputs():
    output = run_demo(
        "--claim-name",
        "Custom Claim",
        "--claim",
        "Custom plain claim",
        "--technical-claim",
        "Custom technical claim",
        "--claimant",
        "alice",
        "--counterparty",
        "bob",
    )
    packet = output["packet"]

    assert packet["claim"]["name"] == "Custom Claim"
    assert packet["claim"]["plain_claim"] == "Custom plain claim"
    assert packet["claim"]["technical_claim"] == "Custom technical claim"
    assert packet["bond"]["claimant"] == "alice"
    assert packet["bond"]["counterparty"] == "bob"
