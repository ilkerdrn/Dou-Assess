# DOU Assess 6.31 Server Upgrade

Beklenen sürüm: `6.31-quality-calendar-governance-server-ready`  
Beklenen şema: `0022_quality_calendar`

Mevcut kalıcı PostgreSQL/kanıt verileri korunur. `docker compose down -v` kullanılmaz.

```bash
chmod +x Upgrade-Server-6.31.sh Verify-6.31.sh
bash Upgrade-Server-6.31.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```
