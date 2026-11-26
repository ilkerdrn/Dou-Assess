#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $# -eq 1 ]] || { echo 'Kullanım: bash Restore-Server.sh /path/to/backup' >&2; exit 2; }
BACKUP="$(cd "$1" && pwd -P)"; ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"; COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
PROJECT_NAME="${PROJECT_NAME:-${COMPOSE_PROJECT_NAME:-$(grep -E '^COMPOSE_PROJECT_NAME=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)}}"
PROJECT_NAME="${PROJECT_NAME:-dou-assess-619-final-server-ready}"
C=(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE")
[[ -s "$BACKUP/postgresql.dump" ]] || { echo '[FAIL] postgresql.dump yok' >&2; exit 1; }
[[ -s "$BACKUP/persistent-data.tar.gz" ]] || { echo '[FAIL] persistent-data.tar.gz yok' >&2; exit 1; }
if [[ -s "$BACKUP/SHA256SUMS.txt" ]]; then (cd "$BACKUP" && sha256sum -c SHA256SUMS.txt) || { echo '[FAIL] backup checksum doğrulanamadı' >&2; exit 1; }; fi
echo 'UYARI: Restore mevcut veritabanını değiştirir.'
[[ "${CONFIRM_RESTORE:-}" == 'YES' ]] || { echo 'CONFIRM_RESTORE=YES olmadan çalışmaz.' >&2; exit 1; }
"${C[@]}" stop api worker scheduler nginx migrate || true
"${C[@]}" up -d db
"${C[@]}" exec -T db sh -lc 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
cat "$BACKUP/postgresql.dump" | "${C[@]}" exec -T db sh -lc 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges'
"${C[@]}" run --rm migrate
cat "$BACKUP/persistent-data.tar.gz" | "${C[@]}" run --rm --no-deps -T api sh -lc 'cd /app/data && tar -xzf -'
"${C[@]}" up -d api worker scheduler nginx
bash Verify-Server.sh
