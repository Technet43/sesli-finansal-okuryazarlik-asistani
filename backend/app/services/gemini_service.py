from __future__ import annotations

import json
import os
import re

from kap_okuryazar.config import DEFAULT_MODEL

try:
    from google import genai
except Exception:  # pragma: no cover - surfaced by API status
    genai = None


def get_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def test_connection() -> tuple[bool, str]:
    client = get_client()
    if client is None:
        if genai is None:
            return False, "google-genai paketi yüklenemedi."
        return False, "GEMINI_API_KEY bulunamadı. .env dosyasına ekle."

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents="Sadece 'hazır' yaz.",
        )
        text = (response.text or "").strip()
        return True, f"Gemini bağlantısı başarılı: {text[:80] or 'yanıt alındı'}"
    except Exception as exc:
        message = str(exc)
        if "API_KEY_INVALID" in message or "INVALID_ARGUMENT" in message:
            return False, "API key geçersiz görünüyor."
        if "PERMISSION_DENIED" in message:
            return False, "API key bu modele erişemiyor veya proje izinleri kapalı."
        if "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
            return False, "Kota veya limit dolmuş görünüyor."
        if "NOT_FOUND" in message:
            return False, f"Model bulunamadı: {DEFAULT_MODEL}."
        return False, f"Gemini bağlantı hatası: {message[:220]}"


def json_from_text(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    return json.loads(text)
