# DOU Assess 6.32 — Closed Loop Quality Operations

Sürüm: `6.32-closed-loop-quality-operations-server-ready`  
Schema: `0022_quality_calendar`

## Yeni
- Kurul kararı → PUKÖ dönüşümü.
- Karar bazlı duplicate açık PUKÖ koruması.
- Sorumlu + termin ataması.
- PUKÖ kapanış hazırlığı servisi.
- Gerçek kalite kanıtı olmadan kapanışı engelleyen kontrol.
- İnsan onaylı, audit izli kapanış.
- Quality360 içinde “Karardan Aksiyona” ve “Kanıttan Kapanışa” çalışma alanları.

## Güvenlik / yönetişim
Sistem otomatik kapanış yapmaz. `admin`, `quality` veya `program_head` rolü gerçek kanıtı inceleyip kapanış notu girmeden PUKÖ kapanmaz.

Yeni migration yoktur; mevcut `0022_quality_calendar` şeması korunur.
