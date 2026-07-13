from __future__ import annotations
import hashlib
import re
from typing import Any

BIDI_CONTROLS = {chr(c) for c in list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A))}
ZERO_WIDTH = {chr(c) for c in list(range(0x200B, 0x2010)) + [0xFEFF]}
UPSIDE_DOWN = {
    "ɐ": "a", "ɑ": "a", "ᵇ": "b", "ɔ": "c", "ǝ": "e", "ɟ": "f",
    "ƃ": "g", "ɥ": "h", "ᴉ": "i", "ı": "i", "ɾ": "j", "ʞ": "k",
    "ɯ": "m", "ɹ": "r", "ʇ": "t", "ʌ": "v", "ʍ": "w", "ʎ": "y",
    "∀": "A", "ᗺ": "B", "Ɔ": "C", "ᗡ": "D", "Ǝ": "E", "Ⅎ": "F",
    "⅁": "G", "ſ": "J", "Ʞ": "K", "˥": "L", "Ԁ": "P", "Ό": "Q",
    "ᴚ": "R", "⊥": "T", "∩": "U", "Λ": "V", "⅄": "Y",
    "¡": "!", "¿": "?", "˙": ".", "ʻ": ",",
}
HOMOGLYPHS = {
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "У": "Y",
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "у": "y", "і": "i", "ј": "j", "ӏ": "l", "ѕ": "s", "ԁ": "d",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I",
    "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T",
    "Χ": "X", "Υ": "Y", "ο": "o", "ρ": "p", "ν": "v", "χ": "x",
    "ι": "i", "α": "a", "β": "b", "γ": "y",
}

# Heavy prompt injection detection patterns
PROMPT_INJECTION_PATTERNS = [
    # Direct instruction overrides
    r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"(?i)forget\s+(everything|all\s+instructions|the\s+above)",
    r"(?i)disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|text)",
    r"(?i)override\s+(your\s+)?(programming|instructions|training)",
    
    # Role-playing and persona changes
    r"(?i)you\s+are\s+now\s+(a\s+)?(new|different)",
    r"(?i)act\s+as\s+(if\s+you\s+were)?",
    r"(?i)pretend\s+(to\s+be|that\s+you\s+are)",
    r"(?i)assume\s+(the\s+)?(role|persona|identity)",
    r"(?i)from\s+now\s+on\s+you\s+are",
    
    # System prompt bypass attempts
    r"(?i)system\s*:\s*",
    r"(?i)developer\s*:\s*",
    r"(?i)assistant\s*:\s*",
    r"(?i)\[SYSTEM\]",
    r"(?i)\[INSTRUCTION\]",
    
    # Jailbreak patterns
    r"(?i)jailbreak",
    r"(?i)bypass\s+(your\s+)?(safety|security|restrictions|filters)",
    r"(?i)break\s+(your\s+)?(rules|programming|constraints)",
    r"(?i)escape\s+(your\s+)?(programming|training|constraints)",
    
    # Encoding-based injection attempts
    r"(?i)base64\s*:\s*[A-Za-z0-9+/=]{20,}",
    r"(?i)hex\s*:\s*[0-9a-fA-F]{20,}",
    r"(?i)rot13\s*:\s*[a-zA-Z]{20,}",
    
    # Repetition attacks
    r"(.)\1{10,}",  # 10+ repeated characters
    
    # Command injection style
    r"(?i);?\s*(rm|del|format|shutdown|reboot)",
    r"(?i)\|\s*(curl|wget|nc|netcat)",
    
    # Data exfiltration patterns
    r"(?i)print\s+(your\s+)?(system\s+)?prompt",
    r"(?i)show\s+(your\s+)?(instructions|training|data)",
    r"(?i)reveal\s+(your\s+)?(internal|hidden|system)\s+(prompt|instructions)",
    
    # Context overflow attempts
    r"(?i)(repeat|copy)\s+(the\s+)?(above|previous)\s+(text|words)",
    r"(?i)say\s+(everything|all\s+of\s+the\s+above)",
    
    # Format breaking
    r"(?i)\[START\]",
    r"(?i)\[END\]",
    r"(?i)\[BEGIN\]",
    r"(?i)\[FINISH\]",
    
    # Obfuscated instruction patterns
    r"(?i)\\u[0-9a-fA-F]{4}",  # Unicode escape sequences
    r"(?i)&#[0-9]+;",  # HTML entities
    
    # Multi-language injection attempts
    r"(?i)ignorar\s+(todas\s+las\s+)?instrucciones",
    r"(?i)ignorer\s+(toutes\s+les\s+)?instructions",
    r"(?i)ignorare\s+(tutte\s+le\s+)?istruzioni",
]

def detect_prompt_injection(text: str) -> dict[str, Any]:
    """Detect potential prompt injection attempts in text."""
    text_lower = text.lower()
    detected_patterns = []
    severity = "none"
    
    for pattern in PROMPT_INJECTION_PATTERNS:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            detected_patterns.append({
                "pattern": pattern,
                "match": match.group(),
                "position": match.start(),
            })
    
    if detected_patterns:
        # Determine severity based on pattern count and type
        high_risk_keywords = ["jailbreak", "bypass", "override", "system:", "developer:"]
        has_high_risk = any(
            keyword in pattern["match"].lower() 
            for pattern in detected_patterns 
            for keyword in high_risk_keywords
        )
        
        if has_high_risk or len(detected_patterns) >= 3:
            severity = "high"
        elif len(detected_patterns) >= 2:
            severity = "medium"
        else:
            severity = "low"
    
    return {
        "detected": len(detected_patterns) > 0,
        "severity": severity,
        "pattern_count": len(detected_patterns),
        "patterns": detected_patterns[:10],  # Limit to first 10 patterns
    }

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def canonicalize(text: str, *, force_reverse: bool = False, strip_zero_width: bool = True, detect_injection: bool = True) -> dict[str, Any]:
    raw = str(text or "")
    out: list[str] = []
    transforms: list[str] = []
    
    # Detect prompt injection in raw text
    injection_detection = detect_prompt_injection(raw) if detect_injection else {"detected": False, "severity": "none", "pattern_count": 0, "patterns": []}
    
    for ch in raw:
        if ch in BIDI_CONTROLS:
            transforms.append("bidi_control_stripped")
            continue
        if strip_zero_width and ch in ZERO_WIDTH:
            transforms.append("zero_width_stripped")
            continue
        if ch in UPSIDE_DOWN:
            transforms.append("upside_down")
            out.append(UPSIDE_DOWN[ch])
            continue
        if ch in HOMOGLYPHS:
            transforms.append("homoglyph")
            out.append(HOMOGLYPHS[ch])
            continue
        out.append(ch)
    if "upside_down" in transforms or force_reverse:
        out.reverse()
        if force_reverse and "upside_down" not in transforms:
            transforms.append("reversed_forced")
    canonical = "".join(out)
    raw_bytes = len(raw.encode("utf-8"))
    canonical_bytes = len(canonical.encode("utf-8"))
    
    # Detect prompt injection in canonical text as well
    canonical_injection_detection = detect_prompt_injection(canonical) if detect_injection else {"detected": False, "severity": "none", "pattern_count": 0, "patterns": []}
    
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
        "prompt_injection_detection": injection_detection,
        "canonical_injection_detection": canonical_injection_detection,
        "injection_risk": injection_detection["severity"] if injection_detection["detected"] else "none",
    }
