# DOU Assess 6.33 Server Upgrade

Mevcut production/pilot verisini yerinde korumak için `Upgrade-Server-6.33.sh` kullanılır.

```bash
chmod +x Upgrade-Server-6.33.sh Verify-6.33.sh
bash Upgrade-Server-6.33.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

`docker compose down -v` çalıştırmayın. PostgreSQL ve kalıcı evidence/scan/ops volume'larını silmeyin.

Beklenen sürüm: `6.33-evidence-readiness-visit-mode-server-ready`
Schema: `0022_quality_calendar`
