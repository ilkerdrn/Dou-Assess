from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.services.quality360 import mudek_version_route, seed_builtin_frameworks
from tests.test_641_accreditation_compliance_core import AY, context

client = TestClient(app)


def _framework(version: str) -> dict:
    r = client.get('/api/quality360/frameworks')
    assert r.status_code == 200, r.text
    return next(x for x in r.json() if x['framework_family'] == 'MÜDEK' and x['version'] == version)


def test_644_registry_contains_official_transition_versions():
    v22 = _framework('2.2'); v30 = _framework('3.0'); v31 = _framework('3.1')
    assert len(v22['criteria']) == 10
    assert any(x['code'] == '10' for x in v22['criteria'])
    assert len(v30['criteria']) == 9 and not any(x['code'] == '10' for x in v30['criteria'])
    assert len(v31['criteria']) == 9 and not any(x['code'] == '10' for x in v31['criteria'])
    assert next(x for x in v30['criteria'] if x['code'] == '5')['annex']['code'] == 'EK-1'
    assert next(x for x in v31['criteria'] if x['code'] == '5')['annex']['code'] == 'EK-1'


def test_644_official_2026_2027_routing_rules():
    with SessionLocal() as db:
        general = mudek_version_route(db, '2026-2027', 'general')
        interim = mudek_version_route(db, '2026-2027', 'interim')
        chosen = mudek_version_route(db, '2026-2027', 'general', preferred_version='3.0')
    assert general['allowed_versions'] == ['3.0', '3.1']
    assert general['selection_required'] is True
    assert interim['allowed_versions'] == ['2.2']
    assert interim['selected_framework']['version'] == '2.2'
    assert chosen['selected_framework']['version'] == '3.0'


def test_644_2027_2028_general_is_v31_and_interim_inherits_previous_general():
    with SessionLocal() as db:
        general = mudek_version_route(db, '2027-2028', 'general')
        interim = mudek_version_route(db, '2027-2028', 'interim', previous_general_version='3.0')
    assert general['allowed_versions'] == ['3.1']
    assert general['selected_framework']['version'] == '3.1'
    assert interim['allowed_versions'] == ['3.0']


def test_644_route_endpoint_and_application_guard():
    ctx = context(); pid = ctx['pid']
    v22 = _framework('2.2'); v30 = _framework('3.0'); v31 = _framework('3.1')
    route = client.get('/api/quality360/frameworks/mudek-route', params={'academic_year':'2026-2027','application_type':'general'})
    assert route.status_code == 200, route.text
    assert route.json()['allowed_versions'] == ['3.0','3.1']

    bad_general = client.post('/api/compliance/applications', json={
        'program_id':pid,'framework_profile_id':v22['id'],'academic_year':'2026-2027','application_type':'general','owner':'Test'
    })
    assert bad_general.status_code == 422
    bad_interim = client.post('/api/compliance/applications', json={
        'program_id':pid,'framework_profile_id':v31['id'],'academic_year':'2026-2027','application_type':'interim','owner':'Test'
    })
    assert bad_interim.status_code == 422
    good = client.post('/api/compliance/applications', json={
        'program_id':pid,'framework_profile_id':v30['id'],'academic_year':'2026-2027','application_type':'general','owner':'Test'
    })
    assert good.status_code in {201,409}, good.text


def test_644_frontend_exposes_version_route_guard():
    js = open('app/static/app.js', encoding='utf-8').read()
    html = open('app/static/index.html', encoding='utf-8').read()
    css = open('app/static/styles.css', encoding='utf-8').read()
    assert 'q644RefreshMudekRoute' in js
    assert '/api/quality360/frameworks/mudek-route' in js
    assert 'q644MudekRoute' in html
    assert '.mudek-route-box' in css
