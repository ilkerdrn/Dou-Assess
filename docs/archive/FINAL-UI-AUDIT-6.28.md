# DOU Assess 6.28 — Final UI / Quality Audit

## Amaç
Yönetim ve kalite rolleri için premium, karar odaklı executive kalite deneyimi.

## Kabul edilen tasarım ilkeleri
- Basit görün, derin çalış.
- Öğretim elemanı ekranları yönetim karmaşıklığından ayrıdır.
- Yönetim ekranı sayı değil aksiyon üretir.
- Üniversite → akademik birim → program drill-down korunur.
- Kalite skoru açıklanabilir sinyallerden üretilir; resmî akreditasyon puanı değildir.
- Framework routing öneridir; kalite yöneticisi manuel override yapabilir.

## Teknik durum
- Schema head: `0021_quality_framework_routing`
- Yeni migration yok.
- Mevcut MEDEK/MÜDEK/TURAK/YÖKAK/ESG/ACQUIN routing korunur.
