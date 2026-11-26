#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"; COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
PROJECT_NAME="${PROJECT_NAME:-${COMPOSE_PROJECT_NAME:-$(grep -E '^COMPOSE_PROJECT_NAME=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)}}"
PROJECT_NAME="${PROJECT_NAME:-dou-assess-619-final-server-ready}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"; OUT="${1:-$ROOT/backups/$STAMP}"; mkdir -p "$OUT"; chmod 700 "$OUT"
C=(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE")
"${C[@]}" ps db >/dev/null
"${C[@]}" exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$OUT/postgresql.dump"
"${C[@]}" exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only' > "$OUT/postgresql-schema.sql"
"${C[@]}" exec -T api sh -lc 'cd /app/data && tar --exclude=ops/automated-backups -czf - evidence scans ops' > "$OUT/persistent-data.tar.gz"

# .env and secrets/ hold the production DB password and other credentials; never
# write them to disk unencrypted. Require an explicit key rather than silently
# falling back to a plaintext copy.
: "${BACKUP_ENCRYPTION_KEY:?BACKUP_ENCRYPTION_KEY ayarlanmadan .env/secrets yedeklenemez (şifresiz yedek riski). Önce: export BACKUP_ENCRYPTION_KEY=\$(openssl rand -base64 48)}"
tar -C "$ROOT" -cf - "$(basename "$ENV_FILE")" secrets \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_ENCRYPTION_KEY -out "$OUT/secrets-and-env.tar.enc"
chmod 600 "$OUT/secrets-and-env.tar.enc"

sha256sum "$OUT"/postgresql.dump "$OUT"/persistent-data.tar.gz "$OUT"/secrets-and-env.tar.enc > "$OUT/SHA256SUMS.txt"
(cd "$OUT" && sha256sum -c SHA256SUMS.txt >/dev/null)
tar -tzf "$OUT/persistent-data.tar.gz" >/dev/null
cat "$OUT/postgresql.dump" | "${C[@]}" exec -T db sh -lc 'pg_restore --list >/dev/null'
# Disaster recovery only: Restore-Server.sh does not need or read this file, it
# uses the live server's own .env/secrets. To recover .env/secrets from a backup:
#   openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_ENCRYPTION_KEY -in secrets-and-env.tar.enc | tar -xf -
echo "$OUT"
