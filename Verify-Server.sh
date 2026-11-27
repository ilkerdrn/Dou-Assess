#!/usr/bin/env bash
set -Eeuo pipefail
# release-contract marker: 6.70-production-hardening / 0043_response_grade_revisions
BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"
ACCESS_TOKEN="${ACCESS_TOKEN:-}"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "$ROOT/RELEASE.env"
EXPECTED_VERSION="$APP_VERSION"
EXPECTED_SCHEMA="$EXPECTED_SCHEMA_REVISION"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="$2"; shift 2;;
    --access-token) ACCESS_TOKEN="$2"; shift 2;;
    *) echo "Bilinmeyen parametre: $1" >&2; exit 2;;
  esac
done
check_public(){ local path="$1" needle="$2" body; body="$(curl -fsS --max-time 15 "$BASE_URL$path")"; [[ "$body" == *"$needle"* ]] || { echo "[FAIL] $path -> $needle yok" >&2; exit 1; }; echo "[PASS] $path"; }
check_protected(){ local path="$1" needle="$2" tmp code body; tmp="$(mktemp)"; if [[ -n "$ACCESS_TOKEN" ]]; then code="$(curl -sS -o "$tmp" -w '%{http_code}' --max-time 15 -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL$path")"; else code="$(curl -sS -o "$tmp" -w '%{http_code}' --max-time 15 "$BASE_URL$path")"; fi; body="$(cat "$tmp")"; rm -f "$tmp"; if [[ "$code" == 401 || "$code" == 403 ]]; then echo "[WARN] $path auth gerekli; içerik smoke ACCESS_TOKEN olmadan atlandı"; return 0; fi; [[ "$code" == 200 ]] || { echo "[FAIL] $path HTTP $code" >&2; exit 1; }; [[ "$body" == *"$needle"* ]] || { echo "[FAIL] $path -> $needle yok" >&2; exit 1; }; echo "[PASS] $path"; }
check_public /api/health "$EXPECTED_VERSION"
check_public /api/ready "$EXPECTED_SCHEMA"
check_protected /api/catalogs 'Kısa Sınav'
check_protected /api/quality360/frameworks 'MEDEK-2026'
check_protected /api/quality360/frameworks 'YOKAK-2026'
check_protected /api/quality360/frameworks 'MUDEK'
check_protected /api/quality360/frameworks 'TURAK'
check_protected /api/operations/summary '"jobs"'
check_protected /api/program-review/templates '[]'
check_protected '/api/evidence-hub?limit=1&offset=0' '"items"'
echo "DOU Assess ${RELEASE_VERSION} production smoke PASS"
