from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

SERVICE_NAME = "kap-okuryazar-backend"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DISCLAIMER = "Bu çıktı yatırım tavsiyesi değildir."

_DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",")
    if origin.strip()
]
