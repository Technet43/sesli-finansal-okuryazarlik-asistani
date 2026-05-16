<div align="center">

# 🇹🇷 KAP Okuryazar

### Sesli Finansal Okuryazarlık Asistanı

**KAP bildirimlerini sıradan vatandaşın anlayacağı sade Türkçe'ye çeviren, finansal tabloları yapay zekâya okutturan ve sesle etkileşim kuran bir okuryazarlık asistanı.**

[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-V3-1E40AF)](https://deepseek.com/)

</div>

---

## 🚀 Hackathon Özeti

**KAP Okuryazar**, halka açık şirketlerin KAP bildirimlerini canlı KAP verisinden çekip sade Türkçe ile açıklar, önemli finansal tablo satırlarını ayıklar, kullanıcının sesli/yazılı sorularına yatırım tavsiyesi vermeden cevap verir.

| Jürinin bakacağı nokta | Bu projede karşılığı |
|---|---|
| Gerçek problem | KAP dili yeni yatırımcılar ve finans bilgisi sınırlı kullanıcılar için zor |
| Gerçek veri | Canlı KAP API, bildirim sayfaları, PDF/HTML/XML ekleri |
| AI katkısı | Gemini/DeepSeek ile sadeleştirme, çapraz referanslı chat, Gemini STT/TTS |
| Özgün teknik taraf | KAP HTML/XBRL tablolarından yapısal finansal satır çıkarımı |
| Güvenlik | Yatırım tavsiyesi yasağı, sayı uydurmama kuralı, regex safety katmanı |
| Kullanılabilirlik | Mikrofon, sesli okuma, anlatım modu, koyu mod, yüksek kontrast, karşılaştırma |

## 🖼️ Demo Ekranları

### Sesli arama ve ana ekran

![KAP Okuryazar ana ekranında Ziraat Bankası araması ve mikrofonla dinleme durumu](docs/screenshots/01-home-voice-input.png)

### Anlatım modu seçimi

![Sade, profesyonel ve detaylı teknik analiz anlatım modları](docs/screenshots/02-explanation-mode.png)

### KAP özeti, anomali ve finansal veriler

![Ziraat Bankası KAP özeti, eksik ek dosya uyarısı ve finansal veriler paneli](docs/screenshots/03-results-financial-summary.png)

### Bağlamlı soru-cevap

![Ziraat Bankası bildirimleri hakkında bağlamlı finansal okuryazarlık sohbeti](docs/screenshots/04-contextual-chat.png)

### İki şirket karşılaştırma

![Ziraat Bankası ve Halkbank KAP bildirimlerinin karşılaştırılması](docs/screenshots/05-company-comparison.png)

---

## 🎯 Problem

KAP (Kamuyu Aydınlatma Platformu) Türkiye'nin tüm halka açık şirketlerinin resmî finansal bildirimlerini yayınladığı zorunlu kaynaktır. Ancak:

- 📚 Bildirimler **finans-hukuk dili** ile yazılır; sıradan vatandaş kavrayamaz.
- 📊 Finansal tablolar **XBRL etiketli HTML tabloları** içinde saklıdır; PDF okuyucular yapısını kaybeder.
- ⏱️ Yeni yatırımcı / yaşlı kullanıcı / finans bilgisi sınırlı vatandaşlar **ekonomistten yorum bekler.**
- 🧱 Hâlihazırdaki AI asistanları KAP'ı doğrudan okumaz, hallüsinasyon yapar.

> **Sonuç:** Sermaye piyasalarına erişim bir bilgi asimetrisine takılıyor.

## 💡 Çözüm

**KAP Okuryazar**, bu asimetriyi kapatır:

1. Kullanıcı şirket adını yazar **veya mikrofona söyler.**
2. Sistem **canlı KAP API'sinden** son bildirimleri çeker.
3. Bildirim HTML'inden **finansal tablo satırları** (Nakit, Varlıklar, Özkaynak, Net Kâr, Faiz vb.) **yapısal şekilde çıkarılır** — XBRL etiketleri ve bilingual etiketler temizlenir.
4. Gemini/DeepSeek modeli bu yapısal veriyi **çapraz referanslı, dönem kıyaslamalı, sayısal** ve eğitici bir Türkçe sadeleştirmeye dönüştürür.
5. Kullanıcı sonuca **konuşma diliyle soru sorabilir**; AI birden fazla bildirimi birleştirerek cevaplar.
6. Kullanıcı anlatımı **sade ve anlaşılır**, **profesyonel özet** veya **detaylı teknik analiz** modunda alabilir.
7. Tüm metin **Gemini Native TTS** ile sesli okunur.

> 🛡️ **Yatırım tavsiyesi vermez.** Resmî açıklamayı sadeleştirir; sayıyı uydurmaz; "al/sat" dilini regex tabanlı bir safety katmanı temizler.

---

## ✨ Öne Çıkan Özellikler

### 🧩 KAP HTML Finansal Tablo Çıkarımı (Bu Projeye Özgü)

KAP'ın finansal disclosure sayfalarındaki tablolar, ilk hücrede XBRL etiketi (`ifrs-full_CashAndCashEquivalents|`), sonraki hücrelerde bilingual Türkçe/İngilizce etiketler, son hücrelerde ise sayısal değerler içerir. Standart `get_text()` bu yapıyı düzleştirip değerleri etiketten koparır.

Bizim çözümümüz:

- 12 öncelikli finansal kalem için **regex + Türkçe normalize** ile satır tespiti
- **Sayısal hücre tanıma** (`_NUMERIC_CELL_RE`): XBRL etiketleri ve bilingual etiketler ayıklanır, sadece gerçek rakamlar kalır
- Sonuç: Cari dönem + önceki dönem + konsolide/bireysel ayrımları korunarak **`{label, values[]}` tablosu**

```python
# Örnek çıktı (T.C. Ziraat Bankası 31.03.2026)
{"label": "Nakit ve Nakit Benzerleri",
 "values": ["610.862.836", "1.159.207.336", "1.770.070.172", "829.612.210"]}
{"label": "Özkaynaklar",
 "values": ["762.192.002", "-12.798.125", "749.393.877", "722.265.964"]}
{"label": "Net Dönem Kârı/Zararı",
 "values": ["50.957.673", "0", "50.957.673", "179.645.756"]}
```

### 🔀 Çapraz Referanslı AI Chat

Kullanıcı "**sorumluluk beyanındaki değerleri verir misin?**" diye sorduğunda:

- ❌ Eski davranış: "Bu bildirimde sayısal değer yoktur." (yüzeysel)
- ✅ Yeni davranış: "Sorumluluk beyanı yalnızca yönetim onayını içerir. **Ancak aynı dönem Konsolide Finansal Rapor'da** Nakit ve Nakit Benzerleri **610.862.836 bin TL** (önceki: 1.159.207.336 bin TL, **%47,3 azalış**), Özkaynaklar **762.192.002 bin TL** olarak raporlandı."

Bağlama gönderilen veri:

- Tüm bildirimlerden derlenmiş **"Anahtar Finansal Değerler"** özet bloğu
- 6 bildirime ait yapısal verisi + 4000 char ham rapor metni
- AI prompt'u **180–350 kelime analitik cevap + dönem kıyası** ister

### 🗣️ Multimodal Etkileşim

| Mod | Teknoloji | Notlar |
|---|---|---|
| Sesli giriş | Gemini Native Audio (`/api/transcribe/audio`) | Türkçe kelimesi kelimesine transkripsiyon |
| Sesli çıkış | Gemini TTS (`Aoede` ses) | Sade, doğal Türkçe okuma |
| Anlatım seviyesi | Prompt mode (`simple`, `professional`, `technical`) | Kullanıcı seviyesine göre cevap tonu |
| Markdown render | `react-markdown` + `remark-gfm` | Tablolar, başlıklar, listeler |
| LaTeX render | `remark-math` + `rehype-katex` | Finansal formüller |
| Streaming chat | Server-Sent Events | Token bazlı akış |

### 🛡️ Güvenlik Katmanı

- `safety_service.clean_advice_language` — "al, sat, kesin yükselir" gibi yönlendirici ifadeleri regex ile temizler
- Rate-limit (`/api/explain`, chat, TTS, STT ve admin endpointleri)
- API anahtarı **frontend'e gömülmez**; gerekirse `X-Gemini-Api-Key` header'ı ile per-request bypass
- Açık admin endpoint yok: `/api/cache/clear` için `ADMIN_API_TOKEN` gerekir
- Proxy IP header'ları yalnızca `TRUST_PROXY_HEADERS=true` ise kullanılır; böylece rate-limit kolayca bypass edilemez
- KAP'a `User-Agent`, attachment/audio ve JSON body boyut limitleri, zaman aşımı (15 sn)
- Frontend ve backend güvenlik header'ları: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`

### 📊 "Finansal Veriler" Görsel Paneli

Sonuç ekranında, finansal rapor bildiriminin çıkarılan tablosu **`Kalem × Dönem` matrisi** olarak gösterilir. Tablodaki sütun sırası bildirimdeki dönem sırasını birebir yansıtır (cari → önceki, konsolide → bireysel).

### 🎨 Apple-style Liquid Glass UI

- Frosted glass paneller, iridescent (mor / cyan / pembe) glow
- Karanlık mod, yüksek kontrast modu (a11y)
- shadcn/Radix UI tabanlı erişilebilir bileşenler
- `localStorage` ile geçmiş aramalar
- Mobil-uyumlu responsive grid
- Karşılaştırma görünümüyle iki şirketin KAP özetlerini yan yana okuma

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│  Kullanıcı (Web / Mobil / Telegram)                             │
└────────────────┬────────────────────────────────────────────────┘
                 │ HTTPS / SSE
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 15 Frontend (React 19 + TS + Tailwind + Radix)         │
│  - Hero Search • Results Panel • Finansal Veriler Tablosu       │
│  - ChatPanel (cross-reference context) • Comparison Panel       │
│  - Web Speech API + Gemini TTS köprüsü                          │
└────────────────┬────────────────────────────────────────────────┘
                 │ REST + SSE  (X-Gemini-Api-Key opsiyonel header)
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python 3.11+, uvicorn, gzip, CORS)            │
│  ┌─────────────────────┐   ┌────────────────────────┐           │
│  │  KAP Service        │   │  AI Provider Service   │           │
│  │  ─ Fuzzy company    │   │  ─ Gemini 2.5 Flash    │           │
│  │    matching         │   │  ─ DeepSeek V3         │           │
│  │  ─ HTML table       │   │  ─ Streaming bridge    │           │
│  │    extraction       │   │  ─ JSON-mode safe      │           │
│  │  ─ PDF/XBRL parse   │   │    parsing             │           │
│  └──────────┬──────────┘   └──────────┬─────────────┘           │
│             │                          │                         │
│  ┌──────────▼──────────────────────────▼─────────────┐          │
│  │  Summarizer + Safety + Anomaly Detection         │          │
│  │  ─ compact_disclosures (prompt budget mgmt)      │          │
│  │  ─ clean_advice_language (regex hard-stop)       │          │
│  │  ─ detect_anomalies (late filing, missing attach)│          │
│  └────────────────────────────────────────────────────┘         │
└────────────────┬────────────────────────────────────────────────┘
                 │ HTTPS
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  KAP API (kap.org.tr)         Gemini API / DeepSeek API         │
│  - Disclosure search          - Sadeleştirme + chat             │
│  - HTML page (XBRL tables)    - TTS (Aoede voice)               │
│  - PDF attachments            - STT (Native Audio)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧰 Teknoloji Yığını

### Backend

| Bileşen | Sürüm | Görev |
|---|---|---|
| **Python** | 3.11+ | Çekirdek dil |
| **FastAPI** | 0.115 | REST API + SSE |
| **uvicorn** | 0.30+ | ASGI server |
| **Pydantic** | v2 | Şema doğrulama |
| **google-genai** | 1.0+ | Gemini SDK |
| **BeautifulSoup4** | 4.12+ | HTML parse |
| **pypdf** | 6.0+ | PDF extraction |
| **rapidfuzz** | 3.9+ | Şirket adı fuzzy match |
| **requests** | 2.32+ | KAP HTTP istemcisi |

### Frontend

| Bileşen | Sürüm | Görev |
|---|---|---|
| **Next.js** | 15 | App Router, SSR |
| **React** | 19 | UI |
| **TypeScript** | 5.7 | Tip güvenliği |
| **Tailwind CSS** | 3.4 | Utility-first styling |
| **Radix UI** | latest | Erişilebilir primitive'ler |
| **lucide-react** | 0.468 | Icon set |
| **react-markdown** | 10 | Markdown render |
| **rehype-katex** | 7 | LaTeX/KaTeX |
| **shadcn-style** components | — | `Button`, `Switch`, `Slider`, `Select`, `Tooltip`, `Card`, `Badge` |

### AI & Multimodal

| Servis | Model | Kullanım |
|---|---|---|
| **Gemini** | `gemini-2.5-flash` | Sadeleştirme, chat, JSON mode |
| **Gemini Native Audio** | — | STT (Türkçe transkripsiyon) |
| **Gemini TTS** | `Aoede` voice | Doğal Türkçe okuma |
| **DeepSeek** | `deepseek-chat` | Alternatif sağlayıcı (drop-in) |

### Veri Kaynakları

- **KAP (Kamuyu Aydınlatma Platformu)** — `https://www.kap.org.tr/tr/api/...`
- KAP HTML disclosure sayfaları (XBRL etiketli)
- KAP PDF/HTML/XML attachment'lar

---

## 🚀 Hızlı Başlangıç

### Tek Tık (Windows)

```powershell
git clone https://github.com/Technet43/sesli-finansal-okuryazarlik-asistani.git
cd sesli-finansal-okuryazarlik-asistani
```

`start.bat`'a çift tıkla. Script:
- Python, Node.js, Git eksikse `winget` ile kurar
- `backend/.env` ve `frontend/.env.local` oluşturur
- `pip install` + `npm install` çalıştırır
- Backend (`:8000`) ve frontend (`:3000`) için iki pencere açar
- Tarayıcıda `http://localhost:3000` adresini açar

### Linux / macOS

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# AI çağrıları için anahtarı uygulama sidebar'ına gir
cd backend
PYTHONPATH=.. uvicorn app.main:app --reload  # :8000

# Frontend (ayrı terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev                                    # :3000
```

### Ortam Değişkenleri

**`backend/.env`:**

```bash
AI_PROVIDER=gemini                  # veya deepseek
GEMINI_MODEL=gemini-2.5-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

API anahtarı **frontend'e gömülmez** ve sunucu `.env`'inden otomatik alınmaz; kullanıcı sidebar'dan tek oturumluk olarak yapıştırır (`X-Gemini-Api-Key` veya `X-DeepSeek-Api-Key` header'ı).

### Full-stack Deploy

Modern Next.js + FastAPI sürümünü Vercel + Render ile yayınlamak için [DEPLOYMENT.md](DEPLOYMENT.md) dosyasını takip et.

---

## 📡 API Referansı

`http://localhost:8000`

| Method | Path | Açıklama | Rate Limit |
|---|---|---|---|
| `GET` | `/health` | Sağlık kontrolü | — |
| `GET` | `/api/version` | Sürüm + git hash | — |
| `GET` | `/api/status` | KAP + AI sağlayıcı durumu | — |
| `POST` | `/api/explain` | Bildirim sadeleştirme + finansal tablo çıkarımı | 10 / dak |
| `POST` | `/api/chat` | Şirket bağlamında AI sohbet | 30 / dak |
| `POST` | `/api/chat/stream` | Aynı sohbet, SSE streaming | 30 / dak |
| `POST` | `/api/tts` | Gemini text-to-speech (WAV b64) | 20 / dak |
| `POST` | `/api/transcribe/audio` | Gemini ile ses transkripsiyonu | 20 / dak |
| `POST` | `/api/test-gemini` | AI bağlantı testi | — |
| `POST` | `/api/cache/clear` | Şirket listesi cache'ini temizle | — |

### `POST /api/explain` — örnek istek

```json
{
  "company": "TCZB",
  "days": 365,
  "summaryCount": 4,
  "mode": "simple",
  "useDemo": false
}
```

### `POST /api/explain` — örnek yanıt

```json
{
  "company": "T.C. ZİRAAT BANKASI A.Ş.",
  "summary": "## Ziraat Bankası 2026 İlk Çeyrek Finansal Raporları ...",
  "notifications": [
    {
      "date": "2026-05-12",
      "title": "Konsolide Finansal Rapor",
      "category": "Finansal Rapor",
      "plainText": "...",
      "reportText": "KAP HTML tablo verisi: Nakit ve Nakit Benzerleri: ...",
      "reportTextSource": "TCZB KONSOLIDE 31.03.2026.pdf + KAP HTML tablosu",
      "financialTable": [
        { "label": "Nakit ve Nakit Benzerleri",
          "values": ["610.862.836", "1.159.207.336", "1.770.070.172", "829.612.210"] },
        { "label": "Özkaynaklar",
          "values": ["762.192.002", "-12.798.125", "749.393.877", "722.265.964"] },
        { "label": "Net Dönem Kârı/Zararı",
          "values": ["50.957.673", "0", "50.957.673", "179.645.756"] },
        { "label": "Faiz Gelirleri",
          "values": ["456.652.143", "347.303.211"] }
      ]
    }
  ],
  "anomalies": [
    { "icon": "📎", "title": "Eksik ek dosya",
      "description": "1 önemli bildirimde ek dosya yok." }
  ],
  "financialNumbers": [],
  "source": "kap",
  "disclaimer": "Bu çıktı yatırım tavsiyesi değildir.",
  "responseTimeMs": 13500,
  "disclosureCount": 4
}
```

---

## 🧠 Nasıl Çalışıyor? (Veri Akışı)

```
1. Kullanıcı "Ziraat Bankası" yazar (veya mikrofona söyler)
        │
2. Frontend → POST /api/explain
        │
3. Backend KAP listesinde fuzzy match yapar (rapidfuzz, token_set_ratio)
        │   ↳ DEMO modu offline çalışır (offline.demo_data)
        │
4. KAP /tr/api/disclosures sorgusu → son N bildirim
        │
5. Her bildirim paralel işlenir (ThreadPoolExecutor, max 6 worker):
        ├─ KAP bildirim sayfası HTTP GET
        ├─ BeautifulSoup ile HTML parse
        ├─ _extract_kap_table_text  → düz tablo metni (AI bağlamı için)
        ├─ _extract_kap_table_rows  → yapısal satırlar (UI tablosu için)
        ├─ Attachment linkleri çıkar (PDF, HTML, XBRL)
        ├─ Attachment indir → text extraction (pypdf / BeautifulSoup / XBRL regex)
        └─ HTML tablo verisi + attachment metni birleştirilir
        │
6. Kategori sınıflandırma (Finansal Rapor, Temettü, Sermaye İşlemi vb.)
        │
7. Anomali tespiti (geç bildirim, eksik ek, yoğun sermaye, gece bildirim...)
        │
8. compact_disclosures: AI prompt'unu 18 000 char limitinde tutar
        │
9. AI sağlayıcı (Gemini / DeepSeek) çağrısı:
        ├─ Sistem prompt: yatırım tavsiyesi yasağı + sayı vurgu + çapraz referans
        ├─ JSON mode (Gemini) / OpenAI-compatible JSON (DeepSeek)
        └─ Yanıt: { summary, notifications[] }
        │
10. clean_advice_language regex'i çıktıyı süzer
        │
11. ExplainResponse şeması (Pydantic) → JSON
        │
12. Frontend:
        ├─ ResultsPanel summary + anomaly + Finansal Veriler tablosu render eder
        └─ ChatPanel buildContext: tüm bildirimlerden anahtar değerleri toplar
```

---

## 🔬 Mimari Kararlar (ADR Özeti)

| Karar | Gerekçe |
|---|---|
| **PDF değil HTML önceliği** | KAP'ın PDF API'si bildirim kapağını döndürür; finansal tablolar **HTML body'de XBRL etiketli olarak yaşar.** Yapısal extraction sadece HTML'den mümkün. |
| **Yapısal `{label, values}` tablosu** | AI yanlış-bilingual-label tuzağına düşmesin diye sayısal hücreler ayrı bir alanda taşınır; UI doğrudan render eder. |
| **Çapraz referanslı chat prompt** | Kullanıcı her zaman doğru bildirimi sormaz; AI _aynı dönemin_ diğer bildirimini bulabilmeli. |
| **AI sağlayıcı soyutlaması** | Gemini ücretsiz kotası bittiğinde DeepSeek (OpenAI uyumlu) fallback'i drop-in. Streaming her ikisinde de aynı API ile. |
| **Sayı uydurma yasağı** | Prompt + post-processing ile çift katman; sayılar **sadece bağlamdan** gelir. |
| **Rate limit + boyut limiti** | KAP'a saygılı (User-Agent + 5 MB cap), spam'a kapalı (in-memory IP bucket). |

---

## 📁 Proje Yapısı

```
sesli-finansal-okuryazarlik-asistani/
├── kap_okuryazar/                   # Ortak Python çekirdeği
│   ├── config.py                    # KAP URL, sözlük, popüler şirket aliasları
│   ├── demo_data.py                 # Offline demo bildirimleri
│   ├── safety.py                    # Yatırım dili temizleme (eski Streamlit)
│   ├── text_utils.py                # normalize_tr, anomali, finansal sayı tespiti
│   └── models.py                    # CompanyMatch dataclass
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, endpoint'ler, rate limit
│   │   ├── core/
│   │   │   ├── config.py            # .env yükleyici, AI sağlayıcı ayarı
│   │   │   └── bootstrap.py         # sys.path yönetimi
│   │   ├── models/schemas.py        # Pydantic şemaları
│   │   └── services/
│   │       ├── kap_service.py       # KAP scraping, HTML table extraction (★)
│   │       ├── gemini_service.py    # Gemini client, JSON parse
│   │       ├── ai_provider_service.py  # Gemini/DeepSeek soyutlaması
│   │       ├── summarizer_service.py   # Prompt building, normalize
│   │       ├── safety_service.py    # clean_advice_language
│   │       └── tts_service.py       # Gemini TTS (WAV)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/                     # Next.js App Router
│   │   ├── components/
│   │   │   ├── AppShell.tsx, Header.tsx, Sidebar.tsx
│   │   │   ├── HeroSearch.tsx       # Arama + mikrofon
│   │   │   ├── ResultsPanel.tsx     # Özet + Finansal Veriler + bildirimler (★)
│   │   │   ├── ChatPanel.tsx        # Çapraz referanslı sohbet (★)
│   │   │   ├── ComparisonPanel.tsx  # 2 şirket kıyaslama
│   │   │   ├── StatusCards.tsx, GlassCard.tsx
│   │   │   └── ui/                  # shadcn-style Radix bileşenleri
│   │   └── lib/
│   │       ├── api.ts               # Fetch wrapper'ları
│   │       ├── types.ts             # TS şemaları (mirror of Pydantic)
│   │       ├── useTextToSpeech.ts   # Web Speech / Gemini TTS bridge
│   │       └── useSpeechRecognition.ts  # Web Speech / Gemini STT bridge
│   ├── package.json
│   └── tailwind.config.ts
│
├── app.py                           # Eski Streamlit demo (korunuyor)
├── telegram_bot.py                  # Opsiyonel Telegram bot
├── start.bat / start.ps1            # Windows tek-tık başlatıcı
├── HACKATHON_NOTLARI.md             # Jüri için kısa pitch
└── README.md                        # bu dosya
```

★ ile işaretli dosyalar projenin **özgün katkı noktaları**.

---

## 🛡️ Güvenlik ve Etik

- **Yatırım tavsiyesi vermez.** "Al / sat / kesin yükselir / kesin düşer / bu hisse alınır" gibi ifadeler hem AI prompt'unda yasaklı hem de `safety_service.clean_advice_language` regex'i ile post-processing'de temizlenir.
- **Sayı uydurmaz.** AI prompt'u "bağlamda olmayan sayı uydurma" kuralı içerir. Finansal değerler **yalnızca KAP HTML tablosundan veya attachment'tan** gelir.
- **API anahtarları repoya commitlenmez.** `.gitignore` ile korunur; örnek dosyalar `.env.example` adıyla mevcut.
- **Rate limiting.** Per-IP in-memory bucket, KAP'a aşırı yük bindirmez.
- **CORS sıkı.** `ALLOWED_ORIGINS` env'i ile kontrol edilir, varsayılan sadece `localhost`.
- **Disclaimer her yerde.** Hem API yanıtında hem UI alt bilgisinde sabit.

---

## 🎬 Demo Senaryoları

### Senaryo 1: Sıradan Vatandaş

> Kullanıcı: "İş Bankası" yazar veya mikrofona söyler
> Sistem: Son 4 bildirimi 13 saniyede sadeleştirir, finansal tabloyu gösterir, sesli okur
> Kullanıcı: "Nakit pozisyonu önceki döneme göre nasıl?"
> AI: Yüzde kıyaslamalı, çapraz referanslı, eğitici bir cevap üretir

### Senaryo 2: Finansal Veri Sorgusu

> Kullanıcı: "TCZB sorumluluk beyanındaki değerleri verir misin"
> AI: "Sorumluluk beyanında değer yok, ancak Konsolide Finansal Rapor'da Nakit 610.862.836 bin TL..."

### Senaryo 3: Anomali Tespiti

> Sistem: 2 önemli bildirimde ek dosya eksikliğini otomatik flag'ler
> UI: Sarı amber kartla bilgilendirir, etkisini açıklar

### Senaryo 4: Sesli ve Kişiselleştirilmiş Anlatım

> Kullanıcı: Mikrofon kartını açıp şirket adını sesle söyler
> Sistem: Gemini ile Türkçe transkripsiyon yapar
> Kullanıcı: "Sade ve anlaşılır", "Profesyonel özet" veya "Detaylı teknik analiz" modunu seçer
> AI: Aynı KAP verisini seçilen bilgi seviyesine göre yeniden anlatır

### Senaryo 5: Şirket Karşılaştırma

> Kullanıcı: Ziraat Bankası ve Halkbank gibi iki şirketi karşılaştırır
> Sistem: Her iki şirketin son KAP bildirimlerini yan yana özetler
> UI: Özetleri, uyarıları ve bildirim kartlarını iki kolon halinde gösterir

---

## ⚠️ Bilinen Sınırlılıklar

- Karşılaştırma ekranı şu an ayrı bir odak görünümüdür; sonuç ekranındaki chat paneli bu görünümde gizlenir. Sonraki sürümde chat'i karşılaştırma ekranında dock/panel olarak korumak planlanıyor.
- Mikrofon transkripsiyonu Gemini API anahtarına bağlıdır; anahtar hatalıysa arama kutusu çalışmaya devam eder, sesli giriş hata mesajı gösterir.

---

## 🔮 Yol Haritası

- [ ] **PWA / mobil uygulama** — offline demo + push notifications
- [ ] **Tarihsel kıyas** — son 4 çeyreğin grafiği (recharts)
- [ ] **PDF içeriği için OCR fallback** — taranmış raporlar için Tesseract
- [ ] **Sektör karşılaştırması** — aynı sektörde şirket benchmark'ı
- [ ] **Karşılaştırma + chat birlikte** — iki şirket kıyaslanırken soru-cevap panelini görünür tutma
- [ ] **Kullanıcı bilgi seviyesi profili** — "yeni başlayan / orta / ileri" personalization
- [ ] **Webhook + bildirim** — favorilenen şirketin yeni KAP açıklamasında push
- [ ] **i18n** — İngilizce KAP versiyonu için EN UI

---

## 🤝 Katkıda Bulunma

PR'lar açıktır. Lütfen:

1. Fork'la, feature branch oluştur (`git checkout -b feature/x`).
2. `npm run lint` ve `python -m pytest` (varsa) yeşil olmalı.
3. Yatırım tavsiyesi yasağı + sayı uydurma yasağı bozulmamalı.
4. Yeni AI prompt değişikliklerinde örnek bir KAP bildirimi ile davranışı doğrula.

---

## 📜 Lisans

MIT — eğitim ve sosyal etki amaçlı.

---

## 👥 Ekip

**Technet43** — Hackathon'26 katılımcısı

---

<div align="center">

### 🇹🇷 Türkiye'de finansal okuryazarlığı artırmak için yapıldı.

**Yatırım tavsiyesi vermez — resmî açıklamayı sade Türkçe'ye çevirir.**

</div>
