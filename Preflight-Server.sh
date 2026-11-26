#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
PROJECT_NAME="${PROJECT_NAME:-${COMPOSE_PROJECT_NAME:-$(grep -E '^COMPOSE_PROJECT_NAME=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)}}"
PROJECT_NAME="${PROJECT_NAME:-dou-assess-619-final-server-ready}"
fail=0
pass(){ printf '[PASS] %s\n' "$*"; }
warn(){ printf '[WARN] %s\n' "$*"; }
err(){ printf '[FAIL] %s\n' "$*" >&2; fail=1; }
need(){ command -v "$1" >/dev/null 2>&1 && pass "$1" || err "$1 bulunamadı"; }
need docker
need curl
need awk
need grep
need sed
[[ -f RELEASE.env ]] && pass "RELEASE.env mevcut" || err "RELEASE.env eksik"
docker compose version >/dev/null 2>&1 && pass 'Docker Compose v2' || err 'Docker Compose v2 bulunamadı'
[[ -n "$PROJECT_NAME" ]] && pass "Compose project: $PROJECT_NAME" || err "Compose project adı çözümlenemedi"
[[ -f "$COMPOSE_FILE" ]] && pass "$COMPOSE_FILE" || err "$COMPOSE_FILE bulunamadı"
[[ -f "$ENV_FILE" ]] && pass "$ENV_FILE" || err "$ENV_FILE bulunamadı"
[[ -s secrets/postgres_password.txt ]] && pass 'PostgreSQL secret mevcut' || err 'secrets/postgres_password.txt eksik/boş'
if [[ -s secrets/postgres_password.txt ]]; then mode=$(stat -c '%a' secrets/postgres_password.txt 2>/dev/null || true); [[ "$mode" == '600' ]] && pass 'PostgreSQL secret mode 600' || warn "PostgreSQL secret mode ${mode:-?}; chmod 600 önerilir"; fi
if [[ -f "$ENV_FILE" ]]; then
  required=(COMPOSE_PROJECT_NAME APP_ENV POSTGRES_DB POSTGRES_USER PUBLIC_HOSTNAME ALLOWED_HOSTS AUTH_REQUIRED AUTH_PROVIDER ENTRA_TENANT_ID ENTRA_CLIENT_ID ENTRA_AUDIENCE ENTRA_ALLOWED_CLIENT_IDS ENTRA_REQUIRED_SCOPES ENTRA_LOGIN_SCOPES ENTRA_REDIRECT_URI)
  for key in "${required[@]}"; do
    value="$(grep -E "^${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '\r' || true)"
    [[ -n "$value" ]] && pass "$key tanımlı" || err "$key eksik"
  done
  grep -Eq '^APP_ENV=production$' "$ENV_FILE" && pass 'APP_ENV=production' || err 'APP_ENV=production olmalı'
  grep -Eq '^AUTH_REQUIRED=(true|1|yes|on)$' "$ENV_FILE" && pass 'AUTH_REQUIRED açık' || err 'AUTH_REQUIRED=true olmalı'
  grep -Eq '^AUTH_PROVIDER=entra$' "$ENV_FILE" && pass 'AUTH_PROVIDER=entra' || err 'AUTH_PROVIDER=entra olmalı'
  grep -Eq '^PILOT_AUTH_ENABLED=(false|0|no|off)$' "$ENV_FILE" && pass 'Pilot auth kapalı' || err 'PILOT_AUTH_ENABLED=false olmalı'
  grep -Eq '^PILOT_DEMO_ENABLED=(false|0|no|off)$' "$ENV_FILE" && pass 'Pilot demo kapalı' || err 'PILOT_DEMO_ENABLED=false olmalı'
  if grep -Eq '^BACKUP_AUTOMATION_ENABLED=(true|1|yes|on)$' "$ENV_FILE"; then pass 'Otomatik backup açık'; else warn 'BACKUP_AUTOMATION_ENABLED kapalı; 6.68 scheduler backup üretmez'; fi
  if grep -Eq 'CHANGE_ME|example\.com' "$ENV_FILE"; then err 'Production .env içinde placeholder değer var'; else pass 'Placeholder yok'; fi
fi
MEM_KB=$(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0); MEM_GB=$((MEM_KB/1024/1024))
(( MEM_GB >= 8 )) && pass "RAM ${MEM_GB} GB" || warn "RAM ${MEM_GB} GB; 8 GB+ önerilir"
FREE_KB=$(df -Pk . | awk 'NR==2{print $4}'); FREE_GB=$((FREE_KB/1024/1024))
(( FREE_GB >= 20 )) && pass "Boş disk ${FREE_GB} GB" || warn "Boş disk ${FREE_GB} GB; evidence/scan büyümesini planlayın"
if [[ $fail -eq 0 ]]; then
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" config >/dev/null && pass 'Compose config geçerli' || err 'Compose config çözümlenemedi'
fi
[[ $fail -eq 0 ]] || exit 1
echo 'Production preflight PASS'
