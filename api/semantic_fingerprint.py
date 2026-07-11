"""Reversible Semantic Transform Fingerprint (RSTF) for OverLLM.

A cryptographic hash identifies exact bytes: change one character and the
hash changes completely. That is correct and by design, but it means a hash
alone cannot answer a narrower, useful question: "are these two byte-different
strings the same recoverable message, just wrapped in a known, reversible
presentation transform?"

This module answers that question for a specific, honestly-scoped set of
transforms that are well-defined and testable:

- reversed        - the string was written back-to-front.
- upside_down     - the string was reversed and each character was swapped
                     for its 180-degree-rotation Unicode lookalike (the
                     technique used by common "flip text" generators).
- bidi_override   - the string contains Unicode bidirectional override or
                     isolate control characters (U+202E RLO and friends) that
                     make the rendered/read text differ from the stored
                     character order. This is the mechanism behind the
                     "Trojan Source" (CVE-2021-42574) filename/code spoofing
                     class of attack, so detecting it has real security value
                     for prompt/content auditing, not just novelty value.
- homoglyph       - characters were swapped for confusable look-alikes from
                     another script (Cyrillic/Greek vs. Latin). This
                     normalization is lossy/many-to-one by construction: it
                     cannot recover which script was originally used.

It is not a general theory of "semantic identity," not a replacement for
Unicode normalization (which it uses, via NFKC, as one step), and not a
perceptual/fuzzy hash. The glyph tables are curated subsets, not exhaustive
Unicode confusables data. Treat this as a heuristic first-class receipt:

    raw_hash             = sha256(exact submitted bytes)
    transform_receipt    = which of the transforms above were detected
    transform_confidence = same four keys, each a 0-1 heuristic evidence
                            score, not cryptographic proof - see the
                            "no OS randomness" false positive in
                            docs/SEMANTIC_TRANSFORM_FINGERPRINT.md for a
                            documented case of a detector being confidently
                            wrong before its threshold was tightened
    canonical_text        = the recovered/normalized message
    canonical_hash        = sha256(canonical_text)
    lossless               = whether the recovery is exactly invertible

"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/fingerprint", tags=["semantic-transform-fingerprint"])

FINGERPRINT_VERSION = "RSTF-1"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Upside-down (180-degree rotation) glyph table.
#
# Curated mapping used by common "flip text" generators. Only lowercase
# ASCII letters, digits, and a handful of punctuation marks have a stable
# rotated lookalike; uppercase input is lowercased before lookup, which is
# why upside-down recovery is labeled lossless for case-insensitive input
# only (case information is not preserved by real flip-text glyphs either).
# ---------------------------------------------------------------------------
_UPSIDE_DOWN_MAP: dict[str, str] = {
    "a": "ɐ", "b": "q", "c": "ɔ", "d": "p", "e": "ǝ", "f": "ɟ", "g": "ƃ",
    "h": "ɥ", "i": "ᴉ", "j": "ɾ", "k": "ʞ", "l": "ʃ", "m": "ɯ", "n": "u",
    "o": "o", "p": "d", "q": "b", "r": "ɹ", "s": "s", "t": "ʇ", "u": "n",
    "v": "ʌ", "w": "ʍ", "x": "x", "y": "ʎ", "z": "z",
    "0": "0", "1": "1", "2": "ᄅ", "3": "Ɛ", "4": "ㄣ", "5": "5", "6": "9",
    "7": "ㄥ", "8": "8", "9": "6",
    ".": "˙", ",": "'", "'": ",", "?": "¿", "!": "¡",
    "(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{",
    "<": ">", ">": "<", "_": "‾",
}
_UPSIDE_DOWN_REVERSE: dict[str, str] = {v: k for k, v in _UPSIDE_DOWN_MAP.items()}
_NON_ASCII_FLIP_VALUES = {v for v in _UPSIDE_DOWN_MAP.values() if ord(v) > 127}


def _decode_upside_down(text: str) -> str:
    reversed_text = text[::-1]
    return "".join(_UPSIDE_DOWN_REVERSE.get(c, c) for c in reversed_text)


def _detect_upside_down(text: str) -> tuple[bool, float]:
    alnum_chars = [c for c in text if c.isalnum()]
    if len(alnum_chars) < 3:
        return False, 0.0
    distinctive = sum(1 for c in alnum_chars if c in _NON_ASCII_FLIP_VALUES)
    ratio = distinctive / len(alnum_chars)
    if ratio < 0.15:
        return False, 0.0
    return True, min(1.0, ratio * 2)


# ---------------------------------------------------------------------------
# Plain reversal detection. There is no character substitution involved, so
# the only signal available is "does reversing the text produce recognizable
# words that the text does not already contain."
# ---------------------------------------------------------------------------
_COMMON_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "to", "of",
    "and", "or", "in", "on", "at", "for", "with", "this", "that", "these",
    "those", "it", "its", "i", "you", "he", "she", "we", "they", "not",
    "no", "yes", "do", "does", "did", "have", "has", "had", "will", "would",
    "can", "could", "should", "from", "by", "as", "if", "but", "so", "my",
    "your", "our", "text", "message", "test",
}
_WORD_RE = re.compile(r"[A-Za-z']+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _WORD_RE.findall(text)]


def _detect_reversed(text: str) -> tuple[bool, float]:
    original_tokens = _tokenize(text)
    # A single short common-word match is not enough signal: e.g. "import os"
    # reversed produces "so tropmi", and "so" alone is a common word, which
    # previously flagged ordinary code (found by the dogfood scan in
    # tools/rstf_dogfood_scan.py). Require a real sentence's worth of tokens
    # and at least two post-reversal matches before calling it reversed.
    if len(original_tokens) < 3:
        return False, 0.0
    candidate_tokens = _tokenize(text[::-1])
    original_hits = sum(1 for t in original_tokens if t in _COMMON_WORDS)
    candidate_hits = sum(1 for t in candidate_tokens if t in _COMMON_WORDS)
    # A margin of just +1 over original_hits is not enough either: short
    # common words are prone to self-reversal collisions with *other* short
    # common words ("no" <-> "on", "OS" <-> "so"), so two independent,
    # legitimate uses of "no" plus one acronym can rack up a +1 margin in
    # ordinary forward-reading text (found by the dogfood scan flagging
    # "arithmetic, no OS randomness, no per-platform..." in
    # lang/overml/docs/DESIGN.md as reversed). Require a +2 margin instead.
    if candidate_hits < 2 or candidate_hits - original_hits < 2:
        return False, 0.0
    confidence = min(1.0, candidate_hits / max(1, len(candidate_tokens)))
    return True, confidence


# ---------------------------------------------------------------------------
# Unicode bidirectional override / isolate recovery.
#
# This is a simplified reconstruction of "what a human reads" for text
# containing RLO/LRO/isolate controls, not a full UAX#9 bidi algorithm
# implementation. It handles the common single- and nested-override case
# (the shape used in Trojan Source-style spoofing) by buffering each
# override/isolate scope and reversing it on close when it was RTL.
# ---------------------------------------------------------------------------
_RLO = "‮"
_LRO = "‭"
_PDF = "‬"
_ISOLATE_STARTS = {"⁦", "⁧", "⁨"}  # LRI, RLI, FSI
_PDI = "⁩"
_BIDI_MARKS = {"‎", "‏", "؜"}  # LRM, RLM, ALM
_BIDI_CONTROL_RE = re.compile(
    "[" + _RLO + _LRO + _PDF + "".join(_ISOLATE_STARTS) + _PDI + "".join(_BIDI_MARKS) + "]"
)


def _recover_bidi_override(text: str) -> tuple[bool, str, list[str]]:
    if not _BIDI_CONTROL_RE.search(text):
        return False, text, []

    trace: list[str] = []
    stack: list[list[Any]] = [[[], False]]
    for c in text:
        if c == _RLO:
            stack.append([[], True])
            trace.append("rlo_start")
        elif c == _LRO:
            stack.append([[], False])
            trace.append("lro_start")
        elif c in _ISOLATE_STARTS:
            stack.append([[], False])
            trace.append("isolate_start")
        elif c in (_PDF, _PDI):
            if len(stack) > 1:
                buf, reverse = stack.pop()
                content = list(reversed(buf)) if reverse else buf
                stack[-1][0].extend(content)
                trace.append("scope_pop")
            else:
                trace.append("unmatched_pop_ignored")
        elif c in _BIDI_MARKS:
            trace.append("mark_stripped")
        else:
            stack[-1][0].append(c)

    while len(stack) > 1:
        buf, reverse = stack.pop()
        content = list(reversed(buf)) if reverse else buf
        stack[-1][0].extend(content)
        trace.append("scope_closed_at_eof")

    recovered = "".join(stack[0][0])
    return True, recovered, trace


# ---------------------------------------------------------------------------
# Homoglyph / confusable normalization.
#
# A curated subset of Cyrillic and Greek letters that are visually identical
# or near-identical to Latin letters. This is deliberately lossy: multiple
# source characters collapse onto the same canonical character, so the
# original script cannot be recovered from canonical_text alone.
# ---------------------------------------------------------------------------
_CONFUSABLES: dict[str, str] = {
    # Cyrillic -> Latin
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "і": "i", "ѕ": "s", "ј": "j", "һ": "h", "ԁ": "d", "ԛ": "q", "ѡ": "w",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X", "Ѕ": "S", "І": "I", "Ј": "J",
    # Greek -> Latin
    "α": "a", "ο": "o", "ρ": "p", "υ": "u", "τ": "t", "ι": "i", "κ": "k",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
}


def _normalize_homoglyphs(text: str) -> tuple[bool, str, dict[str, int], float]:
    # Guard against the single most damaging false-positive mode: monolingual
    # non-Latin prose (plain Russian, Greek, etc.) contains plenty of letters
    # that are in _CONFUSABLES, but there is no Latin string being spoofed —
    # it's just text in another script. A real homograph attack mixes scripts
    # ("аpple.com": Cyrillic а next to Latin p,p,l,e). Only treat confusables
    # as a substitution signal when the text also contains ordinary Latin
    # letters; otherwise leave it untouched. This does not fully solve
    # homograph detection (a sentence that legitimately mixes scripts, e.g.
    # an English sentence naming a Cyrillic word, can still trip this), but
    # it removes the worst case: any non-English input being "corrected"
    # into corrupted text.
    has_latin_letter = any(c.isascii() and c.isalpha() for c in text)
    if not has_latin_letter:
        return False, text, {}, 0.0

    hits: dict[str, int] = {}
    out_chars: list[str] = []
    alpha_count = 0
    for c in text:
        if c.isalpha():
            alpha_count += 1
        replacement = _CONFUSABLES.get(c)
        if replacement is not None:
            hits[c] = hits.get(c, 0) + 1
            out_chars.append(replacement)
        else:
            out_chars.append(c)
    substitution_count = sum(hits.values())
    # Mirrors _detect_upside_down's ratio-based confidence: how much of the
    # text's alphabetic content was actually substituted, not just whether
    # any substitution happened at all.
    confidence = min(1.0, substitution_count / alpha_count) if alpha_count else 0.0
    return (len(hits) > 0), "".join(out_chars), hits, confidence


# ---------------------------------------------------------------------------
# Fingerprint composition.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Encoders. These apply each transform forward and exist to generate
# reproducible benchmark fixtures (see tools/rstf_benchmark.py) from the same
# tables the detectors use — they are not part of the detection API surface.
# ---------------------------------------------------------------------------


def encode_reversed(text: str) -> str:
    return text[::-1]


def encode_upside_down(text: str) -> str:
    """Lowercases the input, then applies the same rotation+reversal a real
    flip-text generator would. Case is intentionally lost, matching how the
    detector's recovery is documented as lossless only for case-insensitive
    input."""
    lowered = text.lower()
    mapped = "".join(_UPSIDE_DOWN_MAP.get(c, c) for c in lowered)
    return mapped[::-1]


def encode_homoglyph(text: str, rate: float = 1.0) -> str:
    """Substitutes lowercase Latin letters with a Cyrillic/Greek confusable
    where one is available in _CONFUSABLES. rate=1.0 substitutes every
    eligible character; lower rates substitute a deterministic subset."""
    reverse_confusables: dict[str, str] = {}
    for confusable, latin in _CONFUSABLES.items():
        reverse_confusables.setdefault(latin, confusable)

    out_chars: list[str] = []
    eligible_index = 0
    for c in text:
        replacement = reverse_confusables.get(c)
        if replacement is not None:
            eligible_index += 1
            if rate >= 1.0 or (eligible_index % max(1, round(1 / rate))) == 0:
                out_chars.append(replacement)
                continue
        out_chars.append(c)
    return "".join(out_chars)


def encode_bidi_override(text: str, start: int, end: int) -> str:
    """Wraps text[start:end] so a human reading the rendered output sees the
    original substring, but the stored character order is reversed within
    the RLO/PDF span (mirrors how RTLO spoofing is actually constructed)."""
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    span = text[start:end][::-1]
    return text[:start] + _RLO + span + _PDF + text[end:]


def compute_fingerprint(raw_text: str) -> dict[str, Any]:
    raw_hash = _sha256_text(raw_text)

    bidi_hit, bidi_text, bidi_trace = _recover_bidi_override(raw_text)
    updown_hit, updown_conf = _detect_upside_down(bidi_text)
    reversed_hit, reversed_conf = _detect_reversed(bidi_text)

    orientation = "none"
    working_text = bidi_text
    audit_trace = list(bidi_trace)
    if updown_hit and updown_conf >= reversed_conf:
        working_text = _decode_upside_down(bidi_text)
        orientation = "upside_down"
        audit_trace.append("upside_down_decoded")
    elif reversed_hit:
        working_text = bidi_text[::-1]
        orientation = "reversed"
        audit_trace.append("string_reversed")

    glyph_hit, canonical_text, glyph_hits, glyph_conf = _normalize_homoglyphs(working_text)
    if glyph_hit:
        audit_trace.append(f"homoglyphs_normalized:{sum(glyph_hits.values())}")

    canonical_text = unicodedata.normalize("NFKC", canonical_text)
    canonical_hash = _sha256_text(canonical_text)

    return {
        "fingerprint_version": FINGERPRINT_VERSION,
        "raw_hash": raw_hash,
        "raw_length": len(raw_text),
        "canonical_hash": canonical_hash,
        "canonical_text": canonical_text,
        "transform_receipt": {
            "bidi_override": bidi_hit,
            "upside_down": orientation == "upside_down",
            "reversed": orientation == "reversed",
            "homoglyph_substitution": glyph_hit,
        },
        "orientation": orientation,
        "transform_detected": bidi_hit or orientation != "none" or glyph_hit,
        "lossless": not glyph_hit,
        # Keys match transform_receipt's keys exactly, each a 0-1 float, so
        # every detected-or-not transform has a comparable confidence value.
        # bidi_override's detector is a deterministic control-character scan
        # (no fuzzy heuristic exists for it, unlike the other three), so its
        # confidence is 1.0 when detected and 0.0 otherwise rather than a
        # graded score - an honest "no uncertainty" value, not a fabricated
        # one.
        "transform_confidence": {
            "bidi_override": 1.0 if bidi_hit else 0.0,
            "upside_down": round(updown_conf, 3),
            "reversed": round(reversed_conf, 3),
            "homoglyph_substitution": round(glyph_conf, 3),
        },
        "homoglyph_substitution_count": sum(glyph_hits.values()),
        "audit_trace": audit_trace,
        "truth_label": "heuristic_curated_tables_not_exhaustive_unicode_coverage",
    }


def compare_fingerprints(text_a: str, text_b: str) -> dict[str, Any]:
    fp_a = compute_fingerprint(text_a)
    fp_b = compute_fingerprint(text_b)
    return {
        "fingerprint_version": FINGERPRINT_VERSION,
        "same_bytes": fp_a["raw_hash"] == fp_b["raw_hash"],
        "same_canonical_message": fp_a["canonical_hash"] == fp_b["canonical_hash"],
        "fingerprint_a": fp_a,
        "fingerprint_b": fp_b,
    }


class FingerprintRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw text to fingerprint")


class CompareRequest(BaseModel):
    text_a: str = Field(..., min_length=1)
    text_b: str = Field(..., min_length=1)


@router.post("/compute")
async def compute(request: FingerprintRequest):
    return compute_fingerprint(request.text)


@router.post("/compare")
async def compare(request: CompareRequest):
    return compare_fingerprints(request.text_a, request.text_b)
