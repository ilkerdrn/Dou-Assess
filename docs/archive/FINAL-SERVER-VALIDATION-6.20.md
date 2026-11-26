# DOU Assess 6.20 Final Server Validation

Paket: `DOU-Assess-6.20-QUALITY360-SERVER-READY.zip`

## Kaynak doğrulaması

- App version: `6.20-quality360-server-ready`
- Expected schema: `0019_quality360`
- Migration chain: `0018_classic_assessment_standard → 0019_quality360`
- Dockerfile APT repository transport: HTTPS (6.19.1 hotfix korunmuştur)
- Upgrade script shell syntax: PASS
- Server smoke script shell syntax: PASS
- Final README/UI visible version: 6.20

## Test sonucu

- `pytest -q`: **55/55 PASS**
- Classic Scan grading: **PASS**
- Legacy classic scan: **PASS**
- Complete assessment engine: **PASS**
- Lifecycle: **PASS**
- Local Pilot UAT 1–9: **41/41 PASS**

Testler final kaynak ağacının gerçek demo DB/data dizinlerini kirletmemek için ayrı geçici SQLite DB ve ayrı evidence/scan/ops dizinleri ile çalıştırılmıştır.

## Migration sonucu

- Fresh SQLite → `0019_quality360`: **PASS**
- Mevcut 6.19.1 demo SQLite `0018_classic_assessment_standard` → `0019_quality360`: **PASS**
- Migration öncesi/sonrası temel veri sayıları korunmuştur:
  - programs: 10 → 10
  - courses: 11 → 11
  - students: 39 → 39
  - exams: 19 → 19
  - responses: 321 → 321
  - app_users: 13 → 13
  - evidence_assets: 3 → 3
  - scan_items: 3 → 3
- Final demo DB revision: `0019_quality360`
- Final demo DB'de yerleşik profiller: `MEDEK-2026`, `MEDEK-2028`, `YOKAK-2026`
- Test sırasında üretilen ekstra Quality360/evidence/scan kayıtları final demo DB/data dizinlerinden temizlenmiştir.

Production PostgreSQL'de migration aynı Alembic revision zinciri üzerinden `migrate` servisi tarafından çalıştırılır. Yükseltme scripti migration öncesi `pg_dump -Fc` ve kaynak/yapılandırma checkpoint'i alır. Gerçek production PostgreSQL/Entra/TLS/OBS ortamı kurum sunucusunda ayrıca saha kabulünden geçirilmelidir.

## Quality360 doğrulaması

- Katalog endpoint: PASS
- MEDEK-2026 / v1.1 / 9 kriter: PASS
- MEDEK-2028 / v2.0 / 8 kriter: PASS
- YÖKAK-2026 / 14 kriter: PASS
- AKTS 60/20/5/15 checker: PASS
- PUKÖ/paydaş/mezun/kadro/altyapı/kurul CRUD: PASS
- 7 yeni Excel şablonu: PASS
- Excel validate/import: PASS
- ÖDR DOCX üretimi: PASS
- Quality evidence upload/download + SHA-256: PASS
- Quality360 frontend contract: PASS

## Paket bütünlüğü

Kaynak manifesti: `SOURCE-MANIFEST-SHA256.txt`

ZIP açıldıktan sonra:

```bash
python3 Verify-Package-Manifest-6.20.py
```

Beklenen sonuç:

```text
[PASS] Manifest doğrulandı: <dosya sayısı> dosya
```

## Sunucu kabul komutu

```bash
bash Verify-6.20.sh --base-url http://127.0.0.1:8080
```

Beklenen:

- health → `6.20-quality360-server-ready`
- ready → `0019_quality360`
- catalogs → `Kısa Sınav`
- frameworks → `MEDEK-2026`
- frameworks → `YOKAK-2026`

## Veri güvenliği notu

`Upgrade-Server-6.20.sh` içinde `docker compose down -v` veya named volume silme işlemi yoktur. Script mevcut Compose proje kökünde çalışarak PostgreSQL/evidence/scan/ops named volume kimliğini korumayı amaçlar; `.env` ve `secrets/` overwrite edilmez.
