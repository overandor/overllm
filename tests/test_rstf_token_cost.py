import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.rstf_token_cost import render_markdown, run_token_cost_benchmark, utf8_byte_length


def test_utf8_byte_length_matches_encode():
    assert utf8_byte_length("test") == 4
    assert utf8_byte_length("ʇsǝʇ") == len("ʇsǝʇ".encode("utf-8"))


def test_reversed_transform_has_zero_byte_savings():
    # Reordering characters cannot change how many UTF-8 bytes they occupy;
    # this is a structural guarantee, not an empirical result.
    report = run_token_cost_benchmark()
    assert report["per_transform"]["reversed"]["byte_savings_ratio"] == 0.0


def test_multibyte_transforms_show_positive_byte_savings():
    # upside_down, homoglyph, and bidi_override all introduce multi-byte
    # UTF-8 sequences (rotation glyphs, Cyrillic/Greek confusables, and bidi
    # control characters respectively) that canonicalization removes.
    report = run_token_cost_benchmark()
    for transform in ("upside_down", "homoglyph", "bidi_override"):
        assert report["per_transform"][transform]["byte_savings_ratio"] > 0, transform


def test_canonical_never_exceeds_raw_bytes_per_example():
    # canonical_text is derived from raw_text by removing/collapsing
    # characters, never adding them, so canonical bytes should never exceed
    # raw bytes for any single example.
    report = run_token_cost_benchmark()
    for example in report["examples"]:
        assert example["canonical_bytes"] <= example["raw_bytes"], example


def test_overall_byte_savings_ratio_is_positive():
    report = run_token_cost_benchmark()
    assert report["overall"]["byte_savings_ratio"] > 0.2


def test_markdown_report_documents_the_byte_proxy_choice():
    report = run_token_cost_benchmark()
    md = render_markdown(report)
    assert "utf8_byte_length" in md
    assert "not a real tokenizer count" in md
