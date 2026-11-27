from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_final_version_and_schema_contract():
    assert '6.70-production-hardening' in MAIN
    assert 'EXPECTED_SCHEMA_REVISION = "0047_institution_settings_outcome_approval"' in MAIN
    assert '6.70-production-hardening' in README
    assert '0042_performance_production_hardening' in README


def test_final_release_has_single_upgrade_verify_entrypoints():
    assert (ROOT / "Upgrade-Server.sh").is_file()
    assert (ROOT / "Verify-Server.sh").is_file()
    assert (ROOT / "Preflight-Server.sh").is_file()
    assert not list(ROOT.glob("Upgrade-Server-*.sh"))
    assert not list(ROOT.glob("Verify-6.*.sh"))


def test_preintegration_boundary_is_explicit():
    doc = (ROOT / "docs/PRE-INTEGRATION-READINESS-6.37.md").read_text(encoding="utf-8")
    assert "Microsoft Entra ID" in doc
    assert "OBS" in doc
    assert "20k öğrenci / 600 hoca" in doc
