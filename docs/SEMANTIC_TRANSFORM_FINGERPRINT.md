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
| `reversed` | Reversing the string produces >=2 recognizable common-word hits, more than the un-reversed form has | Reverse the string | Yes |
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
| `reversed` | 82.5% | 82.5% |
| **Overall (160 positive examples)** | **95.6%** | **95.6%** |
| **Control group (40 unmodified sentences)** | **0% false positive rate** | — |

`reversed`'s detection rate was deliberately traded down from an earlier
97.5% — see the dogfood scan section below for why. The remaining misses are
short/technical sentences where reversing them doesn't produce two or more
common-word hits (the current, tightened bar); see `_detect_reversed` in
`api/semantic_fingerprint.py`.

This is a v0.1, 160-example synthetic benchmark plus a 40-example control
group, not a claim of coverage against real adversarial traffic, zero-width
steganography, fullwidth-form abuse, emoji-encoded payloads, or mixed/stacked
transforms — none of which this module implements yet. **It is also
circular by construction**: the same `encode_*` helpers that generate these
"attacks" are the exact inverse of the `decode_*`/detection logic, so a high
score here proves internal consistency, not real-world efficacy — see the
independent adversarial eval below for a non-circular check.

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

## Independent adversarial eval (non-circular)

`tools/rstf_adversarial_eval.py` runs against `benchmark/rstf/adversarial_corpus.json`,
which is hand-authored / drawn from independently-recalled reference examples
— never produced by calling this module's own `encode_*` helpers. Every
example's provenance is recorded in its `note` field, including one case
where an initial recollection of a "widely cited" flip-text example turned
out to be unreliable and was corrected against arithmetic instead of
asserted (see `updown-2` in the corpus file). It also evaluates a negative
set of legitimate non-English (Russian, Ukrainian, Greek) and edge-case
Latin (accented names, code, URLs) text that the main benchmark never
covered, because its corpus was 100% English ASCII.

```bash
python tools/rstf_adversarial_eval.py
python tools/rstf_adversarial_eval.py --out-md benchmark/rstf/adversarial_report.md
```

Committed run: `benchmark/rstf/adversarial_report.md` / `.json`.

| | Count | Detection/recovery rate | False positive rate |
|---|---|---|---|
| Positive examples (independent) | 12 | 91.7% | — |
| Negative examples (legitimate text) | 9 | — | 0.0% |

**This eval found a real bug, which was fixed, not just documented.** Before
the fix, `_normalize_homoglyphs` flagged *any* text containing a character in
its Cyrillic/Greek confusables table — including plain, monolingual Russian
or Greek prose, which naturally contains those letters. Result: 100% false
positive rate (4/4) on the `legitimate_non_english` category, and
`canonical_text` would "correct" real Russian sentences into corrupted
Latin/Cyrillic mixes. The fix requires the text to also contain ordinary
Latin letters before treating a confusable as a substitution signal — a real
homograph attack mixes scripts (`аpple.com`: Cyrillic а next to Latin
p,p,l,e), monolingual non-Latin text doesn't. This does not fully solve
homograph detection: a sentence that legitimately mixes scripts (e.g. an
English sentence naming a Cyrillic word) can still trip it, which is a
harder problem intentionally out of scope for a curated-table heuristic.

## Dogfood scan (real text, not a customer pilot)

`tools/rstf_dogfood_scan.py` runs the fingerprint module against this
repository's own `.md` and `.py` files, line by line — real, naturally
occurring text that nobody constructed to make RSTF look good or bad. This
is explicitly **not a customer pilot**: no external party supplied the input
data. What it adds beyond the synthetic benchmarks: a check for false
positives on text nobody designed as a test case.

```bash
python tools/rstf_dogfood_scan.py
python tools/rstf_dogfood_scan.py --out-md benchmark/rstf/dogfood_report.md
```

Committed run: `benchmark/rstf/dogfood_report.md` / `.json`.

**This scan also found a real bug, which was fixed.** The first run found 19
lines across `api/main.py`, `api/financeable.py`, `api/vercel.py`,
`training/dpo_trainer.py`, and elsewhere flagged as `reversed` text — every
one was ordinary code containing the substring `os` (`import os`,
`os.getenv(...)`), because reversing `"os"` produces `"so"`, which is itself
a common word, and the detector previously accepted a single short-word
match as sufficient evidence. `_detect_reversed` was tightened to require
at least 3 tokens in the source text and at least 2 post-reversal
common-word hits (not 1), which cut this to 1 remaining unrelated hit. That
1 remaining case (`lang/overml/docs/DESIGN.md:160`, "arithmetic, no OS
randomness...") is a harder, structural edge case: "no" and "on" are both
extremely common English words that are near-mirror-images of each other, so
text using "no" multiple times can out-score itself when reversed. Fixing
that fully would need a real language model or n-gram frequency table, not a
~60-word list — documented as a known residual limitation rather than chased
further, since each additional tightening pass trades away real detection
rate (see the benchmark section above).

## Honest limits

- The upside-down and homoglyph tables are curated subsets (a few dozen
  entries each), not the full Unicode confusables/rotation space. Text using
  glyphs outside these tables will not be detected.
- `_detect_reversed` uses a ~60-word common-word list and requires >=3 tokens
  and >=2 post-reversal hits; it is a weak signal on short or unusual text,
  intentionally tightened after the dogfood scan found it flagging ordinary
  code. A known residual false positive remains on text that repeats short
  near-mirror-image common words (e.g. "no"/"on") — see the dogfood scan
  section above.
- `_normalize_homoglyphs` requires the text to contain both Latin letters and
  a confusable character before flagging, to avoid flagging monolingual
  non-Latin prose (found by the independent adversarial eval, see above). A
  sentence that legitimately mixes scripts can still trip it; this is not a
  full implementation of Unicode's script-mixing restriction levels (UTS
  #39).
- The bidi reconstruction handles the common nested override/isolate case,
  not the full Unicode Bidirectional Algorithm (UAX #9).
- This module does not attempt to detect zero-width character steganography,
  emoji-encoded payloads, or general adversarial typography beyond the four
  transforms above. Those would be separate, additional detectors, not part
  of what is implemented here today.
- The 160-example synthetic benchmark is circular (generated by the same
  tables the detector uses); treat its numbers as an internal-consistency
  check, and the independent adversarial eval / dogfood scan as the
  non-circular evidence.

Read the module docstring and code in `api/semantic_fingerprint.py` for the
exact tables and thresholds — they are the actual spec, not this document.
