# DOU Assess 6.70.11 — Accreditation & Evidence Command Center

Bu hotfix mevcut 0042 şemasını değiştirmeden Akreditasyon Merkezi ve Evidence Hub kullanımını sadeleştirir.

## Akreditasyon Merkezi
- "Şimdi ne yapmalı?" karar kartı.
- Öncelik sırası: ölçülmeyen ders → aksiyonsuz Öğrenim Çıktısı açığı → eksik MIN/AVG/MAX kanıtı → sınav kontrol listesi → kanıt paketi.
- Teknik matris, temsilci kayıtları, aksiyon defteri ve sınav detayları `Detaylı akreditasyon analizi` altında korunur.

## Evidence Hub
- Toplam / doğrulanmış / dikkat isteyen / Program Review'da kullanılan kanıt KPI'ları.
- Eksik dosya, hash uyuşmazlığı ve kontrol bekleyen kanıtlar için karar kartı.
- Tek tık sağlık filtreleri.
- Bütünlük durumları teknik enum yerine kullanıcı dostu Türkçe etiketlerle gösterilir.
- Yeni `/api/evidence-hub/summary` endpoint'i mevcut kanıt kayıtlarından anlık sağlık özeti üretir.

## Veri modeli
- Migration yok.
- Schema revision: `0042_performance_production_hardening`.
