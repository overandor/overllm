from rstf_hyperbench import summarize

def test_summary_math():
    rows = [
        {"model":"m","transform_family":"clean","raw_prompt_tokens":10,"canonical_prompt_tokens":10,"tokens_saved":0,"savings_ratio":0},
        {"model":"m","transform_family":"upside_down","raw_prompt_tokens":20,"canonical_prompt_tokens":5,"tokens_saved":15,"savings_ratio":0.75},
    ]
    s = summarize(rows)
    assert s["overall"]["raw_prompt_tokens"] == 30
    assert s["overall"]["canonical_prompt_tokens"] == 15
    assert s["overall"]["tokens_saved"] == 15
    assert s["overall"]["savings_ratio"] == 0.5
    assert s["by_model_transform"]["m::upside_down"]["examples_with_savings"] == 1
