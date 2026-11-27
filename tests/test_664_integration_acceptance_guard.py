from pathlib import Path

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def _post(path: str, payload: dict):
    r = client.post(path, json=payload)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def test_664_release_and_obs_readonly_contract():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0043_response_grade_revisions"
    root = Path(__file__).resolve().parents[1]
    cfg = (root / "app/config.py").read_text(encoding="utf-8")
    main = (root / "app/main.py").read_text(encoding="utf-8")
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    assert 'OBS_WRITEBACK_ENABLED' in cfg
    assert 'if not settings.obs_writeback_enabled' in main
    assert 'OBS read-only veri köprüsü' in html
    assert 'id="obsResultsPush"' in html and 'hidden disabled' in html
    assert 'OBS_WRITEBACK_ENABLED=false' in (root / '.env.production.example').read_text(encoding='utf-8')


def test_664_public_status_and_writeback_guard():
    auth = client.get('/api/auth/config')
    assert auth.status_code == 200, auth.text
    obs = auth.json()['integrations']['obs']
    assert obs['mode'] == 'read-only'
    assert obs['writeback_enabled'] is False
    assert 'token' not in obs

    program = _post('/api/programs', {'code':'OBS664','name':'OBS Guard Program','faculty':'MYO','department':'BT'})
    course = _post('/api/courses', {
        'program_id': program['id'], 'code':'OBS664C', 'name':'OBS Guard Course',
        'academic_year':'2026-2027', 'term':'Güz'
    })
    blocked = client.post(f"/api/courses/{course['id']}/obs-results/push", json={})
    assert blocked.status_code == 403, blocked.text
    assert 'read-only' in blocked.text
