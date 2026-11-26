# DOU Assess 6.18 — Server Deployment

## Ön koşullar
- Linux sunucu
- Docker Engine + Compose
- DNS / HTTPS sertifikası
- Kalıcı PostgreSQL volume
- Kalıcı scan/evidence/ops volume
- Güvenli production `.env`

## Kontrol
```powershell
powershell -ExecutionPolicy Bypass -File .\Server-Ready-Check-6.18.ps1 -EnvFile .env.production
```

## Deployment
```powershell
powershell -ExecutionPolicy Bypass -File .\Deploy-Production-6.18.ps1 -EnvFile .env.production
```

## Deployment sonrası
- `/api/ready` = ready
- schema = `0016_classic_scan_grading`
- `Security-Smoke-6.18.ps1`
- `Verify-Pilot.ps1`
- backup oluşturma + bütünlük testi
- Entra login testi
- akademik Excel validate/import smoke testi
- gerçek sınav tarama smoke testi
