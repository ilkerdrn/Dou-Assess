# Server Upgrade 6.34

Mevcut sunucu dizini üzerinde yerinde yükseltme yapılır. PostgreSQL volume silinmez. `docker compose down -v` kullanılmaz. Schema head `0022_quality_calendar` olarak korunur.
