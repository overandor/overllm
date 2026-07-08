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
