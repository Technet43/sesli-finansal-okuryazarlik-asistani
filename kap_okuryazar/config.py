from __future__ import annotations

import re

APP_TITLE = "Sesli Finansal Okuryazarlık Asistanı"
DEFAULT_MODEL = "gemini-2.5-flash"

KAP_DISCLOSURE_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
KAP_SEARCH_PAGE = "https://www.kap.org.tr/tr/bildirim-sorgu"
KAP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": KAP_SEARCH_PAGE,
}

POPULAR_COMPANY_ALIASES = {
    "is bankasi": (
        "TÜRKİYE İŞ BANKASI A.Ş.",
        "ISATR, ISBTR, ISCTR, ISKUR, TIB",
        "4028e4a140f2ed7201411682b0cb05c6",
    ),
    "turkiye is bankasi": (
        "TÜRKİYE İŞ BANKASI A.Ş.",
        "ISATR, ISBTR, ISCTR, ISKUR, TIB",
        "4028e4a140f2ed7201411682b0cb05c6",
    ),
    "isbank": (
        "TÜRKİYE İŞ BANKASI A.Ş.",
        "ISATR, ISBTR, ISCTR, ISKUR, TIB",
        "4028e4a140f2ed7201411682b0cb05c6",
    ),
    "halkbank": (
        "TÜRKİYE HALK BANKASI A.Ş.",
        "HALKB, THL",
        "1DE05DAA82C3073AE0530A4A622A2EBD",
    ),
    "halk bankasi": (
        "TÜRKİYE HALK BANKASI A.Ş.",
        "HALKB, THL",
        "1DE05DAA82C3073AE0530A4A622A2EBD",
    ),
    "turkiye halk bankasi": (
        "TÜRKİYE HALK BANKASI A.Ş.",
        "HALKB, THL",
        "1DE05DAA82C3073AE0530A4A622A2EBD",
    ),
}

DISCLOSURE_TYPES = [
    ("Finansal Rapor", ["finansal rapor", "bilanço", "gelir tablosu", "kar veya zarar"]),
    ("Temettü", ["kar payı", "temettü", "nakit kar payı"]),
    ("Genel Kurul", ["genel kurul"]),
    ("Sermaye İşlemi", ["sermaye artırımı", "sermaye azaltımı", "bedelli", "bedelsiz"]),
    ("Özel Durum", ["özel durum", "oda", "önemli nitelikte"]),
    ("Borçlanma", ["borçlanma", "tahvil", "bono", "kira sertifikası"]),
    ("Yönetim", ["yönetim kurulu", "komite", "üst yönetim", "atama"]),
    ("Sözleşme/İhale", ["ihale", "sözleşme", "sipariş", "proje"]),
]

EXAMPLE_COMPANIES = ["İş Bankası", "Halkbank", "THYAO", "ASELS", "GARAN"]

JURY_POINTS = [
    ("Yerel problem", "Türkiye'deki KAP bildirimlerini sadeleştiriyor."),
    ("Sosyal etki", "Yeni yatırımcılar ve yaşlı kullanıcılar için erişilebilirlik sağlıyor."),
    ("Multimodal", "Yazı, ses girişi ve sesli okuma aynı akışta."),
    ("AI kullanımı", "Gemini ile sadeleştirme ve ses kaydından şirket adı çıkarma."),
    ("Gerçek veri", "KAP kaynak linkleriyle doğrulanabilir çıktı."),
    ("Sohbet", "Kullanıcı bildirimler üzerinden Gemini'ye soru sorabilir."),
    ("Güvenlik kalkanı", "Tavsiye dilini regex ile temizleyen otomatik kontrol."),
]

GAP_ITEMS = [
    ("Doğal Türkçe ses", "gTTS çalışıyor ama jüri demosu için daha doğal bir TTS kaliteyi artırır."),
    ("Finansal tablo okuma", "PDF içindeki sayısal tabloları daha derin yorumlamak ikinci faz işi."),
    ("Kişiselleştirme", "Kullanıcının bilgi seviyesine göre anlatımı otomatik ayarlamak eklenebilir."),
    ("Mobil paketleme", "Streamlit demo için iyi; gerçek ürün için PWA veya mobil uygulama gerekir."),
    ("Uyarı/uyum katmanı", "Yatırım tavsiyesi riskini azaltmak için daha sert kural testi eklenebilir."),
]

FINANCIAL_NUMBER_PATTERNS = [
    (
        "Net Dönem Kârı",
        re.compile(
            r"net\s+(?:dönem\s+)?kar(?:ı|i)\s*[:\-]?\s*(?P<amount>[0-9][0-9\.,]*)\s*(?P<scale>milyar|milyon|bin)?\s*(?P<currency>tl|tl\.|₺)?",
            re.I,
        ),
    ),
    (
        "Hasılat / Satış",
        re.compile(
            r"(?:hasılat|satış\s+gelir(?:i|leri)?|gelir(?:ler)?)\s*[:\-]?\s*(?P<amount>[0-9][0-9\.,]*)\s*(?P<scale>milyar|milyon|bin)?\s*(?P<currency>tl|tl\.|₺)?",
            re.I,
        ),
    ),
    (
        "Faaliyet Kârı",
        re.compile(
            r"(?:esas\s+)?faaliyet\s+kar(?:ı|i)\s*[:\-]?\s*(?P<amount>[0-9][0-9\.,]*)\s*(?P<scale>milyar|milyon|bin)?\s*(?P<currency>tl|tl\.|₺)?",
            re.I,
        ),
    ),
]

GLOSSARY = {
    "temettü": "Şirketin kazandığı paranın bir kısmını ortaklarına dağıtması.",
    "kar payı": "Temettü ile aynı: ortaklara dağıtılan pay.",
    "konsolide": "Ana şirket + bağlı tüm şirketlerin birleşik hesabı.",
    "bilanço": "Şirketin sahip olduğu varlıklar, borçlar ve özkaynakların özeti.",
    "hasılat": "Şirketin sattığı mal/hizmetten elde ettiği toplam gelir.",
    "net dönem karı": "Tüm gider ve vergiler düştükten sonra şirketin elinde kalan kar.",
    "faaliyet karı": "Şirketin esas işinden elde ettiği kar (yatırım/borç hariç).",
    "kap": "Kamuyu Aydınlatma Platformu; borsadaki şirketlerin resmi açıklama yeri.",
    "bist": "Borsa İstanbul; Türkiye'nin tek hisse senedi borsası.",
    "sermaye artırımı": "Şirketin hisse sayısını veya değerini artırması.",
    "bedelli": "Sermaye artırımı için ortaklardan para istenmesi.",
    "bedelsiz": "Şirketin kendi kaynaklarından ücretsiz hisse dağıtması.",
    "ihraç": "Şirketin yeni hisse veya tahvil çıkarması.",
    "tahvil": "Şirketin borçlanmak için çıkardığı, faiz ödediği menkul kıymet.",
    "genel kurul": "Şirket ortaklarının toplanıp önemli kararlar aldığı yıllık toplantı.",
    "yönetim kurulu": "Şirketi yöneten, ortaklar tarafından seçilen kurul.",
    "özkaynak": "Şirketin kendi parası; borç olmayan kısım.",
    "borçlanma": "Şirketin para bulmak için tahvil/bono ile borç alması.",
    "kira sertifikası": "Faizsiz finansman sağlayan, kiraya dayalı sukuk türü.",
    "halka arz": "Şirketin ilk kez hisselerini halka açıp borsaya çıkması.",
    "çağrı": "Bir hissedarın diğer ortaklara hisse satın alma teklifi yapması.",
    "fiili dolaşım": "Borsada serbest alınıp satılabilen hisse oranı.",
    "ödenmiş sermaye": "Şirkete fiilen yatırılmış olan sermaye miktarı.",
    "esas sermaye": "Şirketin ana sözleşmesinde belirlenmiş sermaye.",
}

ANOMALY_RULES = {
    "geç_bildirim": "Bildirim KAP'a geç gönderilmiş; düzenleyici sürelere uymamış olabilir.",
    "düzeltme": "Aynı şirket için 2+ düzeltme bildirimi var; ilk açıklamalar belirsizdi.",
    "yoğun_sermaye": "Kısa sürede 2+ sermaye işlemi var; ortaklık yapısı hızla değişiyor.",
    "yoğun_borçlanma": "Kısa sürede 2+ borçlanma bildirimi var; nakit akış baskısı sinyali.",
    "ek_eksik": "Önemli bildirimde ek dosya yok; detay kısıtlı.",
}

TONE_OPTIONS = [
    "anne-babaya anlatır gibi sade",
    "yeni yatırımcıya sakin ve öğretici",
    "çok kısa radyo anonsu gibi",
    "10 yaşındaki çocuğa metaforla anlatır gibi",
    "finans öğrencisine ders niteliğinde",
]

