# DOU Assess 6.54.1 — Production Deployment Hotfix

Application: `6.54-final-production-release`
Deploy tooling: `6.54.1`  
Schema: `0031_medek_final_decision`

## 1. Sunucu gereksinimi
- Linux x86_64
- Docker Engine + Docker Compose v2
- En az 8 GB RAM önerilir
- En az 20 GB boş başlangıç diski; evidence/scan büyümesi ayrıca planlanır
- 80/443 host NGINX'e; container NGINX varsayılan olarak yalnız `127.0.0.1:8080` dinler

## 2. İlk kurulum
```bash
sudo mkdir -p /opt/dou-assess/releases
sudo unzip DOU-Assess-6.54-FINAL-PRODUCTION-SERVER-READY.zip -d /opt/dou-assess/releases/
cd /opt/dou-assess/releases/DOU-Assess-6.54-FINAL-PRODUCTION-SERVER-READY
cp .env.production.example .env
mkdir -p secrets
openssl rand -base64 48 | tr -d '\n' | sudo tee secrets/postgres_password.txt >/dev/null
sudo chmod 600 secrets/postgres_password.txt
# .env içindeki Entra / hostname değerlerini gerçek değerlerle doldurun
bash Preflight-Server.sh
bash Production-GoLive.sh install
```

## 3. Mevcut kurulum yükseltme
Release klasöründeki `.env` ve `secrets/` gerçek production değerleriyle mevcut kurulumdan taşınır. `COMPOSE_PROJECT_NAME=dou_assess` sabit kaldığı için named volume'ler release klasörü değişse bile korunur.
```bash
bash Production-GoLive.sh upgrade
```
Upgrade başlamadan PostgreSQL + evidence/scans/ops backup alınır.

## 4. TLS / domain
`nginx/host-reverse-proxy.example.conf` host NGINX'e örnektir. TLS sertifikası kurum tarafından yönetilir. Uygulama container'ı doğrudan internete açılmaz.

## 5. Go-live doğrulama
```bash
bash Production-GoLive.sh verify
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/ready
```
Beklenen sürüm: `6.54-final-production-release`  
Beklenen schema: `0031_medek_final_decision`

## 6. Backup / restore
```bash
bash Backup-Server.sh
CONFIRM_RESTORE=YES bash Restore-Server.sh /path/to/backup
```
Restore işlemi destructive olduğu için explicit `CONFIRM_RESTORE=YES` ister.

## 7. Sunucuya çıkmadan doldurulması zorunlu dış bağımlılıklar
- Gerçek Microsoft Entra tenant/client/audience/scope/redirect bilgileri
- `assess.dogus.edu.tr` DNS/TLS veya kurumun seçtiği gerçek hostname
- Gerçek production PostgreSQL secret
- OBS/Proliz entegrasyonu devreye alınacaksa gerçek endpoint/contract/token

Bu dış bilgiler olmadan paket lokal olarak valid olsa da kurumsal production login/integration acceptance tamamlanmış sayılmaz.


## 8. 6.54.1 deploy-only hardening
- Install/upgrade smoke checks now read `HTTP_PORT` from `.env`.
- Backup output uses private `umask 077` and directory mode 700.
- Restore verifies `SHA256SUMS.txt` when present.
- Preflight reports PostgreSQL secret permission mode.
- Application/schema are unchanged from 6.54.
