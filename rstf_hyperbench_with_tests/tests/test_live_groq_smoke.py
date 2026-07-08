import os
import pytest
from rstf_hyperbench import GroqClient

pytestmark = pytest.mark.live

def test_live_groq_usage_smoke():
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set")
    out = GroqClient(sleep=0).prompt_tokens("llama-3.1-8b-instant", "hello world")
    assert out["prompt_tokens"] > 0
    assert out["truth_label"] == "groq_provider_usage_prompt_tokens_not_claude_not_anthropic_billing"
