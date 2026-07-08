import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.rstf_benchmark import render_csv, render_markdown, run_benchmark


def test_benchmark_generates_all_examples():
    report = run_benchmark()
    assert report["overall"]["count"] == 160
    assert set(report["per_transform"].keys()) == {
        "reversed", "upside_down", "bidi_override", "homoglyph",
    }
    assert report["control_group"]["count"] == 40


def test_raw_hashes_always_diverge_from_source():
    # A transform that doesn't change the bytes isn't a transform worth
    # benchmarking; this guards against a corpus sentence accidentally
    # being a fixed point of one of the encoders.
    report = run_benchmark()
    assert report["overall"]["raw_hash_divergence_rate"] == 1.0


def test_deterministic_transforms_recover_exactly():
    # bidi_override, homoglyph, and upside_down are exact/deterministic
    # transforms on this synthetic corpus (no ambiguity is introduced by
    # construction), so they should recover perfectly.
    report = run_benchmark()
    for transform in ("bidi_override", "homoglyph", "upside_down"):
        assert report["per_transform"][transform]["exact_recovery_rate"] == 1.0, transform


def test_reversed_detection_meets_minimum_bar():
    # The reversed-text detector is a weak heuristic (common-word-list
    # based) by design; this is a floor, not a target of 1.0.
    report = run_benchmark()
    assert report["per_transform"]["reversed"]["detection_rate"] >= 0.9


def test_overall_detection_meets_minimum_bar():
    report = run_benchmark()
    assert report["overall"]["detection_rate"] >= 0.95


def test_control_group_false_positive_rate_is_low():
    # The detector should stay quiet on unmodified text; this is a ceiling,
    # not a floor, since false positives directly undermine a pilot pitch.
    report = run_benchmark()
    assert report["control_group"]["false_positive_rate"] <= 0.05


def test_markdown_report_includes_key_sections():
    report = run_benchmark()
    md = render_markdown(report)
    assert "## Overall" in md
    assert "## Per-transform" in md
    assert "## Control group" in md
    assert "False positive rate" in md


def test_csv_report_has_one_row_per_example_plus_header():
    report = run_benchmark()
    csv_text = render_csv(report)
    rows = [line for line in csv_text.strip().splitlines() if line]
    # header + 160 positive examples + 40 control examples
    assert len(rows) == 1 + 160 + 40
