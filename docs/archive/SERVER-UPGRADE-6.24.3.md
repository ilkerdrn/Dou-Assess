# DOU Assess 6.24.3 Sunucu Yükseltme

1. ZIP'i `/opt/dou-assess` altında ayrı klasöre çıkarın.
2. Çalışan Compose kökünü silmeyin veya yeniden adlandırmayın.
3. Yeni paket içinden:

```bash
chmod +x Upgrade-Server-6.24.3.sh Verify-6.24.3.sh
bash Upgrade-Server-6.24.3.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

Beklenen uygulama sürümü `6.24-final-design-server-ready`, şema `0020_assessment_intelligence`.

`docker compose down -v`, `docker volume prune` veya canlı PostgreSQL volume'ünü silen komutlar kullanılmamalıdır.
