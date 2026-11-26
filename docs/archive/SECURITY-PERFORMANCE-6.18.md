# DOU Assess 6.18 — Security & Performance

6.16'daki hardening korunmuştur: rate limit, güvenilir proxy CIDR, güçlü upload doğrulaması, XLSX ZIP-bomb koruması, JWKS cache, PostgreSQL pool/statement timeout, CSP, read-only production container, capability drop, backup SHA-256 ve readiness kontrolleri.

6.18 Excel içe aktarımı aynı XLSX güvenlik doğrulamasından geçer. Workbook önce doğrulanır, ilişki hatası varsa transaction başlamadan reddedilir. Öğretim elemanı yalnız yetkili mevcut derslerine aktarabilir. Excel sınavı yalnız taslak olarak oluşturabilir.

Yük testi:
```powershell
powershell -ExecutionPolicy Bypass -File .\Pilot-Load-Test.ps1 -Requests 500 -Concurrency 20
```
