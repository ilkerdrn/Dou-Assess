# DOU Assess 6.18 — Complete Assessment Engine Final Kabul Raporu

Tarih: 22 Ağustos 2026

## Otomatik regresyon

- Mevcut pytest regresyon paketi: **45/45 PASS**.
- Python syntax / compile: **PASS**.
- JavaScript syntax (`app.js` + `modules/assessment-engine.js`): **PASS**.
- Docker Compose YAML parse (`pilot` + `production`): **PASS**.
- Final seed veritabanı `/api/health`: **200 / PASS**.
- Final seed veritabanı `/api/ready`: **200 / PASS**.
- Final seed schema revision: **0016_classic_scan_grading**.
- Alembic temiz kurulum `upgrade head`: **PASS**.
- Alembic `0015 -> 0016` upgrade: **PASS**.
- Klasik tarama + rubrik acceptance: **PASS**.
- Legacy `dou-official-v2` klasik sayfa association/crop acceptance: **PASS**.

## Complete Engine kabul senaryosu

İzole geçici veritabanı ve yerel sahte OBS HTTP alıcısı ile:

- Vize %40 + Final %60 ağırlıklı öğrenci notları: **70 / 80 / 0 — PASS**.
- Ağırlıklı ÖÇ/PÇ hesap motoru: **PASS**.
- Ders bazlı geçme eşiği: **PASS**.
- Eşit puanda eşit derece: **PASS**.
- Cronbach Alpha / KR-20: **0.6667 / 0.6667 — PASS**.
- Ayırt edicilik, point-biserial ve çeldirici analizi: **PASS**.
- Görselli soru PDF üretimi: **PASS**.
- A3 yatay gerçek PDF ölçüsü: yaklaşık **1190.55 × 841.89 pt — PASS**.
- Ayrı OMR + duplex sayfa dengeleme: **4 sayfa — PASS**.
- Rubrikli klasik soru puanlama: **PASS**.
- Rubrik toplamı soru puanına uymadığında kayıt engeli: **HTTP 400 — PASS**.
- OBS outbound adaptörü: **3 öğrenci sonucu test alıcısına ulaştı — PASS**.
- Ders not defteri Excel'i: **PASS**.
- OBS sonuç Excel'i: **PASS**.
- Evidence sürümleme: **v1 / v2 — PASS**.
- Evidence inline preview: **PASS**.
- Öğrenci anonimleştirme: **PASS**.
- Gelişmiş sınav Excel'i: **PASS**.

## Yaşam döngüsü / revizyon kabul senaryosu

- Soru bankası düzenlemede sürüm: **v1 → v2 — PASS**.
- Soru bankası sınav kullanım sayacı: **1 — PASS**.
- Onaya gönderme: **PASS**.
- Revizyon isteme sonrası sınavın taslağa dönmesi: **PASS**.
- Revizyon numarası: **1 → 2 — PASS**.
- Revizyon sonrası eski öğrenci cevaplarının temizlenmesi: **PASS**.
- A5 dikey PDF fiziksel ölçüsü: yaklaşık **419.53 × 595.28 pt — PASS**.

## Paket temizliği

- Regresyon testleri final seed DB üzerinde çalıştırılmadı; ayrı geçici DB kullanıldı.
- Final SQLite pilot veritabanı temiz ve sıfır verili olarak `0016_classic_scan_grading` head ile üretildi.
- Test sırasında oluşan evidence/scan/runtime artıkları final paketten çıkarıldı.
- `__pycache__`, `.pytest_cache` ve `.pyc` dosyaları final paketten çıkarıldı.
- Kaynak dosyalar için SHA256 manifest üretildi.

## Kurum ortamında yapılacak son saha kabulü

Aşağıdaki maddeler kaynak kodun dışında gerçek kurum servisi/donanımı gerektirir; bunlar yazılım eksikliği olarak değerlendirilmemelidir:

1. Doğuş Üniversitesi gerçek Microsoft Entra tenant/client ile kullanıcı girişi.
2. Kurum OBS'sinin gerçek endpoint ve alan sözleşmesiyle sonuç geri gönderimi.
3. Fiziksel ADF/tarayıcı ile toplu OMR kağıdı okutma ve hata senaryoları.
4. Hedef production PostgreSQL + NGINX üzerinde yük/UAT.
5. Gerçek production yedeğinin ayrı ortama tam restore tatbikatı.

Bu saha adımları için Entra, deployment, backup/restore, load-test ve pilot doğrulama scriptleri paket içinde bulunmaktadır.
