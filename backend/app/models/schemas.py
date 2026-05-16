from __future__ import annotations

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=120)
    days: int = Field(default=365, ge=1, le=365)
    summaryCount: int = Field(default=4, ge=1, le=10)
    mode: str = Field(default="simple")
    useDemo: bool = Field(default=False)


class FinancialTableRow(BaseModel):
    label: str
    values: list[str]


class Notification(BaseModel):
    date: str
    title: str
    plainText: str
    url: str | None = None
    category: str | None = None
    reportText: str | None = None
    reportTextSource: str | None = None
    reportTextError: str | None = None
    financialTable: list[FinancialTableRow] | None = None


class AnomalyFlag(BaseModel):
    icon: str
    title: str
    description: str


class FinancialNumber(BaseModel):
    label: str
    value: str


class ExplainResponse(BaseModel):
    company: str
    summary: str
    summaryHtml: str | None = None
    notifications: list[Notification]
    anomalies: list[AnomalyFlag]
    financialNumbers: list[FinancialNumber]
    source: str
    disclaimer: str
    responseTimeMs: int | None = None
    disclosureCount: int | None = None


class HealthResponse(BaseModel):
    ok: bool
    service: str


class StatusItem(BaseModel):
    status: str
    label: str


class StatusResponse(BaseModel):
    kap: StatusItem
    gemini: StatusItem
    lastCheck: str


class GeminiTestResponse(BaseModel):
    ok: bool
    message: str


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str = Field(default="Aoede")


class TTSResponse(BaseModel):
    audio_b64: str
    format: str = "wav"


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=120)
    context: str = Field(default="", max_length=24000)
    history: list[ChatMessage] = Field(default_factory=list)
    message: str = Field(..., min_length=1, max_length=1000)
    file_b64: str | None = Field(default=None, max_length=10_000_000)
    file_mime: str | None = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    reply: str
