from rstf_core import canonicalize, inject_upside_down, inject_homoglyph, inject_bidi, inject_reversed

def test_upside_down_round_trip():
    raw = inject_upside_down("test")
    out = canonicalize(raw)
    assert out["canonical_text"] == "test"
    assert "upside_down" in out["transforms"]
    assert out["bytes_saved"] > 0

def test_homoglyph_round_trip():
    raw = inject_homoglyph("paypal")
    out = canonicalize(raw)
    assert out["canonical_text"] == "paypal"
    assert "homoglyph" in out["transforms"]
    assert out["bytes_saved"] > 0

def test_bidi_stripped():
    out = canonicalize(inject_bidi("safe text"))
    assert out["canonical_text"] == "safe text"
    assert "bidi_control_stripped" in out["transforms"]

def test_clean_no_false_positive():
    out = canonicalize("hello world")
    assert out["canonical_text"] == "hello world"
    assert out["transforms"] == []
    assert out["bytes_saved"] == 0

def test_forced_reverse():
    out = canonicalize(inject_reversed("hello"), force_reverse=True)
    assert out["canonical_text"] == "hello"
    assert "reversed_forced" in out["transforms"]
