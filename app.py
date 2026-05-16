from __future__ import annotations

import json
import os
import re
from html import escape
from datetime import date, timedelta
from io import BytesIO
from typing import Iterable

import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from gtts import gTTS
from pypdf import PdfReader
from rapidfuzz import fuzz, process

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - handled in UI
    genai = None
    types = None

from kap_okuryazar.config import (
    APP_TITLE,
    DEFAULT_MODEL,
    DISCLOSURE_TYPES,
    EXAMPLE_COMPANIES,
    GAP_ITEMS,
    JURY_POINTS,
    KAP_DISCLOSURE_URL,
    KAP_HEADERS,
    KAP_SEARCH_PAGE,
    POPULAR_COMPANY_ALIASES,
    TONE_OPTIONS,
)
from kap_okuryazar.demo_data import DEMO_COMPANY, DEMO_DISCLOSURES
from kap_okuryazar.models import CompanyMatch
from kap_okuryazar.safety import apply_safety_guard
from kap_okuryazar.text_utils import (
    apply_glossary,
    detect_anomalies,
    extract_financial_numbers,
    normalize_tr,
)

load_dotenv()

def get_secret(name: str) -> str | None:
    session_key = f"{name.lower()}_input"
    try:
        session_value = st.session_state.get(session_key)
        if session_value:
            return str(session_value).strip()
    except Exception:
        pass

    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, None)
    except Exception:
        return None


def get_gemini_client():
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def test_gemini_connection() -> tuple[bool, str]:
    client = get_gemini_client()
    if client is None:
        if genai is None:
            return False, "google-genai paketi yüklenemedi."
        return False, "GEMINI_API_KEY bulunamadı. Sidebar'dan anahtar gir veya .env dosyasına ekle."

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents="Sadece 'hazır' yaz.",
        )
        text = (response.text or "").strip()
        return True, f"Gemini çalışıyor: {text[:80] or 'yanıt alındı'}"
    except Exception as exc:
        message = str(exc)
        if "API_KEY_INVALID" in message or "INVALID_ARGUMENT" in message:
            return False, "API key geçersiz görünüyor. Google AI Studio'dan yeni key alıp tekrar dene."
        if "PERMISSION_DENIED" in message:
            return False, "API key bu modele erişemiyor veya proje izinleri kapalı."
        if "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
            return False, "Kota veya limit dolmuş görünüyor."
        if "NOT_FOUND" in message:
            return False, f"Model bulunamadı: {DEFAULT_MODEL}. Model adını kontrol etmek gerekebilir."
        return False, f"Gemini bağlantı hatası: {message[:220]}"


@st.cache_data(ttl=60 * 60)
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


@st.cache_data(ttl=10 * 60)
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


@st.cache_data(ttl=10 * 60)
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


@st.cache_data(ttl=60 * 60)
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


@st.cache_data(ttl=60 * 60)
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


def compact_disclosures(disclosures: Iterable[dict]) -> str:
    chunks = []
    for item in disclosures:
        chunks.append(
            "\n".join(
                [
                    f"Bildirim no: {item['index']}",
                    f"Tarih: {item['publish_datetime']}",
                    f"Kategori: {item['category']}",
                    f"Konu: {item['subject']}",
                    f"Kısa özet: {item['summary']}",
                    f"Metin: {item['page_text'][:1300]}",
                    f"Link: {item['url']}",
                ]
            )
        )
    return "\n\n---\n\n".join(chunks)


def empty_report(company: CompanyMatch) -> dict:
    return {
        "headline": f"{company.name} için sade KAP özeti",
        "one_sentence": "Son bildirimler anlaşılır dile çevrildi.",
        "overall_tone": "nötr",
        "overall_meaning": "Bu bildirimler yatırım tavsiyesi değildir; şirketin kamuya açıkladığı bilgileri anlamaya yardım eder.",
        "watch_out": ["Tek bir KAP bildirimiyle yatırım kararı verilmemeli."],
        "items": [],
        "audio_script": "",
        "disclaimer": "Bu içerik yatırım tavsiyesi değildir.",
    }


def fallback_report(company: CompanyMatch, disclosures: list[dict]) -> dict:
    report = empty_report(company)
    report["one_sentence"] = f"{company.name} için {len(disclosures)} KAP bildirimi bulundu."
    report["items"] = []

    for item in disclosures:
        subject = item["subject"] or "Konu belirtilmemiş"
        report["items"].append(
            {
                "date": item["publish_datetime"][:16],
                "category": item["category"],
                "plain_title": subject,
                "what_happened": item["summary"] or "Şirket bu konuda KAP'a resmi bir bildirim göndermiş.",
                "why_it_matters": category_explanation(item["category"]),
                "small_investor_note": "Bu bilgi tek başına karar vermek için yeterli değildir; şirketin önceki açıklamaları ve finansal durumu da incelenmelidir.",
                "tone": "nötr",
                "risk": "Bildirim metni detaylı olabilir; önemli ayrıntılar ek dosyada yer alabilir.",
                "source_url": item["url"],
            }
        )

    report["audio_script"] = build_audio_script(report)
    return report


def category_explanation(category: str) -> str:
    explanations = {
        "Finansal Rapor": "Şirketin gelir, gider, borç ve kâr durumunu gösterir.",
        "Temettü": "Şirketin ortaklarına para dağıtımıyla ilgili olabilir.",
        "Genel Kurul": "Şirket ortaklarının önemli kararları konuştuğu toplantıyla ilgilidir.",
        "Sermaye İşlemi": "Şirketin hisse sayısı veya sermaye yapısı değişebilir.",
        "Özel Durum": "Şirketin yatırımcıları ilgilendirebilecek özel bir gelişmeyi duyurduğunu gösterir.",
        "Borçlanma": "Şirketin para bulmak için borçlanma aracı kullanabileceğini gösterir.",
        "Yönetim": "Şirketin yönetimi veya karar alma yapısıyla ilgilidir.",
        "Sözleşme/İhale": "Şirketin yeni iş, proje veya sipariş aldığını gösterebilir.",
    }
    return explanations.get(category, "Şirketin kamuya duyurması gereken resmi bir gelişmedir.")


def analyze_with_gemini(company: CompanyMatch, disclosures: list[dict], tone: str) -> dict:
    client = get_gemini_client()
    if client is None:
        return fallback_report(company, disclosures)

    prompt = f"""
Sen Türkiye'de finansal okuryazarlığı artıran sesli asistansın.
KAP bildirimlerini ilkokul seviyesinde, sade Türkçe ile açıkla.

Kesin kurallar:
- Yatırım tavsiyesi verme.
- "Al", "sat", "tut", "kesin yükselir", "kesin düşer" deme.
- Bilmediğin sonucu uydurma.
- Her bildirime risk veya dikkat notu ekle.
- Sesli okunacağı için kısa cümleler kur.
- Ton: {tone}

Sadece geçerli JSON döndür. Markdown kullanma.
Şema:
{{
  "headline": "kısa başlık",
  "one_sentence": "tek cümlelik genel özet",
  "overall_tone": "olumlu | olumsuz | nötr | karışık",
  "overall_meaning": "anne-babaya anlatır gibi genel anlam",
  "watch_out": ["dikkat edilecek nokta 1", "dikkat edilecek nokta 2"],
  "items": [
    {{
      "date": "tarih",
      "category": "bildirim türü",
      "plain_title": "sade başlık",
      "what_happened": "ne oldu",
      "why_it_matters": "neden önemli",
      "small_investor_note": "küçük yatırımcı neye dikkat etmeli",
      "tone": "olumlu | olumsuz | nötr | karışık",
      "risk": "risk veya belirsizlik",
      "source_url": "KAP linki"
    }}
  ],
  "audio_script": "45-75 saniyelik doğal konuşma metni",
  "disclaimer": "yatırım tavsiyesi değildir cümlesi"
}}

Şirket: {company.name}
Hisse kodu: {company.ticker}

KAP bildirimleri:
{compact_disclosures(disclosures)}
"""
    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return sanitize_report(normalize_report(json_from_text(response.text), company, disclosures))
    except Exception:
        return fallback_report(company, disclosures)


def sanitize_report(report: dict) -> dict:
    """Tüm metin alanlarını güvenlik kalkanından geçirir."""
    for key in ("headline", "one_sentence", "overall_meaning", "audio_script"):
        if key in report and isinstance(report[key], str):
            report[key] = apply_safety_guard(report[key])
    if isinstance(report.get("watch_out"), list):
        report["watch_out"] = [apply_safety_guard(w) for w in report["watch_out"] if isinstance(w, str)]
    if isinstance(report.get("items"), list):
        for item in report["items"]:
            if not isinstance(item, dict):
                continue
            for key in ("plain_title", "what_happened", "why_it_matters", "small_investor_note", "risk"):
                if key in item and isinstance(item[key], str):
                    item[key] = apply_safety_guard(item[key])
    return report


def json_from_text(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


def normalize_report(report: dict, company: CompanyMatch, disclosures: list[dict]) -> dict:
    fallback = fallback_report(company, disclosures)
    if not isinstance(report, dict):
        return fallback

    normalized = fallback | {key: report.get(key, fallback[key]) for key in fallback}
    if not isinstance(normalized.get("watch_out"), list):
        normalized["watch_out"] = fallback["watch_out"]
    if not isinstance(normalized.get("items"), list) or not normalized["items"]:
        normalized["items"] = fallback["items"]

    source_by_index = {str(item["index"]): item["url"] for item in disclosures}
    for idx, item in enumerate(normalized["items"]):
        if not isinstance(item, dict):
            normalized["items"][idx] = fallback["items"][min(idx, len(fallback["items"]) - 1)]
            continue
        if not item.get("source_url") and idx < len(disclosures):
            item["source_url"] = disclosures[idx]["url"]
        if str(item.get("source_url")) in source_by_index:
            item["source_url"] = source_by_index[str(item["source_url"])]

    normalized["audio_script"] = normalized.get("audio_script") or build_audio_script(normalized)
    normalized["disclaimer"] = "Bu içerik yatırım tavsiyesi değildir."
    return normalized


def build_audio_script(report: dict) -> str:
    parts = [
        report.get("one_sentence", ""),
        report.get("overall_meaning", ""),
    ]
    for item in report.get("items", [])[:3]:
        parts.append(
            f"{item.get('plain_title', 'Bir bildirim var')}. "
            f"{item.get('what_happened', '')} "
            f"{item.get('small_investor_note', '')}"
        )
    parts.append(report.get("disclaimer", "Bu içerik yatırım tavsiyesi değildir."))
    return " ".join(part for part in parts if part).strip()


@st.cache_data(ttl=60 * 60, show_spinner=False)
def transcribe_company_name(audio_bytes: bytes, mime_type: str) -> str:
    client = get_gemini_client()
    if client is None or types is None:
        raise RuntimeError("Ses tanıma için GEMINI_API_KEY gerekli.")

    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[
            "Bu kısa Türkçe ses kaydında söylenen şirket adını veya hisse kodunu sadece düz metin olarak yaz.",
            audio_part,
        ],
    )
    return response.text.strip().strip('"')


def answer_question(company: CompanyMatch, disclosures: list[dict], question: str, history: list[dict]) -> str:
    client = get_gemini_client()
    if client is None:
        return (
            "Sohbet için GEMINI_API_KEY gerekli. Sidebar'dan key gir veya .env dosyasına ekle. "
            "Bu arada 'Sade anlatım' sekmesinden bildirimleri kural tabanlı özet olarak okuyabilirsin."
        )

    history_text = ""
    if history:
        last = history[-3:]
        history_text = "\n".join(f"Soru: {h['q']}\nCevap: {h['a']}" for h in last)

    prompt = f"""Sen Türk yatırımcılar için finansal okuryazarlık asistanısın.
SADECE aşağıdaki KAP bildirimlerine dayanarak cevap ver. Bilgi yoksa "Bu KAP bildirimlerinde bu konuda net bilgi yok" de.

Kesin kurallar:
- Yatırım tavsiyesi verme. "Al", "sat", "tut", "kesin yükselir" deme.
- Sade Türkçe, kısa cümleler, en fazla 4-5 cümle.
- Cevabın sonuna kısa bir kaynak notu ekle (hangi bildirim numarası).

Şirket: {company.name} ({company.ticker})

KAP Bildirimleri:
{compact_disclosures(disclosures)}

Önceki konuşma:
{history_text or '(boş)'}

Kullanıcı sorusu: {question}

Cevap:"""
    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return apply_safety_guard((response.text or "").strip())
    except Exception as exc:
        return f"Sohbet sırasında hata oluştu: {exc}"


def compare_companies(c1: CompanyMatch, d1: list[dict], c2: CompanyMatch, d2: list[dict]) -> str:
    """İki şirketin son KAP bildirimlerini yan yana karşılaştırır."""
    client = get_gemini_client()
    if client is None:
        # Kural tabanlı basit karşılaştırma
        cats1 = {d["category"] for d in d1}
        cats2 = {d["category"] for d in d2}
        return (
            f"**{c1.name}** son dönemde {len(d1)} bildirim yapmış (kategoriler: {', '.join(sorted(cats1)) or 'yok'}).\n\n"
            f"**{c2.name}** son dönemde {len(d2)} bildirim yapmış (kategoriler: {', '.join(sorted(cats2)) or 'yok'}).\n\n"
            f"Ortak kategoriler: {', '.join(sorted(cats1 & cats2)) or 'ortak kategori yok'}.\n\n"
            "Daha derin karşılaştırma için Gemini API key gerekli."
        )

    prompt = f"""İki Türk şirketinin son KAP bildirimlerini karşılaştır.
Sade Türkçe, jargon kullanma. Yatırım tavsiyesi verme.

Şu başlıklarda Markdown ile yaz:
### Genel resim
### Hangi şirket ne tür haber yapmış?
### Dikkat çeken farklar
### Ortak noktalar
### Küçük yatırımcı için pratik notlar

Şirket A: {c1.name} ({c1.ticker})
{compact_disclosures(d1)}

Şirket B: {c2.name} ({c2.ticker})
{compact_disclosures(d2)}
"""
    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return apply_safety_guard((response.text or "").strip())
    except Exception as exc:
        return f"Karşılaştırma sırasında hata: {exc}"


def simplify_pdf_text(text: str, tone: str = "anne-babaya anlatır gibi sade") -> str:
    """Kullanıcının yüklediği PDF'in ham metnini sade Türkçe'ye çevirir."""
    client = get_gemini_client()
    if client is None:
        return (
            "Sadeleştirme için GEMINI_API_KEY gerekli. "
            "Bu arada metnin ilk 500 karakteri:\n\n" + text[:500]
        )

    prompt = f"""Aşağıdaki Türkçe finansal/resmi belgeyi ilkokul seviyesine indir.
Yatırım tavsiyesi verme. "Al/sat/kesin yükselir" deme.
Ton: {tone}

Şu başlıklarla Markdown çıktı ver:
### Tek cümlelik özet
### Ne anlatıyor?
### Önemli sayılar / tarihler
### Dikkat edilecek noktalar
### Bilinmeyen terimler (varsa kısa tanım)

Belge:
{text[:8000]}
"""
    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return apply_safety_guard((response.text or "").strip())
    except Exception as exc:
        return f"Sadeleştirme sırasında hata: {exc}"


def analyze_visual_document(file_bytes: bytes, mime_type: str, user_note: str, tone: str) -> str:
    """Gemini Vision ile grafik, ekran görüntüsü veya PDF görselini sade anlatır."""
    client = get_gemini_client()
    if client is None or types is None:
        return (
            "Gemini Vision analizi için GEMINI_API_KEY gerekli. "
            "Sidebar'dan API key girip bağlantıyı test edebilirsin."
        )

    visual_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
    note = user_note.strip() or "Kullanıcı ek not girmedi."
    prompt = f"""Sen Türkiye'deki sıradan vatandaşlar için finansal okuryazarlık asistanısın.
Yüklenen görseli veya PDF'i incele. Bu bir BIST grafiği, finansal rapordaki çubuk grafik,
tablo, sunum sayfası veya KAP ekran görüntüsü olabilir.

Kesin kurallar:
- Yatırım tavsiyesi verme.
- "Al", "sat", "tut", "kesin yükselir", "kesin düşer" deme.
- Görselde kanıt yoksa tahmin uydurma.
- Teknik analizi kesin sonuç gibi anlatma; sadece eğitim amaçlı yorumla.
- Kısa, sade Türkçe kullan.
- Ton: {tone}

Kullanıcının notu:
{note}

Şu başlıklarla Markdown yaz:
### Bu görsel ne gösteriyor?
### En dikkat çeken 3 nokta
### Basit yorum
### Riskler ve belirsizlikler
### Sesli okunacak kısa özet
"""
    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=[prompt, visual_part],
        )
        return apply_safety_guard((response.text or "").strip())
    except Exception as exc:
        return f"Grafik analizi sırasında hata oluştu: {exc}"


def extract_pdf_bytes_text(file_bytes: bytes) -> str:
    """Yüklenen PDF byte'larından metin çıkarır."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = []
        for page in reader.pages[:20]:
            pages.append(page.extract_text() or "")
        text = " ".join(pages)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception as exc:
        return f"PDF okunamadı: {exc}"


def increment_stat(key: str, by: int = 1) -> int:
    """Streamlit session içinde basit kullanım sayacı."""
    counts = st.session_state.setdefault("_stats", {})
    counts[key] = counts.get(key, 0) + by
    return counts[key]


def get_stats() -> dict[str, int]:
    return st.session_state.get("_stats", {})


@st.cache_data(ttl=60 * 60)
def text_to_speech_mp3(text: str) -> bytes:
    mp3_fp = BytesIO()
    tts = gTTS(text=text, lang="tr", slow=False)
    tts.write_to_fp(mp3_fp)
    return mp3_fp.getvalue()


def build_markdown_export(company: CompanyMatch, report: dict, disclosures: list[dict]) -> str:
    lines = [
        f"# {company.name} ({company.ticker}) — Sade KAP Raporu",
        "",
        f"**Genel ton:** {report.get('overall_tone', 'nötr')}",
        "",
        f"**Tek cümle:** {report.get('one_sentence', '')}",
        "",
        f"**Genel anlam:** {report.get('overall_meaning', '')}",
        "",
        "## Dikkat edilecekler",
    ]
    for note in report.get("watch_out", []) or []:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## Bildirim Kartları")
    for item in report.get("items", []):
        lines.extend(
            [
                f"### {item.get('plain_title', 'Bildirim')}",
                f"- **Tarih:** {item.get('date', '')}",
                f"- **Kategori:** {item.get('category', '')}",
                f"- **Ne oldu:** {item.get('what_happened', '')}",
                f"- **Neden önemli:** {item.get('why_it_matters', '')}",
                f"- **Dikkat notu:** {item.get('small_investor_note', '')}",
                f"- **Risk:** {item.get('risk', '')}",
                f"- **Kaynak:** {item.get('source_url', '')}",
                "",
            ]
        )
    lines.append("---")
    lines.append("")
    lines.append("## Ham KAP Bildirimleri")
    for item in disclosures:
        lines.append(f"- [{item['publish_datetime'][:16]} · {item['category']}] {item['subject']} — {item['url']}")
    lines.append("")
    lines.append(f"_Disclaimer: {report.get('disclaimer', 'Bu içerik yatırım tavsiyesi değildir.')}_")
    return "\n".join(lines)


def render_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #1d1d1f;
            --muted: #6e6e73;
            --line: rgba(255, 255, 255, 0.45);
            --line-strong: rgba(255, 255, 255, 0.7);
            --paper: rgba(255, 255, 255, 0.55);
            --paper-strong: rgba(255, 255, 255, 0.78);
            --soft: rgba(255, 255, 255, 0.35);
            --accent: #0a84ff;
            --accent-soft: rgba(10, 132, 255, 0.14);
            --warn: #ff9f0a;
            --rose: #ff375f;
            --shadow-near: 0 1px 0 rgba(255, 255, 255, 0.7) inset, 0 0 0 1px rgba(255, 255, 255, 0.35) inset;
            --shadow-far: 0 12px 40px rgba(28, 36, 80, 0.08), 0 2px 6px rgba(28, 36, 80, 0.04);
        }
        .stApp {
            background:
                radial-gradient(ellipse 80% 60% at 12% 8%, rgba(255, 183, 197, 0.55), transparent 55%),
                radial-gradient(ellipse 70% 60% at 90% 10%, rgba(149, 199, 255, 0.6), transparent 55%),
                radial-gradient(ellipse 90% 70% at 50% 110%, rgba(196, 175, 255, 0.55), transparent 55%),
                radial-gradient(ellipse 60% 50% at 95% 90%, rgba(255, 220, 168, 0.5), transparent 55%),
                linear-gradient(180deg, #f4f1ff 0%, #fdf5ee 100%);
            color: var(--ink);
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", system-ui, sans-serif;
        }
        .block-container {
            max-width: 1280px;
            padding-top: 64px;
            padding-bottom: 64px;
        }

        section[data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.55);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            border-right: 1px solid var(--line);
        }
        section[data-testid="stSidebar"] > div {
            background: transparent;
        }
        section[data-testid="stSidebar"] * { color: var(--ink); }
        h1, h2, h3, h4 {
            letter-spacing: -0.022em;
            color: var(--ink);
            font-weight: 650;
        }

        /* === Liquid Glass Tabs === */
        div[data-testid="stTabs"] [role="tablist"] {
            gap: 4px;
            background: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur(30px) saturate(180%);
            -webkit-backdrop-filter: blur(30px) saturate(180%);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 6px;
            box-shadow: var(--shadow-far);
        }
        div[data-testid="stTabs"] button {
            background: transparent;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600;
            color: var(--muted);
            padding: 8px 16px !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }
        div[data-testid="stTabs"] button:hover {
            background: rgba(255, 255, 255, 0.45);
            color: var(--ink);
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: rgba(255, 255, 255, 0.85);
            color: var(--ink);
            box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 4px 12px rgba(28, 36, 80, 0.08);
        }

        /* === Liquid Glass Inputs === */
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stSelectbox"] > div > div,
        div[data-testid="stChatInput"] textarea {
            border-radius: 14px !important;
            min-height: 56px;
            border: 1px solid var(--line) !important;
            background: rgba(255, 255, 255, 0.55) !important;
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            font-size: 1.05rem !important;
            color: var(--ink) !important;
            box-shadow: 0 1px 0 rgba(255, 255, 255, 0.6) inset, 0 4px 16px rgba(28, 36, 80, 0.04);
            transition: all 0.2s ease;
        }
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stChatInput"] textarea:focus {
            border-color: rgba(10, 132, 255, 0.5) !important;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.6) inset,
                0 0 0 4px rgba(10, 132, 255, 0.18),
                0 4px 16px rgba(28, 36, 80, 0.06);
        }

        div[data-testid="stTextInput"] input {
            min-height: 64px !important;
            font-size: 1.1rem !important;
            font-weight: 520;
            padding: 0 18px !important;
            text-align: center !important;
            line-height: 1.1 !important;
            transform: translateY(-10px);
        }
        div[data-testid="stTextInput"] input::placeholder {
            transform: translateY(-10px);
        }
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
            min-height: 48px !important;
            font-size: 1rem !important;
            text-align: left !important;
        }

        /* === Liquid Glass Buttons === */
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button,
        div[data-testid="stLinkButton"] a {
            border-radius: 14px !important;
            min-height: 44px;
            font-weight: 600;
            border: 1px solid var(--line) !important;
            background: rgba(255, 255, 255, 0.6) !important;
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            color: var(--ink) !important;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.8) inset,
                0 0 0 1px rgba(255, 255, 255, 0.35) inset,
                0 4px 14px rgba(28, 36, 80, 0.06);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        div[data-testid="stButton"] button:hover,
        div[data-testid="stDownloadButton"] button:hover,
        div[data-testid="stLinkButton"] a:hover {
            background: rgba(255, 255, 255, 0.85) !important;
            transform: translateY(-1px);
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.9) inset,
                0 0 0 1px rgba(255, 255, 255, 0.45) inset,
                0 8px 22px rgba(28, 36, 80, 0.1);
        }
        div[data-testid="stButton"] button:active {
            transform: translateY(0);
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(180deg, rgba(10, 132, 255, 0.95), rgba(10, 132, 255, 0.85)) !important;
            border-color: rgba(10, 132, 255, 0.4) !important;
            color: #ffffff !important;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.4) inset,
                0 0 0 1px rgba(255, 255, 255, 0.2) inset,
                0 8px 22px rgba(10, 132, 255, 0.32);
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: linear-gradient(180deg, rgba(10, 132, 255, 1), rgba(10, 132, 255, 0.92)) !important;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.5) inset,
                0 12px 30px rgba(10, 132, 255, 0.42);
        }

        /* === Liquid Glass Metrics === */
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.55);
            backdrop-filter: blur(30px) saturate(180%);
            -webkit-backdrop-filter: blur(30px) saturate(180%);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 18px;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.7) inset,
                0 8px 24px rgba(28, 36, 80, 0.06);
        }
        div[data-testid="stMetric"] label {
            color: var(--muted);
            font-weight: 500;
        }

        /* === Liquid Glass Expanders / Alerts === */
        .stExpander, .stAlert,
        div[data-testid="stExpander"] details,
        div[data-baseweb="notification"] {
            background: rgba(255, 255, 255, 0.55) !important;
            backdrop-filter: blur(30px) saturate(180%);
            -webkit-backdrop-filter: blur(30px) saturate(180%);
            border: 1px solid var(--line) !important;
            border-radius: 16px !important;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.7) inset,
                0 6px 20px rgba(28, 36, 80, 0.05);
        }

        /* === Slider === */
        div[data-testid="stSlider"] [data-baseweb="slider"] > div > div {
            background: rgba(10, 132, 255, 0.85) !important;
        }

        /* === Sidebar elements === */
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
        section[data-testid="stSidebar"] div[data-testid="stButton"] button {
            background: rgba(255, 255, 255, 0.7) !important;
        }

        /* === Chat messages === */
        div[data-testid="stChatMessage"] {
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 14px 18px !important;
            margin-bottom: 10px;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.7) inset,
                0 4px 14px rgba(28, 36, 80, 0.04);
        }

        /* === DataFrames / Tables === */
        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
        }

        /* === Audio === */
        audio {
            width: 100%;
            border-radius: 12px;
        }

        /* === Brand & Hero === */
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            padding: 16px 0 28px;
        }
        .brand {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            font-weight: 650;
            color: var(--ink);
            font-size: 1.08rem;
            letter-spacing: -0.01em;
        }
        .brand-mark {
            width: 38px;
            height: 38px;
            border-radius: 12px;
            display: inline-grid;
            place-items: center;
            color: #ffffff;
            background: linear-gradient(135deg, #0a84ff, #5e5ce6);
            font-weight: 700;
            font-size: 1.05rem;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.4) inset,
                0 6px 16px rgba(10, 132, 255, 0.35);
        }
        .brand-tag {
            color: var(--muted);
            font-weight: 500;
            font-size: 0.92rem;
        }

        .lead {
            font-size: 2rem;
            font-weight: 650;
            line-height: 1.1;
            margin: 10px 0 8px;
            color: var(--ink);
            letter-spacing: -0.035em;
            text-align: center;
        }
        .lead-sub {
            color: var(--muted);
            font-size: 1.05rem;
            margin-bottom: 26px;
            max-width: 720px;
        }

        /* === Glass Panels === */
        .panel, .glass {
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(30px) saturate(180%);
            -webkit-backdrop-filter: blur(30px) saturate(180%);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 14px;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.75) inset,
                0 0 0 1px rgba(255, 255, 255, 0.35) inset,
                0 12px 40px rgba(28, 36, 80, 0.08);
            position: relative;
            overflow: hidden;
        }

        .result-card {
            background: rgba(255, 255, 255, 0.55);
            backdrop-filter: blur(30px) saturate(180%);
            -webkit-backdrop-filter: blur(30px) saturate(180%);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 22px 24px;
            margin-bottom: 14px;
            position: relative;
            overflow: hidden;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.75) inset,
                0 0 0 1px rgba(255, 255, 255, 0.35) inset,
                0 10px 30px rgba(28, 36, 80, 0.06);
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }
        .result-card:hover {
            transform: translateY(-2px);
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.8) inset,
                0 0 0 1px rgba(255, 255, 255, 0.4) inset,
                0 16px 40px rgba(28, 36, 80, 0.1);
        }
        .result-card:before {
            content: "";
            position: absolute;
            left: 0;
            top: 18px;
            bottom: 18px;
            width: 3px;
            background: linear-gradient(180deg, #0a84ff, #5e5ce6);
            border-radius: 0 4px 4px 0;
        }
        .result-card h4 {
            margin: 8px 0 12px;
            font-size: 1.12rem;
            font-weight: 650;
            letter-spacing: -0.015em;
        }
        .result-card p { margin: 6px 0; line-height: 1.55; color: var(--ink); }

        .muted { color: var(--muted); font-size: 0.92rem; }

        .badge {
            display: inline-block;
            padding: 4px 11px;
            border: 1px solid var(--line);
            border-radius: 999px;
            font-size: 0.76rem;
            margin-right: 6px;
            background: rgba(255, 255, 255, 0.55);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            color: var(--muted);
            font-weight: 600;
            box-shadow: 0 1px 0 rgba(255, 255, 255, 0.6) inset;
        }
        .badge-good { border-color: rgba(48, 209, 88, 0.4); color: #1f8c3a; background: rgba(48, 209, 88, 0.12); }
        .badge-info { border-color: rgba(10, 132, 255, 0.4); color: #0a84ff; background: rgba(10, 132, 255, 0.12); }
        .badge-warn { border-color: rgba(255, 159, 10, 0.4); color: #b8730a; background: rgba(255, 159, 10, 0.14); }

        .source-row {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            padding: 12px 16px;
            margin-bottom: 8px;
            box-shadow: 0 1px 0 rgba(255, 255, 255, 0.6) inset;
        }

        .footer-note {
            color: var(--muted);
            font-size: 0.85rem;
            text-align: center;
            padding: 22px 0 0;
            margin-top: 32px;
        }

        .kbd {
            display: inline-block;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.6);
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--ink);
            box-shadow: 0 1px 0 rgba(255, 255, 255, 0.7) inset;
        }

        /* === Glossary tooltips === */
        abbr.gloss {
            text-decoration: underline dotted rgba(10, 132, 255, 0.6);
            text-decoration-thickness: 1.5px;
            text-underline-offset: 3px;
            cursor: help;
            color: inherit;
        }
        abbr.gloss:hover {
            color: var(--accent);
            background: rgba(10, 132, 255, 0.08);
            border-radius: 3px;
        }

        /* === Risk panel === */
        .risk-warn {
            background: linear-gradient(180deg, rgba(255, 159, 10, 0.18), rgba(255, 159, 10, 0.08));
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 159, 10, 0.4);
            border-radius: 18px;
            padding: 18px 22px;
            margin: 14px 0;
            box-shadow:
                0 1px 0 rgba(255, 255, 255, 0.6) inset,
                0 6px 22px rgba(255, 159, 10, 0.18);
        }
        .risk-warn h4 {
            color: #b8730a;
            margin-bottom: 10px;
        }
        .risk-row {
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid rgba(255, 159, 10, 0.25);
            border-radius: 12px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        .risk-clean {
            background: linear-gradient(180deg, rgba(48, 209, 88, 0.18), rgba(48, 209, 88, 0.06));
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(48, 209, 88, 0.4);
            border-radius: 14px;
            padding: 12px 18px;
            margin: 14px 0;
            color: #1f8c3a;
            font-weight: 600;
        }

        /* === A/B compare blocks === */
        .ab-block {
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 14px 16px;
            min-height: 140px;
            font-size: 0.95rem;
            line-height: 1.5;
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
        }
        .ab-official {
            background: linear-gradient(180deg, rgba(150, 150, 150, 0.10), rgba(150, 150, 150, 0.04));
            border-color: rgba(120, 120, 120, 0.3);
        }
        .ab-plain {
            background: linear-gradient(180deg, rgba(10, 132, 255, 0.10), rgba(94, 92, 230, 0.06));
            border-color: rgba(10, 132, 255, 0.3);
        }

        /* Smooth scroll */
        html { scroll-behavior: smooth; }

        @media (max-width: 760px) {
            .block-container { padding-left: 14px; padding-right: 14px; }
            .lead { font-size: 1.35rem; }
            .topbar { flex-direction: column; align-items: flex-start; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="topbar">
            <div class="brand">
                <span class="brand-mark">K</span>
                <span>KAP Okuryazar</span>
            </div>
            <div class="brand-tag">resmi bildirimleri sade Türkçe'ye çevirir</div>
        </div>
        <div class="lead">Hangi şirketin haberlerini anlamak istiyorsun?</div>
        """,
        unsafe_allow_html=True,
    )


def remember_search(query: str) -> None:
    query = query.strip()
    if not query:
        return
    history = st.session_state.setdefault("search_history", [])
    normalized = normalize_tr(query)
    history[:] = [item for item in history if normalize_tr(item) != normalized]
    history.insert(0, query)
    del history[5:]


def render_search_history() -> None:
    history = st.session_state.get("search_history", [])
    if not history:
        st.caption("Geçmiş aramalar burada görünecek.")
        return

    st.caption("Geçmişte arattıklarınız")
    columns = st.columns(min(len(history), 5))
    for column, item in zip(columns, history):
        if column.button(item, use_container_width=True, key=f"hist_{normalize_tr(item)}"):
            st.session_state["company_query"] = item


def render_company_header(company: CompanyMatch, disclosure_count: int, demo_mode: bool) -> None:
    demo_line = "Demo verisiyle gösteriliyor." if demo_mode else "KAP'tan son resmi bildirimler alındı."
    st.markdown(
        f"""
        <div class="panel">
            <div class="muted">Şirket</div>
            <h3>{escape(company.name)}</h3>
            <div class="muted">{escape(company.ticker or "kod yok")} · {disclosure_count} haber bulundu · {demo_line}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_anomaly_panel(disclosures: list[dict]) -> None:
    flags = detect_anomalies(disclosures)
    if not flags:
        st.markdown(
            '<div class="risk-clean">✅ <strong>Risk taraması temiz</strong> — '
            'belirgin bir anomali tespit edilmedi.</div>',
            unsafe_allow_html=True,
        )
        return
    st.markdown('<div class="risk-warn">', unsafe_allow_html=True)
    st.markdown(f"#### ⚠️ Risk dedektörü — {len(flags)} sinyal")
    for title, detail in flags:
        st.markdown(
            f'<div class="risk-row"><strong>{escape(title)}</strong>'
            f'<div class="muted">{escape(detail)}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def render_report(report: dict, company: CompanyMatch, disclosures: list[dict]) -> None:
    st.markdown(f"### {report.get('headline', 'Sade Anlatım')}")
    st.write(report.get("one_sentence", ""))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Genel ton", report.get("overall_tone", "nötr"))
    col2.metric("Bildirim sayısı", len(report.get("items", [])))
    col3.metric("Risk sinyali", len(detect_anomalies(disclosures)))
    col4.metric("Dil seviyesi", "Sade")

    render_anomaly_panel(disclosures)

    st.markdown("#### Genel anlamı")
    st.info(report.get("overall_meaning", "KAP bildirimleri sadeleştirildi."))

    watch_out = report.get("watch_out") or []
    if watch_out:
        st.markdown("#### Dikkat edilecekler")
        for note in watch_out[:4]:
            st.markdown(f"- {note}")

    render_financial_highlights(disclosures)

    st.markdown("#### Bildirim kartları (resmi dil ↔ sade dil)")
    items = report.get("items", []) or []
    for idx, item in enumerate(items):
        original = disclosures[idx] if idx < len(disclosures) else None
        render_analysis_card(item, original)

    st.markdown("---")
    md_export = build_markdown_export(company, report, disclosures)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", company.name)[:40] or "kap-raporu"
    st.download_button(
        "📥 Markdown raporu indir",
        data=md_export.encode("utf-8"),
        file_name=f"{safe_name}_kap_rapor.md",
        mime="text/markdown",
        use_container_width=True,
    )


def render_financial_highlights(disclosures: list[dict]) -> None:
    findings: list[tuple[str, str, str]] = []
    for item in disclosures:
        if item["category"] != "Finansal Rapor":
            continue
        for label, value in extract_financial_numbers(item.get("page_text", "") + " " + item.get("summary", "")):
            findings.append((label, value, item["url"]))
    if not findings:
        return
    st.markdown("#### PDF'ten otomatik çıkarılan rakamlar")
    cols = st.columns(min(len(findings), 3))
    for idx, (label, value, _url) in enumerate(findings[:6]):
        cols[idx % len(cols)].metric(label, value)
    st.caption("Bu sayılar PDF metninden regex ile çıkarıldı. Resmi rakam için kaynak KAP linkine bakın.")


def render_analysis_card(item: dict, original: dict | None = None) -> None:
    category = escape(str(item.get("category", "Diğer")))
    tone = escape(str(item.get("tone", "nötr")))
    date_text = escape(str(item.get("date", "")))
    plain_title = escape(str(item.get("plain_title", "Bildirim")))
    # Glossary tooltipleri sade dile uygulanır
    what_happened = apply_glossary(str(item.get("what_happened", "")))
    why_it_matters = apply_glossary(str(item.get("why_it_matters", "")))
    small_investor_note = apply_glossary(str(item.get("small_investor_note", "")))
    risk = apply_glossary(str(item.get("risk", "")))
    st.markdown(
        f"""
        <div class="result-card">
            <span class="badge badge-info">{category}</span>
            <span class="badge">{tone}</span>
            <div class="muted">{date_text}</div>
            <h4>{plain_title}</h4>
            <p><strong>Ne oldu?</strong> {what_happened}</p>
            <p><strong>Neden önemli?</strong> {why_it_matters}</p>
            <p><strong>Dikkat notu:</strong> {small_investor_note}</p>
            <p class="muted"><strong>Risk:</strong> {risk}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # A/B karşılaştırma: KAP'ın resmi dili ↔ sade versiyon
    if original:
        with st.expander("🔀 Resmi dil ↔ Sade dil karşılaştırması", expanded=False):
            ab_left, ab_right = st.columns(2)
            with ab_left:
                st.markdown("**🏛️ KAP'ın orijinal dili**")
                official = original.get("subject", "") or "—"
                summary = original.get("summary") or original.get("page_text", "")[:600]
                st.markdown(
                    f"<div class='ab-block ab-official'>"
                    f"<div class='muted'>Konu</div><div>{escape(official)}</div>"
                    f"<div class='muted' style='margin-top:8px'>Özet</div>"
                    f"<div>{escape(summary or 'Özet yok')}</div></div>",
                    unsafe_allow_html=True,
                )
            with ab_right:
                st.markdown("**✨ Bizim sade dilimiz**")
                st.markdown(
                    f"<div class='ab-block ab-plain'>"
                    f"<div class='muted'>Başlık</div><div><strong>{escape(item.get('plain_title', ''))}</strong></div>"
                    f"<div class='muted' style='margin-top:8px'>Ne oldu</div>"
                    f"<div>{apply_glossary(item.get('what_happened', ''))}</div></div>",
                    unsafe_allow_html=True,
                )

    source_url = item.get("source_url")
    if source_url:
        st.link_button("KAP kaynağını aç", source_url)


def render_disclosure_cards(disclosures: list[dict]) -> None:
    for item in disclosures:
        title = f"{item['publish_datetime'][:16]} - {item['category']} - {item['subject']}"
        with st.expander(title):
            st.write(item["summary"] or "Kısa özet yok.")
            flags = []
            if item["has_attachment"]:
                flags.append("Ek dosya var")
            if item["is_corrective"]:
                flags.append("Düzeltme bildirimi")
            if item["is_late"]:
                flags.append("Geç gönderilmiş")
            if flags:
                st.caption(" · ".join(flags))
            st.link_button("KAP bildirimini aç", item["url"])


def render_visualizations(disclosures: list[dict]) -> None:
    if not disclosures:
        return
    st.markdown("#### Bildirim dağılımı")
    counts: dict[str, int] = {}
    for d in disclosures:
        counts[d["category"]] = counts.get(d["category"], 0) + 1
    chart_col, time_col = st.columns(2)
    with chart_col:
        st.caption("Kategori bazında")
        st.bar_chart(counts, height=260)
    with time_col:
        st.caption("Zaman çizelgesi (son bildirimler)")
        rows = []
        for d in disclosures:
            rows.append(
                {
                    "tarih": d["publish_datetime"][:10],
                    "kategori": d["category"],
                    "konu": (d["subject"] or "")[:60],
                }
            )
        st.dataframe(rows, hide_index=True, use_container_width=True, height=260)


def render_chat_tab(company: CompanyMatch, disclosures: list[dict]) -> None:
    st.markdown("### Bildirimler hakkında soru sor")
    st.caption(
        "Sorduğun her şey sadece yukarıda çekilen KAP bildirimlerine dayanır. "
        "Yatırım tavsiyesi verilmez."
    )

    chat_key = f"chat_{company.oid}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    history: list[dict] = st.session_state[chat_key]

    voice_col, voice_meta = st.columns([1, 3])
    with voice_col:
        voice_reply = st.toggle("🔊 Sesli cevap", key=f"voice_{company.oid}", value=False)
    with voice_meta:
        if voice_reply:
            st.caption("Cevaplar gTTS ile Türkçe okunacak — full duplex sesli asistan modu.")

    suggestions = [
        "Son dönemde temettü ödemesi var mı?",
        "Genel kurul tarihi açıklandı mı?",
        "En önemli bildirim hangisi ve neden?",
        "Şüpheli/anormal bir şey var mı?",
    ]
    cols = st.columns(len(suggestions))
    for col, sug in zip(cols, suggestions):
        if col.button(sug, key=f"sug_{company.oid}_{sug[:10]}", use_container_width=True):
            st.session_state[f"_pending_q_{company.oid}"] = sug

    pending_key = f"_pending_q_{company.oid}"
    pending = st.session_state.pop(pending_key, None)

    user_msg = st.chat_input("Bir soru yaz, ör: 'Bu şirket borçlanma yaptı mı?'")
    question = pending or user_msg

    for entry in history:
        with st.chat_message("user"):
            st.write(entry["q"])
        with st.chat_message("assistant"):
            st.write(entry["a"])
            if entry.get("audio"):
                st.audio(entry["audio"], format="audio/mp3")

    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Düşünüyor..."):
                answer = answer_question(company, disclosures, question, history)
            st.write(answer)
            audio_bytes = None
            if voice_reply and answer:
                try:
                    audio_bytes = text_to_speech_mp3(answer[:2500])
                    st.audio(audio_bytes, format="audio/mp3")
                except Exception as exc:
                    st.caption(f"Sesli cevap üretilemedi: {exc}")
        increment_stat("chat_questions")
        entry = {"q": question, "a": answer}
        if audio_bytes:
            entry["audio"] = audio_bytes
        history.append(entry)
        st.session_state[chat_key] = history

    if history:
        if st.button("🗑️ Sohbeti temizle", key=f"clear_{company.oid}"):
            st.session_state[chat_key] = []
            st.rerun()


def render_compare_tab(primary: CompanyMatch, primary_disclosures: list[dict], days: int, limit: int) -> None:
    st.markdown("### Şirket karşılaştırma")
    st.caption("Birinci şirket zaten yüklü. İkinci şirketi yaz, AI yan yana karşılaştırsın.")

    other_query = st.text_input(
        "Karşılaştırılacak ikinci şirket",
        placeholder='Örn: "Garanti", "AKBNK", "THYAO"',
        key="compare_query",
    )
    cmp_cols = st.columns(len(EXAMPLE_COMPANIES))
    for col, ex in zip(cmp_cols, EXAMPLE_COMPANIES):
        if col.button(ex, use_container_width=True, key=f"cmp_ex_{ex}"):
            st.session_state["compare_query"] = ex
            other_query = ex

    if not other_query.strip():
        st.info(f"İkinci şirket adı yaz; {primary.name} ile karşılaştırılacak.")
        return

    if st.button("🔀 Karşılaştır", type="primary", key="compare_btn"):
        try:
            with st.spinner(f"{other_query} aranıyor..."):
                other = resolve_company(other_query)
            if other is None:
                st.error("İkinci şirket bulunamadı.")
                return
            remember_search(other_query)
            with st.spinner("İkinci şirketin bildirimleri çekiliyor..."):
                other_disclosures = fetch_disclosures(other.oid, days, limit)
            if not other_disclosures:
                st.warning("İkinci şirket için bildirim bulunamadı.")
                return

            increment_stat("compare_runs")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"#### 🏛️ {primary.name}")
                st.caption(f"{primary.ticker} · {len(primary_disclosures)} bildirim")
                for d in primary_disclosures[:4]:
                    st.markdown(f"- **{d['category']}** · {d['publish_datetime'][:10]} · {d['subject'][:80]}")
            with col_b:
                st.markdown(f"#### 🏛️ {other.name}")
                st.caption(f"{other.ticker} · {len(other_disclosures)} bildirim")
                for d in other_disclosures[:4]:
                    st.markdown(f"- **{d['category']}** · {d['publish_datetime'][:10]} · {d['subject'][:80]}")

            with st.spinner("AI karşılaştırması üretiliyor..."):
                comparison = compare_companies(primary, primary_disclosures, other, other_disclosures)
            st.markdown("---")
            st.markdown(comparison)
        except requests.RequestException as exc:
            st.error(f"KAP verisi alınamadı: {exc}")


def render_pdf_tab() -> None:
    st.markdown("### Kendi PDF'ini sade Türkçe'ye çevir")
    st.caption("KAP dışı belgeleri de sadeleştirebilirsin: yıllık raporlar, mevzuat, sözleşmeler.")

    uploaded = st.file_uploader("PDF yükle", type=["pdf"], key="user_pdf")
    if uploaded is None:
        st.info("Maksimum 20 sayfa okunur. Hassas/gizli belge yükleme.")
        return

    pdf_bytes = uploaded.getvalue()
    if len(pdf_bytes) > 5_000_000:
        st.error("PDF çok büyük (5 MB üstü). Daha küçük bir dosya yükle.")
        return

    with st.spinner("PDF okunuyor..."):
        pdf_text = extract_pdf_bytes_text(pdf_bytes)

    if not pdf_text or pdf_text.startswith("PDF okunamadı"):
        st.error(pdf_text or "PDF metin çıkarılamadı.")
        return

    st.success(f"✅ {len(pdf_text):,} karakter çıkarıldı.")
    with st.expander("Ham metin önizleme"):
        st.text(pdf_text[:2000] + ("..." if len(pdf_text) > 2000 else ""))

    tone = st.selectbox("Anlatım modu", TONE_OPTIONS, key="pdf_tone")
    if st.button("✨ Sadeleştir", type="primary", key="pdf_simplify"):
        with st.spinner("Gemini sadeleştiriyor..."):
            simplified = simplify_pdf_text(pdf_text, tone)
        increment_stat("pdf_simplifications")
        st.markdown(simplified)
        st.download_button(
            "📥 Sade versiyonu indir",
            data=simplified.encode("utf-8"),
            file_name=f"{uploaded.name.rsplit('.', 1)[0]}_sade.md",
            mime="text/markdown",
        )


def render_visual_analysis_tab(tone: str) -> None:
    st.markdown("### Gemini Vision ile grafik analizi")
    st.caption(
        "BIST grafiği, finansal rapor görseli, KAP ekran görüntüsü veya PDF yükle. "
        "Gemini görseli sade Türkçe'ye çevirir."
    )

    uploaded = st.file_uploader(
        "Grafik/görsel/PDF yükle",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key="vision_upload",
    )
    user_note = st.text_area(
        "İstersen bağlam ekle",
        placeholder="Örn: THYAO son 3 aylık fiyat grafiği, hacim çubukları altta görünüyor.",
        key="vision_note",
        height=90,
    )

    if uploaded is None:
        st.info(
            "Demo fikri: Bir BIST fiyat grafiğinin ekran görüntüsünü yükle. "
            "Uygulama grafiği yatırım tavsiyesi vermeden sade dille açıklar."
        )
        st.markdown(
            """
            <div class="source-row">
                <span class="badge badge-info">Multimodal Gemini</span>
                <div class="muted">Metin + görsel + sesli anlatım aynı ürün hikayesinde birleşir.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    file_bytes = uploaded.getvalue()
    mime_type = uploaded.type or "application/octet-stream"

    if len(file_bytes) > 7_000_000:
        st.error("Dosya çok büyük (7 MB üstü). Daha küçük bir görsel veya PDF yükle.")
        return

    if mime_type.startswith("image/"):
        st.image(file_bytes, caption="Yüklenen görsel", use_container_width=True)
    else:
        st.caption(f"Yüklenen dosya: {uploaded.name} ({mime_type})")

    if st.button("Görseli sade Türkçe anlat", type="primary", use_container_width=True):
        with st.spinner("Gemini görseli inceliyor..."):
            result = analyze_visual_document(file_bytes, mime_type, user_note, tone)
        increment_stat("vision_analyses")
        st.markdown(result)

        st.download_button(
            "Görsel analizini Markdown indir",
            data=result.encode("utf-8"),
            file_name="gemini_vision_grafik_analizi.md",
            mime="text/markdown",
            use_container_width=True,
        )

        try:
            audio_mp3 = text_to_speech_mp3(result[:4200])
            st.audio(audio_mp3, format="audio/mp3")
            st.download_button(
                "Görsel analizini MP3 indir",
                data=audio_mp3,
                file_name="gemini_vision_grafik_analizi.mp3",
                mime="audio/mp3",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"Sesli okuma üretilemedi: {exc}")


def render_live_watch(company: CompanyMatch, days: int, limit: int) -> None:
    st.markdown("### 🔔 Canlı izleme")
    st.caption(
        f"{company.name} için KAP'taki son bildirimi kontrol eder. Demo sırasında sekmeden atmayacak şekilde güvenli modda çalışır."
    )

    enabled_key = f"live_{company.oid}"
    seen_key = f"_last_seen_{company.oid}"
    enabled = st.toggle("Canlı izlemeyi aç", key=enabled_key, value=False)
    if not enabled:
        st.info("Anahtarı açınca son KAP bildirimi kaydedilir. Sonra 'Şimdi kontrol et' ile yeni bildirim var mı bakılır.")
        return

    try:
        with st.spinner("KAP son bildirimi kontrol ediliyor..."):
            current = fetch_disclosures(company.oid, days, limit)
    except Exception as exc:
        st.warning(f"KAP'a ulaşılamadı: {exc}")
        return

    if not current:
        st.warning("Bu aralıkta izlenecek KAP bildirimi bulunamadı.")
        return

    latest = current[0]
    latest_index = latest.get("index")
    last_seen = st.session_state.get(seen_key)

    if last_seen is None:
        st.session_state[seen_key] = latest_index
        st.success("Canlı izleme açıldı. Mevcut son bildirim referans olarak kaydedildi.")
    elif str(last_seen) != str(latest_index):
        increment_stat("live_alerts")
        st.session_state[seen_key] = latest_index
        st.toast(f"Yeni KAP bildirimi: {latest['subject'][:80]}")
        st.success(f"Yeni bildirim bulundu: {latest['subject']}")
        st.link_button("KAP'ta aç", latest["url"])
    else:
        st.info("Yeni bildirim yok. Son KAP bildirimi aynı.")

    st.markdown(
        f"""
        <div class="source-row">
            <span class="badge badge-info">Son kontrol</span>
            <div><strong>{escape(str(latest.get("subject", "Bildirim")))}</strong></div>
            <div class="muted">{escape(str(latest.get("publish_datetime", "")))}
            · bildirim no: {escape(str(latest_index))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.link_button("Son bildirimi KAP'ta aç", latest["url"])
    if st.button("Şimdi tekrar kontrol et", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def render_jury_package(company: CompanyMatch, report: dict, disclosures: list[dict]) -> None:
    st.markdown("### Jüri Paketi")
    st.write(
        "Bu bölüm demo videosunda ve başvuru metninde kullanılacak en kısa, en net hikayeyi çıkarır."
    )

    render_visualizations(disclosures)

    col1, col2 = st.columns([1.1, 0.9], gap="large")
    with col1:
        st.markdown("#### Neden güçlü?")
        for title, detail in JURY_POINTS:
            st.markdown(
                f"""
                <div class="source-row">
                    <span class="badge badge-good">{escape(title)}</span>
                    <div class="muted">{escape(detail)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown("#### Kalan eksikler")
        for title, detail in GAP_ITEMS:
            st.markdown(
                f"""
                <div class="source-row">
                    <span class="badge">{escape(title)}</span>
                    <div class="muted">{escape(detail)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("#### 60 saniyelik demo metni")
    st.code(build_demo_script(company, report, disclosures), language="text")

    st.markdown("#### Başvuru özeti")
    st.code(build_submission_summary(company, disclosures), language="text")


def build_demo_script(company: CompanyMatch, report: dict, disclosures: list[dict]) -> str:
    first_subject = disclosures[0]["subject"] if disclosures else "son KAP bildirimi"
    first_plain = ""
    if report.get("items"):
        first_plain = report["items"][0].get("what_happened", "")
    return "\n".join(
        [
            "Merhaba, projemiz Sesli Finansal Okuryazarlık Asistanı.",
            "Problem şu: KAP bildirimleri resmi ve güvenilir ama sıradan vatandaş için zor anlaşılır.",
            f"Örneğin kullanıcı '{company.name}' diyor veya yazıyor.",
            f"Uygulama KAP'tan '{first_subject}' bildirimini buluyor.",
            f"Gemini bunu sade Türkçe'ye çeviriyor: {first_plain}",
            "Sonra metni sesli okuyor, kullanıcı kaynak KAP linkini açabiliyor ve bildirimler hakkında sohbet edebiliyor.",
            "Sistem yatırım tavsiyesi vermez; çıktıdaki tavsiye dilini regex tabanlı güvenlik kalkanı temizler.",
            "Bu sayede yeni yatırımcılar ve yaşlı kullanıcılar finansal bilgiyi daha güvenli okuyabilir.",
        ]
    )


def build_submission_summary(company: CompanyMatch, disclosures: list[dict]) -> str:
    categories = sorted({item["category"] for item in disclosures})
    return "\n".join(
        [
            "Proje adı: Sesli Finansal Okuryazarlık Asistanı",
            "Alan: Yapay zeka ile finans",
            "Problem: KAP bildirimleri güvenilir ama teknik dil yüzünden geniş kitleler tarafından anlaşılamıyor.",
            "Çözüm: Şirket adı veya hisse kodu girildiğinde son KAP bildirimlerini çekip Gemini ile sade Türkçe'ye çeviren, sesli okuyan ve bildirimler üzerinden Q&A sunan asistan.",
            f"Canlı örnek şirket: {company.name}",
            f"İşlenen bildirim türleri: {', '.join(categories) if categories else 'KAP bildirimleri'}",
            "AI kullanımı: Gemini ile sadeleştirme, sesten metne çevirme ve bildirim üstünde RAG-tarzı sohbet.",
            "Sosyal etki: Finansal okuryazarlığı düşük kullanıcıların resmi veriyi daha güvenli anlaması.",
            "Güvenlik: Çıktı yatırım tavsiyesi değildir; tavsiye dili regex tabanlı kalkanla temizlenir; kaynak KAP linkleri gösterilir.",
        ]
    )


def render_sidebar_status(has_key: bool, demo_mode: bool) -> None:
    st.markdown("#### Sistem durumu")
    st.markdown(
        f"""
        <div class="source-row">
            <span class="badge {'badge-warn' if demo_mode else 'badge-good'}">KAP</span>
            <span class="muted">{'Demo veri' if demo_mode else 'Canlı veri kaynağı'}</span>
        </div>
        <div class="source-row">
            <span class="badge {'badge-good' if has_key else ''}">Gemini</span>
            <span class="muted">{'Hazır' if has_key else 'Fallback modda'}</span>
        </div>
        <div class="source-row">
            <span class="badge badge-info">gTTS</span>
            <span class="muted">Türkçe sesli okuma</span>
        </div>
        <div class="source-row">
            <span class="badge badge-good">Güvenlik kalkanı</span>
            <span class="muted">Tavsiye dili regex ile temizlenir</span>
        </div>
        <div class="source-row">
            <span class="badge badge-info">Risk dedektörü</span>
            <span class="muted">Anomali paternlerini yakalar</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stats = get_stats()
    if stats:
        st.markdown("#### Bu oturumda")
        labels = {
            "analyses": "Analiz",
            "chat_questions": "Sohbet sorusu",
            "compare_runs": "Karşılaştırma",
            "pdf_simplifications": "PDF sadeleştirme",
            "live_alerts": "Canlı uyarı",
        }
        for key, label in labels.items():
            if stats.get(key):
                st.markdown(
                    f'<div class="source-row"><span class="badge">{stats[key]}</span>'
                    f'<span class="muted">{label}</span></div>',
                    unsafe_allow_html=True,
                )


def render_high_contrast_css() -> None:
    """Erişilebilirlik için yüksek kontrast modu — WCAG AAA."""
    st.markdown(
        """
        <style>
        :root {
            --ink: #000000 !important;
            --muted: #2a2a2a !important;
            --line: rgba(0, 0, 0, 0.45) !important;
            --paper: rgba(255, 255, 255, 0.95) !important;
            --accent: #003e8a !important;
        }
        .stApp {
            background: #ffffff !important;
        }
        section[data-testid="stSidebar"] { background: #ffffff !important; }
        .panel, .glass, .result-card, .source-row {
            background: #ffffff !important;
            border: 2px solid #000000 !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
        }
        div[data-testid="stButton"] button {
            border: 2px solid #000000 !important;
            background: #ffffff !important;
            font-weight: 700 !important;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: #003e8a !important;
            color: #ffffff !important;
            border-color: #000000 !important;
        }
        .badge { border-width: 2px !important; }
        abbr.gloss { text-decoration-thickness: 2px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_gemini_settings() -> bool:
    st.markdown("#### Gemini API")
    env_key = os.getenv("GEMINI_API_KEY")
    try:
        secrets_key = st.secrets.get("GEMINI_API_KEY", None)
    except Exception:
        secrets_key = None

    if env_key:
        st.success(".env üzerinden Gemini anahtarı bulundu.")
    elif secrets_key:
        st.success("Streamlit secrets üzerinden Gemini anahtarı bulundu.")
    else:
        st.info("Demo için API key'i buraya girebilirsin. Anahtar dosyaya yazılmaz.")

    st.text_input(
        "Geçici Gemini API key",
        type="password",
        key="gemini_api_key_input",
        placeholder="AIza...",
        help="Bu değer sadece bu Streamlit oturumunda tutulur.",
    )

    has_key = bool(get_secret("GEMINI_API_KEY"))
    if st.button("Gemini bağlantısını test et", use_container_width=True):
        ok, message = test_gemini_connection()
        if ok:
            st.success(message)
        else:
            st.error(message)

    return has_key


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    render_styles()

    render_hero()

    with st.sidebar:
        st.header("Ayarlar")
        demo_mode = st.toggle(
            "Demo modu (offline)",
            value=False,
            help="API key veya internet olmadan örnek şirket verisiyle çalışır.",
        )
        high_contrast = st.toggle(
            "♿ Yüksek kontrast (erişilebilirlik)",
            value=False,
            help="WCAG AAA — görme zorluğu çekenler için keskin kontrast.",
        )
        days = st.slider("Kaç günlük KAP bildirimi?", 30, 365, 180, 30)
        limit = st.slider("Kaç bildirim özetlensin?", 1, 8, 4)
        tone = st.selectbox("Anlatım modu", TONE_OPTIONS)
        has_key = render_gemini_settings()
        render_sidebar_status(has_key, demo_mode)

    if high_contrast:
        render_high_contrast_css()

    typed_query = st.text_input(
        "Şirket adı veya hisse kodu",
        placeholder='Örn: İş Bankası, THYAO, ASELS',
        key="company_query",
        label_visibility="collapsed",
    )

    render_search_history()

    with st.expander("🎙️ Mikrofonla söylemek istersen", expanded=False):
        audio_query_holder = st.container()
        audio_value = st.audio_input(" ", label_visibility="collapsed")
    audio_query = ""
    if audio_value is not None and not demo_mode:
        try:
            audio_bytes = audio_value.getvalue()
            mime_type = getattr(audio_value, "type", None) or "audio/wav"
            with st.spinner("Ses kaydı metne çevriliyor..."):
                audio_query = transcribe_company_name(audio_bytes, mime_type)
            if audio_query:
                audio_query_holder.info(f"Duyduğum şirket: **{audio_query}**")
        except Exception as exc:
            audio_query_holder.error(f"Ses tanıma çalışmadı: {exc}")

    query = (typed_query or "").strip() or audio_query.strip()

    btn_col1, btn_col2 = st.columns([1, 3])
    with btn_col1:
        analyze = st.button(
            "Anlat",
            type="primary",
            disabled=not (query or demo_mode),
            use_container_width=True,
        )
    with btn_col2:
        if demo_mode:
            st.caption("Demo modu açık — örnek şirketle çalışır.")
        elif not query:
            st.caption("Bir şirket adı yaz veya yukarıdan örnek seç.")

    if not analyze:
        st.markdown(
            '<div class="footer-note">Bu uygulama yatırım tavsiyesi vermez. '
            'Resmi KAP açıklamalarını anlaşılır hale getirir. '
            'AI çıktısındaki tavsiye dili otomatik temizlenir.</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    if demo_mode:
        company = CompanyMatch(DEMO_COMPANY[0], DEMO_COMPANY[1], DEMO_COMPANY[2], 100.0)
        disclosures = list(DEMO_DISCLOSURES)[:limit]
    else:
        with st.spinner("KAP şirket listesinde aranıyor..."):
            try:
                company = resolve_company(query)
            except requests.RequestException as exc:
                st.error(f"KAP şirket listesi alınamadı: {exc}. Demo modunu deneyebilirsin.")
                st.stop()

        if company is None:
            st.error("Bu şirketi KAP listesinde bulamadım. Hisse kodu ile tekrar dene.")
            st.stop()
        remember_search(query)

        try:
            with st.spinner("Son KAP bildirimleri çekiliyor..."):
                disclosures = fetch_disclosures(company.oid, days, limit)
        except requests.RequestException as exc:
            st.error(f"KAP verisi alınamadı: {exc}")
            st.stop()

        if not disclosures:
            st.warning("KAP bildirimi bulunamadı. Tarih aralığını artır veya farklı şirket dene.")
            st.stop()

    render_company_header(company, len(disclosures), demo_mode)

    with st.spinner("Bildirimler sadeleştiriliyor..."):
        report = analyze_with_gemini(company, disclosures, tone)
    increment_stat("analyses")

    (
        tab_summary,
        tab_audio,
        tab_chat,
        tab_compare,
        tab_pdf,
        tab_vision,
        tab_live,
        tab_sources,
        tab_jury,
    ) = st.tabs(
        [
            "📰 Sade anlatım",
            "🔊 Sesli okuma",
            "💬 AI sohbet",
            "🔀 Karşılaştır",
            "📄 PDF yükle",
            "📈 Grafik analizi",
            "🔔 Canlı izleme",
            "📚 Kaynaklar",
            "🏆 Jüri paketi",
        ]
    )

    with tab_summary:
        render_report(report, company, disclosures)

    with tab_audio:
        st.markdown("### Okunacak metin")
        audio_script = report.get("audio_script") or build_audio_script(report)
        audio_script = apply_safety_guard(audio_script)
        st.write(audio_script)
        try:
            audio_mp3 = text_to_speech_mp3(audio_script[:4500])
            st.audio(audio_mp3, format="audio/mp3")
            safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", company.name)[:40] or "kap"
            st.download_button(
                "MP3 olarak indir",
                data=audio_mp3,
                file_name=f"{safe_name}_kap_ozet.mp3",
                mime="audio/mp3",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"Sesli okuma üretilemedi: {exc}")

    with tab_chat:
        render_chat_tab(company, disclosures)

    with tab_compare:
        render_compare_tab(company, disclosures, days, limit)

    with tab_pdf:
        render_pdf_tab()

    with tab_vision:
        render_visual_analysis_tab(tone)

    with tab_live:
        if demo_mode:
            st.info("Canlı izleme demo modunda kullanılamaz; gerçek KAP'a bağlan.")
        else:
            render_live_watch(company, days, limit)

    with tab_sources:
        st.markdown("### Kaynak KAP bildirimleri")
        render_disclosure_cards(disclosures)

    with tab_jury:
        render_jury_package(company, report, disclosures)


if __name__ == "__main__":
    main()
