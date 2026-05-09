from __future__ import annotations

import json
import os
import re

from kap_okuryazar.config import DEFAULT_MODEL


def _load_genai():
    try:
        from google import genai  # type: ignore
        return genai
    except BaseException:  # pyo3 panics inherit from BaseException
        return None


def get_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    genai = _load_genai()
    if genai is None:
        return None
    try:
        return genai.Client(api_key=api_key)
    except BaseException:
        return None


def test_connection() -> tuple[bool, str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return False, "GEMINI_API_KEY bulunamadı. .env dosyasına ekle."
    if _load_genai() is None:
        return False, "google-genai paketi yüklenemedi."

    client = get_client()
    if client is None:
        return False, "Gemini istemcisi başlatılamadı."

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
