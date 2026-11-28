# DOU Assess 6.70.9 — Student Success & Decision Dashboard

## Amaç
Öğrenci Karnesi, sınav raporları ve kalite dashboard'unu veri kalabalığından çıkarıp karar odaklı hale getirmek.

## Öğrenci Karnesi
- Üstte karar özeti ve önerilen sonraki adım.
- Risk varsa gelişim odağına doğrudan geçiş.
- PDF karnesine tek tık erişim.
- Mevcut ÖÇ/PÇ, ders gelişimi, doğrulama ve mezuniyet snapshot fonksiyonları korunur.

## Sınav Analiz / Raporlama
- İlk ekranda yönetici özeti.
- Sınıf başarısı, başarı oranı, ÖÇ ve PÇ durumu dört temel KPI ile öne çıkar.
- Medyan, standart sapma, Cronbach Alpha ve KR-20 teknik ayrıntılara taşınır.
- Risk varsa ÖÇ/soru/öğrenci detayına tek tık geçiş.

## Kalite Dashboard
- İlk ekranda kalite kararı ve aksiyonsuz açık sayısı.
- Dört temel KPI.
- Riskli dersler ve "Şimdi ne yapmalı?" kısa yolları önde.
- Heatmap ve dönem trendi `Detaylı kalite analizi` altında açılır.
- Mevcut drill-down ve Excel raporu korunur.

## Teknik
- DB migration yok.
- Schema: 0042_performance_production_hardening
- Asset cache key: 6709-decision-dashboard
- Full regression: 297/297 PASS
