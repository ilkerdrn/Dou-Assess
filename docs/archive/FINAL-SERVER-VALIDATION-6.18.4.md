# DOU Assess 6.18.4 — Final Server Validation

## Uygulanan özellik

Taranmış klasik cevapların öğrenci/soru ile ilişkilendirilmesi ve rubrikle yan yana puanlanması tamamlandı.

### Yeni kağıtlar
- Her soru sayfasında öğrenci/sınav/kitapçık/mantıksal sayfa QR'ı bulunur.
- ADF sayfa sırasından bağımsız klasik sayfa eşlemesi yapılır.

### Eski kağıtlar
- `dou-official-v2` kapak QR'ı tanınır.
- QR'dan sonraki soru sayfaları legacy sıralı fallback ile aynı öğrenciye bağlanır.
- Legacy sayfa geometrisi klasik cevap crop işleminde ayrıca desteklenir.

### Puanlama
- Cevap alanı / soru+cevap / tam sayfa görüntüleme
- Rubrik kriter bazlı puan
- Canlı rubrik toplamı
- Kaydet / Kaydet ve sonraki

## Otomatik doğrulama sonuçları

- Pytest: **45/45 PASS**
- Classic Scan Grading acceptance: **PASS**
  - 2 sayfa işlendi
  - 1 OMR accepted
  - 1 classic support page
  - cevap crop: **1181×345 px**
  - rubrik kayıt sonucu: **8/10**
- Legacy v2 classic scan acceptance: **PASS**
  - takip eden soru sayfası legacy association ile bağlandı
  - legacy answer crop: **1181×345 px**
- Complete Engine acceptance: **PASS**
- Lifecycle acceptance: **PASS**
- Pilot UAT 1–9: **41/41 PASS**
- Fresh Alembic migration: **0016_classic_scan_grading**
- Pilot/production Compose YAML parse: **PASS**
- Python compile: **PASS**
- Frontend JavaScript syntax: **PASS**

## Gerçek eski paket okuma kontrolü

Kullanıcının 90 sayfalık eski `dou-official-v2` sınav PDF'i streaming decoder ile sayfa sayfa işlendi:

- toplam sayfa: **90**
- v2 QR bulunan öğrenci kapak/OMR sayfası: **30**
- takip eden QR'sız klasik/soru sayfası: **60**

Bu yapı 6.18.4 legacy association tasarımıyla uyumludur.

## Üretim hardening

- PostgreSQL 17
- migration-before-API startup
- API 2 worker
- read-only API container filesystem
- `no-new-privileges`
- `cap_drop: ALL`
- rate limiting
- NGINX upload/connection limiting
- scan/upload read timeout: **300 sn**
- `MAX_PDF_PAGES=120`
- `MAX_IMAGE_MEGAPIXELS=40`
- scan/evidence/ops kalıcı volumes
- büyük PDF taramalarında sayfa bazlı streaming rasterization

## Bu ortamda doğrulanamayan saha maddeleri

Bu çalışma ortamında Docker CLI ve kurum dış servis kimlikleri bulunmadığı için gerçek production container runtime, Microsoft Entra tenant, gerçek OBS, TLS/DNS ve fiziksel ADF tarayıcı kabulü burada çalıştırılamadı. Compose/config statik olarak doğrulandı; uygulama/migration/acceptance testleri doğrudan çalıştırıldı.
