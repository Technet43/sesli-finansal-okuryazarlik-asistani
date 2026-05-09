from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

SERVICE_NAME = "kap-okuryazar-backend"
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DISCLAIMER = "Bu çıktı yatırım tavsiyesi değildir."
