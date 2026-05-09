# KAP Okuryazar

Türkiye'deki şirketlerin KAP bildirimlerini sade Türkçe ile anlatan finansal okuryazarlık asistanı. Amaç yatırım tavsiyesi vermek değil, resmi açıklamaları herkesin anlayacağı dile çevirmek.

## Mimarisi

| Katman | Teknoloji | Konum |
|---|---|---|
| Ortak Python çekirdeği | Pure Python (regex, sözlük, demo data, safety) | `kap_okuryazar/` |
| Backend API | FastAPI + Pydantic + uvicorn | `backend/` |
| Frontend | Next.js 15 + TypeScript + Tailwind + shadcn-stili Radix bileşenleri | `frontend/` |
| Eski Streamlit demo | Streamlit + gTTS (korunuyor) | `app.py` |
| Telegram bot (opsiyonel) | python-telegram-bot | `telegram_bot.py` |

KAP veri çekme, Gemini sadeleştirme ve güvenlik (yatırım tavsiyesi dilini temizleme) tamamen Python tarafında. Frontend yalnızca API çağırır; API key frontend koduna gömülmez.

## Hızlı başlangıç (Windows, tek tık)

1. Depoyu indir:
   ```powershell
   git clone https://github.com/Technet43/sesli-finansal-okuryazarlik-asistani.git
   cd sesli-finansal-okuryazarlik-asistani
   git checkout claude/modernize-ui-frontend-rHs29
   ```
2. `start.bat` dosyasına **çift tıkla**.

Script eksik araçları (Git, Python, Node.js) `winget` ile kurmayı dener, `.env` dosyalarını oluşturur, paketleri yükler, backend (`:8000`) ve frontend (`:3000`) pencerelerini ayrı ayrı başlatır ve tarayıcıda `http://localhost:3000` adresini açar.

Kapatmak için iki PowerShell penceresinde de `Ctrl+C`.

## Ortam değişkenleri

`.env` dosyaları repoya commitlenmez (`.gitignore` koruma altında). Örnekler:

```
.env.example                # Streamlit ve Telegram için kök seviye
backend/.env.example        # FastAPI backend için
frontend/.env.example       # Next.js frontend için
```

Backend için:

```bash
cp backend/.env.example backend/.env
# Backend/.env içine GEMINI_API_KEY ekle
```

Frontend için:

```bash
cp frontend/.env.example frontend/.env.local
```

API key kesinlikle frontend `.env`'ine yazılmamalı. Frontend sadece `NEXT_PUBLIC_API_URL` üzerinden backend'e istek atar; key backend'in `.env`'inde tutulur.

## FastAPI backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Adres: `http://localhost:8000`

### Endpointler

| Method | Path | Açıklama |
|---|---|---|
| GET | `/health` | Sağlık kontrolü |
| GET | `/api/status` | KAP ve Gemini durumu |
| POST | `/api/explain` | Bildirimleri sadeleştir |
| POST | `/api/test-gemini` | Gemini API bağlantı testi |

`POST /api/explain` örneği:

```json
{
  "company": "Ziraat Bankası",
  "days": 365,
  "summaryCount": 4,
  "mode": "simple",
  "useDemo": false
}
```

Cevap:

```json
{
  "company": "...",
  "summary": "Sade açıklama metni...",
  "notifications": [
    { "date": "2026-01-01", "title": "...", "plainText": "..." }
  ],
  "source": "kap",
  "disclaimer": "Bu çıktı yatırım tavsiyesi değildir."
}
```

CORS izni `ALLOWED_ORIGINS` env'i ile kontrol edilir (varsayılan `http://localhost:3000,http://127.0.0.1:3000`).

## Next.js frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Adres: `http://localhost:3000`

Production build:

```bash
npm run build
npm run start
```

### Tasarım

- Apple Liquid Glass hissinde frosted glass paneller
- Hafif iridescent (mor / cyan / pembe) glow
- shadcn-stili Radix UI bileşenleri (Switch, Slider, Select, Tooltip, Button, Badge, Card)
- Tailwind tabanlı utility class'lar; özel `glass-surface`, `glass-soft`, `iris-glow` class'ları
- Yüksek kontrast modu (`prefers-reduced-motion` ve renk kontrastı için)
- Geçmiş aramalar `localStorage` ile saklanır

### Frontend dosya yapısı

```
frontend/
  components.json
  src/
    app/
      layout.tsx
      page.tsx
      globals.css
    components/
      AppShell.tsx
      Header.tsx
      Sidebar.tsx
      HeroSearch.tsx
      ResultsPanel.tsx
      StatusCards.tsx
      GlassCard.tsx
      ui/
        button.tsx
        switch.tsx
        slider.tsx
        select.tsx
        input.tsx
        card.tsx
        badge.tsx
        tooltip.tsx
    lib/
      api.ts
      types.ts
      utils.ts
```

## Eski Streamlit demosu

Streamlit modu silinmedi; jüri sunumu için zengin demo (sesli okuma, mikrofon, PDF analizi, anomali tespiti) korunuyor.

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Adres: `http://localhost:8501`

## Güvenlik

- Yatırım tavsiyesi verilmez. Gemini çıktısındaki "al / sat / kesin yükselir" gibi ifadeler `kap_okuryazar/safety.py` tarafından regex ile temizlenir.
- API key repoya commitlenmez (`.gitignore` koruma altında).
- Backend hata mesajları gizli anahtarı sızdırmaz.
- Frontend API key tutmaz; sidebar'da "anahtar `.env` üzerinden okunur" mesajı gösterilir.

## Geliştirme notları

- Streamlit ve yeni mimari paralel çalışır.
- Backend, `kap_okuryazar/` çekirdeğini import eder; bootstrap `sys.path`'e repo kökünü ekler.
- Ortak iş mantığı (KAP arama, sadeleştirme, safety) tek yerde tanımlı: çekirdekte ve servis modüllerinde.
- Mikrofon kartı bu fazda statik görseldir; ses kaydı şimdilik yalnızca Streamlit demosunda.
- shadcn ekosisteminden yalnızca kullanılan bileşenler eklendi: `@radix-ui/react-switch`, `react-slider`, `react-select`, `react-tooltip`, `react-slot`.
