# Sesli Finansal Okuryazarlık Asistanı

KAP bildirimlerini sıradan vatandaşın anlayacağı sade Türkçe'ye çeviren AI asistan. Multimodal Gemini + gerçek KAP verisi + Apple Liquid Glass UI.

Kullanıcı şirket adını yazar veya mikrofona söyler. Uygulama KAP'tan son bildirimleri çeker, sade Türkçe'ye dönüştürür, sesli okur, sorularını yanıtlar, anomalileri yakalar ve kullanıcının kendi PDF'ini sadeleştirir.

## Öne Çıkanlar

### Çekirdek
- 🇹🇷 **Yerel problem** — Türk KAP bildirimleri, BIST şirketleri
- 🎙️ **Multimodal giriş** — yazı, ses (Gemini transkripsiyon), PDF ve görsel yükleme
- 📰 **Sade kartlar** — ne oldu, neden önemli, küçük yatırımcı notu, risk
- 🔊 **Sesli okuma + indirme** — gTTS, MP3 olarak indirilebilir
- 🛡️ **Güvenlik kalkanı** — AI çıktısındaki "al/sat/kesin yükselir" gibi tavsiye dili regex ile otomatik temizlenir
- 🎨 **Apple Liquid Glass UI** — backdrop blur, gradient mesh, frosted panels

### Akıllı özellikler
- 💬 **AI Sohbet** — bildirimler üzerinde RAG-tarzı Q&A, sesli cevap modu (full duplex)
- ⚠️ **Risk Dedektörü** — geç bildirim, çoklu düzeltme, yoğun sermaye/borçlanma, gece saati paternleri
- 🔀 **Şirket Karşılaştırma** — iki şirketi yan yana AI ile karşılaştır
- 📄 **PDF Sadeleştirme** — KAP dışı belgeleri (yıllık rapor, mevzuat) sade Türkçe'ye çevir
- 📈 **Gemini Vision Grafik Analizi** — BIST grafiği, finansal rapor görseli veya KAP ekran görüntüsünü sade Türkçe + sesli anlatıma çevir
- 🔔 **Canlı İzleme** — st.fragment ile her 60 saniyede otomatik KAP polling, yeni bildirim toast bildirimi
- 📚 **Glossary Tooltips** — "temettü", "konsolide" gibi terimler otomatik altı çizili, hover'da açıklama
- 🔍 **A/B Karşılaştırma** — her kartın altında "KAP'ın resmi dili ↔ bizim sade dilimiz" yan yana
- 📊 **Otomatik Finansal Sayı Çıkarma** — finansal rapor PDF'lerinden gelir/kâr metric kartları
- 📈 **Görselleştirme** — kategori bar chart + zaman çizelgesi
- 👶 **Çocuk modu** — "10 yaşındaki çocuğa metaforla anlatır gibi" anlatım modu

### Erişilebilirlik & UX
- ♿ **Yüksek kontrast modu** — WCAG AAA, görme zorluğu için
- 🎯 **Demo modu** — API key/internet olmadan tam akış (offline)
- 📊 **Oturum istatistikleri** — kaç analiz, kaç sohbet, kaç uyarı

### Mobil erişim
- 🤖 **Telegram Bot** (`telegram_bot.py`) — `/analiz İş Bankası`, `/risk THYAO`, `/sor ASELS | temettü ödedi mi?` komutları + sesli mesaj cevabı

### Çıktılar
- 📥 **Markdown raporu** indir
- 🎵 **MP3 sesli özet** indir
- 🔧 **Jüri paketi** — güçlü yönler, eksikler, demo metni, başvuru özeti

## Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` dosyasına `GEMINI_API_KEY` (ve opsiyonel `TELEGRAM_BOT_TOKEN`) ekle.

## Streamlit ile Çalıştırma

```powershell
streamlit run app.py
```

Tarayıcıda:

```text
http://localhost:8501
```

## Telegram Bot (opsiyonel)

[BotFather](https://t.me/BotFather)'a `/newbot` ile bot oluştur, token'ı `.env`'e koy:

```powershell
python telegram_bot.py
```

Komutlar:
- `/start` veya `/yardim` — komut listesi
- `/analiz İş Bankası` — sade özet + sesli mesaj
- `/risk THYAO` — risk/anomali taraması
- `/sor ASELS | temettü ödedi mi?` — bildirimler üzerinden Q&A

## Demo Akışı (Streamlit)

1. Sidebar'dan **Demo modu** aç (veya gerçek şirket adı yaz: "İş Bankası", "THYAO").
2. **"Anlat"** butonuna bas → 9 sekme açılır.
3. **📰 Sade anlatım** — bildirim kartları, risk dedektörü, finansal metric'ler, A/B karşılaştırma.
4. **🔊 Sesli okuma** — gTTS okuma + MP3 indir.
5. **💬 AI sohbet** — sorular sor, sesli cevap toggle'ı aç.
6. **🔀 Karşılaştır** — ikinci şirket gir, yan yana karşılaştır.
7. **📄 PDF yükle** — kendi belgeni sadeleştir.
8. **📈 Grafik analizi** — BIST grafiği veya finansal rapor görselini Gemini Vision ile yorumlat.
9. **🔔 Canlı izleme** — yeni bildirim için arka plan polling.
10. **📚 Kaynaklar** — orijinal KAP linkleri.
11. **🏆 Jüri paketi** — grafikler, demo metni, başvuru özeti.

## Mimari

```
[Kullanıcı] → text/voice/PDF/image
     ↓
[Gemini #1] ses → şirket adı (multimodal transcription)
     ↓
[KAP API] → ham bildirim metinleri
     ↓
[Gemini Vision] grafik/PDF görseli → sade finansal okuryazarlık yorumu
     ↓
[Risk Dedektörü] → anomali paternleri (rule-based)
     ↓
[Gemini #2] → ham metin → sade JSON rapor
     ↓
[Güvenlik Kalkanı] → regex post-processing
     ↓
[UI] kartlar + glossary tooltips + A/B karşılaştırma
     ↓
[Gemini #3] → bildirimler üzerinde Q&A (RAG-lite)
     ↓
[gTTS] → sesli cevap (full duplex)
```

## Güvenlik

Çıktılar yatırım tavsiyesi değildir; resmi KAP bildirimlerini anlaşılır hale getirir.

**Çift katmanlı güvenlik:**
1. Gemini'ye prompt'ta "al/sat/kesin yükselir deme" kuralı verilir.
2. Çıktıdan sonra `apply_safety_guard()` regex'leri tavsiye dilini `[bilgi]` ile değiştirir.
