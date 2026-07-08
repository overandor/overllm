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
