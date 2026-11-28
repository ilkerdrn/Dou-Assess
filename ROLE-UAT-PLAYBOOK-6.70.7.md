# DOU Assess 6.70.7 — Role-Based UAT Playbook

Amaç: kullanıcının eğitim almadan temel işini 5–8 dakika içinde tamamlayabildiğini ölçmek.

## Ortak UAT Kuralı
- Kullanıcıya menü yolu söylenmez; yalnız görev verilir.
- Testi izleyen kişi yardım etmez, sadece takılma noktasını kaydeder.
- Başarı ölçütü: doğru ekranı bulma, görevi tamamlama, geri dönüş yolunu anlayabilme.
- Pilot ortamında `? Kılavuz → Bu ekranda sürtünme bildir` ile gözlem anında kaydedilir.
- Bir görevde 20 saniyeden uzun kararsızlık UX sürtünmesi olarak işaretlenir.
- Yanlış sayfaya 2 veya daha fazla geçiş UX açığı kabul edilir.

## 1. Öğretim Elemanı — hedef ≤ 7 dakika
1. Kendi dersini bul ve aç.
2. Ders için yeni bir soru oluştur.
3. Aynı ders için yeni sınav taslağı oluştur.
4. Soruyu sınava ekle ve sınavı kontrol et.
5. Değerlendirme ekranına git ve puanlama bekleyen işi bul.

Kabul kriterleri:
- Ders seçimi ≤ 30 sn.
- Soru oluşturma ekranı tek denemede bulunur.
- Kullanıcı “Soru Bankası” ile “Sınav Sorusu” farkını açıklama almadan anlayabilir.
- Sınav oluşturma ana akışı Gelişmiş ayarlara girmeden tamamlanabilir.
- Değerlendirmeye en fazla 2 navigasyon hareketiyle ulaşılır.

## 2. Program Başkanı — hedef ≤ 8 dakika
1. Programının genel durumunu aç.
2. Öğrenim Çıktısı → Program Çıktısı durumunu kontrol et.
3. Riskli/açık bir alanı bul.
4. Program Review kaydını aç veya başlat.
5. İlgili kanıtı Kanıt Merkezi'nden bul.

Kabul kriterleri:
- Program bağlamı kaybolmadan analiz → review → kanıt akışı kurulabilir.
- Yönetim ekranlarında öğretim elemanına ait operasyonel ayrıntılar baskın değildir.
- Kullanıcı eksik kanıt veya review işini doğrudan aksiyona çevirebilir.
- Standart kalite görünümü günlük karar için yeterlidir.

## 3. Kalite Kullanıcısı — hedef ≤ 8 dakika
1. Kalite & Akreditasyon ekranını aç.
2. Açık bir PUKÖ/kalite aksiyonunu bul.
3. Kalite Takvimi'nde yaklaşan işi kontrol et.
4. Kanıt Merkezi'nde ilgili kanıtı ara.
5. Gerekirse Uzman Görünüm'e geç ve tekrar Standart Görünüm'e dön.

Kabul kriterleri:
- İlk açılışta yalnız Standart Görünüm temel işleri gösterir.
- Kullanıcı framework/ziyaret ayrıntılarına ihtiyaç duymadan günlük işi tamamlar.
- Kanıt araması ve kalite aksiyonuna dönüş ≤ 3 tıklama.
- Uzman Görünüm'ün isteğe bağlı olduğu anlaşılır.

## Gözlem Kaydı
Her görev için:
- Tamamlandı: Evet / Hayır
- Süre
- Yanlış sayfa sayısı
- Yardım ihtiyacı
- Kullanıcı cümlesi / tereddüt noktası
- Önerilen düzeltme

## Release kabul eşiği
- Her rolde en az 3 gerçek kullanıcı.
- Temel görev tamamlama oranı ≥ %90.
- Kritik görevlerde yardım ihtiyacı = 0.
- Ortalama görev süresi hedef sürenin altında.
- Aynı sürtünme 2+ kullanıcıda görülürse ürün backlog'una P0/P1 usability maddesi olarak girer.
