"""
KAP Okuryazar — Telegram bot (FastAPI backend servisleriyle entegre).

Kurulum:
    pip install python-telegram-bot==21.6 gtts

.env dosyasına ekle:
    TELEGRAM_BOT_TOKEN=...
    GEMINI_API_KEY=...

Çalıştır:
    python telegram_bot.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from io import BytesIO
from pathlib import Path

# Repo kökünü path'e ekle — kap_okuryazar modülünü bulabilmek için
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv

load_dotenv()

try:
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
except ImportError as exc:
    raise SystemExit(
        "python-telegram-bot kurulu değil. Çalıştır: pip install python-telegram-bot==21.6"
    ) from exc

try:
    from gtts import gTTS
    _GTTS = True
except ImportError:
    _GTTS = False

# Shared backend services
from app.core.bootstrap import ensure_repo_root_on_path  # noqa: E402
ensure_repo_root_on_path()

from app.services.kap_service import resolve_company, fetch_disclosures  # noqa: E402
from app.services.gemini_service import get_client  # noqa: E402
from app.services.safety_service import clean_advice_language  # noqa: E402
from kap_okuryazar.config import DEFAULT_MODEL  # noqa: E402
from kap_okuryazar.text_utils import detect_anomalies  # noqa: E402

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
log = logging.getLogger("kapbot")

WELCOME = (
    "👋 *KAP Okuryazar Bot*\n\n"
    "Resmi KAP bildirimlerini sade Türkçe'ye çeviren AI asistan.\n\n"
    "*Komutlar:*\n"
    "• `/analiz İş Bankası` — sade özet + sesli mesaj\n"
    "• `/pro THYAO` — kısa profesyonel özet\n"
    "• `/risk THYAO` — risk/anomali taraması\n"
    "• `/sor ASELS | temettü dağıttı mı?` — bildirimler üzerinden Q&A\n"
    "• `/yardim` — bu mesaj\n\n"
    "_Bu bot yatırım tavsiyesi vermez._"
)

MODE_LABELS = {
    "simple": "sade ve anlaşılır Türkçe, yalın cümleler",
    "professional": "kısa ve öz profesyonel dil",
    "technical": "detaylı teknik analiz",
}


def _compact(disclosures: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"Tarih: {d.get('publish_datetime', '')[:16]}\n"
        f"Konu: {d.get('subject', '')}\n"
        f"Özet: {str(d.get('summary', ''))[:400]}\n"
        f"Link: {d.get('url', '')}"
        for d in disclosures
    )


def _analyze(company_name: str, ticker: str, disclosures: list[dict], mode: str = "simple") -> str:
    tone = MODE_LABELS.get(mode, MODE_LABELS["simple"])
    client = get_client()
    if client is None:
        lines = [f"*{company_name}* için son {len(disclosures)} bildirim:"]
        for d in disclosures:
            lines.append(f"• [{str(d.get('publish_datetime', ''))[:10]}] {str(d.get('subject', ''))[:120]}")
        lines.append("\n_(Detaylı sadeleştirme için GEMINI\\_API\\_KEY gerekli.)_")
        return "\n".join(lines)

    prompt = f"""Türkiye'de finansal okuryazarlığı artıran KAP Okuryazar asistanısın.
KAP bildirimlerini Türkçe açıkla. Dil seviyesi: {tone}.
Yatırım tavsiyesi verme. "Al/sat/kesin yükselir" deme.
Telegram için kısa, emoji destekli, max 500 kelime.

Yapı:
📰 *Genel resim* (1-2 cümle)

📌 *Bildirimler:*
Her bildirim için tek madde.

⚠️ *Dikkat:* (varsa 1-2 nokta)

🛡️ Bu içerik yatırım tavsiyesi değildir.

Şirket: {company_name} ({ticker})
Bildirimler:
{_compact(disclosures)}"""

    try:
        resp = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return clean_advice_language((resp.text or "").strip())
    except Exception as exc:
        log.exception("Gemini analyze error")
        return f"AI hatası: {exc}"


def _answer_question(company_name: str, disclosures: list[dict], question: str) -> str:
    client = get_client()
    if client is None:
        return "Soru-cevap için GEMINI\\_API\\_KEY gerekli."

    prompt = f"""Türk yatırımcılar için finansal okuryazarlık asistanısın.
SADECE aşağıdaki KAP bildirimlerine dayanarak cevap ver.
Bilgi yoksa "Bu bildirimlerde net bilgi yok" de.
Yatırım tavsiyesi verme. Kısa, sade, max 4-5 cümle.

Şirket: {company_name}
Bildirimler:
{_compact(disclosures)}

Soru: {question}"""

    try:
        resp = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        return clean_advice_language((resp.text or "").strip())
    except Exception as exc:
        return f"Hata: {exc}"


def _voice_bytes(text: str) -> bytes | None:
    if not _GTTS:
        return None
    try:
        fp = BytesIO()
        gTTS(text=text[:3500], lang="tr", slow=False).write_to_fp(fp)
        return fp.getvalue()
    except Exception:
        log.warning("gTTS failed", exc_info=True)
        return None


async def _do_analiz(update: Update, query: str, mode: str = "simple") -> None:
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        company = await asyncio.to_thread(resolve_company, query)
        if not company:
            await update.message.reply_text("Şirket bulunamadı. Hisse kodu veya tam adıyla dene.")
            return
        disclosures = await asyncio.to_thread(fetch_disclosures, company.oid, 90, 4)
        if not disclosures:
            await update.message.reply_text(f"{company.name} için son 90 günde bildirim bulunamadı.")
            return

        summary = await asyncio.to_thread(_analyze, company.name, company.ticker, disclosures, mode)
        await update.message.reply_text(summary, parse_mode="Markdown", disable_web_page_preview=True)

        if mode == "simple":
            await update.message.chat.send_action(ChatAction.RECORD_VOICE)
            plain = re.sub(r"[*_`#]", "", summary)
            voice = await asyncio.to_thread(_voice_bytes, plain)
            if voice:
                await update.message.reply_voice(voice=voice, caption=f"🔊 {company.name}")
    except Exception as exc:
        log.exception("analiz error")
        await update.message.reply_text(f"Hata: {exc}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_analiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Kullanım: `/analiz İş Bankası`", parse_mode="Markdown")
        return
    await _do_analiz(update, query, mode="simple")


async def cmd_pro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Kullanım: `/pro THYAO`", parse_mode="Markdown")
        return
    await _do_analiz(update, query, mode="professional")


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
                f"✅ *{company.name}* — risk taraması temiz.\n\nSon {len(disclosures)} bildirimde belirgin anomali yok.",
                parse_mode="Markdown",
            )
        else:
            flag_lines = "\n\n".join(f"{icon} *{title}*: {desc}" for icon, title, desc in flags)
            await update.message.reply_text(
                f"⚠️ *{company.name}* — {len(flags)} risk sinyali:\n\n{flag_lines}",
                parse_mode="Markdown",
            )
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
        answer = await asyncio.to_thread(_answer_question, company.name, disclosures, question)
        await update.message.reply_text(
            f"*{company.name}*\n\n_Soru:_ {question}\n\n{answer}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        await update.message.reply_text(f"Hata: {exc}")


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return
    context.args = text.split()
    await cmd_analiz(update, context)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN eksik. .env dosyasına ekle.")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler(["yardim", "help"], cmd_help))
    application.add_handler(CommandHandler("analiz", cmd_analiz))
    application.add_handler(CommandHandler("pro", cmd_pro))
    application.add_handler(CommandHandler("risk", cmd_risk))
    application.add_handler(CommandHandler("sor", cmd_sor))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    log.info("KAP Okuryazar Bot başlatılıyor (model=%s)...", DEFAULT_MODEL)
    application.run_polling()


if __name__ == "__main__":
    main()
