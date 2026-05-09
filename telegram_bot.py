"""
Sesli Finansal Okuryazarlık Asistanı — Telegram bot uzantısı.

Aynı KAP + Gemini akışını WhatsApp/Telegram benzeri bir kanaldan kullanılabilir hale
getirir. Streamlit'e bağımlı değildir; mobil kullanıcılar (yaşlılar, mobil-first
kullanıcılar) için ana erişim katmanıdır.

Kurulum:
    pip install python-telegram-bot==21.6

.env dosyasına ekle:
    TELEGRAM_BOT_TOKEN=...
    GEMINI_API_KEY=...

Çalıştır:
    python telegram_bot.py

Bot komutları:
    /start                — karşılama
    /analiz <şirket>      — sade KAP özeti + sesli mesaj
    /sor <şirket>|<soru>  — bildirimler üzerinde Q&A
    /risk <şirket>        — sadece risk dedektörü çıktısı
    /yardim               — komut listesi
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO

import requests
from dotenv import load_dotenv
from gtts import gTTS
from rapidfuzz import fuzz, process

try:
    from google import genai
    from google.genai import types  # noqa: F401
except Exception:
    genai = None
    types = None

try:
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
except Exception as exc:
    raise SystemExit(
        "python-telegram-bot kurulu değil. Çalıştır: pip install python-telegram-bot==21.6"
    ) from exc

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"
KAP_DISCLOSURE_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
KAP_SEARCH_PAGE = "https://www.kap.org.tr/tr/bildirim-sorgu"
KAP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": KAP_SEARCH_PAGE,
}

POPULAR_ALIASES = {
    "is bankasi": ("TÜRKİYE İŞ BANKASI A.Ş.", "ISCTR", "4028e4a140f2ed7201411682b0cb05c6"),
    "isbank": ("TÜRKİYE İŞ BANKASI A.Ş.", "ISCTR", "4028e4a140f2ed7201411682b0cb05c6"),
}

FORBIDDEN_PATTERNS = [
    (re.compile(r"\b(kesinlikle|kesin)\s+(yüksel|düş|art|azal)\w*", re.I), "[bilgi]"),
    (re.compile(r"\b(hisseyi|hisse)\s+(al|sat|tut)\w*\b", re.I), "[bilgi]"),
    (re.compile(r"\bgaranti\s+(kazanç|kar|getiri|yüksel)\w*", re.I), "[bilgi]"),
    (re.compile(r"\b(mutlaka|kesinlikle)\s+(al|sat)\w*\b", re.I), "[bilgi]"),
    (re.compile(r"\btavsiye\s+ed(er|iyor)\w*\b", re.I), "değerlendirilebilir"),
]

ANOMALY_RULES = {
    "geç_bildirim": "KAP'a geç gönderilen bildirim var.",
    "düzeltme": "2+ düzeltme bildirimi — ilk açıklamalar belirsizdi.",
    "yoğun_sermaye": "Kısa sürede 2+ sermaye işlemi.",
    "yoğun_borçlanma": "Kısa sürede 2+ borçlanma bildirimi.",
}

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger("kapbot")

_companies_cache: list[dict] | None = None


@dataclass(frozen=True)
class CompanyMatch:
    name: str
    ticker: str
    oid: str
    score: float


# ---------- Yardımcılar ----------

def normalize_tr(text: str) -> str:
    text = text.strip().lower()
    text = text.translate(str.maketrans("çğıöşüİı", "cgiosuii"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def apply_safety_guard(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern, replacement in FORBIDDEN_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def fetch_companies() -> list[dict]:
    global _companies_cache
    if _companies_cache is not None:
        return _companies_cache

    response = requests.get(KAP_SEARCH_PAGE, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
    response.raise_for_status()

    companies: dict[str, dict] = {}
    for chunk in response.text.split("},{"):
        if "mkkMemberOid" not in chunk or "stockCode" not in chunk:
            continue
        oid_match = re.search(r'mkkMemberOid\\":\\"(?P<value>[0-9a-f]+)\\"', chunk)
        title_match = re.search(r'kapMemberTitle\\":\\"(?P<value>.*?)\\"', chunk)
        stock_match = re.search(r'stockCode\\":\\"(?P<value>.*?)\\"', chunk)
        if not (oid_match and title_match and stock_match):
            continue
        title = title_match.group("value").strip()
        stock = stock_match.group("value").strip()
        oid = oid_match.group("value").strip()
        if not title or not stock or stock == "null":
            continue
        key = normalize_tr(f"{title} {stock}")
        companies[key] = {"name": title, "ticker": stock, "oid": oid, "search": key}

    _companies_cache = list(companies.values())
    return _companies_cache


def resolve_company(query: str) -> CompanyMatch | None:
    norm = normalize_tr(query)
    if not norm:
        return None

    for alias, (name, tickers, oid) in POPULAR_ALIASES.items():
        if alias in norm or norm in alias:
            return CompanyMatch(name, tickers, oid, 100.0)

    companies = fetch_companies()
    upper = query.strip().upper()
    for company in companies:
        codes = [c.strip().upper() for c in company["ticker"].split(",")]
        if upper in codes:
            return CompanyMatch(company["name"], company["ticker"], company["oid"], 100.0)

    choices = {company["search"]: company for company in companies}
    result = process.extractOne(norm, choices.keys(), scorer=fuzz.WRatio, score_cutoff=55)
    if not result:
        return None
    matched_key, score, _ = result
    company = choices[matched_key]
    return CompanyMatch(company["name"], company["ticker"], company["oid"], float(score))


def fetch_disclosures(oid: str, days: int = 90, limit: int = 4) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=days)
    payload = {
        "fromDate": start.isoformat(),
        "toDate": end.isoformat(),
        "mkkMemberOidList": [oid],
        "inactiveMkkMemberOidList": [],
        "disclosureClass": "",
        "subjectList": [],
        "disclosureIndexList": [],
    }
    response = requests.post(KAP_DISCLOSURE_URL, json=payload, headers=KAP_HEADERS, timeout=30)
    response.raise_for_status()
    rows = response.json() if isinstance(response.json(), list) else []

    items = []
    for row in rows[:limit]:
        index = row.get("disclosureIndex")
        items.append(
            {
                "index": index,
                "publish_datetime": row.get("publishDate") or "",
                "subject": row.get("subject") or "",
                "summary": row.get("summary") or "",
                "is_late": bool(row.get("isLate")),
                "is_corrective": bool(row.get("modifyStatus")),
                "has_attachment": bool(row.get("attachmentCount")),
                "url": f"https://www.kap.org.tr/tr/Bildirim/{index}",
            }
        )
    return items


def detect_anomalies(disclosures: list[dict]) -> list[str]:
    flags = []
    if any(d["is_late"] for d in disclosures):
        flags.append("⏰ Geç bildirim: " + ANOMALY_RULES["geç_bildirim"])
    if sum(1 for d in disclosures if d["is_corrective"]) >= 2:
        flags.append("✏️ " + ANOMALY_RULES["düzeltme"])
    cats = " ".join((d["subject"] or "").lower() for d in disclosures)
    if cats.count("sermaye") >= 2:
        flags.append("📊 " + ANOMALY_RULES["yoğun_sermaye"])
    if cats.count("borçlan") + cats.count("tahvil") >= 2:
        flags.append("💸 " + ANOMALY_RULES["yoğun_borçlanma"])
    return flags


def compact_disclosures(disclosures: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"Tarih: {d['publish_datetime']}\nKonu: {d['subject']}\nÖzet: {d['summary']}\nLink: {d['url']}"
        for d in disclosures
    )


def analyze(company: CompanyMatch, disclosures: list[dict]) -> str:
    """Sade Türkçe metin (markdown-lite, Telegram için)."""
    client = get_gemini_client()
    if client is None:
        lines = [f"*{company.name}* için son {len(disclosures)} bildirim:"]
        for d in disclosures:
            lines.append(f"• [{d['publish_datetime'][:10]}] {d['subject'][:120]}")
        lines.append("\n_(Detaylı sadeleştirme için GEMINI_API_KEY gerekli.)_")
        return "\n".join(lines)

    prompt = f"""Türkiye'de finansal okuryazarlığı artıran sesli asistansın.
KAP bildirimlerini ilkokul seviyesinde, sade Türkçe açıkla.
Yatırım tavsiyesi verme. "Al/sat/kesin yükselir" deme.
Telegram için kısa, emoji destekli, max 600 kelime.

Şu yapıyı kullan:
📰 *Genel resim* (1 cümle)

📌 *Bildirimler:*
1. ...
2. ...

⚠️ *Dikkat edilecekler:* (2-3 madde)

🛡️ Bu içerik yatırım tavsiyesi değildir.

Şirket: {company.name} ({company.ticker})

Bildirimler:
{compact_disclosures(disclosures)}
"""
    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return apply_safety_guard((response.text or "").strip())
    except Exception as exc:
        return f"AI hatası: {exc}"


def answer_question(company: CompanyMatch, disclosures: list[dict], question: str) -> str:
    client = get_gemini_client()
    if client is None:
        return "Soru-cevap için GEMINI_API_KEY gerekli."

    prompt = f"""Türk yatırımcılar için finansal okuryazarlık asistanısın.
SADECE aşağıdaki KAP bildirimlerine dayanarak cevap ver.
Bilgi yoksa "Bu bildirimlerde net bilgi yok" de.
Yatırım tavsiyesi verme. Kısa, sade, max 4-5 cümle.

Şirket: {company.name}

Bildirimler:
{compact_disclosures(disclosures)}

Soru: {question}
"""
    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return apply_safety_guard((response.text or "").strip())
    except Exception as exc:
        return f"Hata: {exc}"


def synthesize_voice(text: str) -> bytes:
    """Telegram voice mesajı için Türkçe TTS."""
    fp = BytesIO()
    gTTS(text=text[:3500], lang="tr", slow=False).write_to_fp(fp)
    return fp.getvalue()


# ---------- Telegram handlers ----------

WELCOME = (
    "👋 *KAP Okuryazar Bot*\n\n"
    "Resmi KAP bildirimlerini sade Türkçe'ye çeviren AI asistan.\n\n"
    "*Komutlar:*\n"
    "• `/analiz İş Bankası` — sade özet + sesli mesaj\n"
    "• `/risk THYAO` — risk/anomali taraması\n"
    "• `/sor ASELS | temettü dağıttı mı?` — bildirimler üzerinden Q&A\n"
    "• `/yardim` — bu mesaj\n\n"
    "_Bu bot yatırım tavsiyesi vermez._"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_analiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Kullanım: `/analiz İş Bankası`", parse_mode="Markdown")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        company = await asyncio.to_thread(resolve_company, query)
        if not company:
            await update.message.reply_text("Şirket bulunamadı. Hisse kodu ile dene.")
            return
        disclosures = await asyncio.to_thread(fetch_disclosures, company.oid, 90, 4)
        if not disclosures:
            await update.message.reply_text(f"{company.name} için son 90 günde bildirim yok.")
            return

        summary = await asyncio.to_thread(analyze, company, disclosures)
        await update.message.reply_text(summary, parse_mode="Markdown", disable_web_page_preview=True)

        # Sesli mesaj olarak da yolla
        await update.message.chat.send_action(ChatAction.RECORD_VOICE)
        plain_text = re.sub(r"[*_`#]", "", summary)
        voice = await asyncio.to_thread(synthesize_voice, plain_text)
        await update.message.reply_voice(voice=voice, caption=f"🔊 {company.name}")
    except Exception as exc:
        log.exception("analiz error")
        await update.message.reply_text(f"Hata: {exc}")


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Kullanım: `/risk THYAO`", parse_mode="Markdown")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        company = await asyncio.to_thread(resolve_company, query)
        if not company:
            await update.message.reply_text("Şirket bulunamadı.")
            return
        disclosures = await asyncio.to_thread(fetch_disclosures, company.oid, 180, 8)
        flags = detect_anomalies(disclosures)
        if not flags:
            await update.message.reply_text(
                f"✅ *{company.name}* — risk taraması temiz.\n\n"
                f"Son {len(disclosures)} bildirimde belirgin anomali yok.",
                parse_mode="Markdown",
            )
        else:
            text = f"⚠️ *{company.name}* — {len(flags)} risk sinyali:\n\n" + "\n\n".join(flags)
            await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"Hata: {exc}")


async def cmd_sor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args).strip()
    if "|" not in raw:
        await update.message.reply_text(
            "Kullanım: `/sor İş Bankası | temettü ödedi mi?`",
            parse_mode="Markdown",
        )
        return

    company_query, _, question = raw.partition("|")
    company_query, question = company_query.strip(), question.strip()
    if not company_query or not question:
        await update.message.reply_text("Şirket ve soruyu | ile ayır.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        company = await asyncio.to_thread(resolve_company, company_query)
        if not company:
            await update.message.reply_text("Şirket bulunamadı.")
            return
        disclosures = await asyncio.to_thread(fetch_disclosures, company.oid, 180, 6)
        if not disclosures:
            await update.message.reply_text("Bildirim bulunamadı.")
            return
        answer = await asyncio.to_thread(answer_question, company, disclosures, question)
        await update.message.reply_text(
            f"*{company.name}*\n\n_Soru:_ {question}\n\n{answer}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        await update.message.reply_text(f"Hata: {exc}")


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Komut olmayan mesajları şirket arama olarak yorumla."""
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return
    context.args = text.split()
    await cmd_analiz(update, context)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN eksik. .env dosyasına ekle.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["yardim", "help"], cmd_help))
    app.add_handler(CommandHandler("analiz", cmd_analiz))
    app.add_handler(CommandHandler("risk", cmd_risk))
    app.add_handler(CommandHandler("sor", cmd_sor))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    log.info("Bot başlatılıyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
