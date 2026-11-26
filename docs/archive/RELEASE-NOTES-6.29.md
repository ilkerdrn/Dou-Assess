# DOU Assess 6.29 — Quality Action Engine

Sürüm: `6.29-quality-action-engine-server-ready`

## Amaç
Kalite dashboard'unda görülen riskleri pasif uyarı olarak bırakmak yerine açıklanabilir ve insan onaylı PUKÖ aksiyonlarına dönüştürmek.

## Yeni
- Program + akademik yıl + kalite framework'ü bazında otomatik aksiyon önerileri.
- Öneri içinde: ölçüt, kalite skoru, eksik sinyaller, önem seviyesi, önerilen sorumlu, termin ve beklenen kanıt.
- Planla → Uygula → Kontrol Et → Önlem Al metinleri otomatik taslaklanır.
- Kalite/program yöneticisi tek tıkla öneriyi gerçek `QualityCycle` kaydına dönüştürebilir.
- Sistem kullanıcı onayı olmadan PUKÖ oluşturmaz.
- Aynı program/yıl/ölçüt için açık PUKÖ varken ikinci döngü oluşturulması engellenir.
- Premium “Akıllı İyileştirme Motoru” kartları Quality360 çalışma alanına eklendi.

## Uyumluluk
- Schema head değişmedi: `0021_quality_framework_routing`.
- 6.28 Executive Quality Command Center korunur.
- MEDEK/MÜDEK/TURAK/YÖKAK/ESG/ACQUIN framework routing korunur.
