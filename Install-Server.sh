#!/usr/bin/env bash
set -Eeuo pipefail
# release-contract marker: 6.70-production-hardening / 0043_response_grade_revisions
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"; COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
PROJECT_NAME="${PROJECT_NAME:-${COMPOSE_PROJECT_NAME:-$(grep -E '^COMPOSE_PROJECT_NAME=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)}}"
PROJECT_NAME="${PROJECT_NAME:-dou-assess-619-final-server-ready}"
C=(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE")
HTTP_PORT_EFFECTIVE="${HTTP_PORT:-$(grep -E '^HTTP_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)}"
HTTP_PORT_EFFECTIVE="${HTTP_PORT_EFFECTIVE:-8080}"
bash Preflight-Server.sh
"${C[@]}" pull db nginx || true
"${C[@]}" build --pull api migrate worker scheduler
"${C[@]}" up -d db
"${C[@]}" run --rm migrate
"${C[@]}" up -d api worker scheduler nginx
for _ in $(seq 1 90); do if curl -fsS --max-time 3 http://127.0.0.1:"${HTTP_PORT_EFFECTIVE}"/api/ready >/dev/null 2>&1; then break; fi; sleep 2; done
bash Verify-Server.sh --base-url "http://127.0.0.1:${HTTP_PORT_EFFECTIVE}"
"${C[@]}" ps
echo 'DOU Assess production install PASS'
