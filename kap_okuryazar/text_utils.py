from __future__ import annotations

import re
import unicodedata
from html import escape

from kap_okuryazar.config import ANOMALY_RULES, FINANCIAL_NUMBER_PATTERNS, GLOSSARY


def normalize_tr(text: str) -> str:
    text = text.strip().lower()
    replacements = str.maketrans("çğıöşüİı", "cgiosuii")
    text = text.translate(replacements)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_financial_numbers(text: str) -> list[tuple[str, str]]:
    if not text:
        return []
    findings: list[tuple[str, str]] = []
    seen_labels: set[str] = set()
    for label, pattern in FINANCIAL_NUMBER_PATTERNS:
        match = pattern.search(text)
        if not match or label in seen_labels:
            continue
        amount = (match.group("amount") or "").strip()
        if not amount:
            continue
        scale = (match.group("scale") or "").strip()
        value = " ".join(part for part in [amount, scale, "TL"] if part)
        findings.append((label, value))
        seen_labels.add(label)
    return findings


def detect_anomalies(disclosures: list[dict]) -> list[tuple[str, str]]:
    if not disclosures:
        return []
    flags: list[tuple[str, str]] = []

    if any(d.get("is_late") for d in disclosures):
        late_count = sum(1 for d in disclosures if d.get("is_late"))
        flags.append(
            (
                "⏰ Geç bildirim",
                f"{late_count} bildirim geç gönderilmiş. " + ANOMALY_RULES["geç_bildirim"],
            )
        )

    correctives = sum(1 for d in disclosures if d.get("is_corrective"))
    if correctives >= 2:
        flags.append(
            (
                "✏️ Çoklu düzeltme",
                f"{correctives} düzeltme bildirimi. " + ANOMALY_RULES["düzeltme"],
            )
        )

    sermaye = sum(1 for d in disclosures if d.get("category") == "Sermaye İşlemi")
    if sermaye >= 2:
        flags.append(("📊 Yoğun sermaye işlemi", ANOMALY_RULES["yoğun_sermaye"]))

    borc = sum(1 for d in disclosures if d.get("category") == "Borçlanma")
    if borc >= 2:
        flags.append(("💸 Yoğun borçlanma", ANOMALY_RULES["yoğun_borçlanma"]))

    important_no_attach = [
        d
        for d in disclosures
        if d.get("category") in {"Finansal Rapor", "Sermaye İşlemi", "Özel Durum"}
        and not d.get("has_attachment")
    ]
    if important_no_attach:
        flags.append(
            (
                "📎 Eksik ek dosya",
                f"{len(important_no_attach)} önemli bildirimde ek dosya yok. "
                + ANOMALY_RULES["ek_eksik"],
            )
        )

    late_night = 0
    for disclosure in disclosures:
        timestamp = disclosure.get("publish_datetime", "")
        match = re.search(r"(\d{2}):(\d{2})", timestamp)
        if match:
            hour = int(match.group(1))
            if hour >= 23 or hour < 6:
                late_night += 1
    if late_night >= 2:
        flags.append(
            (
                "🌙 Geç saat bildirim",
                f"{late_night} bildirim gece 23:00-06:00 arasında gönderilmiş; bu olağandışıdır.",
            )
        )

    return flags


def apply_glossary(text: str) -> str:
    if not text:
        return ""
    out = escape(text)
    for term in sorted(GLOSSARY.keys(), key=len, reverse=True):
        explanation = GLOSSARY[term]
        pattern = re.compile(
            rf"(?<![a-zçğıöşüA-ZÇĞİÖŞÜ])({re.escape(term)})(?![a-zçğıöşüA-ZÇĞİÖŞÜ])",
            re.IGNORECASE,
        )
        out = pattern.sub(
            lambda match: f'<abbr class="gloss" title="{escape(explanation)}">{match.group(1)}</abbr>',
            out,
        )
    return out
