# DOU Assess 6.32 — Sunucu Yükseltme

Beklenen sürüm: `6.32-closed-loop-quality-operations-server-ready`  
Beklenen şema: `0022_quality_calendar`

```bash
chmod +x Upgrade-Server-6.32.sh Verify-6.32.sh
bash Upgrade-Server-6.32.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

Bu sürüm yeni migration içermez. `.env`, secrets, PostgreSQL ve kalıcı evidence/scans/ops volume'leri korunur. `docker compose down -v` kullanılmaz.
