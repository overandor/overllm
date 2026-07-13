import os
import pytest
from rstf_hyperbench import GroqClient, measure_row

class FakeResponse:
    def __init__(self, status_code, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._payload

def test_groq_usage_parsing(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    def fake_post(*args, **kwargs):
        return FakeResponse(200, {"usage":{"prompt_tokens":123,"completion_tokens":1}}, headers={"x-ratelimit-remaining-tokens":"999"})
    monkeypatch.setattr("requests.post", fake_post)
    out = GroqClient(sleep=0).prompt_tokens("model", "text")
    assert out["prompt_tokens"] == 123
    assert out["completion_tokens"] == 1
    assert out["headers"]["x-ratelimit-remaining-tokens"] == "999"

def test_groq_429_retry(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    calls = {"n": 0}
    def fake_sleep(_):
        return None
    def fake_post(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(429, text="rate limited", headers={"retry-after":"0"})
        return FakeResponse(200, {"usage":{"prompt_tokens":5,"completion_tokens":1}})
    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr("time.sleep", fake_sleep)
    out = GroqClient(sleep=0, max_retries=2).prompt_tokens("model", "text")
    assert calls["n"] == 2
    assert out["prompt_tokens"] == 5

def test_measure_row_truth_label(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    def fake_post(*args, **kwargs):
        return FakeResponse(200, {"usage":{"prompt_tokens":10,"completion_tokens":1}}, headers={})
    monkeypatch.setattr("requests.post", fake_post)
    row = {"id":"x","source_text":"test","text":"ʇsǝʇ","transform_family":"upside_down","force_reverse":False}
    out = measure_row(GroqClient(sleep=0), "llama-3.1-8b-instant", row, 0)
    assert out["truth_label"] == "groq_provider_usage_prompt_tokens_not_claude_not_anthropic_billing"
    assert out["raw_prompt_tokens"] >= out["canonical_prompt_tokens"]
