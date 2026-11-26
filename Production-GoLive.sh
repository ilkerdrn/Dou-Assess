#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"; cd "$ROOT"
MODE="${1:-install}"
case "$MODE" in
  install) bash Install-Server.sh;;
  upgrade) bash Upgrade-Server.sh;;
  verify) bash Verify-Server.sh;;
  *) echo 'Kullanım: bash Production-GoLive.sh {install|upgrade|verify}' >&2; exit 2;;
esac
