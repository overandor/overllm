# RSTF Bill Savings Pipe

Measures direct provider-reported prompt-token savings for raw transformed text vs RSTF canonical text.

Providers supported:
- OpenRouter Chat Completions API
- Groq Chat Completions API

Important: put API keys in environment variables. Do not hard-code keys in this repo.

## Setup

```bash
cd rstf_bill_savings_pipe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit .env locally, or export variables in your shell:

```bash
export OPENROUTER_API_KEY="..."
export GROQ_API_KEY="..."
```

## Run

OpenRouter Claude-routed test:
```bash
python bill_savings_pipe.py --provider openrouter --model anthropic/claude-sonnet-4.5 --input examples.jsonl --out results/openrouter_claude_proxy.jsonl
```

Groq test:
```bash
python bill_savings_pipe.py --provider groq --model llama-3.3-70b-versatile --input examples.jsonl --out results/groq_llama.jsonl
```
