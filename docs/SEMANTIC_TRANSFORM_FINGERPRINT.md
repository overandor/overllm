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
raw_hash             = sha256(exact submitted bytes)
transform_receipt    = { bidi_override, upside_down, reversed, homoglyph_substitution }
transform_confidence = same four keys, each a 0-1 float scoring detector certainty
canonical_text        = recovered/normalized message
canonical_hash        = sha256(canonical_text)
lossless               = whether the recovery is exactly invertible
```

**`transform_confidence` scores are heuristic evidence scores, not
cryptographic proof.** `transform_receipt` stays the stable boolean field —
existing consumers reading it are unaffected. `transform_confidence` is a
separate, additive field carrying the graded signal each detector already
computes internally to decide *how sure* it is, kept symmetric with
`transform_receipt`'s four keys so every transform has a comparable score,
detected or not. `bidi_override`'s detector is a deterministic
control-character scan (no fuzziness exists to score), so its confidence is
always exactly 1.0 when detected and 0.0 otherwise, not a graded value like
the other three. `homoglyph_substitution`'s confidence is the ratio of
substituted to total alphabetic characters (e.g. one Cyrillic letter among
five in "аpple" scores 0.2); the raw substitution count is still available
separately as `homoglyph_substitution_count`, since "how confident" and
"how many characters" are different questions.

A high evidence score is a measured signal, not a guarantee: the
`_detect_reversed` false positive documented in the dogfood scan section
below ("arithmetic, no OS randomness...") was a case where the detector
was confidently wrong, before its threshold was tightened in response.
`transform_confidence` records how strongly the heuristic believed its own
call at fingerprint time — it does not retroactively certify that call was
correct.

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
  "transform_confidence": {"bidi_override": 0.0, "upside_down": 1.0, "reversed": 0.0, "homoglyph_substitution": 0.0},
  "homoglyph_substitution_count": 0,
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
| `reversed` | 80.0% | 80.0% |
| **Overall (160 positive examples)** | **95.0%** | **95.0%** |
| **Control group (40 unmodified sentences)** | **0% false positive rate** | — |

`reversed`'s detection rate was deliberately traded down twice: first from
97.5% to 82.5% (see the dogfood scan section below for the `import os`
false-positive fix), then from 82.5% to 80.0% (see below for the
`no`/`on` self-reversal false-positive fix). The remaining misses are
short/technical sentences where reversing them doesn't produce a strong
enough common-word signal (the current, tightened bar); see
`_detect_reversed` in `api/semantic_fingerprint.py`.

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

## Real tokenizer measurement (not a proxy)

The byte-cost benchmark above uses UTF-8 byte length because no production
tokenizer vocabulary host is reachable from this environment (confirmed:
both `openaipublic.blob.core.windows.net` and `huggingface.co` return 403
through the sandbox's egress proxy, and the Anthropic SDK dropped its local
tokenizer years ago — token counting now requires a live API call). Rather
than stop at a proxy, `tools/bpe_tokenizer.py` trains a real byte-level BPE
tokenizer — the same algorithm GPT-2/3.5/4, Claude, and Llama use — on this
repo's own docs (`README.md`, `DEPLOY.md`, `NO_MOCK_FUNCTIONALITY.md`,
`docs/*.md`; 65,948 bytes, 1,244 learned merges, 1,500-token vocabulary).

**Scope honesty**: this is OverLLM's own tokenizer, trained on a few tens of
KB of this repo's own text, not GPT-4/Claude/Llama's production tokenizer.
Absolute token counts here don't represent what a production API bills.
What's real: the algorithm itself, genuinely trained and genuinely applied,
and the measurement methodology — not a proxy.

The implementation exists in two places that must agree: `tools/bpe_tokenizer.py`
(Python trainer + reference encoder/decoder) and `cpp/src/tokenizer.cpp`
(the real BPE implementation that replaced this repo's earlier
single-character-lookup stub — see git history). `tools/bpe_parity_check.py`
compiles the C++ mirror and asserts byte-for-byte identical token ID
sequences against the Python reference across 13+ test cases, including
RSTF-transformed text.

```bash
python tools/bpe_tokenizer.py train --corpus-glob "README.md" "docs/*.md" --vocab-size 1500 --out-dir cpp/tokenizer_data
python tools/bpe_parity_check.py
python tools/rstf_bpe_token_cost.py --out-md benchmark/rstf/bpe_token_cost_report.md
```

Committed runs: `benchmark/rstf/bpe_token_cost_report.md` / `.json`,
`benchmark/rstf/bpe_parity_report.json`.

| Transform | Token savings ratio |
|---|---|
| `homoglyph` | 78.8% |
| `upside_down` | 75.0% |
| `bidi_override` | 43.0% |
| `reversed` | **38.0%** |
| **Overall** | **66.2%** |

**The key finding this real tokenizer reveals that the byte proxy structurally
cannot**: `reversed` shows real, substantial token savings (38.0%), not 0%.
UTF-8 byte length cannot change under reordering — that's simple arithmetic.
But BPE token count *can*, because merges are learned from forward-reading
corpus text (common substrings like "the", " to", "tion"). Reversing a
string breaks those learned merges, so the reversed text tokenizes into many
more, smaller tokens than the correctly-ordered canonical text. This is a
genuine property of real tokenizers that a byte-length proxy is
mathematically incapable of demonstrating, and it directly supports the
"canonicalization reduces token spend" claim in a way the proxy alone could
not for the `reversed` transform class.

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

**This scan found two real bugs, both fixed, not just documented.** The
first run found 19 lines across `api/main.py`, `api/financeable.py`,
`api/vercel.py`, `training/dpo_trainer.py`, and elsewhere flagged as
`reversed` text — every one was ordinary code containing the substring `os`
(`import os`, `os.getenv(...)`), because reversing `"os"` produces `"so"`,
which is itself a common word, and the detector previously accepted a
single short-word match as sufficient evidence. `_detect_reversed` was
tightened to require at least 3 tokens in the source text and at least 2
post-reversal common-word hits (not 1), which cut this to 1 remaining
unrelated hit: `lang/overml/docs/DESIGN.md`, "arithmetic, no OS
randomness, no per-platform float rounding differences." — flagged (and
its `canonical_text` corrupted into character-reversed gibberish) because
two independent, legitimate uses of "no" reverse into "on" (itself a common
word) and the acronym "OS" reverses into "so" (also a common word), giving
a +1 margin over the source text's own common-word count purely by
coincidence. A rerun after other repo content changed re-surfaced this
exact case, so `_detect_reversed` was tightened again to require the
post-reversal common-word count to exceed the source text's own count by a
margin of at least 2, not just 1. This eliminated the false positive
(verified: `unexpected_hits_elsewhere` went from 1 to 0) at a cost of 1
additional detection out of 40 in the `reversed` benchmark category (see
above). Short common-word self-reversal collisions (`no`/`on` is the
sharpest example — most 2-letter common words don't reverse into another
common word) remain a structural weak point of a word-list heuristic in
general; a real language model or n-gram frequency table would close it
more completely, but is out of scope for this module.

## Honest limits

- The upside-down and homoglyph tables are curated subsets (a few dozen
  entries each), not the full Unicode confusables/rotation space. Text using
  glyphs outside these tables will not be detected.
- `_detect_reversed` uses a ~60-word common-word list, requires >=3 tokens in
  the source text, and requires the post-reversal common-word count to beat
  the source text's own count by a margin of >=2 (not just a raw count of
  >=2); it is a weak signal on short or unusual text, intentionally
  tightened twice after the dogfood scan found it flagging ordinary code and
  then, on a rerun, text repeating short near-mirror-image common words
  (e.g. "no"/"on") — see the dogfood scan section above. This is a
  general property of a fixed word list, not a fully closed problem: any
  short common word that happens to reverse into a different common word is
  a latent false-positive source, though "no"/"on" was the only such
  collision found in this repo's own text.
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
