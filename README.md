# KAP Okuryazar

KAP Okuryazar, Türkiye'deki şirketlerin KAP bildirimlerini sade Türkçe ile anlatan sesli finansal okuryazarlık asistanıdır. Amaç yatırım tavsiyesi vermek değil, resmi açıklamaları herkesin anlayacağı dile çevirmektir.

## Durum

- Eski Streamlit uygulaması korunuyor: `app.py`
- Ortak Python çekirdeği ayrıldı: `kap_okuryazar/`
- Yeni FastAPI backend eklendi: `backend/`
- Yeni Next.js frontend iskeleti eklendi: `frontend/`

## Özellikler

- KAP şirket arama ve bildirim çekme
- Gemini ile sadeleştirme, fallback modda kural tabanlı özet
- Yatırım tavsiyesi dilini temizleyen güvenlik katmanı
- Demo/offline veri akışı
- Streamlit tarafında ses, PDF, görsel analiz, canlı izleme ve jüri paketi
- Yeni frontend tarafında Liquid Glass hissinde modern arayüz, geçmiş aramalar ve API bağlantısı

## Klasör Yapısı

```text
app.py                         Eski Streamlit uygulaması
kap_okuryazar/                 Ortak config, demo data, model, safety, text utils
backend/app/main.py            FastAPI uygulaması
backend/app/services/          KAP, Gemini, summarizer, safety servisleri
backend/app/models/schemas.py  Pydantic API modelleri
frontend/src/app/              Next.js app router
frontend/src/components/       Liquid Glass UI bileşenleri
frontend/src/lib/              API client ve TypeScript tipleri
telegram_bot.py                Opsiyonel Telegram bot
```

## Ortam Değişkenleri

Kök Streamlit uygulaması için:

```powershell
Copy-Item .env.example .env
```

Backend için:

```powershell
Copy-Item backend\.env.example backend\.env
```

`.env` içine Gemini anahtarını koy:

```text
GEMINI_API_KEY=...
```

API key repoya yazılmamalı.

## Streamlit Modu

Streamlit modu şimdilik ana demo olarak çalışmaya devam eder.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Adres:

```text
http://localhost:8501
```

## FastAPI Backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Adres:

```text
http://localhost:8000
```

Endpointler:

- `GET /health`
- `GET /api/status`
- `POST /api/explain`
- `POST /api/test-gemini`

Örnek `/api/explain` body:

```json
{
  "company": "Ziraat Bankası",
  "days": 365,
  "summaryCount": 4,
  "mode": "simple",
  "useDemo": false
}
```

## Next.js Frontend

Bu ortamda `npm` PATH'te olmadığı için build burada çalıştırılamadı; dosyalar hazırlandı. Node/npm kurulu bir terminalde:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Adres:

```text
http://localhost:3000
```

Frontend varsayılan olarak backend'i buradan çağırır:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Güvenlik

Bu uygulama yatırım tavsiyesi vermez. Gemini çıktıları prompt kurallarıyla sınırlandırılır ve sonrasında `apply_safety_guard()` ile "al", "sat", "kesin yükselir" gibi tavsiye dili temizlenir.

## Geliştirme Notları

- Streamlit silinmedi; yeni mimari paralel eklendi.
- Backend, mevcut KAP ve Gemini mantığını Python tarafında tutar.
- Frontend sadece API çağırır; API key frontend koduna gömülmez.
- Geçmiş aramalar frontend tarafında `localStorage` ile saklanır.
