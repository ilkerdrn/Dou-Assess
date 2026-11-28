from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_0032_uses_postgresql_boolean_literals():
    text = (ROOT / "migrations/versions/0032_academic_structure_foundation.py").read_text(encoding="utf-8")
    assert "'migration',1,:dt)" not in text
    assert "'required',1,:dt)" not in text
    assert text.count("TRUE,:dt)") >= 4


def test_release_metadata_marks_canonical_hotfix():
    release = dict(
        line.split("=", 1)
        for line in (ROOT / "RELEASE.env").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    assert release["RELEASE_VERSION"] == "6.70"
    assert release["DEPLOY_TOOLING_VERSION"] == "6.70"
    assert release["APP_VERSION"] == "6.70-production-hardening"
    assert release["EXPECTED_SCHEMA_REVISION"] == "0048_question_bank_versions"
