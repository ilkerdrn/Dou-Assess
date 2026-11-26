# DOU Assess 6.18.4 — Sunucu Yayın Kontrol Listesi

## Paket durumu

- Uygulama sürümü: `6.18.4`
- Alembic head: `0016_classic_scan_grading`
- Production veritabanı: PostgreSQL 17
- Reverse proxy iç katman: NGINX
- Uygulama konteyneri: read-only filesystem, `cap_drop: ALL`, `no-new-privileges`
- Kalıcı alanlar: PostgreSQL, evidence, scans, ops

## 1. Sunucuda ön koşullar

- Docker Engine / Docker Desktop + Compose v2
- TLS sonlandıran kurum reverse proxy'si veya load balancer
- DNS kaydı, ör. `assess.dogus.edu.tr`
- Microsoft Entra app registration değerleri
- En az 24 karakterlik PostgreSQL parolası
- Kurum OBS endpoint/token bilgisi kullanılacaksa ilgili sözleşme

## 2. Production env

```powershell
Copy-Item .env.production.example .env.production
```

`.env.production` içinde `CHANGE_ME` bırakmayın. Özellikle:

- `PUBLIC_HOSTNAME`
- `ALLOWED_HOSTS`
- `TRUSTED_PROXY_CIDRS`
- `ENTRA_TENANT_ID`
- `ENTRA_CLIENT_ID`
- `ENTRA_AUDIENCE`
- `ENTRA_ALLOWED_CLIENT_IDS`
- `ENTRA_REQUIRED_SCOPES`
- `ENTRA_LOGIN_SCOPES`
- `ENTRA_REDIRECT_URI`

## 3. PostgreSQL secret

`secrets/postgres_password.txt` içine yalnız production parolasını yazın. Dosya repoya/ZIP dışına kopyalanmamalı ve erişimi sunucuda sınırlandırılmalıdır.

## 4. Preflight

```powershell
powershell -ExecutionPolicy Bypass -File .\Production-Preflight.ps1 -EnvFile .env.production
```

Preflight; placeholder, secret uzunluğu, upload limitleri, compose config, container hardening, scan volume ve NGINX limitlerini kontrol eder.

## 5. Deployment

```powershell
powershell -ExecutionPolicy Bypass -File .\Deploy-Production-6.18.ps1 -EnvFile .env.production
```

`migrate` servisi API başlamadan önce `alembic upgrade head` çalıştırır.

## 6. TLS reverse proxy

Production compose varsayılan olarak yalnız:

`127.0.0.1:8080`

üzerinden yayın yapar. Kurum TLS reverse proxy'si HTTPS trafiğini bu adrese iletmelidir. `X-Forwarded-Proto`, `X-Forwarded-For` ve host bilgileri yalnız `TRUSTED_PROXY_CIDRS` içindeki güvenilir proxy'den kabul edilmelidir.

## 7. İlk sağlık kontrolü

TLS adresinden:

- `/api/health` → `200`
- `/api/ready` → `status=ready`
- `/api/ready` → `schema_revision=0016_classic_scan_grading`
- `/api/ready` → evidence/scans/ops storage hazır

## 8. Kabul testi

Production verisini kullanmadan test dersi ile:

1. 1 test + 1 klasik rubrikli sınav oluşturun.
2. Bir öğrenciyi sınava atayın.
3. Öğrenci kağıdını üretin.
4. PDF veya fiziksel ADF taramasını yükleyin.
5. Tarama oturumunda `support_count >= 1` doğrulayın.
6. Puanlama ekranında klasik cevap görselini açın.
7. Rubriği puanlayıp kaydedin.
8. Toplam not/analiz sonuçlarını kontrol edin.

## 9. Backup / restore

İlk gerçek veri girişinden önce backup alın ve boş bir test ortamına restore tatbikatı yapın. Backup; PostgreSQL ile birlikte evidence, scans ve ops alanlarını kapsamalıdır.

## 10. Kurumda tamamlanacak saha işleri

Bu paket kod/config tarafını hazırlar; aşağıdakiler kurum erişimi gerektirir:

- gerçek Entra tenant kabulü
- gerçek OBS sonucu gönderme sözleşmesi
- TLS/DNS
- fiziksel ADF/tarayıcı kalite testi
- kurum backup hedefi ve geri dönüş tatbikatı
- KVKK saklama/anonimleştirme süresinin kurum kararıyla onayı
