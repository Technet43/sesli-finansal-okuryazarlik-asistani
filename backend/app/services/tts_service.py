from __future__ import annotations

import base64
import logging
import struct
import wave
from io import BytesIO

logger = logging.getLogger(__name__)

TTS_MODEL = "gemini-2.5-flash-preview-tts"
_DEFAULT_VOICE = "Aoede"
_SAMPLE_RATE = 24_000
_CHANNELS = 1
_SAMPLE_WIDTH = 2  # 16-bit


def _pcm_to_wav(pcm: bytes) -> bytes:
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


def generate_speech(text: str, api_key: str | None = None, voice: str = _DEFAULT_VOICE) -> bytes | None:
    """Return WAV bytes, or None if Gemini is unavailable."""
    from app.services.gemini_service import get_client

    client = get_client(api_key=api_key)
    if client is None:
        return None

    try:
        from google.genai import types  # type: ignore

        response = client.models.generate_content(
            model=TTS_MODEL,
            contents=text[:3500],
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                ),
            ),
        )
        parts = response.candidates[0].content.parts if response.candidates else []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                raw = inline.data if isinstance(inline.data, bytes) else base64.b64decode(inline.data)
                mime = getattr(inline, "mime_type", "")
                if "wav" in mime:
                    return raw
                return _pcm_to_wav(raw)
        logger.warning("TTS: no audio part in response")
        return None
    except Exception as exc:
        logger.exception("TTS generation failed: %s", exc)
        return None
