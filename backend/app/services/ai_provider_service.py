from __future__ import annotations

import json
import logging
from typing import Iterator

import requests

from app.core.config import (
    AI_PROVIDER,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    GEMINI_MODEL,
)
from app.services.gemini_service import get_client

logger = logging.getLogger(__name__)

API_LIMIT_MESSAGE = "API kullanım limiti doldu. Lütfen birkaç dakika bekleyip tekrar deneyin."
API_KEY_MESSAGE = "API anahtarı bulunamadı. Lütfen ayarlardan kendi API anahtarını gir."


class AIProviderError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


ProviderName = str


def active_provider(provider: ProviderName | None = None) -> str:
    candidate = (provider or AI_PROVIDER).strip().lower()
    return candidate if candidate in {"gemini", "deepseek"} else "gemini"


def provider_label(provider: ProviderName | None = None) -> str:
    return "DeepSeek" if active_provider(provider) == "deepseek" else "Gemini"


def has_provider_key(api_key: str | None = None, provider: ProviderName | None = None) -> bool:
    return bool((api_key or "").strip())


def generate_text(
    prompt: str,
    api_key: str | None = None,
    json_mode: bool = False,
    provider: ProviderName | None = None,
) -> str:
    if active_provider(provider) == "deepseek":
        messages = [{"role": "user", "content": prompt}]
        return _deepseek_chat(messages, api_key=api_key, json_mode=json_mode)
    return _gemini_text(prompt, api_key=api_key)


def generate_chat(contents: list[dict], api_key: str | None = None, provider: ProviderName | None = None) -> str:
    if active_provider(provider) == "deepseek":
        return _deepseek_chat(_contents_to_openai_messages(contents), api_key=api_key)
    return _gemini_contents(contents, api_key=api_key)


def stream_chat(contents: list[dict], api_key: str | None = None, provider: ProviderName | None = None) -> Iterator[str]:
    if active_provider(provider) == "deepseek":
        yield from _deepseek_stream(_contents_to_openai_messages(contents), api_key=api_key)
        return
    yield from _gemini_stream(contents, api_key=api_key)


def test_connection(api_key: str | None = None, provider: ProviderName | None = None) -> tuple[bool, str]:
    try:
        text = generate_text("Sadece 'hazır' yaz.", api_key=api_key, provider=provider)
        return True, f"{provider_label(provider)} bağlantısı başarılı: {text[:80] or 'yanıt alındı'}"
    except AIProviderError as exc:
        return False, exc.message
    except Exception as exc:
        return False, f"{provider_label(provider)} bağlantı hatası: {str(exc)[:220]}"


def _gemini_text(prompt: str, api_key: str | None = None) -> str:
    client = get_client(api_key=api_key)
    if client is None:
        raise AIProviderError(API_KEY_MESSAGE, status_code=503)
    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return (response.text or "").strip()
    except Exception as exc:
        raise _map_provider_exception(exc) from exc


def _gemini_contents(contents: list[dict], api_key: str | None = None) -> str:
    client = get_client(api_key=api_key)
    if client is None:
        raise AIProviderError(API_KEY_MESSAGE, status_code=503)
    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=contents)
        return (response.text or "").strip()
    except Exception as exc:
        raise _map_provider_exception(exc) from exc


def _gemini_stream(contents: list[dict], api_key: str | None = None) -> Iterator[str]:
    client = get_client(api_key=api_key)
    if client is None:
        raise AIProviderError(API_KEY_MESSAGE, status_code=503)
    try:
        stream = client.models.generate_content_stream(model=GEMINI_MODEL, contents=contents)
        for chunk in stream:
            text = chunk.text or ""
            if text:
                yield text
    except Exception as exc:
        raise _map_provider_exception(exc) from exc


def _deepseek_chat(
    messages: list[dict[str, str]],
    api_key: str | None = None,
    json_mode: bool = False,
) -> str:
    key = (api_key or "").strip()
    if not key:
        raise AIProviderError(API_KEY_MESSAGE, status_code=503)

    payload: dict = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=_deepseek_headers(key),
            json=payload,
            timeout=60,
        )
    except requests.RequestException as exc:
        raise AIProviderError(f"DeepSeek bağlantı hatası: {str(exc)[:220]}", status_code=502) from exc
    _raise_for_deepseek_status(response)
    data = response.json()
    return str(data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()


def _deepseek_stream(messages: list[dict[str, str]], api_key: str | None = None) -> Iterator[str]:
    key = (api_key or "").strip()
    if not key:
        raise AIProviderError(API_KEY_MESSAGE, status_code=503)

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=_deepseek_headers(key),
            json={
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "stream": True,
            },
            timeout=60,
            stream=True,
        )
    except requests.RequestException as exc:
        raise AIProviderError(f"DeepSeek bağlantı hatası: {str(exc)[:220]}", status_code=502) from exc
    _raise_for_deepseek_status(response)

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue
        data = raw_line[6:].strip()
        if data == "[DONE]":
            break
        try:
            payload = json.loads(data)
            text = payload.get("choices", [{}])[0].get("delta", {}).get("content") or ""
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.debug("Malformed DeepSeek stream chunk: %s", data[:200])
            continue
        if text:
            yield str(text)


def _deepseek_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _raise_for_deepseek_status(response: requests.Response) -> None:
    if response.status_code == 429:
        raise AIProviderError(API_LIMIT_MESSAGE, status_code=429)
    if response.status_code in {401, 403}:
        raise AIProviderError(API_KEY_MESSAGE, status_code=503)
    if not response.ok:
        raise AIProviderError(f"DeepSeek bağlantı hatası: HTTP {response.status_code}", status_code=502)


def _contents_to_openai_messages(contents: list[dict]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for item in contents:
        role = "assistant" if item.get("role") == "model" else "user"
        text_parts: list[str] = []
        for part in item.get("parts", []):
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
        content = "\n".join(part for part in text_parts if part).strip()
        if content:
            messages.append({"role": role, "content": content})
    return messages


def _map_provider_exception(exc: Exception) -> AIProviderError:
    message = str(exc)
    lower = message.lower()
    if "429" in message or "resource_exhausted" in lower or "quota" in lower:
        return AIProviderError(API_LIMIT_MESSAGE, status_code=429)
    if "api_key_invalid" in lower or "permission_denied" in lower or "invalid api key" in lower:
        return AIProviderError(API_KEY_MESSAGE, status_code=503)
    return AIProviderError(f"AI bağlantı hatası: {message[:220]}", status_code=502)
