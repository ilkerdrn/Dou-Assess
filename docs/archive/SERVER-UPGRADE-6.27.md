# DOU Assess 6.27 Sunucu Yükseltme

Yeni paket ayrı klasöre çıkarılır ve mevcut çalışan klasör hedeflenir:

```bash
chmod +x Upgrade-Server-6.27.sh Verify-6.27.sh
bash Upgrade-Server-6.27.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

Beklenen sürüm: `6.27-university-quality-os-server-ready`
Beklenen schema: `0021_quality_framework_routing`

`docker compose down -v` kullanılmaz. PostgreSQL volume silinmez.
