from __future__ import annotations

import re

FORBIDDEN_PATTERNS = [
    (re.compile(r"\b(kesinlikle|kesin)\s+(yüksel|düş|art|azal|kazand)\w*", re.I), "[bilgi]"),
    (re.compile(r"\bal\s*[.,!?]?\s*sat\b", re.I), "[bilgi]"),
    (re.compile(r"\b(hisseyi|hisse)\s+(al|sat|tut)\w*\b", re.I), "[bilgi]"),
    (re.compile(r"\bgaranti\s+(kazanç|kar|getiri|yüksel)\w*", re.I), "[bilgi]"),
    (re.compile(r"\b(mutlaka|kesinlikle)\s+(al|sat)\w*\b", re.I), "[bilgi]"),
    (re.compile(r"\btavsiye\s+ed(er|iyor)\w*\b", re.I), "değerlendirilebilir"),
]


def apply_safety_guard(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern, replacement in FORBIDDEN_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned

