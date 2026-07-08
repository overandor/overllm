import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.rstf_dogfood_scan import render_markdown, run_scan


def test_scan_covers_a_meaningful_amount_of_real_text():
    report = run_scan()
    assert report["files_scanned"] > 30
    assert report["lines_scanned"] > 1000


def test_unexpected_hits_stay_at_the_known_residual_case():
    # After fixing the "import os" false-positive bug (19 -> 1 unrelated
    # hits), the one remaining hit is a documented, understood limitation:
    # short high-frequency word pairs like no/on are near-mirror-images of
    # each other, so text with multiple "no"s can outscore itself when
    # reversed. This is a ceiling, not a target — if this regresses upward,
    # something got worse; if new unrelated hits appear elsewhere, that's a
    # new real finding worth investigating, not routinely raising the bar.
    report = run_scan()
    assert report["unexpected_hits_elsewhere"] <= 1


def test_rstf_own_files_are_correctly_excluded_from_unexpected_hits():
    # api/semantic_fingerprint.py's own docstrings/tables legitimately
    # contain example glyphs like the upside-down rendering of "test" -
    # those must be categorized as expected, not counted as findings.
    report = run_scan()
    own_file_hits = [h for h in report["hits"] if h["within_rstf_own_files"]]
    assert report["expected_hits_within_rstf_own_files"] == len(own_file_hits)
    assert any("semantic_fingerprint.py" in h["file"] for h in own_file_hits)


def test_markdown_report_states_this_is_not_a_customer_pilot():
    report = run_scan()
    md = render_markdown(report)
    assert "not a customer pilot" in md
