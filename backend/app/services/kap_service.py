from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from io import BytesIO
from urllib.parse import urljoin, urlparse

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

logger = logging.getLogger(__name__)

_COMPANY_CACHE: list[dict] = []
_COMPANY_CACHE_TS: float = 0.0
_COMPANY_CACHE_TTL: float = 3600.0  # 1 hour

_SAFE_ATTACHMENT_EXTENSIONS = {".pdf", ".html", ".htm", ".xhtml", ".xml", ".xbrl"}
_MAX_ATTACHMENTS_PER_DISCLOSURE = 3
_MAX_ATTACHMENT_BYTES = 5_000_000
_MAX_ATTACHMENT_PDF_PAGES = 10
_MAX_REPORT_TEXT_CHARS = 6000

# Normalized (normalize_tr) keywords used to identify financial table rows
_FINANCIAL_ROW_KEYWORDS = frozenset({
    "nakit", "varlik", "borc", "ozkaynak", "kar", "gelir", "gider",
    "akis", "aktif", "pasif", "sermaye", "yukumluluk", "zarar", "donem",
    "toplam", "net", "faiz", "vergi", "satis", "maliyet", "brut",
})

# Priority financial row labels for structured UI extraction (normalize_tr applied at match time)
_PRIORITY_ROW_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Nakit ve Nakit Benzerleri", ("nakit ve nakit benzerleri",)),
    ("Toplam Varlıklar", ("toplam varliklar", "toplam aktif")),
    ("Toplam Yükümlülükler", ("toplam yukumluluk", "toplam pasif")),
    ("Özkaynaklar", ("ozkaynaklar", "toplam ozkaynak", "ana ortakliga ait ozkaynaklar")),
    ("Net Dönem Kârı/Zararı", ("net donem kar", "donem net kar", "net donem zarar")),
    ("Faiz Gelirleri", ("faiz gelirleri",)),
    ("Net Faiz Geliri", ("net faiz gelir",)),
    ("Faiz Giderleri", ("faiz giderleri",)),
    ("Satış Gelirleri", ("satis gelirleri", "hasilat")),
    ("Brüt Kâr/Zarar", ("brut kar", "brut zarar")),
    ("Esas Faaliyet Kârı", ("esas faaliyet kari", "esas faaliyet karlari"))
,
    ("Nakit Akışları", ("nakit akis", "isletme faaliyetlerinden nakit"))
,
)


def ping_kap() -> bool:
    try:
        response = requests.head(
            KAP_SEARCH_PAGE, headers={"User-Agent": "Mozilla/5.0"}, timeout=5
        )
        return response.status_code < 500
    except Exception:
        return False


def invalidate_company_cache() -> None:
    global _COMPANY_CACHE, _COMPANY_CACHE_TS
    _COMPANY_CACHE = []
    _COMPANY_CACHE_TS = 0.0
    logger.info("Company cache invalidated")


def demo_company() -> CompanyMatch:
    name, ticker, oid = DEMO_COMPANY
    return CompanyMatch(name=name, ticker=ticker, oid=oid, score=100.0)


def demo_disclosures(limit: int) -> list[dict]:
    return list(DEMO_DISCLOSURES)[:limit]


def _http_get_with_retry(url: str, *, timeout: int, headers: dict, max_retries: int = 2) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def fetch_companies() -> list[dict]:
    global _COMPANY_CACHE, _COMPANY_CACHE_TS
    now = time.monotonic()
    if _COMPANY_CACHE and (now - _COMPANY_CACHE_TS) < _COMPANY_CACHE_TTL:
        logger.debug("Company list served from cache (%d entries)", len(_COMPANY_CACHE))
        return _COMPANY_CACHE

    logger.info("Fetching company list from KAP")
    response = _http_get_with_retry(KAP_SEARCH_PAGE, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)

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

    result = list(companies.values())
    _COMPANY_CACHE = result
    _COMPANY_CACHE_TS = now
    logger.info("Company list cached: %d entries", len(result))
    return result


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
    for attempt in range(3):
        response = requests.post(KAP_DISCLOSURE_URL, json=payload, headers=KAP_HEADERS, timeout=30)
        if response.status_code == 429:
            wait = 1.5 * (attempt + 1)
            logger.warning("KAP disclosure search rate-limited, retrying in %.1fs", wait)
            time.sleep(wait)
            continue
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    logger.error("KAP disclosure search exhausted retries for oid=%s", member_oid)
    return []


def _build_disclosure_entry(row: dict) -> dict:
    index = row.get("disclosureIndex")
    url = f"https://www.kap.org.tr/tr/Bildirim/{index}"
    subject = row.get("subject") or ""
    page_text, financial_table_text, financial_table_rows = fetch_disclosure_page_text(url)
    attachments = discover_attachment_links(row, url)
    report_text, report_text_source, report_text_error = fetch_report_attachment_text(attachments)
    # KAP HTML tables preserve row-label/value structure better than PDF text extraction,
    # so always prepend table text when available (keeps financial figures visible in first chars).
    if financial_table_text:
        if report_text:
            report_text = (
                "KAP HTML tablo verisi:\n"
                + financial_table_text[:3000]
                + "\n\nEk dosya metni:\n"
                + report_text
            )[:_MAX_REPORT_TEXT_CHARS]
            report_text_source = (report_text_source + " + KAP HTML tablosu").strip(" +")
        else:
            report_text = financial_table_text[:_MAX_REPORT_TEXT_CHARS]
            report_text_source = "KAP HTML tablosu"
    if row.get("attachmentCount") and not attachments:
        report_text_error = "KAP ek dosya bağlantısı bulunamadı."
    elif row.get("attachmentCount") and attachments and not report_text and not report_text_error:
        report_text_error = "KAP ek dosya içeriği okunamadı."
    return {
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
        "attachments": attachments,
        "report_text": report_text,
        "report_text_source": report_text_source,
        "report_text_error": report_text_error,
        "financial_table_rows": financial_table_rows,
        "_order": 0,  # filled below
    }


def fetch_disclosures(member_oid: str, days: int, limit: int) -> list[dict]:
    rows = post_kap_disclosure_search(days=days, member_oid=member_oid)
    target_rows = rows[:limit]

    logger.info("Fetching %d disclosures in parallel", len(target_rows))
    futures: dict = {}
    with ThreadPoolExecutor(max_workers=min(len(target_rows) or 1, 6)) as pool:
        for order, row in enumerate(target_rows):
            fut = pool.submit(_build_disclosure_entry, row)
            futures[fut] = order

    ordered: list[tuple[int, dict]] = []
    for fut in as_completed(futures):
        order = futures[fut]
        try:
            entry = fut.result()
            entry["_order"] = order
            ordered.append((order, entry))
        except Exception as exc:
            logger.warning("Failed to fetch disclosure at position %d: %s", order, exc)

    ordered.sort(key=lambda x: x[0])
    disclosures = [entry for _, entry in ordered]
    for d in disclosures:
        d.pop("_order", None)
    return disclosures


def classify_disclosure(subject: str, summary: str, page_text: str) -> str:
    haystack = normalize_tr(f"{subject} {summary} {page_text[:800]}")
    for label, keywords in DISCLOSURE_TYPES:
        if any(normalize_tr(keyword) in haystack for keyword in keywords):
            return label
    return "Diğer"


def _iter_table_rows(soup: BeautifulSoup):
    """Yield (label, values) tuples from every <tr> in every <table>.

    Strips whitespace and drops empty cells; first cell is the label, remaining
    cells are values. Skips rows with fewer than 2 non-empty cells.
    """
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [
                re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip()
                for td in tr.find_all(["td", "th"])
            ]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            yield cells[0], cells[1:]


def _extract_kap_table_text(soup: BeautifulSoup) -> str:
    """Extract financial table rows from KAP HTML as 'Label: V1 | V2' lines."""
    lines: list[str] = []
    seen: set[str] = set()
    for label, values in _iter_table_rows(soup):
        if label in seen or len(label) < 3:
            continue
        label_norm = normalize_tr(label)
        has_kw = any(kw in label_norm for kw in _FINANCIAL_ROW_KEYWORDS)
        has_num = any(re.search(r"\d", v) for v in values)
        if has_kw or has_num:
            seen.add(label)
            lines.append(f"{label}: {' | '.join(values[:4])}")
        if len(lines) >= 80:
            break
    return "\n".join(lines)


_NUMERIC_CELL_RE = re.compile(r"^-?\d[\d.,\s]*$")


def _is_numeric_cell(value: str) -> bool:
    """True for cells like '610.862.836', '1.234,56', '-1.000', ignores XBRL tags & labels."""
    cleaned = value.replace("\xa0", "").strip()
    if not cleaned:
        return False
    return bool(_NUMERIC_CELL_RE.match(cleaned))


def _extract_kap_table_rows(soup: BeautifulSoup) -> list[dict]:
    """Extract priority financial rows as structured [{label, values}] for UI.

    KAP financial tables prefix rows with an XBRL tag and bilingual labels,
    so we search the whole row for a Turkish keyword match and keep only the
    cells that are actually numeric values.
    """
    result: list[dict] = []
    seen: set[str] = set()
    for raw_label, raw_values in _iter_table_rows(soup):
        all_cells = [raw_label] + raw_values
        row_blob = " ".join(normalize_tr(c) for c in all_cells)
        matched: str | None = None
        for display_label, patterns in _PRIORITY_ROW_PATTERNS:
            if display_label in seen:
                continue
            if any(p in row_blob for p in patterns):
                matched = display_label
                break
        if not matched:
            continue
        numeric_values = [c for c in all_cells if _is_numeric_cell(c)]
        if not numeric_values:
            continue
        seen.add(matched)
        result.append({"label": matched, "values": numeric_values[:4]})
        if len(result) >= 12:
            break
    return result


def fetch_disclosure_page_text(url: str) -> tuple[str, str, list[dict]]:
    """Return (page_text, financial_table_text, financial_table_rows).

    Always fetches the HTML page so that financial tables embedded directly
    in the KAP disclosure page are extracted even when the PDF API succeeds.
    """
    index = url.rstrip("/").split("/")[-1]
    financial_table_text = ""
    financial_table_rows: list[dict] = []
    plain_text = ""

    try:
        response = _http_get_with_retry(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        financial_table_text = _extract_kap_table_text(soup)
        financial_table_rows = _extract_kap_table_rows(soup)
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        plain_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
    except requests.RequestException:
        pass

    if not plain_text:
        pdf_text = fetch_disclosure_pdf_text(index)
        return pdf_text[:3000], financial_table_text, financial_table_rows

    page_text = (
        (financial_table_text[:1000] + "\n" + plain_text if financial_table_text else plain_text)[:3000]
    )
    return page_text, financial_table_text, financial_table_rows


def fetch_disclosure_pdf_text(index: str) -> str:
    if not index or not index.isdigit():
        return ""
    url = f"https://www.kap.org.tr/tr/api/BildirimPdf/{index}"
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 429:
            logger.warning("KAP PDF rate-limited for index %s", index)
            return ""
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            return ""
        reader = PdfReader(BytesIO(response.content))
        text = " ".join(page.extract_text() or "" for page in reader.pages[:3])
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]
    except Exception:
        return ""


def discover_attachment_links(row: dict, disclosure_url: str) -> list[dict]:
    seen: set[str] = set()
    attachments: list[dict] = []

    for attachment in _attachment_candidates_from_api_row(row):
        normalized = _normalize_attachment(attachment, disclosure_url)
        if normalized and normalized["url"] not in seen:
            attachments.append(normalized)
            seen.add(normalized["url"])
        if len(attachments) >= _MAX_ATTACHMENTS_PER_DISCLOSURE:
            return attachments

    if attachments:
        return attachments

    for attachment in _attachment_candidates_from_html(disclosure_url):
        normalized = _normalize_attachment(attachment, disclosure_url)
        if normalized and normalized["url"] not in seen:
            attachments.append(normalized)
            seen.add(normalized["url"])
        if len(attachments) >= _MAX_ATTACHMENTS_PER_DISCLOSURE:
            break

    return attachments


def _attachment_candidates_from_api_row(row: dict) -> list[dict]:
    candidates: list[dict] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            text = " ".join(str(value.get(key, "")) for key in value.keys())
            if any(token in text.lower() for token in _SAFE_ATTACHMENT_EXTENSIONS):
                candidates.append(value)
            elif any("attach" in str(key).lower() or "file" in str(key).lower() for key in value.keys()):
                candidates.append(value)
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(row)
    return candidates


def _attachment_candidates_from_html(disclosure_url: str) -> list[dict]:
    try:
        response = _http_get_with_retry(disclosure_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    candidates: list[dict] = []
    for link in soup.find_all("a", href=True):
        href = str(link.get("href") or "")
        label = link.get_text(" ", strip=True)
        haystack = f"{href} {label}".lower()
        if "/api/bildirimpdf/" in href.lower():
            continue
        if "/api/file/download/" not in href.lower() and not any(ext in haystack for ext in _SAFE_ATTACHMENT_EXTENSIONS):
            continue
        candidates.append({"url": href, "name": label})
    return candidates


def _normalize_attachment(raw: dict, base_url: str) -> dict | None:
    url = _first_present(raw, ["url", "downloadUrl", "downloadURL", "fileUrl", "fileURL", "href", "link"])
    name = _first_present(raw, ["name", "fileName", "filename", "title", "label", "text"]) or "KAP eki"

    if not url:
        for value in raw.values():
            if isinstance(value, str) and ("kap.org.tr" in value or value.startswith("/")):
                url = value
                break
    if not url:
        return None

    absolute = urljoin(base_url, str(url))
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or parsed.netloc.lower() != "www.kap.org.tr":
        return None

    ext = _safe_extension(str(name), absolute)
    if not ext and "/api/file/download/" not in parsed.path.lower():
        return None

    return {"name": str(name).strip() or "KAP eki", "url": absolute, "extension": ext}


def _first_present(raw: dict, keys: list[str]) -> str:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _safe_extension(name: str, url: str, content_type: str = "") -> str:
    for source in (name, urlparse(url).path):
        match = re.search(r"(\.[a-z0-9]+)(?:$|[?#])", source.lower())
        if match and match.group(1) in _SAFE_ATTACHMENT_EXTENSIONS:
            return match.group(1)
    content_type = content_type.lower()
    if "pdf" in content_type:
        return ".pdf"
    if "html" in content_type:
        return ".html"
    if "xml" in content_type:
        return ".xml"
    return ""


def fetch_report_attachment_text(attachments: list[dict]) -> tuple[str, str, str]:
    if not attachments:
        return "", "", ""

    chunks: list[str] = []
    sources: list[str] = []
    errors: list[str] = []

    for attachment in attachments[:_MAX_ATTACHMENTS_PER_DISCLOSURE]:
        if len(" ".join(chunks)) >= _MAX_REPORT_TEXT_CHARS:
            break
        text, error = _download_and_extract_attachment(attachment)
        if text:
            name = attachment.get("name") or attachment.get("url") or "KAP eki"
            chunks.append(f"{name}: {text}")
            sources.append(str(name))
        elif error:
            errors.append(error)

    report_text = re.sub(r"\s+", " ", " ".join(chunks)).strip()[:_MAX_REPORT_TEXT_CHARS]
    return report_text, ", ".join(sources), "; ".join(errors)[:500]


def _download_and_extract_attachment(attachment: dict) -> tuple[str, str]:
    url = str(attachment.get("url") or "")
    if not url:
        return "", "Ek URL bulunamadı."

    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        if response.status_code == 429:
            return "", "KAP ek dosya indirme limiti doldu."
        response.raise_for_status()
        content_length = int(response.headers.get("Content-Length") or "0")
        if content_length > _MAX_ATTACHMENT_BYTES:
            return "", "Ek dosya çok büyük olduğu için atlandı."

        data = BytesIO()
        for chunk in response.iter_content(chunk_size=64_000):
            if not chunk:
                continue
            data.write(chunk)
            if data.tell() > _MAX_ATTACHMENT_BYTES:
                return "", "Ek dosya boyut limiti aştığı için atlandı."
        content = data.getvalue()
    except requests.RequestException as exc:
        return "", f"Ek dosya indirilemedi: {str(exc)[:120]}"

    ext = _safe_extension(str(attachment.get("name") or ""), url, response.headers.get("Content-Type", ""))
    if ext == ".pdf":
        return _extract_pdf_attachment_text(content), ""
    if ext in {".html", ".htm", ".xhtml"}:
        return _extract_html_attachment_text(content), ""
    if ext in {".xml", ".xbrl"}:
        return _extract_xml_attachment_text(content), ""
    return "", "Desteklenmeyen ek dosya türü atlandı."


def _extract_pdf_attachment_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        pages = reader.pages[:_MAX_ATTACHMENT_PDF_PAGES]
        text = " ".join(page.extract_text() or "" for page in pages)
        return re.sub(r"\s+", " ", text).strip()[:_MAX_REPORT_TEXT_CHARS]
    except Exception:
        return ""


def _extract_html_attachment_text(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()[:_MAX_REPORT_TEXT_CHARS]


def _extract_xml_attachment_text(content: bytes) -> str:
    raw = content.decode("utf-8", errors="ignore")
    lines: list[str] = []
    for match in re.finditer(r"<(?P<tag>[A-Za-z0-9_:.-]+)[^>]*>(?P<value>[^<]{1,120})</(?P=tag)>", raw):
        tag = match.group("tag").split(":")[-1]
        value = re.sub(r"\s+", " ", match.group("value")).strip()
        if not value:
            continue
        if re.search(r"\d", value) or any(token in tag.lower() for token in ["profit", "asset", "equity", "cash", "income", "revenue", "kar", "varlik"]):
            lines.append(f"{tag}: {value}")
        if len(" ".join(lines)) >= _MAX_REPORT_TEXT_CHARS:
            break
    if not lines:
        text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()[:_MAX_REPORT_TEXT_CHARS]
    return " ".join(lines)[:_MAX_REPORT_TEXT_CHARS]
