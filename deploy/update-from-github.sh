#!/usr/bin/env bash
# DOU Assess — GitHub'dan çekip sunucuyu güncelleyen betik (pilot compose düzeni).
# Kullanım (depo klasöründe):  bash deploy/update-from-github.sh
# Ortam değişkenleri (isteğe bağlı):
#   ENV_FILE   (varsayılan: ../.env.internal)
#   PROJECT    (varsayılan: dou-assess-619-final-server-ready  -> mevcut veri birimlerini korur)
#   BRANCH     (varsayılan: main)
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE="${ENV_FILE:-../.env.internal}"
PROJECT="${PROJECT:-dou-assess-619-final-server-ready}"
BRANCH="${BRANCH:-main}"
DC=(docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f docker-compose.yml)

[ -f "$ENV_FILE" ] || { echo "HATA: $ENV_FILE bulunamadı."; exit 1; }
set -a; . "$ENV_FILE"; set +a

echo "==> 1/5 Yedek alınıyor"
mkdir -p ../backups
"${DC[@]}" exec -T db pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "../backups/pre-update-$(date +%Y%m%d-%H%M%S).sql.gz"

echo "==> 2/5 GitHub'dan çekiliyor ($BRANCH)"
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"
git log --oneline -1

echo "==> 3/5 İmajlar derleniyor (api, worker, scheduler)"
"${DC[@]}" build

echo "==> 4/5 Servisler başlatılıyor (migration otomatik çalışır)"
"${DC[@]}" up -d

echo "==> 5/5 Sağlık kontrolü"
for i in $(seq 1 30); do
  if curl -fsS "http://localhost:${HTTP_PORT:-8080}/api/health" >/dev/null 2>&1; then
    echo "Sağlıklı."; "${DC[@]}" ps; exit 0
  fi
  sleep 3
done
echo "UYARI: sağlık kontrolü geçmedi. Günlük: ${DC[*]} logs --tail=100 api"; exit 1
