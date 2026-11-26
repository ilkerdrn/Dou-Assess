from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock"
OUT = ROOT / "SBOM-6.70.cdx.json"


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()

components = []
for raw in LOCK.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    name, version = line.split("==", 1)
    norm = canonical(name)
    components.append({
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{norm}@{version}",
    })

sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "serialNumber": "urn:uuid:00000000-0000-4000-8000-000000000670",
    "version": 1,
    "metadata": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": {"type": "application", "name": "DOU Assess", "version": "6.70-production-hardening"},
        "properties": [{"name": "dou-assess:dependency-lock", "value": "requirements.lock"}],
    },
    "components": sorted(components, key=lambda x: x["name"].lower()),
}
OUT.write_text(json.dumps(sbom, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {OUT.name}: {len(components)} components")
