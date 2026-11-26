# DOU Assess 6.54 — Final Production Release

Bu release feature expansion yapmaz. 6.53 fonksiyonel baseline'ını production deployment için mühürler.

- APP_VERSION: `6.54-final-production-release`
- Schema: `0031_medek_final_decision` (migration değişmedi)
- Eski Upgrade/Verify scriptlerindeki 6.48/6.49 sürüm drift'i kaldırıldı.
- Production preflight gerçek Entra/auth/hostname/secrets kontrolleri yapar.
- Fresh install ve in-place upgrade akışları ayrıldı.
- PostgreSQL + evidence/scans/ops backup scripti eklendi.
- Explicit-confirm restore scripti eklendi.
- Stable `COMPOSE_PROJECT_NAME=dou_assess` ile named volume continuity dokümante edildi.
- Host TLS reverse proxy örneği eklendi.
- Tek giriş noktası: `Production-GoLive.sh`.
