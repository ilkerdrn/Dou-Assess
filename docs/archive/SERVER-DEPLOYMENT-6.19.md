# DOU Assess 6.19 — Sunucu Kurulumu

## Mimari

Production compose:

- PostgreSQL 17
- Alembic migrate service
- FastAPI / 2 worker
- NGINX internal reverse proxy
- Persistent volumes: PostgreSQL, evidence, scans, ops
- Varsayılan bind: `127.0.0.1:8080`

Kurumun TLS reverse proxy/load balancer katmanı HTTPS trafiğini bu bind adresine iletmelidir.

## 1. Dosyaları sunucuya alın

Final ZIP'i ayrı bir dizine çıkarın. Eski sürümün üzerine dosya kopyalamayın.

## 2. Production env

```powershell
Copy-Item .env.production.example .env.production
```

`.env.production` içinde `CHANGE_ME` bırakmayın. Özellikle:

- `PUBLIC_HOSTNAME`
- `ALLOWED_HOSTS`
- `TRUSTED_PROXY_CIDRS`
- Microsoft Entra tenant/client/audience/scope/redirect değerleri
- upload/PDF/image sınırları
- DB pool/statement timeout

## 3. PostgreSQL secret

```text
secrets\postgres_password.txt
```

En az 24 karakterlik rastgele production parolası kullanın. Parolayı Git/ZIP'e eklemeyin.

## 4. Preflight

```powershell
powershell -ExecutionPolicy Bypass -File .\Production-Preflight.ps1 -EnvFile .env.production
powershell -ExecutionPolicy Bypass -File .\Server-Ready-Check-6.19.ps1 -EnvFile .env.production
```

## 5. Deploy

```powershell
powershell -ExecutionPolicy Bypass -File .\Deploy-Production-6.19.ps1 -EnvFile .env.production
```

`migrate` servisi API başlamadan önce `alembic upgrade head` çalıştırır.

## 6. İlk sağlık kontrolü

TLS adresinden:

- `/api/health` → HTTP 200
- `/api/ready` → `status=ready`
- `/api/ready` → `schema_revision=0018_classic_assessment_standard`
- evidence/scans/ops storage hazır

## 7. İlk kurum kabulü

Production verisini kullanmadan test dersi ile:

1. Bir Öğretim Görevlisi hesabını Entra üzerinden doğrulayın.
2. Test dersini ve 2 öğrenciyi yükleyin.
3. 1 test + 1 klasik sorulu, toplam 100 puan sınav oluşturun.
4. Klasik soruya beklenen cevap + ÖÇ + analitik rubrik ekleyin.
5. Kağıdı üretin ve fiziksel ADF/PDF ile tarayın.
6. OMR sonucu ve klasik crop görüntüsünü doğrulayın.
7. Bir öğrenciyi `absent` yapıp analiz paydasından çıktığını doğrulayın.
8. Klasik rubriği puanlayın.
9. Puanları kilitleyin; normal değişiklik girişiminin reddedildiğini doğrulayın.
10. Test itirazı açıp kontrollü rubrik yeniden değerlendirme yapın.
11. Kalite/ÖÇ sonucunu ve kanıt paketini üretin.

## 8. Backup / restore

İlk gerçek veri girişinden önce backup alın ve ayrı test ortamına restore tatbikatı yapın:

```powershell
powershell -ExecutionPolicy Bypass -File .\Backup-Pilot.ps1
powershell -ExecutionPolicy Bypass -File .\Backup-Integrity-Test-6.19.ps1 -CreateBackup
```

Restore scripti SHA-256 doğrulaması ve migration sonrasında veriyi geri yükler.

## 9. Saha dış bağımlılıklar

Final yazılım paketi aşağıdaki dış sistemleri kendi başına doğrulayamaz:

- Gerçek Microsoft Entra tenant/app registration
- Gerçek OBS API alan sözleşmesi/token
- TLS/DNS
- Fiziksel ADF tarayıcı ve kağıt baskı kalibrasyonu
- Kurum backup hedefi
- Hedef sunucuda gerçek eşzamanlı yük testi
