from __future__ import annotations

import re

FORBIDDEN_PATTERNS = [
    # Hard investment commands
    (re.compile(r"\b(kesinlikle|kesin)\s+(yüksel|düş|art|azal|kazand)\w*", re.I), "[bilgi]"),
    (re.compile(r"\bal\s*[.,!?]?\s*sat\b", re.I), "[bilgi]"),
    (re.compile(r"\b(hisseyi|hisse)\s+(al|sat|tut)\w*\b", re.I), "[bilgi]"),
    (re.compile(r"\bgaranti\s+(kazanç|kar|getiri|yüksel)\w*", re.I), "[bilgi]"),
    (re.compile(r"\b(mutlaka|kesinlikle)\s+(al|sat)\w*\b", re.I), "[bilgi]"),
    # Advice phrases
    (re.compile(r"\btavsiye\s+ed(er|iyor)\w*\b", re.I), "değerlendirilebilir"),
    (re.compile(r"\byatırım\s+tavsiyesi\b", re.I), "bilgilendirme"),
    (re.compile(r"\b(portföy(nüze|ünüze)?)\s+(ekle|katın|alın)\w*\b", re.I), "[bilgi]"),
    # Guaranteed outcome framing
    (re.compile(r"\b(fiyat\s+)?(kesin(likle)?|mutlaka)\s+(yüksele|düşe|artaca|azalaca)\w*", re.I), "[bilgi]"),
    (re.compile(r"\b(çok\s+)?kârlı\s+(bir\s+)?(fırsat|yatırım)\b", re.I), "[bilgi]"),
    (re.compile(r"\bbu\s+hisseyi?\s+(alın|satın|tutun)\b", re.I), "[bilgi]"),
    # Softer but still directive
    (re.compile(r"\bhemen\s+(al|sat|karar\s+ver)\w*\b", re.I), "[bilgi]"),
    (re.compile(r"\bfiyat\s+hedefi\s+\d", re.I), "[fiyat tahmini]"),
    (re.compile(r"\b(güçlü\s+)?(al|sat)\s+önerisi\b", re.I), "[bilgi]"),
]


def apply_safety_guard(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern, replacement in FORBIDDEN_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned

