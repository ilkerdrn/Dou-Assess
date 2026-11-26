# DOU Assess – Veritabanı Denetimi

**Kaynak:** `e98e723` (6.70.3). SQLite üzerinde çalıştırılan doğrulamalar + kod okuma. **PostgreSQL bu ortamda yok → Postgres davranışı `NOT_VERIFIED`.**
"[D]" = ben ayrıca çalıştırarak/okuyarak doğruladım.

## Sayılar

| Konu | Değer | Doğrulama |
|---|---|---|
| Tablo sayısı (`Base.metadata`) | **111** (+`alembic_version` = 112 DB'de) | [D] `python -c "from app.models import Base…"` → 111 |
| "55 tablo" iddiası | **YANLIŞ / eski** — gerçek sayı 111 | [D] |
| Foreign key | 145 (metadata) | [D] |
| `ondelete` dağılımı | 121 CASCADE, 21 SET NULL, 3 RESTRICT (`models.py:1027,1050,1967`) | denetim ajanı |
| Alembic | Tek head `0042_performance_production_hardening` = `RELEASE.env EXPECTED_SCHEMA_REVISION`; boş SQLite'ta 0001→0042 hatasız | denetim ajanı (çalıştırdı) |
| Kullanılmayan tablo | Hiçbiri tamamen ölü değil; en az referanslılar: `import_batches` (2, yalnız yazılıyor), `pilot_uat_runs` (3), `program_educational_objective_outcome_maps` (3), `survey_answers` (4), `answer_key_revisions` (4), `assessment_blueprint_items` (4), `teaching_assignments` (5), `quality_graduate_followups` (5) | referans sayımı; gerçekten çalışıp çalışmadığı `NOT_VERIFIED` |

Not: Tablo sayısı mimarinin tamamlandığını göstermez (görev şartı). 111 tablonun işlevsel olgunluğu modül raporunda değerlendirilir.

## Bulgular

| # | Bulgu | Durum | Öncelik | Kanıt |
|---|---|---|---|---|
| D1 | Üretim PostgreSQL, ama **hiçbir test canlı PostgreSQL'e bağlanmıyor**. Postgres'e özgü bir hata daha önce yaşanmış (6.62.1 hotfix); `test_6621…` yalnız statik içerik kontrolü. | NOT_VERIFIED | Yüksek | [D] `tests/test_6621_postgres_migration_hotfix.py:6`; `tests/test_core.py:734` yalnız config |
| D2 | `Backup-Server.sh` yedek dizinine **`.env` ve `secrets/` klasörünü şifresiz kopyalıyor** (DB parolası, Entra/OBS token'ları). Öğrenci verisi (KVKK) ile birlikte aynı arşivde. | BROKEN (güvenlik) | Yüksek | [D] `Backup-Server.sh:14` |
| D3 | `Restore-Server.sh` **önceden güvenlik yedeği almadan** `dropdb` yapıyor; yalnız `CONFIRM_RESTORE=YES` kontrolü var. Otomatik yedek varsayılan **kapalı** (`BACKUP_AUTOMATION_ENABLED=false`); `create_operational_backup` (`services/operations.py:225`) yedeği **aynı sunucuda** tutuyor, off-site kopya yok. Gerçek backup/restore tatbikatı yapılmadı. | PARTIALLY_COMPLETE | Yüksek | [D] `Restore-Server.sh:14,17` |
| D4 | **Silme/arşiv stratejisi eksik:** soft-delete yok; yalnız bazı tablolarda `status='archived'`. 121 CASCADE nedeniyle program/ders/öğrenci silinmesi sınav, yanıt ve kanıt zincirini sessizce silebilir. KVKK saklama/silme akışı eksik. | PARTIALLY_COMPLETE | Yüksek | `models.py` FK tanımları (denetim ajanı) |
| D5 | `app/db.py` SQLite'ta `PRAGMA foreign_keys` açmıyor → testler FK/CASCADE ihlallerini yakalamıyor. | PARTIALLY_COMPLETE | Orta | `app/db.py` |
| D6 | Transaction yönetimi: `_commit()` (`main.py:129`) hatada rollback yapıyor ama her endpoint commit'i elle çağırıyor; çok-commit'li akışların atomikliği doğrulanmadı. | NOT_VERIFIED | Orta | `main.py:129` |
| D7 | İzlenen olumlu noktalar: `students.student_no` unique; `responses(exam_student_id, question_id)` unique; yedek betiğinde checksum ve `pg_restore --list` doğrulaması (okunarak; **çalıştırılmadı**). | PARTIALLY_COMPLETE | — | denetim ajanı |
| D8 | `data/{evidence,scans,ops}/.gitkeep` pakette yok; Dockerfile dizinleri oluşturduğu için çalışmayı engellemez ama manifest bu dosyaları listeliyor (manifest tutarsızlığı). | PARTIALLY_COMPLETE | Düşük | [D] `sha256sum -c` çıktısı |

## Yapılamayanlar

- PostgreSQL üzerinde migration, indeks planı, performans (büyük veri sorguları) — `NOT_VERIFIED`.
- Gerçek yedekleme/geri yükleme ve veri kaybı senaryoları — `NOT_VERIFIED`.
- Canlı veritabanı ("55 tablo" iddiasının kaynağı) — sunucuya erişim yok (`BLOCKED`).

## Öneriler (öncelik sırasıyla)

1. Yedekten `.env`/`secrets`'i çıkar veya şifrele (age/gpg); yedeği off-site tut.
2. `Restore-Server.sh`'a otomatik "pre-restore" yedek ekle; aylık restore tatbikatı.
3. CI'da PostgreSQL servisiyle migration + test koş.
4. Kritik tablolarda CASCADE → RESTRICT/soft-delete politikası; KVKK saklama işi.
5. SQLite test bağlantısında `PRAGMA foreign_keys=ON`.
