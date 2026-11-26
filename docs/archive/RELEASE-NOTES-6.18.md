# DOU Assess 6.18.5 — UI Fix Release Notes

- Sidebar menü çakışması giderildi; nav kendi scroll bölgesine alındı.
- Menü grupları tek-açık accordion davranışına geçti.
- Mobil/kısa ekran sidebar yüksekliği `100dvh` ve taşma güvenliği ile düzeltildi.
- CSS/JS cache anahtarı yenilendi.
- Final akademik veritabanı temiz migration head üzerinde yeniden üretildi.
- Regresyon: 46/46; UAT 1–9: 41/41; klasik/legacy/engine/lifecycle kabul testleri PASS.

### 6.18.4 Klasik tarama puanlama

- Soru sayfalarına öğrenci/sınav/kitapçık/mantıksal sayfa QR kimliği eklendi.
- Klasik cevap sayfaları taramada öğrenciye otomatik bağlanıyor.
- Puanlama ekranında taranmış cevap ve rubrik yan yana gösteriliyor.
- Cevap alanı, soru+cevap ve tam sayfa görüntü modları eklendi.
- Eski `dou-official-v2` kağıtları için sıralı legacy fallback ve eski crop geometrisi korundu.
- Büyük ADF PDF taramalarında bellek kullanımını sınırlamak için sayfa bazlı streaming rasterization eklendi.
- Alembic head `0016_classic_scan_grading`.

# DOU Assess 6.18 — Complete Assessment Engine Release Notes

## Akademik değerlendirme motoru
- Ders bazlı geçme eşiği eklendi.
- Vize/final/proje gibi sınavların yüzde ağırlıkları dönem notuna gerçek katkı verir.
- Sınav ağırlıkları %100 değilse OBS sonuç gönderimi engellenir.
- Ders not defteri; öğrenci bazlı sınav katkıları, dönem notu, başarı durumu, ağırlıklı ÖÇ ve PÇ sonuçlarını üretir.
- Eşit toplam puan alan öğrenciler aynı dereceyi alır.

## Soru Bankası 2.0 ve rubrik
- Konu, ünite, zorluk, Bloom düzeyi, yazar, inceleyen, sürüm ve kullanım geçmişi eklendi.
- PNG/JPEG soru görselleri banka ve sınav sorularında desteklenir.
- Klasik sorular ölçüt bazlı rubrik ile puanlanabilir; rubrik maksimum toplamı soru puanına uymuyorsa kayıt engellenir.

## Paper Studio v2
- A3, A4 ve A5 kağıt seçenekleri.
- Dikey/yatay yönlendirme.
- Optik alanı ilk sayfada veya ayrı sayfada üretme.
- Görselli soru basımı.
- Çift taraflı baskı için tek sayılı PDF'lerde bilinçli boş sayfa dengeleme.

## Gelişmiş ölçme-değerlendirme
- Cronbach Alpha ve KR-20.
- Soru ayırt edicilik ve point-biserial analizi.
- Çeldirici dağılımı.
- Çok kolay/çok zor, düşük/negatif ayırt edicilik ve yüksek boş bırakma uyarıları.
- Excel raporlarında konu, ünite, Bloom, zorluk, güvenilirlik ve kalite bayrakları.

## Kurumsal onay ve revizyon
- Onaya gönderme, yönetici onayı ve revizyon isteme akışı.
- Gerçek kimlik doğrulamalı kullanımda hazırlayan/onaylayan ayrımı zorunlu.
- Revizyon isteğinde sınav taslağa döner, revizyon numarası artar ve yeniden puanlama için cevaplar temizlenir.
- Tüm kritik işlemler audit izine yazılır.

## OBS, kanıt ve KVKK
- OBS uyumlu sonuç Excel'i ve HTTPS sonuç push adaptörü.
- Kanıtlarda kategori, açıklama, sürüm, saklama tarihi, önizleme, indirme, silme ve süre dolumu temizliği.
- Öğrenci kimlik alanları akademik ilişkileri bozmadan geri döndürülemez biçimde anonimleştirilebilir.
- Pilot readiness; KVKK saklama politikasını ve outbound OBS kanalını ayrıca kontrol eder.

## Teknik
- Alembic head: `0016_classic_scan_grading`.
- Assessment Engine saf frontend yardımcıları `app/static/modules/assessment-engine.js` modülüne ayrıldı.
- Mevcut otomatik test paketi korunarak geriye dönük uyumluluk sağlandı.

## Local UAT 1-9 update
- Added `Run-UAT-1-9.ps1` and `UAT-1-9-GUIDE.md`.
- Added 41-check end-to-end local acceptance scenario.
- Fixed `generate_omr_fixture.py` for the current OMR v2 normalized layout, personalized QR and separate/embedded OMR pages.
- Final verification: 45/45 regression + 41/41 UAT PASS.

## UX Final Polish
- Doğuş kurumsal kırmızısını temel alan daha sakin ve modern ürün arayüzü uygulandı.
- Sol navigasyon, üst bar, kartlar, tablolar, formlar ve aksiyonlar ortak tasarım sistemine taşındı.
- 900 px altındaki ekranlarda off-canvas mobil navigasyon eklendi; menü seçiminde ve Escape ile otomatik kapanır.
- Responsive dashboard/aksiyon/form düzenleri iyileştirildi.
- Klavye focus görünürlüğü ve `prefers-reduced-motion` desteği eklendi.
- Mevcut CSP güvenlik sözleşmesi ve backend davranışı değiştirilmedi.

## Soru Havuzu Excel Toplu Aktarım
- Soru Havuzu ekranına `Excel şablonu` ve `Excel ile toplu ekle` aksiyonları eklendi.
- Yeni endpointler: `/api/import/question-bank/template`, `/api/import/question-bank/validate`, `/api/import/question-bank`.
- Çoktan seçmeli ve klasik sorular; ders, ÖÇ, etiket, konu, ünite, zorluk, Bloom ve klasik rubrik alanlarıyla toplu alınabilir.
- Ders/yetki/ÖÇ doğrulaması atomik importtan önce yapılır.
- Aynı ders + aynı soru metni tekrar yüklendiğinde yinelenen soru oluşturulmaz; kayıt atlanır ve uyarı döner.
- Örnek paket: Bilgisayar Teknolojisi seçili 6 teknik derste 60 test + 12 klasik = 72 soru.
