import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from rstf_bpe_token_cost import DEFAULT_VOCAB_DIR, render_markdown, run_bpe_token_cost_benchmark


def test_benchmark_covers_all_160_examples():
    report = run_bpe_token_cost_benchmark(DEFAULT_VOCAB_DIR)
    assert report["overall"]["count"] == 160
    assert set(report["per_transform"].keys()) == {
        "reversed", "upside_down", "bidi_override", "homoglyph",
    }


def test_overall_token_savings_is_positive():
    report = run_bpe_token_cost_benchmark(DEFAULT_VOCAB_DIR)
    assert report["overall"]["token_savings_ratio"] > 0.3


def test_reversed_shows_real_token_savings_unlike_the_byte_proxy():
    # This is the key result that distinguishes real tokenizer measurement
    # from the UTF-8 byte-length proxy in tools/rstf_token_cost.py: byte
    # count structurally cannot change under reordering (0.0% there), but
    # BPE token count can, because merges are learned from forward-reading
    # text. This must stay clearly positive, not near zero, or the module
    # docstring's explanation is wrong.
    report = run_bpe_token_cost_benchmark(DEFAULT_VOCAB_DIR)
    assert report["per_transform"]["reversed"]["token_savings_ratio"] > 0.2


def test_markdown_report_documents_the_tokenizer_scope():
    report = run_bpe_token_cost_benchmark(DEFAULT_VOCAB_DIR)
    md = render_markdown(report)
    assert "not GPT-4/Claude/Llama" in md
    assert "## Per-transform" in md


def test_bpe_token_cost_summary_shape():
    report = run_bpe_token_cost_benchmark(DEFAULT_VOCAB_DIR)
    assert report["metric"] == "overllm_bpe_token_count"
    assert report["overall"]["count"] > 0
    assert "per_transform" in report
    assert report["truth_label"] == "real_tokenizer_measurement_small_repo_trained_vocab_not_production_scale"


def test_bpe_token_cost_does_not_claim_provider_billing():
    report = run_bpe_token_cost_benchmark(DEFAULT_VOCAB_DIR)
    assert "not GPT-4/Claude/Llama" in report["metric_note"]
    assert "not_production_scale" in report["truth_label"]
