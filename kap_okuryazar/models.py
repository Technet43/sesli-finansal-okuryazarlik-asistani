from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyMatch:
    name: str
    ticker: str
    oid: str
    score: float

