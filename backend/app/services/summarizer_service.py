from __future__ import annotations

from kap_okuryazar.config import DEFAULT_MODEL
from kap_okuryazar.models import CompanyMatch

from app.services.gemini_service import get_client, json_from_text
from app.services.safety_service import clean_advice_language


MODE_LABELS = {
    "simple": "sade ve anlaşılır Türkçe, yalın ve net cümleler",
    "professional": "kısa ve öz profesyonel dil, gerektiğinde finansal terminoloji kullan",
    "technical": "detaylı teknik analiz, rakamları ve yasal referansları dahil et",
}


_MAX_TEXT_PER_DISCLOSURE = 1200
_MAX_TOTAL_PROMPT_CHARS = 18_000


def compact_disclosures(disclosures: list[dict]) -> str:
    chunks = []
    total = 0
    for item in disclosures:
        page_text = str(item.get("page_text") or "")[:_MAX_TEXT_PER_DISCLOSURE]
        chunk = "\n".join(
            [
                f"Bildirim no: {item.get('index', '')}",
                f"Tarih: {item.get('publish_datetime', '')}",
                f"Kategori: {item.get('category', '')}",
                f"Konu: {item.get('subject', '')}",
                f"Kısa özet: {item.get('summary', '')}",
                f"Metin: {page_text}",
                f"Link: {item.get('url', '')}",
            ]
        )
        if total + len(chunk) > _MAX_TOTAL_PROMPT_CHARS:
            break
        chunks.append(chunk)
        total += len(chunk)
    return "\n\n---\n\n".join(chunks)


def fallback_summary(company: CompanyMatch, disclosures: list[dict]) -> dict:
    notifications = []
    for item in disclosures:
        title = item.get("subject") or "KAP bildirimi"
        plain = item.get("summary") or category_explanation(item.get("category", "Diğer"))
        notifications.append(
            {
                "date": str(item.get("publish_datetime", ""))[:10],
                "title": clean_advice_language(title),
                "plainText": clean_advice_language(plain),
                "url": item.get("url"),
                "category": item.get("category"),
            }
        )

    summary = (
        f"{company.name} için {len(disclosures)} resmi KAP bildirimi bulundu. "
        "Bildirimler sadeleştirildi; bu çıktı yalnızca bilgilendirme amaçlıdır."
    )
    if not disclosures:
        summary = f"{company.name} için seçilen aralıkta KAP bildirimi bulunamadı."

    return {"summary": clean_advice_language(summary), "notifications": notifications}


def explain_disclosures(
    company: CompanyMatch,
    disclosures: list[dict],
    mode: str,
    api_key: str | None = None,
) -> dict:
    client = get_client(api_key=api_key)
    if client is None:
        return fallback_summary(company, disclosures)

    tone = MODE_LABELS.get(mode, MODE_LABELS["simple"])
    disclosure_count = len(disclosures)
    prompt = f"""Sen Türkiye'de finansal okuryazarlığı artıran KAP Okuryazar asistanısın.
KAP bildirimlerini sade Türkçe ile açıkla.

Kesin kurallar:
1. Yatırım tavsiyesi verme. "Al", "sat", "tut", "kesin yükselir", "kesin düşer" gibi yönlendirici ifade kullanma.
2. Bilmediğin bir sonucu uydurma; bilgi yoksa bunu belirt.
3. Dil seviyesi: {tone}.
4. Her bildirim için notifications dizisine tam olarak bir giriş ekle ({disclosure_count} bildirim var).
5. Sadece geçerli JSON döndür. Başına veya sonuna hiçbir açıklama, markdown veya kod bloğu ekleme.

Yanıt formatı (bu şemayı TAM olarak uygula):
{{
  "summary": "Tüm bildirimlerin {disclosure_count}-5 cümlelik genel sade özeti",
  "notifications": [
    {{
      "date": "YYYY-MM-DD",
      "title": "kısa bildirim başlığı",
      "plainText": "bu bildirimin sade açıklaması, 1-3 cümle",
      "url": "KAP bildirimi tam URL",
      "category": "bildirim kategorisi"
    }}
  ]
}}

Şirket: {company.name}
Hisse kodu: {company.ticker}

KAP bildirimleri:
{compact_disclosures(disclosures)}"""
    try:
        response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        data = json_from_text(response.text or "")
        return normalize_summary(data, company, disclosures)
    except Exception:
        return fallback_summary(company, disclosures)


def normalize_summary(data: dict, company: CompanyMatch, disclosures: list[dict]) -> dict:
    fallback = fallback_summary(company, disclosures)
    if not isinstance(data, dict):
        return fallback

    summary = clean_advice_language(str(data.get("summary") or fallback["summary"]))
    raw_items = data.get("notifications")
    if not isinstance(raw_items, list) or not raw_items:
        return {"summary": summary, "notifications": fallback["notifications"]}

    notifications = []
    for idx, item in enumerate(raw_items[: len(disclosures) or 10]):
        if not isinstance(item, dict):
            continue
        source = disclosures[idx] if idx < len(disclosures) else {}
        notifications.append(
            {
                "date": str(item.get("date") or source.get("publish_datetime", ""))[:10],
                "title": clean_advice_language(str(item.get("title") or source.get("subject") or "")),
                "plainText": clean_advice_language(str(item.get("plainText") or source.get("summary") or "")),
                "url": item.get("url") or source.get("url"),
                "category": item.get("category") or source.get("category"),
            }
        )

    return {"summary": summary, "notifications": notifications or fallback["notifications"]}


def category_explanation(category: str) -> str:
    explanations = {
        "Finansal Rapor": "Şirket gelir, gider, borç ve kâr durumuyla ilgili bilgi paylaştı.",
        "Temettü": "Şirket ortaklara kâr payı dağıtımıyla ilgili bilgi verdi.",
        "Genel Kurul": "Şirket ortaklarının karar alacağı toplantıyla ilgili bilgi verdi.",
        "Sermaye İşlemi": "Şirketin sermaye veya hisse yapısıyla ilgili bir gelişme var.",
        "Özel Durum": "Şirket yatırımcıları ilgilendirebilecek özel bir gelişme duyurdu.",
        "Borçlanma": "Şirket finansman için borçlanma aracı kullanabileceğini duyurdu.",
        "Yönetim": "Şirketin yönetim yapısıyla ilgili bir gelişme var.",
        "Sözleşme/İhale": "Şirket yeni iş, proje veya siparişle ilgili bilgi verdi.",
    }
    return explanations.get(category, "Şirket kamuya duyurması gereken resmi bir gelişme paylaştı.")
