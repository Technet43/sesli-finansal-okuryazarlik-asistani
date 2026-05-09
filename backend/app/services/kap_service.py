from __future__ import annotations

import re
from datetime import date, timedelta
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from rapidfuzz import fuzz, process

from kap_okuryazar.config import (
    DISCLOSURE_TYPES,
    KAP_DISCLOSURE_URL,
    KAP_HEADERS,
    KAP_SEARCH_PAGE,
    POPULAR_COMPANY_ALIASES,
)
from kap_okuryazar.demo_data import DEMO_COMPANY, DEMO_DISCLOSURES
from kap_okuryazar.models import CompanyMatch
from kap_okuryazar.text_utils import normalize_tr


def demo_company() -> CompanyMatch:
    name, ticker, oid = DEMO_COMPANY
    return CompanyMatch(name=name, ticker=ticker, oid=oid, score=100.0)


def demo_disclosures(limit: int) -> list[dict]:
    return list(DEMO_DISCLOSURES)[:limit]


def fetch_companies() -> list[dict]:
    response = requests.get(KAP_SEARCH_PAGE, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
    response.raise_for_status()

    companies: dict[str, dict] = {}
    for chunk in response.text.split("},{"):
        if "mkkMemberOid" not in chunk or "stockCode" not in chunk:
            continue
        oid_match = re.search(r'mkkMemberOid\\":\\"(?P<value>[0-9a-f]+)\\"', chunk)
        title_match = re.search(r'kapMemberTitle\\":\\"(?P<value>.*?)\\"', chunk)
        stock_match = re.search(r'stockCode\\":\\"(?P<value>.*?)\\"', chunk)
        if not oid_match or not title_match or not stock_match:
            continue

        title = title_match.group("value").strip()
        stock_codes = stock_match.group("value").strip()
        oid = oid_match.group("value").strip()
        if not title or not stock_codes or stock_codes == "null":
            continue

        key = normalize_tr(f"{title} {stock_codes}")
        companies[key] = {"name": title, "ticker": stock_codes, "oid": oid, "search": key}

    return list(companies.values())


def resolve_company(query: str) -> CompanyMatch | None:
    query_norm = normalize_tr(query)
    if not query_norm:
        return None

    for alias, (name, tickers, oid) in POPULAR_COMPANY_ALIASES.items():
        if alias in query_norm or query_norm in alias:
            return CompanyMatch(name, tickers, oid, 100.0)

    companies = fetch_companies()
    ticker_query = query.strip().upper()
    exact_ticker = next(
        (
            company
            for company in companies
            if ticker_query in [code.strip().upper() for code in company["ticker"].split(",")]
        ),
        None,
    )
    if exact_ticker:
        return CompanyMatch(
            exact_ticker["name"], exact_ticker["ticker"], exact_ticker["oid"], 100.0
        )

    query_tokens = set(query_norm.split())
    choices = {company["search"]: company for company in companies}
    scorer = fuzz.token_set_ratio if len(query_tokens) <= 2 else fuzz.WRatio
    result = process.extractOne(query_norm, choices.keys(), scorer=scorer, score_cutoff=72)
    if not result:
        return None

    matched_key, score, _ = result
    matched_tokens = set(matched_key.split())
    if query_tokens and not (query_tokens & matched_tokens):
        return None
    if len(query_norm) >= 5 and query_norm not in matched_key and score < 86:
        return None

    company = choices[matched_key]
    return CompanyMatch(company["name"], company["ticker"], company["oid"], float(score))


def post_kap_disclosure_search(days: int, member_oid: str) -> list[dict]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    payload = {
        "fromDate": start_date.isoformat(),
        "toDate": end_date.isoformat(),
        "mkkMemberOidList": [member_oid],
        "inactiveMkkMemberOidList": [],
        "disclosureClass": "",
        "subjectList": [],
        "disclosureIndexList": [],
    }
    response = requests.post(KAP_DISCLOSURE_URL, json=payload, headers=KAP_HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def fetch_disclosures(member_oid: str, days: int, limit: int) -> list[dict]:
    rows = post_kap_disclosure_search(days=days, member_oid=member_oid)
    disclosures = []

    for row in rows[:limit]:
        index = row.get("disclosureIndex")
        url = f"https://www.kap.org.tr/tr/Bildirim/{index}"
        subject = row.get("subject") or ""
        page_text = fetch_disclosure_page_text(url)
        disclosures.append(
            {
                "index": index,
                "publish_datetime": row.get("publishDate") or "",
                "company_name": row.get("kapTitle") or row.get("memberTitle") or "",
                "stock_codes": row.get("stockCodes") or "",
                "subject": subject,
                "category": classify_disclosure(subject, row.get("summary") or "", page_text),
                "summary": row.get("summary") or "",
                "type": row.get("disclosureType") or "",
                "has_attachment": bool(row.get("attachmentCount")),
                "is_late": bool(row.get("isLate")),
                "is_corrective": bool(row.get("modifyStatus")),
                "url": url,
                "page_text": page_text,
            }
        )

    return disclosures


def classify_disclosure(subject: str, summary: str, page_text: str) -> str:
    haystack = normalize_tr(f"{subject} {summary} {page_text[:800]}")
    for label, keywords in DISCLOSURE_TYPES:
        if any(normalize_tr(keyword) in haystack for keyword in keywords):
            return label
    return "Diğer"


def fetch_disclosure_page_text(url: str) -> str:
    index = url.rstrip("/").split("/")[-1]
    pdf_text = fetch_disclosure_pdf_text(index)
    if pdf_text:
        return pdf_text

    try:
        response = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:3000]


def fetch_disclosure_pdf_text(index: str) -> str:
    if not index or not index.isdigit():
        return ""
    url = f"https://www.kap.org.tr/tr/api/BildirimPdf/{index}"
    try:
        response = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        if len(response.content) > 1_500_000:
            return ""
        reader = PdfReader(BytesIO(response.content))
        text = " ".join(page.extract_text() or "" for page in reader.pages[:2])
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]
    except Exception:
        return ""
