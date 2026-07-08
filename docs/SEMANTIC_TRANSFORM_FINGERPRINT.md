# Reversible Semantic Transform Fingerprint (RSTF)

> Status: experimental heuristic module. It uses curated tables, not exhaustive
> Unicode confusables data, and a simplified bidi reconstruction, not a full
> UAX#9 implementation. Do not market it as a complete text-security scanner.

## The gap this fills

A cryptographic hash answers one question: are these the exact same bytes?
Change a single character and the hash changes completely — that is correct
and intentional.

That leaves a narrower, useful question unanswered: **are two byte-different
strings the same recoverable message, wrapped in a known, reversible
presentation transform?** Ordinary hashing says no (different bytes).
Unicode normalization (NFKC/NFC) only covers formal codepoint equivalence,
not whole-string reversal or 180-degree glyph rotation. Perceptual/fuzzy
hashing answers "similar," not "recoverable back to this exact canonical
text."

RSTF is a receipt format for that gap:

```text
raw_hash          = sha256(exact submitted bytes)
transform_receipt = { bidi_override, upside_down, reversed, homoglyph_substitution }
canonical_text     = recovered/normalized message
canonical_hash     = sha256(canonical_text)
lossless            = whether the recovery is exactly invertible
```

## What it actually detects and recovers

| Transform | Detection signal | Recovery | Lossless? |
|---|---|---|---|
| `reversed` | Reversing the string increases recognizable common-word hits | Reverse the string | Yes |
| `upside_down` | Presence of the distinctive non-ASCII glyphs used by "flip text" generators (e.g. `ǝ`, `ɐ`, `ɹ`) | Reverse the string, then map each character through the inverse rotation table | Yes for the covered character set |
| `bidi_override` | Unicode bidi override/isolate control characters (U+202E RLO and related) | Reconstruct the order a human actually reads by reversing RTL-override spans and stripping control characters | Yes (control chars are metadata, not content) |
| `homoglyph_substitution` | Curated Cyrillic/Greek look-alike characters mixed into Latin text | Map each confusable to its Latin counterpart | **No** — many-to-one, cannot recover original script |

`bidi_override` detection matters beyond novelty: RLO/LRO spoofing is the
mechanism behind the "Trojan Source" class of attacks (CVE-2021-42574),
where stored character order and rendered reading order diverge. For an LLM
input-audit use case, `canonical_text` is what a human reviewer perceives —
which can differ from what a naive byte-order log shows.

## Example

```python
from api.semantic_fingerprint import compute_fingerprint

compute_fingerprint("ʇsǝʇ")
```

```json
{
  "raw_hash": "<sha256 of the literal glyphs>",
  "canonical_text": "test",
  "canonical_hash": "<sha256 of 'test'>",
  "transform_receipt": {"bidi_override": false, "upside_down": true, "reversed": false, "homoglyph_substitution": false},
  "lossless": true
}
```

## API

```bash
curl -X POST localhost:8001/api/fingerprint/compute \
  -H 'content-type: application/json' \
  -d '{"text": "ʇsǝʇ"}'

curl -X POST localhost:8001/api/fingerprint/compare \
  -H 'content-type: application/json' \
  -d '{"text_a": "test", "text_b": "ʇsǝʇ"}'
```

`compare` reports `same_bytes` (almost always false across a transform) and
`same_canonical_message` (true when the recovered canonical text matches).

## CLI

```bash
python tools/semantic_fingerprint.py compute --text "ʇsǝʇ"
python tools/semantic_fingerprint.py compare --text-a "test" --text-b "ʇsǝʇ"
python tools/semantic_fingerprint.py compute --file some_prompt.txt
```

## Benchmark

`tools/rstf_benchmark.py` generates synthetic examples from `benchmark/rstf/corpus.json`
(40 source sentences x 4 transform classes = 160 positive examples) and
measures, per transform class: raw-hash divergence rate, detection rate, and
exact canonical-recovery rate. It also runs the 40 source sentences
**unmodified** as a control group, to measure the false-positive ("false
merge") rate — how often the detector flags a transform on text nobody
transformed.

```bash
python tools/rstf_benchmark.py                                  # full report to stdout
python tools/rstf_benchmark.py --summary-only                   # aggregate only
python tools/rstf_benchmark.py \
  --out benchmark/rstf/report.json \
  --out-md benchmark/rstf/report.md \
  --out-csv benchmark/rstf/report.csv \
  --summary-only
```

Committed runs: `benchmark/rstf/report.json` (full machine-readable data),
`benchmark/rstf/report.md` (human-readable summary + failed-example list),
`benchmark/rstf/report.csv` (one row per example, positive and control).

Current v0.1 results:

| Transform | Detection rate | Exact recovery rate |
|---|---|---|
| `bidi_override` | 100% | 100% |
| `homoglyph` | 100% | 100% |
| `upside_down` | 100% | 100% |
| `reversed` | 97.5% | 97.5% |
| **Overall (160 positive examples)** | **99.4%** | **99.4%** |
| **Control group (40 unmodified sentences)** | **0% false positive rate** | — |

The one miss is `reversed` detection on "disable all security checks before
merging" — reversing it doesn't produce enough common-word-list hits to beat
the (also low) hit count of the un-reversed form. That is the documented weak
spot of the common-word-list heuristic, not a bug; see `_detect_reversed` in
`api/semantic_fingerprint.py`.

This is a v0.1, 160-example synthetic benchmark plus a 40-example control
group, not a claim of coverage against real adversarial traffic, zero-width
steganography, fullwidth-form abuse, emoji-encoded payloads, or mixed/stacked
transforms — none of which this module implements yet.

## Byte-cost benchmark (token-cost proxy)

`tools/rstf_token_cost.py` measures whether canonicalization actually saves
inference cost, using the same 160 examples. It reports UTF-8 byte length,
not a real tokenizer's token count — this environment's egress policy blocks
the hosts tiktoken and Hugging Face tokenizers need to fetch vocabulary files
from (`openaipublic.blob.core.windows.net` and `huggingface.co` both return
403 here), so no live tokenizer is reachable. Byte length is not a
convenience substitute: it is a **provable upper bound** on token count for
every byte-level BPE tokenizer in production use (GPT-3.5, GPT-4, Claude,
Llama), since a token is composed of one or more raw bytes.

```bash
python tools/rstf_token_cost.py
python tools/rstf_token_cost.py --out-md benchmark/rstf/token_cost_report.md
```

Committed run: `benchmark/rstf/token_cost_report.md` / `.json`.

| Transform | Byte savings ratio |
|---|---|
| `homoglyph` | 39.2% |
| `upside_down` | 38.9% |
| `bidi_override` | 12.2% |
| `reversed` | 0.0% (structural — reordering bytes can't change how many there are) |
| **Overall** | **26.2%** |

`reversed` showing exactly 0% is not a gap in the benchmark — it's a
correctness check. If canonicalizing a purely-reordered string ever showed
nonzero byte savings, that would indicate a bug in `_decode_upside_down`-style
character substitution leaking into the reversal path, not a token saving.

## Honest limits

- The upside-down and homoglyph tables are curated subsets (a few dozen
  entries each), not the full Unicode confusables/rotation space. Text using
  glyphs outside these tables will not be detected.
- `_detect_reversed` uses a ~60-word common-word list; it is a weak signal on
  short or unusual text and is intentionally conservative (it requires
  reversing to produce *more* recognizable words than the input already has).
- The bidi reconstruction handles the common nested override/isolate case,
  not the full Unicode Bidirectional Algorithm (UAX #9).
- This module does not attempt to detect zero-width character steganography,
  emoji-encoded payloads, or general adversarial typography beyond the four
  transforms above. Those would be separate, additional detectors, not part
  of what is implemented here today.

Read the module docstring and code in `api/semantic_fingerprint.py` for the
exact tables and thresholds — they are the actual spec, not this document.
