from __future__ import annotations

from kap_okuryazar.models import CompanyMatch

from app.services.ai_provider_service import AIProviderError, generate_text
from app.services.gemini_service import json_from_text
from app.services.safety_service import clean_advice_language


MODE_LABELS = {
    "simple": "sade ve anlaşılır Türkçe, yalın ve net cümleler",
    "professional": "kısa ve öz profesyonel dil, gerektiğinde finansal terminoloji kullan",
    "technical": "detaylı teknik analiz, rakamları ve yasal referansları dahil et",
}


_MAX_TEXT_PER_DISCLOSURE = 1200
_MAX_REPORT_TEXT_PER_DISCLOSURE = 6000
_MAX_TOTAL_PROMPT_CHARS = 18_000


def compact_disclosures(disclosures: list[dict]) -> str:
    chunks = []
    total = 0
    for item in disclosures:
        page_text = str(item.get("page_text") or "")[:_MAX_TEXT_PER_DISCLOSURE]
        report_text = str(item.get("report_text") or "")[:_MAX_REPORT_TEXT_PER_DISCLOSURE]
        if not report_text and item.get("has_attachment"):
            report_text = (
                "Bu raporun ek içeriği sistem tarafından okunamadığı için yalnızca KAP bildirimi üzerinden yorum yapabiliyorum."
            )
        chunk = "\n".join(
            [
                f"Bildirim no: {item.get('index', '')}",
                f"Tarih: {item.get('publish_datetime', '')}",
                f"Kategori: {item.get('category', '')}",
                f"Konu: {item.get('subject', '')}",
                f"Kısa özet: {item.get('summary', '')}",
                f"Metin: {page_text}",
                f"Rapor eki içeriği: {report_text}",
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
                "reportText": item.get("report_text") or "",
                "reportTextSource": item.get("report_text_source") or "",
                "reportTextError": item.get("report_text_error") or "",
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
    tone = MODE_LABELS.get(mode, MODE_LABELS["simple"])
    disclosure_count = len(disclosures)
    prompt = f"""Sen Türkiye'de finansal okuryazarlığı artıran KAP Okuryazar asistanısın.
KAP bildirimlerini, finansal raporları ve şirket açıklamalarını yatırım tavsiyesi vermeden sade Türkçe ile açıkla.

Kesin kurallar:
1. Yatırım tavsiyesi verme. "Al", "sat", "tut", "kesin yükselir", "kesin düşer" gibi yönlendirici ifade kullanma.
2. İçerikte olmayan finansal veri uydurma; bilgi yoksa bunu açıkça belirt.
3. Dil seviyesi: {tone}.
4. Her bildirim için notifications dizisine tam olarak bir giriş ekle ({disclosure_count} bildirim var).
5. Sadece geçerli JSON döndür. Başına veya sonuna hiçbir açıklama, markdown veya kod bloğu ekleme.
6. HTML etiketi kullanma.
7. Sayısal veri yoksa hesaplama yapma.
8. Formül, oran veya hesap gerekiyorsa LaTeX kullan; formülü ayrı satırda yaz.
9. Uzun paragraf yazma; kısa cümleler ve kısa bullet point mantığıyla yaz.
10. Bildirim sadece "finansal rapor yayımlandı" türündeyse bunun tek başına iyi veya kötü haber olmadığını belirt.
11. Summary genelde 120-220 Türkçe kelime arasında olsun.
12. Her Markdown bölümü en fazla 2 kısa cümle içersin.
13. Bullet listeler en fazla 3 madde içersin ve maddeler arasında boş satır bırakma.

Yanıt formatı (bu şemayı TAM olarak uygula):
{{
  "summary": "Tüm bildirimlerin 120-220 kelimelik kısa Markdown özeti. Temiz ## başlıkları, en fazla 2 kısa cümlelik bölümler ve gerekiyorsa en fazla 3 bullet kullan.",
  "notifications": [
    {{
      "date": "YYYY-MM-DD",
      "title": "kısa bildirim başlığı",
      "plainText": "bu bildirimin sade açıklaması. Uzun paragraf yazma; en fazla 2 kısa cümle veya en fazla 3 kısa bullet kullan.",
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
        text = generate_text(prompt, api_key=api_key, json_mode=True)
        data = json_from_text(text)
        return normalize_summary(data, company, disclosures)
    except AIProviderError:
        raise
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
                "reportText": source.get("report_text") or "",
                "reportTextSource": source.get("report_text_source") or "",
                "reportTextError": source.get("report_text_error") or "",
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
