from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import ensure_repo_root_on_path

ensure_repo_root_on_path()

from app.core.config import ALLOWED_ORIGINS, DISCLAIMER, SERVICE_NAME  # noqa: E402
from app.models.schemas import (  # noqa: E402
    ExplainRequest,
    ExplainResponse,
    GeminiTestResponse,
    HealthResponse,
    Notification,
    StatusItem,
    StatusResponse,
)
from app.services.gemini_service import get_client, test_connection  # noqa: E402
from app.services.kap_service import (  # noqa: E402
    demo_company,
    demo_disclosures,
    fetch_disclosures,
    resolve_company,
)
from app.services.summarizer_service import explain_disclosures  # noqa: E402

app = FastAPI(title="KAP Okuryazar API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, service=SERVICE_NAME)


@app.get("/api/status", response_model=StatusResponse)
def status() -> StatusResponse:
    gemini_connected = get_client() is not None
    return StatusResponse(
        kap=StatusItem(status="live", label="Canlı veri kaynağı"),
        gemini=StatusItem(
            status="connected" if gemini_connected else "fallback",
            label="Bağlı" if gemini_connected else "Fallback modda",
        ),
        lastCheck="Az önce",
    )


@app.post("/api/test-gemini", response_model=GeminiTestResponse)
def test_gemini() -> GeminiTestResponse:
    ok, message = test_connection()
    return GeminiTestResponse(ok=ok, message=message)


@app.post("/api/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest) -> ExplainResponse:
    try:
        if request.useDemo:
            company = demo_company()
            disclosures = demo_disclosures(request.summaryCount)
            source = "demo"
        else:
            company = resolve_company(request.company)
            if company is None:
                raise HTTPException(
                    status_code=404,
                    detail="Şirket KAP listesinde güvenli şekilde eşleşmedi. Hisse kodu veya tam şirket adıyla tekrar dene.",
                )
            disclosures = fetch_disclosures(company.oid, request.days, request.summaryCount)
            source = "kap"

        result = explain_disclosures(company, disclosures, request.mode)
        return ExplainResponse(
            company=company.name,
            summary=result["summary"],
            notifications=[Notification(**item) for item in result["notifications"]],
            source=source,
            disclaimer=DISCLAIMER,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Analiz hazırlanamadı: {str(exc)[:220]}") from exc
