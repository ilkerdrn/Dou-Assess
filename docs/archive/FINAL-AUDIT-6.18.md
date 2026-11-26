# DOU Assess 6.18 — Final Complete Engine Audit

## Ürün zinciri
Akademik Veri → ÖÇ/PÇ Merkezi → Soru Bankası 2.0 → Sınav Merkezi → Paper Studio / Kitapçık → Optik & Kontrol → Rubrikli Puanlama → Gelişmiş Sınav Analizi → Ağırlıklı Ders Başarısı → Kalite/Akreditasyon → Evidence → OBS Sonuç Köprüsü.

## Kapanan kritik yazılım açıkları
- Vize/final/proje ağırlıkları dönem notuna gerçek katkı veriyor.
- ÖÇ/PÇ ders seviyesi hesapları sınav ağırlıklarını dikkate alıyor.
- Ders bazlı geçme eşiği ve eşit puanda eşit sıra uygulanıyor.
- Soru bankasında konu, ünite, zorluk, Bloom, yazar/inceleyen, görsel, rubrik, sürüm ve kullanım geçmişi tutuluyor.
- Klasik sorular ölçüt bazlı rubrik ile puanlanabiliyor.
- Cronbach Alpha, KR-20, ayırt edicilik, point-biserial ve çeldirici analizi üretilebiliyor.
- A3/A4/A5, yatay/dikey, ayrı/dahili OMR ve duplex PDF destekleniyor.
- Onaya gönderme, yönetici onayı ve revizyon isteme maker-checker izi ile yürütülüyor.
- Evidence sürümleme, önizleme, indirme, saklama tarihi ve purge yaşam döngüsü mevcut.
- Öğrenci kimliği akademik ilişkiler korunarak geri döndürülemez biçimde anonimleştirilebiliyor.
- OBS sonuç Excel'i ve HTTPS outbound adaptörü mevcut; ağırlık toplamı %100 değilse gönderim engelleniyor.

## Otomatik kabul özeti
- Regresyon: 45/45 PASS.
- Complete Engine kabul senaryosu: PASS.
- Yaşam döngüsü/revizyon kabul senaryosu: PASS.
- Alembic temiz kurulum ve 0015 ↔ 0014 round-trip: PASS.
- Python compile ve JavaScript syntax: PASS.

## Kurum ortamında kalan saha kabulü
Bunlar yazılım eksikliği değil, harici kurum altyapısı gerektiren son kabul adımlarıdır:
- Gerçek Doğuş Üniversitesi Microsoft Entra tenant ile kullanıcı girişi.
- Gerçek OBS endpoint/alan sözleşmesi ile sonuç gönderimi.
- Fiziksel ADF/tarayıcı ile toplu OMR.
- Hedef PostgreSQL + NGINX sunucusunda yük/UAT.
- Gerçek production yedeğinin ayrı ortama restore tatbikatı.
