# DOU Assess 6.25 Sunucu Yükseltme

6.25 yeni veritabanı migration'ı taşımaz. Mevcut `0020_assessment_intelligence` şeması korunur.

```bash
chmod +x Upgrade-Server-6.25.sh Verify-6.25.sh
bash Upgrade-Server-6.25.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

Script PostgreSQL dump, persistent data checkpoint ve kod checkpoint alır; `.env`, `secrets` ve Docker named volume kimliğini korur. `docker compose down -v` kullanmaz.
