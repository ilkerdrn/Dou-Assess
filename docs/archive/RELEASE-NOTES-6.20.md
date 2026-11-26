# DOU Assess 6.20 — Quality & Accreditation 360

## Sürüm özeti

6.20, mevcut sınav/optik/klasik değerlendirme motorunu koruyarak program kalite ve akreditasyon süreçlerini tek merkezde birleştirir. Bu sürümde veriyi mümkün olduğunca serbest metinle yazmak yerine katalogdan seçme yaklaşımı kullanılır.

## Yeni: Kalite & Akreditasyon 360

- MEDEK v1.1 (2026) için 9 genel ölçütlü hazırlık görünümü.
- MEDEK v2.0 için 2028+ ilk/genel yeniden değerlendirme geçiş profili ve 8 genel ölçüt.
- YÖKAK 2026 kalite profili: Değerlendirme Programları Kılavuzu v3.3 / KİDR v3.2.1 metadata'sı ve 14 kriter.
- Otomatik ölçüt hazırlık skoru + 1–5 manuel olgunluk değerlendirmesi.
- Müfredat/AKTS denetleyici: 60 / 20 / 5 / 15 AKTS eşikleri.
- PUKÖ kayıtları; Planla → Uygula → Kontrol Et → Önlem Al zinciri.
- Paydaş geri bildirimi ve aksiyona/kurul kararına dönüşüm kaydı.
- Mezun istihdam/izleme envanteri.
- Öğretim kadrosu envanteri.
- Laboratuvar, derslik, ağ/sunucu, yazılım lisansı, erişilebilirlik ve İSG altyapı kayıtları.
- Kurul/toplantı/karar zinciri.
- Gelişmiş kalite kanıt dosyası yönetimi, SHA-256, sürüm/saklama metadata'sı.
- Program verilerinden otomatik ÖDR çalışma taslağı (.docx).

## Katalog / seçim yaklaşımı

Yerleşik kataloglar:
- Sınav türü: Vize, Final, Bütünleme, Mazeret, Tek Ders, Muafiyet, Kısa Sınav, Uygulama.
- Sınıf: 1.–4. Sınıf.
- Dönem: Güz, Bahar, Yaz.
- Akademik yıl.
- Ders kategorisi.
- Paydaş ve paydaş etkileşim türü.
- Mezun istihdam durumu.
- Öğretim elemanı unvanı ve çalışma türü.
- Altyapı türü.
- Kalite/olgunluk durumları.

Sınav türü seçildiğinde önerilen süre otomatik uygulanır; kullanıcı gerekirse süreyi değiştirebilir.

## Excel Veri Merkezi

6.20 ile aşağıdaki yeni toplu şablonlar eklendi:
1. Müfredat / AKTS
2. Paydaşlar
3. Mezun izleme
4. Öğretim kadrosu
5. Altyapı
6. PUKÖ
7. Kurul / karar

Akış değişmedi: **Şablonu indir → doldur → doğrula → içe aktar**. Doğrulaması başarısız dosya transaction'a yazılmaz.

## Veritabanı

Yeni Alembic revision: `0019_quality360`.

10 yeni tablo:
- `quality_framework_profiles`
- `quality_curriculum_items`
- `quality_stakeholders`
- `quality_graduates`
- `quality_faculty`
- `quality_infrastructure`
- `quality_cycles`
- `quality_governance_decisions`
- `quality_criterion_assessments`
- `quality_evidence_assets`

Migration, mevcut `0018_classic_assessment_standard` verisini silmeden yalnız additive kalite tablolarını ekler.

## Sunucu yükseltme

Yeni Linux scripti: `Upgrade-Server-6.20.sh`.

Script:
- çalışan proje klasörünü korur,
- PostgreSQL `pg_dump` alır,
- evidence/scans/ops checkpoint almaya çalışır,
- `.env` ve `secrets` dosyalarını overwrite etmez,
- kaynak kod checkpoint'i alır,
- image'ları rebuild eder,
- `0019_quality360` migration'ını çalıştırır,
- `/api/ready`, Alembic head ve 6.20 smoke kontrollerini doğrular.

**Script içinde `docker compose down -v` veya volume silme işlemi yoktur.**

## Doğrulama

- Pytest: 55/55 PASS
- Classic Scan acceptance: PASS
- Legacy Classic Scan acceptance: PASS
- Complete Engine acceptance: PASS
- Lifecycle acceptance: PASS
- UAT 1–9: 41/41 PASS
- Fresh DB → `0019_quality360`: PASS
- Existing `0018` → `0019` + veri koruma: PASS

## Resmî profil kaynakları

- MEDEK: https://medek.org.tr/
- YÖKAK: https://www.yokak.gov.tr/

DOU Assess içindeki yerleşik profiller operasyonel takip içindir. Resmî başvuru öncesinde güncel kurum kılavuzları ve program özel ölçütleri ayrıca kontrol edilmelidir.
