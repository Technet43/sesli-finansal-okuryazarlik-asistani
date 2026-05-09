from __future__ import annotations

from kap_okuryazar.safety import apply_safety_guard


def clean_advice_language(text: str | None) -> str:
    return apply_safety_guard(text)
