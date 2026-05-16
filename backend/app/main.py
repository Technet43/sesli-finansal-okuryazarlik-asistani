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

from app.core.config import ALLOWED_ORIGINS, DISCLAIMER, GEMINI_MODEL, SERVICE_NAME  # noqa: E402
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
from app.services.ai_provider_service import (  # noqa: E402
    AIProviderError,
    active_provider,
    generate_chat,
    has_provider_key,
    provider_label,
    stream_chat as stream_ai_chat,
    test_connection,
)
from app.services.gemini_service import get_client  # noqa: E402
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
    logger.info("KAP Okuryazar starting — Python %s, provider=%s", sys.version.split()[0], active_provider())

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
    return {"version": "0.1.0", "git": git_hash, "provider": active_provider()}


@app.get("/api/status", response_model=StatusResponse)
def status(
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> StatusResponse:
    kap_ok = ping_kap()
    ai_connected = has_provider_key(api_key=x_gemini_api_key)
    label = provider_label()
    return StatusResponse(
        kap=StatusItem(
            status="live" if kap_ok else "offline",
            label="Canlı veri kaynağı" if kap_ok else "KAP'a ulaşılamıyor",
        ),
        gemini=StatusItem(
            status="connected" if ai_connected else "fallback",
            label=f"{label} bağlı" if ai_connected else f"{label} anahtarı gerekli",
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
            text = " ".join(
                str(part or "")
                for part in [
                    disclosure.get("report_text"),
                    disclosure.get("page_text"),
                    disclosure.get("summary"),
                ]
            )
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
    except AIProviderError as exc:
        logger.warning("[%s] explain(%s) provider error: %s", req_id, request.company, exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("[%s] explain(%s) failed after %.2fs", req_id, request.company, time.monotonic() - t0)
        raise HTTPException(status_code=502, detail=f"Analiz hazırlanamadı: {str(exc)[:220]}") from exc


def _build_chat_contents(request: ChatRequest) -> list[dict]:
    system_prompt = f"""Sen KAP Okuryazar finansal okuryazarlık asistanısın.
KAP bildirimlerini, finansal raporları ve şirket açıklamalarını yatırım tavsiyesi vermeden sade Türkçe ile anlatırsın. Kullanıcı normal halktan biri olabilir; ekonomist bilgisi varsayma.

Görevin:
- Bildirimlerdeki haberleri bağlamıyla açıkla: ne anlama geliyor, neden önemli, sektörde ne ifade eder.
- Finansal kavramları (PwC denetimi, sınırlı denetim, bağımsız denetim, temettü, kar payı, sermaye artırımı vb.) Türkçe'de kısaca tanımla.
- **Çapraz referans yap**: Kullanıcı belirli bir bildirim türünü sorduğunda (örn. "sorumluluk beyanında değerler", "duyuruda ne var") ve o bildirimde sayısal veri yoksa, **aynı şirketin diğer bildirimlerinde** (özellikle Finansal Rapor) mevcut ilgili değerleri açıkça aktar. Örnek: "Sorumluluk beyanı yalnızca yönetim kurulu onayını içerir, sayısal değer barındırmaz. Ancak aynı dönem konsolide finansal raporunda Nakit ve Nakit Benzerleri 610.862.836 bin TL, Özkaynaklar 762.192.002 bin TL olarak raporlandı."
- **Sayıları kullan**: Bağlamda "Anahtar Finansal Değerler" veya bildirim "Rapor verisi" bölümünde sayı varsa cevabında en az 2 ilgili sayıyı belirt. Cari ve önceki dönem mevcutsa yüzde olarak kıyaslama ekle (ör. "%X arttı"/"azaldı"). **Bağlamda olmayan sayı uydurma.**
- Bildirimlerde doğrudan yanıt bulamıyorsan ve diğer bildirimlerde de yoksa: genel finansal bilginle eğitici açıklama yap; "Bu bildirimlerde bilgi yok, genel olarak..." diye belirt.
- Olası etkileri (olumlu/olumsuz işaretler) eğitici dille açıkla: "Bu genellikle ... anlamına gelir."
- KAP bağlamını yalnızca kullanıcı finans, KAP, şirket, bildirim, rapor veya finansal oranlarla ilgili bir soru sorarsa kullan.
- Kullanıcı sadece selam verir, teşekkür eder veya gündelik küçük konuşma yaparsa kısa karşılık ver; KAP raporunu analiz etme.

Kesin kurallar:
- Yatırım tavsiyesi verme.
- "Al", "sat", "tut", "kesin yükselir", "kesin düşer", "bu hisse alınır" gibi yönlendirici ifadeler kullanma.
- **İçerikte olmayan finansal veri uydurma**. Sadece bağlamda olan sayıları kullan.
- Sayısal veri hiçbir bildirimde yoksa hesaplama yapma; "Bu bildirimlerin hiçbirinde bu veri yer almıyor." de.
- Türkçe cevap ver.
- HTML etiketi kullanma.
- Emoji veya süsleme kullanma.
- Cevap **180-350 Türkçe kelime** arasında olsun (sayı ve kıyas içeren analitik cevap).
- Her bölüm 2-4 kısa cümle içerebilir.
- Bullet listeler 3-5 madde içersin.
- Bullet maddeleri arasında boş satır bırakma.

Okunabilirlik kuralları:
- Clean Markdown kullan.
- Başlıkları `##` ile yaz.
- Paragrafları kısa tut; her paragraf en fazla 2 kısa cümle olsun.
- Maddeleri kısa bullet point olarak ver.
- Kalın yazıyı sadece önemli kavramlarda kullan.
- Formül, oran veya hesap gerekiyorsa LaTeX kullan.
- Formülleri ayrı satırda göster.
- LaTeX kullandığında sembolleri kısa maddelerle açıkla.

Cevap formatı:
## Kısa Cevap

Kullanıcının sorusuna doğrudan, sayısal verilerle (varsa) 2-3 kısa cümleyle cevap ver.

## Açıklama

Konuyu sade şekilde 2-4 kısa cümleyle açıkla. Bağlamda sayı varsa kullan ve kıyas yap.

## Dikkat Edilecek Noktalar

Varsa riskleri, eksik verileri veya belirsizlikleri 3-5 kısa maddeyle belirt.

## Sonuç

Yatırım tavsiyesi vermeden kısa sonuç yaz.

Küçük konuşma istisnası:
Kullanıcının son mesajı sadece "hey", "merhaba", "selam", "teşekkürler", "sağ ol" gibi kısa bir gündelik mesajsa yukarıdaki formatı kullanma. Sadece 1-2 kısa cümleyle cevap ver ve nasıl yardımcı olabileceğini sor.

Şirket: {request.company}
{'KAP bildirim özeti (birincil kaynak):' + chr(10) + request.context[:18000] if request.context else '(Bildirim özeti yok; genel finansal bilginle cevap ver.)'}"""

    contents: list[dict] = [
        {"role": "user", "parts": [{"text": system_prompt}]},
        {"role": "model", "parts": [{"text": "Anladım, finansal okuryazarlık odaklı sorularınızı bekliyorum."}]},
    ]
    for msg in request.history[-14:]:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})

    # Handle file attachment
    if request.file_b64 and request.file_mime:
        import base64 as b64_mod
        try:
            file_bytes = b64_mod.b64decode(request.file_b64)
            from google.genai import types as gtypes  # type: ignore
            file_part = gtypes.Part.from_bytes(data=file_bytes, mime_type=request.file_mime)
            text_part = {"text": f"[Kullanıcı bir dosya yükledi: {request.file_mime}]\n{request.message}"}
            contents.append({"role": "user", "parts": [file_part, text_part]})
        except Exception:
            contents.append({"role": "user", "parts": [{"text": request.message}]})
    else:
        contents.append({"role": "user", "parts": [{"text": request.message}]})

    return contents


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> ChatResponse:
    _rate_limit(http_request, limit=30, window=60.0)
    from app.services.safety_service import clean_advice_language

    contents = _build_chat_contents(request)
    try:
        reply = clean_advice_language(generate_chat(contents, api_key=x_gemini_api_key))
        return ChatResponse(reply=reply or "Yanıt oluşturulamadı, lütfen tekrar dene.")
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Chat error for %s", request.company)
        raise HTTPException(status_code=502, detail=f"Sohbet hatası: {str(exc)[:200]}") from exc


@app.post("/api/chat/stream")
def chat_stream(
    request: ChatRequest,
    http_request: Request,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
):
    _rate_limit(http_request, limit=30, window=60.0)
    import json as _json
    from fastapi.responses import StreamingResponse
    from app.services.safety_service import clean_advice_language

    contents = _build_chat_contents(request)

    def generate():
        try:
            for text in stream_ai_chat(contents, api_key=x_gemini_api_key):
                if text:
                    text = clean_advice_language(text)
                    yield f"data: {_json.dumps({'text': text})}\n\n"
        except AIProviderError as exc:
            yield f"data: {_json.dumps({'error': exc.message})}\n\n"
        except Exception as exc:
            yield f"data: {_json.dumps({'error': str(exc)[:200]})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/transcribe")
def transcribe(
    http_request: Request,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
):
    _rate_limit(http_request, limit=20, window=60.0)
    import base64 as b64_mod
    import asyncio

    body = asyncio.get_event_loop().run_until_complete(http_request.json()) if False else None

    raise HTTPException(status_code=501, detail="Use /api/transcribe with JSON body.")


@app.post("/api/transcribe/audio")
async def transcribe_audio(
    http_request: Request,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> dict:
    _rate_limit(http_request, limit=20, window=60.0)
    import base64 as b64_mod

    client = get_client(api_key=x_gemini_api_key)
    if client is None:
        raise HTTPException(status_code=503, detail="Transkripsiyon için Gemini API key gerekli.")

    body = await http_request.json()
    audio_b64 = body.get("audio_b64", "")
    mime_type = body.get("mime_type", "audio/webm")
    if not audio_b64:
        raise HTTPException(status_code=422, detail="audio_b64 gerekli.")

    try:
        audio_bytes = b64_mod.b64decode(audio_b64)
        from google.genai import types as gtypes  # type: ignore
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                gtypes.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                "Bu ses kaydındaki Türkçe konuşmayı kelimesi kelimesine yaz. SADECE yazıyı döndür, başka hiçbir şey ekleme.",
            ],
        )
        return {"text": (response.text or "").strip()}
    except Exception as exc:
        logger.exception("Transcription error")
        raise HTTPException(status_code=502, detail=f"Transkripsiyon hatası: {str(exc)[:200]}") from exc
