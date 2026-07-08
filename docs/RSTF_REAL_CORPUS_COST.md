# RSTF real-corpus cost scan

`tools/rstf_real_corpus_cost.py` measures RSTF on real input text as-is. It does **not** generate synthetic reversed/upside-down/homoglyph/bidi examples.

Use it when you want to answer:

```text
How often do RSTF-style transforms occur in this actual corpus, and how much token/byte cost changes when they do?
```

## Why this exists

Synthetic benchmarks are useful for proving the detector can recover known transforms. They do not prove prevalence in real traffic.

The real-corpus scanner separates:

1. prevalence — how many records actually contain detected transforms;
2. transformed-only savings — savings on records where RSTF acted;
3. overall savings — corpus-level impact after accounting for prevalence.

A clean real corpus may show near-zero savings. That is a valid result.

## Run against repo docs

```bash
python tools/rstf_real_corpus_cost.py \
  --input-dir docs \
  --glob "*.md" \
  --tokenizer bytes
```

## Run against a JSONL export

```bash
python tools/rstf_real_corpus_cost.py \
  --input-file data/messages.jsonl \
  --text-field message \
  --tokenizer tiktoken \
  --model gpt-4o \
  --include-examples
```

## Outputs

Default outputs:

```text
benchmark/rstf/real_corpus_cost_report.json
benchmark/rstf/real_corpus_cost_report.md
```

## Truth label

```text
non_synthetic_real_input_rtf_scan_not_generated_attack_corpus
```

## Buyer-safe claim

Use this:

```text
RSTF was evaluated in shadow mode on real input records. The report separates transform prevalence from savings on transformed records and corpus-level savings.
```

Do not use this:

```text
The synthetic 78% token savings number applies to all production traffic.
```

## Test

```bash
python -m pytest tests/test_rstf_real_corpus_cost.py -v
```
