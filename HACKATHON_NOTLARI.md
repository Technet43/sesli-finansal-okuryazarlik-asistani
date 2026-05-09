# Hackathon'26 Jüri Notları

## Tek Cümlelik Fikir

KAP bildirimlerini sıradan vatandaşın anlayacağı sade Türkçe'ye çeviren ve sesli okuyan finansal okuryazarlık asistanı.

## Problem

KAP bildirimleri resmi ve güvenilir kaynaktır, fakat dili teknik olduğu için yeni yatırımcılar, yaşlı kullanıcılar ve finans bilgisi sınırlı vatandaşlar tarafından zor anlaşılır.

## Çözüm

Kullanıcı şirket adını yazar veya mikrofona söyler. Uygulama şirketi KAP listesinde bulur, son KAP bildirimlerini çeker, bildirim türünü sınıflandırır, Gemini ile sade Türkçe rapora dönüştürür ve gTTS ile sesli okur.

## Neden Birincilik Potansiyeli Var?

- Yerel problem: Türkiye sermaye piyasası ve KAP verisi.
- Sosyal etki: Finansal okuryazarlığı artırır.
- Multimodal: Metin, ses girişi, sesli çıktı.
- Gerçek veri: Kaynak KAP linkleri gösterilir.
- Gemini kullanımı: Sadeleştirme ve ses kaydından şirket adı çıkarma.
- Güvenlik: Yatırım tavsiyesi vermez, sadece resmi açıklamayı anlaşılır hale getirir.

## Demo Video Akışı

1. "İş Bankası" yaz veya mikrofona söyle.
2. Uygulamanın şirketi bulduğunu göster.
3. Son KAP bildirimlerinden birini göster.
4. "Ne oldu?", "Neden önemli?", "Dikkat notu" kartlarını göster.
5. Sesli okuma sekmesinden metni dinlet.
6. Kaynak KAP linkini göster.
7. "Bu yatırım tavsiyesi değildir; resmi bilgiyi anlaşılır hale getirir" cümlesiyle bitir.

## Eksikler ve Sonraki Adımlar

- Daha doğal Türkçe TTS eklenebilir.
- Finansal tablo PDF'leri için daha derin sayısal analiz yapılabilir.
- Kullanıcı bilgi seviyesine göre anlatım otomatik kişiselleştirilebilir.
- Streamlit demosu PWA veya mobil uygulamaya taşınabilir.
- Model çıktısı için daha kapsamlı yatırım tavsiyesi güvenlik testleri eklenebilir.
