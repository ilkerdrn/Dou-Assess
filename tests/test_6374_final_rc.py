from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_compose_forces_pilot_kill_switches():
    text = (ROOT / 'docker-compose.production.yml').read_text(encoding='utf-8')
    assert 'PILOT_AUTH_ENABLED: "false"' in text
    assert 'PILOT_DEMO_ENABLED: "false"' in text
    assert 'AUTH_PROVIDER: entra' in text


def test_production_env_documents_pilot_kill_switches():
    text = (ROOT / '.env.production.example').read_text(encoding='utf-8')
    assert 'PILOT_AUTH_ENABLED=false' in text
    assert 'PILOT_DEMO_ENABLED=false' in text


def test_ui_uses_expanded_outcome_terms():
    static = ROOT / 'app' / 'static'
    joined = '\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in static.rglob('*') if p.is_file() and p.suffix in {'.html','.js','.css'})
    # User-facing language should prefer explicit terms. Legacy release-note comments are not user-visible.
    for term in ('ÖÇ / PÇ Merkezi', 'ÖÇ/PÇ Merkezi', '>ÖÇ<', '>PÇ<'):
        assert term not in joined
    assert 'Öğrenim' in joined
    assert 'Program Çıkt' in joined


def test_runtime_artifacts_are_excluded_from_build_context():
    text = (ROOT / '.dockerignore').read_text(encoding='utf-8')
    assert 'dou_assess.db' in text
    assert 'data/evidence/*' in text
    assert 'data/scans/*' in text
