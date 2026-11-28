from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_654_version_and_schema_contract():
    main = (ROOT / 'app/main.py').read_text(encoding='utf-8')
    assert 'APP_VERSION = "6.70-production-hardening"' in main
    assert 'EXPECTED_SCHEMA_REVISION = "0048_question_bank_versions"' in main


def test_654_deployment_scripts_are_current():
    verify = (ROOT / 'Verify-Server.sh').read_text(encoding='utf-8')
    upgrade = (ROOT / 'Upgrade-Server.sh').read_text(encoding='utf-8')
    preflight = (ROOT / 'Preflight-Server.sh').read_text(encoding='utf-8')
    assert '6.70-production-hardening' in verify
    assert '0048_question_bank_versions' in verify
    assert '6.70-production-hardening' in upgrade
    assert '0048_question_bank_versions' in upgrade
    assert 'APP_ENV=production' in preflight
    assert 'PILOT_AUTH_ENABLED=false' in preflight


def test_654_production_assets_exist():
    for name in [
        'docker-compose.production.yml', '.env.production.example',
        'Install-Server.sh', 'Upgrade-Server.sh', 'Backup-Server.sh',
        'Restore-Server.sh', 'Production-GoLive.sh',
        'PRODUCTION-DEPLOYMENT-6.54.md', 'nginx/host-reverse-proxy.example.conf',
    ]:
        assert (ROOT / name).is_file(), name
