from __future__ import annotations

from kap_okuryazar.config import DEFAULT_MODEL
from kap_okuryazar.models import CompanyMatch

from app.services.gemini_service import get_client, json_from_text
from app.services.safety_service import clean_advice_language


MODE_LABELS = {
    "simple": "anne-babaya anlatır gibi sade",
    "professional": "kısa profesyonel özet",
    "technical": "detaylı teknik açıklama ama yatırım tavsiyesi vermeden",
}


def compact_disclosures(disclosures: list[dict]) -> str:
    chunks = []
    for item in disclosures:
        chunks.append(
            "\n".join(
                [
                    f"Bildirim no: {item.get('index', '')}",
                    f"Tarih: {item.get('publish_datetime', '')}",
                    f"Kategori: {item.get('category', '')}",
                    f"Konu: {item.get('subject', '')}",
                    f"Kısa özet: {item.get('summary', '')}",
                    f"Metin: {str(item.get('page_text', ''))[:1300]}",
                    f"Link: {item.get('url', '')}",
                ]
            )
        )
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
            }
        )

    summary = (
        f"{company.name} için {len(disclosures)} resmi KAP bildirimi bulundu. "
        "Bildirimler sadeleştirildi; bu çıktı yalnızca bilgilendirme amaçlıdır."
    )
    if not disclosures:
        summary = f"{company.name} için seçilen aralıkta KAP bildirimi bulunamadı."

    return {"summary": clean_advice_language(summary), "notifications": notifications}


def explain_disclosures(company: CompanyMatch, disclosures: list[dict], mode: str) -> dict:
    client = get_client()
    if client is None:
        return fallback_summary(company, disclosures)

    tone = MODE_LABELS.get(mode, MODE_LABELS["simple"])
    prompt = f"""
Sen Türkiye'de finansal okuryazarlığı artıran KAP Okuryazar asistanısın.
KAP bildirimlerini sade Türkçe ile açıkla.

Kesin kurallar:
- Yatırım tavsiyesi verme.
- "Al", "sat", "tut", "kesin yükselir", "kesin düşer" deme.
- Bilmediğin sonucu uydurma.
- Dil seviyesi: {tone}
- Sadece geçerli JSON döndür. Markdown kullanma.

JSON şeması:
{{
  "summary": "genel sade açıklama",
  "notifications": [
    {{
      "date": "YYYY-MM-DD",
      "title": "bildirim başlığı",
      "plainText": "sade açıklama"
    }}
  ]
}}

Şirket: {company.name}
Hisse kodu: {company.ticker}

KAP bildirimleri:
{compact_disclosures(disclosures)}
"""
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
