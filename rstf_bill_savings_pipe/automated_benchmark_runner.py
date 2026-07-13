#!/usr/bin/env python3
"""Production-grade automated RSTF benchmark runner.

Supports 1000s of tests across multiple providers with automatic rate limit handling,
retry logic, comprehensive reporting, and production-ready error handling.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import requests
from dotenv import load_dotenv

# Import RSTF core
sys.path.insert(0, str(Path(__file__).parent))
from rstf_core import canonicalize

# Provider configurations
PROVIDER_CONFIGS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "models": [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma-7b-it",
        ],
        "rate_limit_rpm": 30,
        "env_key": "GROQ_API_KEY",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "models": [
            "anthropic/claude-sonnet-4.5",
            "openai/gpt-4o",
        ],
        "rate_limit_rpm": 60,
        "env_key": "OPENROUTER_API_KEY",
    },
}

# Rate limiting configuration
REQUEST_INTERVAL = 2.1  # seconds between requests
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0
BATCH_SIZE = 10  # Process in batches for large corpora

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL file with error handling."""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"ERROR: Bad JSONL at {path}:{line_no}: {e}", file=sys.stderr)
                continue
    return rows

def post_chat(provider: str, model: str, user_text: str, api_key: str) -> Dict[str, Any]:
    """Post chat request with retry logic and rate limit handling."""
    config = PROVIDER_CONFIGS[provider]
    url = config["url"]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    if provider == "openrouter":
        headers["X-OpenRouter-Metadata"] = "enabled"
        site = os.environ.get("OPENROUTER_SITE_URL")
        app = os.environ.get("OPENROUTER_APP_NAME")
        if site:
            headers["HTTP-Referer"] = site
        if app:
            headers["X-Title"] = app
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a token-cost measurement endpoint. Reply with exactly one character: ."},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0,
        "max_tokens": 1,
        "stream": False,
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 429:
                # Rate limit hit
                wait_time = RETRY_BACKOFF ** (attempt + 1) + random.uniform(0, 1)
                print(f"  Rate limit hit, waiting {wait_time:.1f}s (retry {attempt + 1}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(wait_time)
                continue
            
            if response.status_code >= 400:
                raise RuntimeError(f"{provider} HTTP {response.status_code}: {response.text[:1000]}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF ** (attempt + 1)
                print(f"  Request error: {e}, waiting {wait_time:.1f}s (retry {attempt + 1}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(wait_time)
                continue
            raise
    
    raise RuntimeError(f"Max retries ({MAX_RETRIES}) exceeded for {provider}")

def usage_prompt_tokens(resp: Dict[str, Any]) -> int | None:
    """Extract prompt tokens from response."""
    usage = resp.get("usage") or {}
    if "prompt_tokens" in usage:
        return int(usage["prompt_tokens"])
    if "input_tokens" in usage:
        return int(usage["input_tokens"])
    return None

def measure_one(provider: str, model: str, row: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """Measure single example with error handling."""
    try:
        raw_text = str(row.get("text", ""))
        fp = canonicalize(raw_text, force_reverse=bool(row.get("force_reverse", False)))
        canonical_text = fp["canonical_text"]
        
        # Rate limiting
        time.sleep(REQUEST_INTERVAL)
        
        raw_resp = post_chat(provider, model, raw_text, api_key)
        raw_tokens = usage_prompt_tokens(raw_resp)
        
        time.sleep(REQUEST_INTERVAL)
        
        canonical_resp = post_chat(provider, model, canonical_text, api_key)
        canonical_tokens = usage_prompt_tokens(canonical_resp)
        
        if raw_tokens is None or canonical_tokens is None:
            raise RuntimeError("Provider response missing prompt/input tokens")
        
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
            "injection_risk": fp.get("injection_risk", "none"),
            "truth_label": f"{provider}_usage_prompt_tokens_not_direct_anthropic_billing",
            "status": "success",
        }
        
    except Exception as e:
        return {
            "id": row.get("id"),
            "provider": provider,
            "model": model,
            "status": "error",
            "error": str(e),
            "raw_text": row.get("text", ""),
        }

def run_benchmark(input_path: Path, output_dir: Path, provider: str, models: List[str], max_examples: int | None = None) -> Dict[str, Any]:
    """Run comprehensive benchmark across all models."""
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Automated Benchmark Runner", file=sys.stderr)
    print(f"Provider: {provider}", file=sys.stderr)
    print(f"Models: {', '.join(models)}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    # Load input data
    input_rows = load_jsonl(input_path)
    if max_examples:
        input_rows = input_rows[:max_examples]
    
    print(f"Loaded {len(input_rows)} examples from {input_path}", file=sys.stderr)
    
    # Get API key
    config = PROVIDER_CONFIGS[provider]
    api_key = os.environ.get(config["env_key"])
    if not api_key:
        raise SystemExit(f"Missing {config['env_key']}")
    
    # Run benchmarks for each model
    all_results = {}
    model_summaries = {}
    
    for model in models:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Testing model: {model}", file=sys.stderr)
        print(f"Examples: {len(input_rows)}", file=sys.stderr)
        print(f"Estimated time: {len(input_rows) * 2 * REQUEST_INTERVAL / 60:.1f} minutes", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        
        model_results = []
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        for i, row in enumerate(input_rows, 1):
            try:
                print(f"[{i}/{len(input_rows)}] {row.get('id', '<no id>')}", file=sys.stderr)
                result = measure_one(provider, model, row, api_key)
                model_results.append(result)
                
                if result["status"] == "success":
                    success_count += 1
                else:
                    error_count += 1
                    print(f"  ERROR: {result.get('error', 'Unknown error')}", file=sys.stderr)
                
                # Progress update every 10 examples
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    remaining = (len(input_rows) - i) * (elapsed / i)
                    print(f"  Progress: {i}/{len(input_rows)} ({i/len(input_rows)*100:.1f}%) | Elapsed: {elapsed/60:.1f}m | ETA: {remaining/60:.1f}m", file=sys.stderr)
                    
            except KeyboardInterrupt:
                print(f"\nInterrupted at example {i}/{len(input_rows)}", file=sys.stderr)
                break
            except Exception as e:
                print(f"  UNEXPECTED ERROR: {e}", file=sys.stderr)
                error_count += 1
                continue
        
        # Calculate summary
        successful_results = [r for r in model_results if r["status"] == "success"]
        if successful_results:
            raw_total = sum(r["raw_prompt_tokens"] for r in successful_results)
            canonical_total = sum(r["canonical_prompt_tokens"] for r in successful_results)
            saved_total = raw_total - canonical_total
            summary = {
                "provider": provider,
                "model": model,
                "examples_tested": len(input_rows),
                "examples_successful": success_count,
                "examples_failed": error_count,
                "raw_prompt_tokens_total": raw_total,
                "canonical_prompt_tokens_total": canonical_total,
                "tokens_saved_total": saved_total,
                "savings_ratio": saved_total / raw_total if raw_total else 0.0,
                "execution_time_seconds": time.time() - start_time,
                "truth_label": f"{provider}_usage_prompt_tokens_not_direct_anthropic_billing",
            }
        else:
            summary = {
                "provider": provider,
                "model": model,
                "examples_tested": len(input_rows),
                "examples_successful": 0,
                "examples_failed": error_count,
                "error": "No successful measurements",
                "execution_time_seconds": time.time() - start_time,
            }
        
        model_summaries[model] = summary
        all_results[model] = model_results
        
        # Save results for this model
        model_output_path = output_dir / f"{provider}_{model.replace('/', '_')}_results.jsonl"
        with model_output_path.open("w", encoding="utf-8") as f:
            for result in model_results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        
        model_summary_path = output_dir / f"{provider}_{model.replace('/', '_')}_summary.json"
        with model_summary_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        
        print(f"\nModel {model} complete:", file=sys.stderr)
        print(f"  Successful: {success_count}/{len(input_rows)}", file=sys.stderr)
        print(f"  Failed: {error_count}/{len(input_rows)}", file=sys.stderr)
        if successful_results:
            print(f"  Tokens saved: {saved_total} ({summary['savings_ratio']*100:.1f}%)", file=sys.stderr)
        print(f"  Execution time: {summary['execution_time_seconds']/60:.1f} minutes", file=sys.stderr)
    
    # Generate overall summary
    overall_summary = {
        "benchmark_run": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "models_tested": models,
            "input_file": str(input_path),
            "examples_total": len(input_rows),
        },
        "model_summaries": model_summaries,
    }
    
    overall_summary_path = output_dir / f"{provider}_overall_summary.json"
    with overall_summary_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(overall_summary, indent=2, ensure_ascii=False) + "\n")
    
    print(f"\n{'='*60}", file=sys.stderr)
    print("Benchmark complete!", file=sys.stderr)
    print(f"Results saved to: {output_dir}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    return overall_summary

def main() -> int:
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Automated RSTF benchmark runner")
    parser.add_argument("--provider", choices=["groq", "openrouter"], required=True)
    parser.add_argument("--models", nargs="+", help="Models to test (default: all available)")
    parser.add_argument("--input", type=Path, default=Path("examples.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--max-examples", type=int, help="Limit number of examples to test")
    args = parser.parse_args()
    
    # Determine models to test
    config = PROVIDER_CONFIGS[args.provider]
    if args.models:
        models = args.models
    else:
        models = config["models"]
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run benchmark
    try:
        summary = run_benchmark(args.input, args.output_dir, args.provider, models, args.max_examples)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
