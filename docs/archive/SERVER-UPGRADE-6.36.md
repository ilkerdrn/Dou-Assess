# DOU Assess 6.36 — Server Upgrade

Hedef sürüm: `6.36-strategic-quality-management-server-ready`  
Schema head: `0023_strategic_quality`

```bash
chmod +x Upgrade-Server-6.36.sh Verify-6.36.sh
bash Upgrade-Server-6.36.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

> PostgreSQL volume korunur. `docker compose down -v` kullanılmaz.
