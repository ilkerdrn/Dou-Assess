from __future__ import annotations

import os
from pathlib import Path


def _load_release_file() -> dict[str, str]:
    candidates = [
        Path(os.getenv("DOU_ASSESS_RELEASE_FILE", "")).expanduser() if os.getenv("DOU_ASSESS_RELEASE_FILE") else None,
        Path(__file__).resolve().parent.parent / "RELEASE.env",
        Path.cwd() / "RELEASE.env",
    ]
    for path in candidates:
        if not path or not path.is_file():
            continue
        data: dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
        return data
    return {}


_RELEASE = _load_release_file()

def _value(name: str, default: str) -> str:
    return os.getenv(name, _RELEASE.get(name, default)).strip() or default

APP_VERSION = _value("APP_VERSION", "dev")
RELEASE_VERSION = _value("RELEASE_VERSION", APP_VERSION)
UI_ASSET_VERSION = _value("UI_ASSET_VERSION", APP_VERSION)
EXPECTED_SCHEMA_REVISION = _value("EXPECTED_SCHEMA_REVISION", "unknown")
BUILD_SHA = _value("BUILD_SHA", "source")
BUILD_TIME = _value("BUILD_TIME", "unknown")
DEPLOY_TOOLING_VERSION = _value("DEPLOY_TOOLING_VERSION", RELEASE_VERSION)

def build_metadata() -> dict[str, str]:
    return {
        "version": APP_VERSION,
        "release": RELEASE_VERSION,
        "asset_version": UI_ASSET_VERSION,
        "schema_expected": EXPECTED_SCHEMA_REVISION,
        "build_sha": BUILD_SHA,
        "build_time": BUILD_TIME,
        "deploy_tooling": DEPLOY_TOOLING_VERSION,
    }
