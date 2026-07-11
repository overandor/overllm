from __future__ import annotations

import pytest

from tools import rstf_cost_pipeline as pipeline

from conftest import tiktoken_encoding_reachable


pytestmark = pytest.mark.skipif(
    not tiktoken_encoding_reachable(),
    reason="tiktoken not installed, or its encoding data is unreachable (egress-blocked) in this environment",
)


def test_pipeline_report_shape_and_truth_label():
    report = pipeline.run_pipeline(
        tiktoken_models=["gpt-4o-mini"],
        prices_per_1m={"gpt-4o-mini": 0.15},
        vocab_dir=pipeline.DEFAULT_VOCAB_DIR,
    )

    assert report["report_type"] == "RSTF Cost Reduction Comparison"
    assert report["truth_labels"]["report"] == pipeline.REPORT_TRUTH_LABEL
    assert len(report["models_tested"]) == 3  # one tiktoken + byte proxy + OverLLM BPE
    assert "pricing_disclaimer" in report
    assert "production_disclaimer" in report


def test_pipeline_contains_all_transform_breakdowns():
    report = pipeline.run_pipeline(
        tiktoken_models=["gpt-4o-mini"],
        prices_per_1m={},
        vocab_dir=pipeline.DEFAULT_VOCAB_DIR,
    )

    assert set(report["transform_breakdown"].keys()) == {
        "bidi_override",
        "homoglyph",
        "reversed",
        "upside_down",
    }


def test_pipeline_cost_estimate_uses_supplied_price_only():
    report = pipeline.run_pipeline(
        tiktoken_models=["gpt-4o-mini"],
        prices_per_1m={"gpt-4o-mini": 0.15},
        vocab_dir=pipeline.DEFAULT_VOCAB_DIR,
    )

    tiktoken_row = next(row for row in report["models_tested"] if row["model"] == "gpt-4o-mini")
    assert tiktoken_row["estimated_cost_saved_usd"] is not None
    assert tiktoken_row["pricing_source"] == "user_supplied_price_not_live_provider_pricing"


def test_pipeline_markdown_keeps_disclaimers():
    report = pipeline.run_pipeline(
        tiktoken_models=["gpt-4o-mini"],
        prices_per_1m={},
        vocab_dir=pipeline.DEFAULT_VOCAB_DIR,
    )
    markdown = pipeline.render_markdown(report)

    assert "not live provider pricing" in markdown
    assert "do not guarantee savings on arbitrary production traffic" in markdown
    assert pipeline.REPORT_TRUTH_LABEL in markdown
