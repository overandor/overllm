from __future__ import annotations

import hashlib
from typing import Any

BIDI_CONTROLS = {chr(c) for c in list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A))}
ZERO_WIDTH = {chr(c) for c in list(range(0x200B, 0x2010)) + [0xFEFF]}
UPSIDE_DOWN = {
    "a":"ɐ","b":"ᵇ","c":"ɔ","e":"ǝ","f":"ɟ","g":"ƃ","h":"ɥ",
    "i":"ᴉ","j":"ɾ","k":"ʞ","m":"ɯ","r":"ɹ","t":"ʇ","v":"ʌ",
    "w":"ʍ","y":"ʎ",".":"˙","!":"¡","?":"¿",
}
UPSIDE_DOWN_RECOVER = {v:k for k,v in UPSIDE_DOWN.items()}
UPSIDE_DOWN_RECOVER.update({
    "ɑ":"a","ı":"i","∀":"A","ᗺ":"B","Ɔ":"C","ᗡ":"D","Ǝ":"E","Ⅎ":"F",
    "⅁":"G","ſ":"J","Ʞ":"K","˥":"L","Ԁ":"P","Ό":"Q","ᴚ":"R","⊥":"T",
    "∩":"U","Λ":"V","⅄":"Y","ʻ":",",
})
HOMO_INJECT = {
    "A":"А","B":"В","E":"Е","K":"К","M":"М","H":"Н","O":"О","P":"Р","C":"С","T":"Т","X":"Х","Y":"У",
    "a":"а","e":"е","o":"о","p":"р","c":"с","x":"х","y":"у","i":"і","j":"ј","l":"ӏ","s":"ѕ","d":"ԁ",
}
HOMO_RECOVER = {v:k for k,v in HOMO_INJECT.items()}
HOMO_RECOVER.update({
    "Α":"A","Β":"B","Ε":"E","Ζ":"Z","Η":"H","Ι":"I","Κ":"K","Μ":"M","Ν":"N","Ο":"O","Ρ":"P","Τ":"T","Χ":"X","Υ":"Y",
    "ο":"o","ρ":"p","ν":"v","χ":"x","ι":"i","α":"a","β":"b","γ":"y",
})

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def inject_homoglyph(text: str) -> str:
    return "".join(HOMO_INJECT.get(ch, ch) for ch in text)

def inject_upside_down(text: str) -> str:
    return "".join(UPSIDE_DOWN.get(ch, ch) for ch in text)[::-1]

def inject_bidi(text: str) -> str:
    return "\u202e" + text + "\u202c"

def inject_reversed(text: str) -> str:
    return text[::-1]

def canonicalize(text: str, *, force_reverse: bool = False, strip_zero_width: bool = True) -> dict[str, Any]:
    raw = str(text or "")
    out: list[str] = []
    transforms: list[str] = []
    for ch in raw:
        if ch in BIDI_CONTROLS:
            transforms.append("bidi_control_stripped")
            continue
        if strip_zero_width and ch in ZERO_WIDTH:
            transforms.append("zero_width_stripped")
            continue
        if ch in UPSIDE_DOWN_RECOVER:
            transforms.append("upside_down")
            out.append(UPSIDE_DOWN_RECOVER[ch])
            continue
        if ch in HOMO_RECOVER:
            transforms.append("homoglyph")
            out.append(HOMO_RECOVER[ch])
            continue
        out.append(ch)
    if "upside_down" in transforms or force_reverse:
        out.reverse()
        if force_reverse and "upside_down" not in transforms:
            transforms.append("reversed_forced")
    canonical = "".join(out)
    raw_bytes = len(raw.encode("utf-8"))
    canonical_bytes = len(canonical.encode("utf-8"))
    return {
        "raw_text": raw,
        "canonical_text": canonical,
        "changed": raw != canonical or bool(transforms),
        "transforms": sorted(set(transforms)),
        "raw_utf8_bytes": raw_bytes,
        "canonical_utf8_bytes": canonical_bytes,
        "bytes_saved": raw_bytes - canonical_bytes,
        "raw_sha256": sha256_hex(raw),
        "canonical_sha256": sha256_hex(canonical),
    }
