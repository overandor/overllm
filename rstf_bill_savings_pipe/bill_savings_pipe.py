#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv
from rstf_core import canonicalize

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"
SYSTEM_PROMPT = "You are a token-cost measurement endpoint. Reply with exactly one character: ."

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"Bad JSONL at {path}:{line_no}: {e}") from e
    return rows

def post_chat(provider: str, model: str, user_text: str) -> dict[str, Any]:
    if provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise SystemExit("Missing OPENROUTER_API_KEY")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Metadata": "enabled",
        }
        site = os.environ.get("OPENROUTER_SITE_URL")
        app = os.environ.get("OPENROUTER_APP_NAME")
        if site:
            headers["HTTP-Referer"] = site
        if app:
            headers["X-Title"] = app
        url = OPENROUTER_URL
    elif provider == "groq":
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise SystemExit("Missing GROQ_API_KEY")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        url = GROQ_URL
    elif provider == "ollama":
        url = OLLAMA_URL
        headers = {
            "Content-Type": "application/json",
        }
    else:
        raise ValueError(f"Unknown provider: {provider}")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0,
        "max_tokens": 1,
        "stream": False,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"{provider} HTTP {r.status_code}: {r.text[:2000]}")
    return r.json()

def usage_prompt_tokens(resp: dict[str, Any]) -> int | None:
    usage = resp.get("usage") or {}
    if "prompt_tokens" in usage:
        return int(usage["prompt_tokens"])
    if "input_tokens" in usage:
        return int(usage["input_tokens"])
    # Ollama format
    if "prompt_count" in resp:
        return int(resp["prompt_count"])
    return None

def measure_one(provider: str, model: str, row: dict[str, Any], sleep_s: float) -> dict[str, Any]:
    raw_text = str(row.get("text", ""))
    fp = canonicalize(raw_text, force_reverse=bool(row.get("force_reverse", False)))
    canonical_text = fp["canonical_text"]
    raw_resp = post_chat(provider, model, raw_text)
    if sleep_s:
        time.sleep(sleep_s)
    canonical_resp = post_chat(provider, model, canonical_text)
    raw_tokens = usage_prompt_tokens(raw_resp)
    canonical_tokens = usage_prompt_tokens(canonical_resp)
    if raw_tokens is None or canonical_tokens is None:
        raise RuntimeError(f"Provider response missing prompt/input tokens: raw={raw_resp} canonical={canonical_resp}")
    saved = raw_tokens - canonical_tokens
    ratio = saved / raw_tokens if raw_tokens else 0.0
    return {
        "id": row.get("id"),
        "provider": provider,
        "model": model,
        "method": f"{provider}_chat_completion_usage",
        "raw_text": raw_text,
        "canonical_text": canonical_text,
        "transforms": fp["transforms"],
        "changed": fp["changed"],
        "raw_prompt_tokens": raw_tokens,
        "canonical_prompt_tokens": canonical_tokens,
        "tokens_saved": saved,
        "savings_ratio": ratio,
        "raw_utf8_bytes": fp["raw_utf8_bytes"],
        "canonical_utf8_bytes": fp["canonical_utf8_bytes"],
        "bytes_saved": fp["bytes_saved"],
        "raw_sha256": fp["raw_sha256"],
        "canonical_sha256": fp["canonical_sha256"],
        "truth_label": (
            "provider_usage_prompt_tokens_not_direct_anthropic_count_tokens"
            if provider == "openrouter"
            else "groq_usage_prompt_tokens_not_claude"
        ),
    }

def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "provider", "model", "method", "raw_prompt_tokens",
        "canonical_prompt_tokens", "tokens_saved", "savings_ratio",
        "raw_utf8_bytes", "canonical_utf8_bytes", "bytes_saved",
        "changed", "transforms", "truth_label", "raw_sha256", "canonical_sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            r = dict(row)
            r["transforms"] = ",".join(r.get("transforms") or [])
            writer.writerow({k: r.get(k) for k in fieldnames})

def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw_total = sum(r["raw_prompt_tokens"] for r in rows)
    canonical_total = sum(r["canonical_prompt_tokens"] for r in rows)
    saved = raw_total - canonical_total
    return {
        "examples": len(rows),
        "raw_prompt_tokens_total": raw_total,
        "canonical_prompt_tokens_total": canonical_total,
        "tokens_saved_total": saved,
        "savings_ratio": saved / raw_total if raw_total else 0.0,
        "examples_with_savings": sum(1 for r in rows if r["tokens_saved"] > 0),
        "examples_unchanged_or_worse": sum(1 for r in rows if r["tokens_saved"] <= 0),
    }

def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["openrouter", "groq"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", type=Path, default=Path("examples.jsonl"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--sleep", type=float, default=2.0)
    args = parser.parse_args()
    input_rows = load_jsonl(args.input)
    results = []
    for i, row in enumerate(input_rows, 1):
        print(f"[{i}/{len(input_rows)}] measuring {row.get('id') or '<no id>'}", file=sys.stderr)
        results.append(measure_one(args.provider, args.model, row, args.sleep))
    write_jsonl(args.out, results)
    if args.csv:
        write_csv(args.csv, results)
    summary = summarize(results)
    summary_row = {
        "provider": args.provider,
        "model": args.model,
        **summary,
        "truth_label": results[0]["truth_label"] if results else "no_results",
    }
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary_row, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary_row, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
