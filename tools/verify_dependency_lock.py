from __future__ import annotations

import importlib.metadata as md
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock"


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_lock() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for raw in LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise SystemExit(f"Unpinned dependency in {LOCK.name}: {line}")
        name, version = line.split("==", 1)
        out[canonical(name)] = (name, version)
    return out


def main() -> int:
    expected = parse_lock()
    installed = {canonical(d.metadata["Name"]): d.version for d in md.distributions() if d.metadata.get("Name")}
    failures: list[str] = []
    for key, (name, version) in expected.items():
        actual = installed.get(key)
        if actual is None:
            failures.append(f"MISSING {name}=={version}")
        elif actual != version:
            failures.append(f"MISMATCH {name}: expected {version}, installed {actual}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"LOCK PASS: {len(expected)} pinned production packages match the runtime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
