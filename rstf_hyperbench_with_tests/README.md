# RSTF HyperBench with Tests

A serious benchmark harness for RSTF provider-token savings.

This package upgrades the previous Groq brute bench into a tested hyper-benchmark:

- Deterministic corpus generation
- Transform-family coverage
- Provider usage parsing
- 429 retry/backoff logic
- Summary math
- CSV/JSONL/Markdown report generation
- Pytest unit tests
- Live Groq provider testing
- GitHub Actions CI

## What it proves

Valid after a live run:
> Groq provider usage accounting showed X% prompt-token reduction on N benchmark measurements.

Not valid:
> Claude billing was reduced by X%.

## Setup

```bash
cd rstf_hyperbench_with_tests
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Run tests

```bash
pytest -q
```

## Run live Groq hyperbench

```bash
export GROQ_API_KEY="..."
python rstf_hyperbench.py   --provider groq   --models llama-3.1-8b-instant,llama-3.3-70b-versatile   --n-per-transform 100   --repeats 1   --out-dir results/groq_hyper_100
```

## Output

- `corpus.jsonl`
- `rows.jsonl`
- `rows.csv`
- `summary.json`
- `summary.md`
