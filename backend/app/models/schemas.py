from __future__ import annotations

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=120)
    days: int = Field(default=365, ge=1, le=365)
    summaryCount: int = Field(default=4, ge=1, le=10)
    mode: str = Field(default="simple")
    useDemo: bool = Field(default=False)


class Notification(BaseModel):
    date: str
    title: str
    plainText: str
    url: str | None = None
    category: str | None = None


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
