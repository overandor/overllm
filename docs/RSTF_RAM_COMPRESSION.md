# RSTF RAM compression policy

RSTF canonicalization should be evaluated separately at two layers:

1. token/cache RAM pressure — token IDs, embeddings, prompt windows, KV-cache growth;
2. byte/storage compression — zlib/zstd/LZ4/gzip-style compressed byte size.

The real-corpus scanner includes A/B compression metrics so this can be measured instead of assumed.

## Run RAM compression A/B

```bash
python tools/rstf_real_corpus_cost.py \
  --input-file data/messages.jsonl \
  --text-field message \
  --tokenizer tiktoken \
  --model gpt-4o \
  --compressor zlib \
  --include-examples
```

If `zstandard` is installed, use:

```bash
python tools/rstf_real_corpus_cost.py \
  --input-file data/messages.jsonl \
  --text-field message \
  --tokenizer tiktoken \
  --model gpt-4o \
  --compressor zstd \
  --include-examples
```

## Metrics emitted

```text
raw_utf8_bytes
canonical_utf8_bytes
utf8_bytes_saved
receipt_json_bytes
compressed_raw_bytes
compressed_canonical_bytes
compressed_canonical_plus_receipt_bytes
hot_path_compressed_bytes_saved
hot_path_compressed_savings_ratio
audit_path_compressed_delta_bytes
audit_path_compressed_delta_ratio
```

## Interpretation

`hot_path_compressed_*` compares:

```text
raw_text compressed
vs.
canonical_text compressed
```

This is the RAM/cache path.

`audit_path_compressed_*` compares:

```text
raw_text compressed
vs.
canonical_text + compact receipt compressed
```

This estimates the cost of keeping provenance metadata near the hot path.

## Production rule

Hot path:

```text
canonical_text only
```

Audit path:

```text
raw_hash
canonical_hash
transform_receipt
lossless flag
truth_label
```

Cold archive, only if policy requires replay:

```text
raw_text
```

## Truth label

```text
lossless_ram_compression_ab_probe_not_os_memory_compressor_exact_model
```

The scanner uses a selected lossless compressor such as zlib or zstd as an A/B probe. It is not an exact simulation of macOS, Linux, JVM, browser, database, vector-store, or GPU memory compression.

## Safe claim

Use this:

```text
RSTF can be measured as a RAM/cache pre-normalization stage. The real-corpus scanner reports whether canonical text improves compressed hot-path size and whether receipt metadata outweighs the gain.
```

Do not use this:

```text
RSTF always improves RAM compression.
```
