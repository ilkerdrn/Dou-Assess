#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
python tools/verify_dependency_lock.py
python -m pip check
python - <<'PY'
import json
from pathlib import Path
p=Path('SBOM-6.70.cdx.json')
d=json.loads(p.read_text())
assert d['bomFormat']=='CycloneDX'
assert d['metadata']['component']['version']=='6.70-production-hardening'
assert len(d.get('components',[])) >= 30
print(f"SBOM PASS: {len(d['components'])} components")
PY
if command -v pip-audit >/dev/null 2>&1; then
  pip-audit -r requirements.lock
else
  echo "INFO: pip-audit not installed in this runtime; vulnerability DB scan was not executed."
fi
if command -v trivy >/dev/null 2>&1; then
  trivy fs --scanners vuln,secret --exit-code 1 .
else
  echo "INFO: trivy not installed in this runtime; filesystem vulnerability scan was not executed."
fi
