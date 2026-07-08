from rstf_hyperbench import TRANSFORM_FAMILIES, build_corpus

def test_corpus_size_and_families():
    rows = build_corpus(n_per_transform=3, seed=1)
    assert len(rows) == len(TRANSFORM_FAMILIES) * 3
    assert {r["transform_family"] for r in rows} == set(TRANSFORM_FAMILIES)

def test_corpus_deterministic_seed():
    a = build_corpus(n_per_transform=2, seed=42)
    b = build_corpus(n_per_transform=2, seed=42)
    assert a == b

def test_reversed_family_sets_force_reverse():
    rows = build_corpus(n_per_transform=1, seed=7)
    rev = [r for r in rows if r["transform_family"] == "reversed_forced"][0]
    assert rev["force_reverse"] is True
