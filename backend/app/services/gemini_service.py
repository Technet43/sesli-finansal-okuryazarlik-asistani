from __future__ import annotations

import json
import logging
import re

from kap_okuryazar.config import DEFAULT_MODEL

logger = logging.getLogger(__name__)

_CLIENT_CACHE: dict[str, object] = {}


def _load_genai():
    try:
        from google import genai  # type: ignore
        return genai
    except BaseException:  # pyo3 panics inherit from BaseException
        return None


def get_client(api_key: str | None = None):
    key = (api_key or "").strip()
    if not key:
        return None
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]
    genai = _load_genai()
    if genai is None:
        return None
    try:
        client = genai.Client(api_key=key)
        _CLIENT_CACHE[key] = client
        logger.debug("Gemini client created and cached")
        return client
    except BaseException:
        return None


def test_connection(api_key: str | None = None) -> tuple[bool, str]:
    key = (api_key or "").strip()
    if not key:
        return False, "Gemini API key bulunamadı. Sidebar'a kendi anahtarını yapıştır."
    if _load_genai() is None:
        return False, "google-genai paketi yüklenemedi."

    client = get_client(api_key=key)
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
    # Strip markdown code fences
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I | re.M).strip()
        text = re.sub(r"\s*```\s*$", "", text, flags=re.M).strip()
    # Extract first JSON object
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    try:
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object")
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("json_from_text parse error: %s | raw=%s", exc, text[:200])
        raise
