# DOU Assess 6.29 Server Upgrade

Mevcut çalışan Compose proje kökü korunarak çalıştırın:

```bash
bash Upgrade-Server-6.29.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

Script `.env`, secrets ve kalıcı Docker volume'lerini korur. `docker compose down -v` kullanmaz.
Schema değişmez: `0021_quality_framework_routing`.
