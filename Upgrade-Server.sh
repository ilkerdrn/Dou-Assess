#!/usr/bin/env bash
set -Eeuo pipefail
# release-contract marker: 6.70-production-hardening / 0048_question_bank_versions
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"; COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
PROJECT_NAME="${PROJECT_NAME:-${COMPOSE_PROJECT_NAME:-$(grep -E '^COMPOSE_PROJECT_NAME=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)}}"
PROJECT_NAME="${PROJECT_NAME:-dou-assess-619-final-server-ready}"
C=(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE")
HTTP_PORT_EFFECTIVE="${HTTP_PORT:-$(grep -E '^HTTP_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)}"
HTTP_PORT_EFFECTIVE="${HTTP_PORT_EFFECTIVE:-8080}"
source "$ROOT/RELEASE.env"; EXPECTED_VERSION="$APP_VERSION"; EXPECTED_SCHEMA="$EXPECTED_SCHEMA_REVISION"
bash Preflight-Server.sh
BACKUP_DIR="$(bash Backup-Server.sh)"; echo "Backup: $BACKUP_DIR"
"${C[@]}" build --pull api migrate worker scheduler
"${C[@]}" up -d db
"${C[@]}" run --rm migrate
"${C[@]}" up -d api worker scheduler nginx
for _ in $(seq 1 90); do READY="$(curl -fsS --max-time 4 http://127.0.0.1:${HTTP_PORT_EFFECTIVE}/api/ready 2>/dev/null || true)"; [[ "$READY" == *"$EXPECTED_SCHEMA"* ]] && break; sleep 2; done
HEALTH="$(curl -fsS --max-time 8 http://127.0.0.1:${HTTP_PORT_EFFECTIVE}/api/health)"; READY="$(curl -fsS --max-time 8 http://127.0.0.1:${HTTP_PORT_EFFECTIVE}/api/ready)"
[[ "$HEALTH" == *"$EXPECTED_VERSION"* ]] || { echo '[FAIL] sürüm doğrulanamadı' >&2; exit 1; }
[[ "$READY" == *"$EXPECTED_SCHEMA"* ]] || { echo '[FAIL] schema doğrulanamadı' >&2; exit 1; }
bash Verify-Server.sh --base-url "http://127.0.0.1:${HTTP_PORT_EFFECTIVE}"
"${C[@]}" ps
echo "DOU Assess upgrade PASS · rollback backup: $BACKUP_DIR"
