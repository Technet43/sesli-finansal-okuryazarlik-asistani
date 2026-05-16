from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from threading import Lock

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.core.bootstrap import ensure_repo_root_on_path

ensure_repo_root_on_path()

from app.core.config import ALLOWED_ORIGINS, DISCLAIMER, SERVICE_NAME  # noqa: E402
from kap_okuryazar.config import DEFAULT_MODEL  # noqa: E402
from app.models.schemas import (  # noqa: E402
    AnomalyFlag,
    ChatRequest,
    ChatResponse,
    ExplainRequest,
    ExplainResponse,
    FinancialNumber,
    GeminiTestResponse,
    HealthResponse,
    Notification,
    StatusItem,
    StatusResponse,
    TTSRequest,
    TTSResponse,
)
from app.services.gemini_service import get_client, test_connection  # noqa: E402
from app.services.kap_service import (  # noqa: E402
    demo_company,
    demo_disclosures,
    fetch_disclosures,
    invalidate_company_cache,
    ping_kap,
    resolve_company,
)
from app.services.summarizer_service import explain_disclosures  # noqa: E402
from kap_okuryazar.text_utils import (  # noqa: E402
    apply_glossary,
    detect_anomalies,
    extract_financial_numbers,
)

logger = logging.getLogger(__name__)
app = FastAPI(title="KAP Okuryazar API", version="0.1.0")

# ── Simple in-memory rate limiter (no extra deps) ──────────────────────────
_rl_lock = Lock()
_rl_buckets: dict[str, list[float]] = defaultdict(list)
_RL_LIMIT = 10       # max requests
_RL_WINDOW = 60.0    # per N seconds


def _rate_limit(request: Request, limit: int = _RL_LIMIT, window: float = _RL_WINDOW) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _rl_lock:
        bucket = _rl_buckets[ip]
        _rl_buckets[ip] = [t for t in bucket if now - t < window]
        if len(_rl_buckets[ip]) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Çok fazla istek. {window:.0f} saniye içinde en fazla {limit} analiz yapabilirsin.",
            )
        _rl_buckets[ip].append(now)


@app.on_event("startup")
def on_startup() -> None:
    import sys
    logger.info("KAP Okuryazar starting — Python %s, model=%s", sys.version.split()[0], DEFAULT_MODEL)

app.add_middleware(GZipMiddleware, minimum_size=512)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, service=SERVICE_NAME)


@app.get("/api/version")
def version() -> dict:
    import subprocess
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        git_hash = "unknown"
    return {"version": "0.1.0", "git": git_hash, "model": DEFAULT_MODEL}


@app.get("/api/status", response_model=StatusResponse)
def status(
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> StatusResponse:
    kap_ok = ping_kap()
    gemini_connected = get_client(api_key=x_gemini_api_key) is not None
    return StatusResponse(
        kap=StatusItem(
            status="live" if kap_ok else "offline",
            label="Canlı veri kaynağı" if kap_ok else "KAP'a ulaşılamıyor",
        ),
        gemini=StatusItem(
            status="connected" if gemini_connected else "fallback",
            label="Bağlı" if gemini_connected else "Fallback modda",
        ),
        lastCheck="Az önce",
    )


@app.post("/api/test-gemini", response_model=GeminiTestResponse)
def test_gemini(
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> GeminiTestResponse:
    ok, message = test_connection(api_key=x_gemini_api_key)
    return GeminiTestResponse(ok=ok, message=message)


@app.post("/api/cache/clear")
def clear_cache() -> dict:
    invalidate_company_cache()
    logger.info("Company cache cleared via API")
    return {"ok": True, "message": "Şirket listesi önbelleği temizlendi."}


@app.post("/api/tts", response_model=TTSResponse)
def tts(
    request: TTSRequest,
    http_request: Request,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> TTSResponse:
    _rate_limit(http_request, limit=20, window=60.0)
    import base64
    from app.services.tts_service import generate_speech

    wav = generate_speech(request.text, api_key=x_gemini_api_key, voice=request.voice)
    if wav is None:
        raise HTTPException(status_code=503, detail="Gemini TTS kullanılamıyor. API key kontrol et veya servisi dene.")
    return TTSResponse(audio_b64=base64.b64encode(wav).decode(), format="wav")


@app.post("/api/explain", response_model=ExplainResponse)
def explain(
    request: ExplainRequest,
    http_request: Request,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> ExplainResponse:
    _rate_limit(http_request)
    req_id = str(uuid.uuid4())[:8]
    t0 = time.monotonic()
    logger.info("[%s] explain(%s) started", req_id, request.company)
    try:
        t_gemini = t0
        if request.useDemo:
            company = demo_company()
            disclosures = demo_disclosures(request.summaryCount)
            source = "demo"
        else:
            t_kap = time.monotonic()
            company = resolve_company(request.company)
            if company is None:
                raise HTTPException(
                    status_code=404,
                    detail="Şirket KAP listesinde güvenli şekilde eşleşmedi. Hisse kodu veya tam şirket adıyla tekrar dene.",
                )
            disclosures = fetch_disclosures(company.oid, request.days, request.summaryCount)
            logger.info("[%s] KAP fetch: %.2fs (%d disclosures)", req_id, time.monotonic() - t_kap, len(disclosures))
            source = "kap"

        t_gemini = time.monotonic()
        result = explain_disclosures(
            company, disclosures, request.mode, api_key=x_gemini_api_key
        )
        logger.info("[%s] Gemini summarize: %.2fs", req_id, time.monotonic() - t_gemini)
        anomalies_raw = detect_anomalies(disclosures)
        anomalies = [
            AnomalyFlag(icon=icon, title=title, description=description)
            for icon, title, description in anomalies_raw
        ]
        financial_numbers_dict: dict[str, str] = {}
        for disclosure in disclosures:
            text = disclosure.get("page_text") or disclosure.get("summary") or ""
            numbers = extract_financial_numbers(text)
            for label, value in numbers:
                if label not in financial_numbers_dict:
                    financial_numbers_dict[label] = value
        financial_numbers = [
            FinancialNumber(label=label, value=value)
            for label, value in financial_numbers_dict.items()
        ]
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        response = ExplainResponse(
            company=company.name,
            summary=result["summary"],
            summaryHtml=apply_glossary(result["summary"]),
            notifications=[Notification(**item) for item in result["notifications"]],
            anomalies=anomalies,
            financialNumbers=financial_numbers,
            source=source,
            disclaimer=DISCLAIMER,
            responseTimeMs=elapsed_ms,
            disclosureCount=len(disclosures),
        )
        logger.info("[%s] explain(%s) completed in %.2fs", req_id, request.company, time.monotonic() - t0)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[%s] explain(%s) failed after %.2fs", req_id, request.company, time.monotonic() - t0)
        raise HTTPException(status_code=502, detail=f"Analiz hazırlanamadı: {str(exc)[:220]}") from exc


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> ChatResponse:
    _rate_limit(http_request, limit=30, window=60.0)
    from app.services.safety_service import clean_advice_language

    client = get_client(api_key=x_gemini_api_key)
    if client is None:
        raise HTTPException(status_code=503, detail="Sohbet için Gemini API key gerekli. Sidebar'a yapıştır.")

    system_prompt = f"""Sen KAP Okuryazar finansal okuryazarlık asistanısın.
Türk yatırımcılara KAP (Kamuyu Aydınlatma Platformu) bildirimlerini sade, dürüst Türkçe ile açıklıyorsun.

Kurallar:
- SADECE aşağıdaki bildirim özetine dayanarak cevap ver.
- Bilgi yoksa "Bu bildirimlerde bu konuda bilgi bulamadım." de.
- Yatırım tavsiyesi verme; "al", "sat", "kesin yükselir/düşer" deme.
- Kısa ve net cevaplar ver (max 4-5 cümle).
- Türkçe cevap ver.

Şirket: {request.company}
Bildirim özeti:
{request.context[:8000] if request.context else "(Bildirim özeti sağlanmadı.)"}"""

    contents: list[dict] = [
        {"role": "user", "parts": [{"text": system_prompt}]},
        {"role": "model", "parts": [{"text": "Anladım. Sorularınızı bekliyorum."}]},
    ]
    for msg in request.history[-12:]:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    contents.append({"role": "user", "parts": [{"text": request.message}]})

    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=contents)
        reply = clean_advice_language((response.text or "").strip())
        if not reply:
            reply = "Bir yanıt oluşturulamadı. Lütfen tekrar dene."
        return ChatResponse(reply=reply)
    except Exception as exc:
        logger.exception("Chat error for %s", request.company)
        raise HTTPException(status_code=502, detail=f"Sohbet hatası: {str(exc)[:200]}") from exc
