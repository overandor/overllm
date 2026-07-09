import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.semantic_fingerprint import compare_fingerprints, compute_fingerprint


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_plain_text_has_no_detected_transform():
    result = compute_fingerprint("hello world")
    assert result["transform_detected"] is False
    assert result["raw_hash"] == result["canonical_hash"]
    assert result["lossless"] is True


def test_upside_down_round_trip_matches_known_flip_text():
    # "ʇsǝʇ" is the widely used upside-down rendering of "test".
    result = compute_fingerprint("ʇsǝʇ")
    assert result["transform_receipt"]["upside_down"] is True
    assert result["canonical_text"] == "test"
    assert result["canonical_hash"] == sha256_text("test")
    assert result["raw_hash"] != result["canonical_hash"]
    assert result["lossless"] is True


def test_reversed_text_is_detected_and_recovered():
    original = "the cat sat on the mat"
    result = compute_fingerprint(original[::-1])
    assert result["transform_receipt"]["reversed"] is True
    assert result["canonical_text"] == original
    assert result["canonical_hash"] == sha256_text(original)


def test_bidi_override_recovers_human_reading_order():
    # "abc" + RLO + "def" + PDF + "ghi": a human reading this sees "abcfedghi"
    # even though the stored codepoint order is a,b,c,d,e,f,g,h,i.
    raw = "abc‮def‬ghi"
    result = compute_fingerprint(raw)
    assert result["transform_receipt"]["bidi_override"] is True
    assert result["canonical_text"] == "abcfedghi"
    assert result["raw_hash"] != result["canonical_hash"]


def test_homoglyph_substitution_is_detected_and_marked_lossy():
    # Cyrillic "а" (U+0430) substituted for Latin "a".
    raw = "аpple"
    result = compute_fingerprint(raw)
    assert result["transform_receipt"]["homoglyph_substitution"] is True
    assert result["canonical_text"] == "apple"
    assert result["canonical_hash"] == sha256_text("apple")
    assert result["lossless"] is False


def test_compare_reports_same_canonical_message_across_transform():
    comparison = compare_fingerprints("test", "ʇsǝʇ")
    assert comparison["same_bytes"] is False
    assert comparison["same_canonical_message"] is True


def test_compare_reports_different_canonical_message_for_unrelated_text():
    comparison = compare_fingerprints("test", "completely different sentence")
    assert comparison["same_bytes"] is False
    assert comparison["same_canonical_message"] is False


def test_transform_confidence_keys_match_transform_receipt_keys():
    # transform_confidence must stay symmetric with transform_receipt: same
    # four keys, always present, regardless of what the input triggers.
    # transform_receipt itself is unchanged/still boolean - this is an
    # additive field, not a replacement.
    result = compute_fingerprint("hello world")
    assert set(result["transform_confidence"].keys()) == set(result["transform_receipt"].keys())
    assert all(isinstance(v, bool) for v in result["transform_receipt"].values())


def test_transform_confidence_is_zero_for_every_transform_on_plain_text():
    result = compute_fingerprint("hello world")
    assert result["transform_receipt"] == {
        "bidi_override": False,
        "upside_down": False,
        "reversed": False,
        "homoglyph_substitution": False,
    }
    assert all(v == 0.0 for v in result["transform_confidence"].values())


def test_selected_transform_produces_a_nonzero_evidence_score():
    # Acceptance criterion: detection of a transform must produce a nonzero
    # score for that transform specifically, not just a True flag.
    upside_down = compute_fingerprint("ʇsǝʇ")
    assert upside_down["transform_receipt"]["upside_down"] is True
    assert upside_down["transform_confidence"]["upside_down"] > 0.0

    reversed_text = compute_fingerprint("the cat sat on the mat"[::-1])
    assert reversed_text["transform_receipt"]["reversed"] is True
    assert reversed_text["transform_confidence"]["reversed"] > 0.0


def test_bidi_override_confidence_is_binary_not_fabricated_fuzziness():
    # bidi detection is a deterministic control-character scan, so its
    # evidence score is 1.0 when detected and 0.0 otherwise - never a
    # graded value in between, unlike the other three transforms.
    detected = compute_fingerprint("abc‮def‬ghi")
    assert detected["transform_confidence"]["bidi_override"] == 1.0
    not_detected = compute_fingerprint("hello world")
    assert not_detected["transform_confidence"]["bidi_override"] == 0.0


def test_homoglyph_confidence_scales_with_substitution_ratio():
    # "аpple" has one Cyrillic "а" among 5 alphabetic characters (0.2).
    # "аррlе" has four Cyrillic substitutions among 5 (0.8) - heavier
    # substitution should score higher confidence, not just a flag.
    partial = compute_fingerprint("аpple")
    heavier = compute_fingerprint("аррlе")
    assert 0.0 < partial["transform_confidence"]["homoglyph_substitution"] < 1.0
    assert heavier["transform_confidence"]["homoglyph_substitution"] > partial["transform_confidence"]["homoglyph_substitution"]


def test_homoglyph_substitution_count_is_a_separate_top_level_field():
    result = compute_fingerprint("аpple")
    assert result["homoglyph_substitution_count"] == 1
    # It must not be nested inside transform_confidence anymore -
    # transform_confidence values are all 0-1 floats now, not a mix of
    # floats and raw counts.
    assert "homoglyph_substitutions" not in result["transform_confidence"]
    assert isinstance(result["transform_confidence"]["homoglyph_substitution"], float)
