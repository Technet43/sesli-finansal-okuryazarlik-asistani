# Full-stack deploy

Bu dosya modern Next.js + FastAPI surumunu web sitesine cikarmak icin kisa rehberdir.
API anahtari koyma: kullanicilar Gemini veya DeepSeek anahtarini uygulama sidebar'ina girer.

## 1. Backend: Render

1. Render hesabina GitHub ile gir.
2. **New** -> **Blueprint** sec.
3. Repo olarak `Technet43/sesli-finansal-okuryazarlik-asistani` sec.
4. Render repo kokundeki `render.yaml` dosyasini okuyup `kap-okuryazar-api` servisini olusturur.
5. Deploy bitince backend URL'ini not al. Ornek:

```text
https://kap-okuryazar-api.onrender.com
```

Render env ayarlari `render.yaml` icinde hazir gelir. API key ekleme.

Ilk kurulumda `ALLOWED_ORIGIN_REGEX=https://.*\.vercel\.app` Vercel preview/production domainlerini kabul eder.
Vercel domainin kesinlesince bunu daha dar yapmak daha iyidir:

```text
ALLOWED_ORIGINS=https://senin-vercel-domainin.vercel.app
ALLOWED_ORIGIN_REGEX=
```

## 2. Frontend: Vercel

1. Vercel hesabina GitHub ile gir.
2. **Add New** -> **Project** sec.
3. Ayni repo'yu import et.
4. **Root Directory** olarak `frontend` sec.
5. Framework preset: **Next.js**.
6. Environment Variables:

```text
NEXT_PUBLIC_API_URL=https://kap-okuryazar-api.onrender.com
```

Buradaki URL'i kendi Render backend URL'inle degistir.

7. Deploy et.

## 3. Deploy sonrasi kontrol

Frontend linkini ac:

```text
https://senin-vercel-domainin.vercel.app
```

Kontrol listesi:

- Sidebar'da API key girilmeden AI baglantisi basarisiz olmali.
- Kullanici kendi Gemini/DeepSeek key'ini girince test basarili olmali.
- Backend URL'i dogru degilse frontend "Backend'e ulasilamadi" hatasi verir.
- CORS hatasi gorursen Render `ALLOWED_ORIGINS` degerine Vercel domainini ekle.

## 4. Ucretsiz plan notlari

- Vercel frontend icin genelde hizli acilir.
- Render free backend uykuya gecebilir; ilk istek 30-60 saniye surebilir.
- Sunucuya API key koymadigimiz icin AI maliyeti uygulama sahibine yazilmaz.
