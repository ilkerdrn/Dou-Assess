# DOU Assess 6.23 Sunucu Yükseltme

Mevcut 6.22/6.20 çalışan Compose proje kökünü ve volume kimliğini korur. Önce PostgreSQL dump + kalıcı veri checkpoint alınır, sonra kod uygulanır ve `0020_assessment_intelligence` migration çalıştırılır.

```bash
bash Upgrade-Server-6.23.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

`docker compose down -v` kullanılmaz. `.env`, secrets, PostgreSQL, evidence, scans ve ops korunur.
