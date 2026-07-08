from __future__ import annotations

import importlib.util

import pytest

from tools import rstf_tiktoken_cost as ttc


pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("tiktoken") is None,
    reason="tiktoken not installed in this environment",
)


def test_tiktoken_cost_summary_shape():
    report = ttc.run_tiktoken_cost_benchmark(encoding_name="cl100k_base")

    assert report["metric"] == "tiktoken_token_count"
    assert report["overall"]["count"] > 0
    assert report["encoding_resolved"] == "cl100k_base"
    assert "per_transform" in report
    assert report["truth_label"] == "real_tiktoken_count_for_selected_model_or_encoding_not_provider_bill"


def test_tiktoken_cost_does_not_claim_provider_billing():
    report = ttc.run_tiktoken_cost_benchmark(encoding_name="cl100k_base")

    assert "not a universal provider bill" in report["metric_note"]
    assert report["cost_estimate"]["truth_label"] == "no_price_supplied_no_cost_claim"


def test_input_cost_estimate_uses_caller_supplied_per_1m_price():
    estimate = ttc.estimate_input_cost_savings(tokens_saved=500_000, input_price_per_1m=2.0)

    assert estimate["input_cost_saved_usd"] == 1.0
    assert estimate["input_price_per_1m_tokens"] == 2.0
    assert estimate["truth_label"] == "user_supplied_price_not_live_provider_pricing"
