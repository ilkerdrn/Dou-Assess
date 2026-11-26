# 6.20 → 6.22 Sunucu Yükseltmesi

6.22 veritabanı şemasını değiştirmez; mevcut PostgreSQL ve persistent volume kimlikleri korunur.

```bash
cd /opt/dou-assess/DOU-Assess-6.22-PREMIUM-UX-SERVER-READY
chmod +x Upgrade-Server-6.22.sh Verify-6.22.sh
bash Upgrade-Server-6.22.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

Canlı Compose kökü 6.19 isimli klasörde olsa bile 6.20 koduyla çalışıyor olabilir; `--current-dir` çalışan Compose klasörünü göstermelidir. `docker compose down -v` kullanmayın.
