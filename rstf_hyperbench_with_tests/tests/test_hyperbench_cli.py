import json
from pathlib import Path
from rstf_hyperbench import run_bench

def test_run_bench_groq_outputs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    
    class FakeResponse:
        def __init__(self, status_code, payload=None, text="", headers=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.text = text
            self.headers = headers or {}
        def json(self):
            return self._payload
    
    def fake_post(*args, **kwargs):
        return FakeResponse(200, {"usage":{"prompt_tokens":10,"completion_tokens":1}}, headers={})
    
    monkeypatch.setattr("requests.post", fake_post)
    
    summary = run_bench(
        provider="groq",
        models=["llama-3.1-8b-instant"],
        n_per_transform=2,
        repeats=1,
        out_dir=tmp_path,
        seed=123,
        sleep=0,
    )
    assert summary["overall"]["count"] == 12
    assert (tmp_path / "rows.jsonl").exists()
    assert (tmp_path / "rows.csv").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.md").exists()
    loaded = json.loads((tmp_path / "summary.json").read_text())
    assert loaded["overall"]["count"] == 12
