# Server Upgrade 6.35

Mevcut veri ve Docker volume korunur. `docker compose down -v` kullanılmaz.

```bash
chmod +x Upgrade-Server-6.35.sh Verify-6.35.sh
bash Upgrade-Server-6.35.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```
