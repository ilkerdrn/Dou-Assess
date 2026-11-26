from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.services.quality360 import (
    medek_program_specific_catalog,
    medek_version_route,
    seed_builtin_frameworks,
)

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def _framework(version: str) -> dict:
    r = client.get('/api/quality360/frameworks')
    assert r.status_code == 200, r.text
    return next(x for x in r.json() if x['framework_family'] == 'MEDEK' and x['version'] == version)


def _post(path: str, payload: dict, expected=(200, 201)) -> dict:
    r = client.post(path, json=payload)
    assert r.status_code in expected, (path, r.status_code, r.text)
    return r.json()


def _iat_program() -> dict:
    suffix = uuid.uuid4().hex[:8].upper()
    return _post('/api/programs', {
        'code': f'IAT646-{suffix}',
        'name': 'İnternet ve Ağ Teknolojileri',
        'faculty': 'Meslek Yüksekokulu',
        'department': 'Bilgisayar Teknolojileri',
    })


def test_646_release_and_medek_v20_registry_precision():
    main = (ROOT / 'app/main.py').read_text(encoding='utf-8')
    assert 'APP_VERSION = "6.70-production-hardening"' in main
    v11 = _framework('v1.1'); v20 = _framework('v2.0')
    assert len(v11['criteria']) == 9
    assert sum(len(x.get('subcriteria') or []) for x in v11['criteria']) == 46
    assert len(v20['criteria']) == 8
    assert not any(x['code'] == '9' for x in v20['criteria'])
    assert sum(len(x.get('subcriteria') or []) for x in v20['criteria']) == 45
    assert v20['thresholds']['official_subcriteria_count'] == 45
    assert v20['thresholds']['required_medek_outcomes'] == 11
    c3 = next(x for x in v20['criteria'] if x['code'] == '3')
    assert len(c3['program_outcomes']) == 11
    assert any(x['code'] == '3.2' and x['automation_key'] == 'medek_program_specific' for x in c3['subcriteria'])


def test_646_medek_general_and_interim_version_routing_rules():
    with SessionLocal() as db:
        r26 = medek_version_route(db, '2026-2027', 'general')
        r27 = medek_version_route(db, '2027-2028', 'renewal')
        r28 = medek_version_route(db, '2028-2029', 'general')
        interim11 = medek_version_route(db, '2028-2029', 'interim', previous_general_version='v1.1')
        interim20 = medek_version_route(db, '2029-2030', 'interim', previous_general_version='v2.0')
        missing = medek_version_route(db, '2028-2029', 'interim')
    assert r26['allowed_versions'] == ['v1.1'] and r26['selected_framework']['version'] == 'v1.1'
    assert r27['allowed_versions'] == ['v1.1']
    assert r28['allowed_versions'] == ['v2.0'] and r28['selected_framework']['version'] == 'v2.0'
    assert interim11['allowed_versions'] == ['v1.1']
    assert interim20['allowed_versions'] == ['v2.0']
    assert missing['selection_required'] is True and missing['allowed_versions'] == []


def test_646_medek_route_endpoint_and_backend_application_guard():
    p = _iat_program(); v11 = _framework('v1.1'); v20 = _framework('v2.0')
    route = client.get('/api/quality360/frameworks/medek-route', params={
        'academic_year': '2028-2029', 'application_type': 'general'
    })
    assert route.status_code == 200, route.text
    assert route.json()['allowed_versions'] == ['v2.0']

    bad_2028 = client.post('/api/compliance/applications', json={
        'program_id': p['id'], 'framework_profile_id': v11['id'], 'academic_year': '2028-2029',
        'application_type': 'general', 'owner': 'Test'
    })
    assert bad_2028.status_code == 422

    bad_2026 = client.post('/api/compliance/applications', json={
        'program_id': p['id'], 'framework_profile_id': v20['id'], 'academic_year': '2026-2027',
        'application_type': 'general', 'owner': 'Test'
    })
    assert bad_2026.status_code == 422

    good_old = client.post('/api/compliance/applications', json={
        'program_id': p['id'], 'framework_profile_id': v11['id'], 'academic_year': '2027-2028',
        'application_type': 'general', 'owner': 'Test'
    })
    assert good_old.status_code == 201, good_old.text

    inferred_route = client.get('/api/quality360/frameworks/medek-route', params={
        'academic_year': '2028-2029', 'application_type': 'interim', 'program_id': p['id']
    })
    assert inferred_route.status_code == 200, inferred_route.text
    assert inferred_route.json()['allowed_versions'] == ['v1.1']

    inherited = client.post('/api/compliance/applications', json={
        'program_id': p['id'], 'framework_profile_id': v11['id'], 'academic_year': '2028-2029',
        'application_type': 'interim', 'owner': 'Test'
    })
    assert inherited.status_code == 201, inherited.text

    p2 = _iat_program()
    missing_history = client.post('/api/compliance/applications', json={
        'program_id': p2['id'], 'framework_profile_id': v20['id'], 'academic_year': '2028-2029',
        'application_type': 'interim', 'owner': 'Test'
    })
    assert missing_history.status_code == 422


def test_646_iat_program_specific_outputs_are_versioned():
    v11 = medek_program_specific_catalog('İnternet ve Ağ Teknolojileri', 'v1.1')
    v20 = medek_program_specific_catalog('Internet ve Ag Teknolojileri', 'v2.0')
    unknown = medek_program_specific_catalog('Bilinmeyen Program', 'v2.0')
    assert v11['match_status'] == 'exact' and v11['required_count'] == 4
    assert v20['match_status'] == 'exact' and v20['required_count'] == 5
    assert {x['code'] for x in v20['outputs']} == {'PÖÇ1','PÖÇ2','PÖÇ3','PÖÇ4','PÖÇ5'}
    assert unknown['match_status'] == 'manual_required' and unknown['required_count'] == 0


def test_646_program_specific_profile_tracks_exact_po_mapping():
    p = _iat_program(); v20 = _framework('v2.0')
    po = _post(f"/api/programs/{p['id']}/program-outcomes", {
        'academic_year': '2028-2029', 'code': 'PÇ1', 'description': 'Ağ sistemlerini kurar ve yönetir.'
    })
    before = client.get(f"/api/quality360/programs/{p['id']}/medek-program-specific", params={
        'framework_id': v20['id'], 'academic_year': '2028-2029'
    })
    assert before.status_code == 200, before.text
    data = before.json()
    assert data['required_count'] == 5 and data['mapped_count'] == 0 and data['coverage_percent'] == 0

    mapped = _post('/api/compliance/program-outcome-components', {
        'program_outcome_id': po['id'], 'code': 'MEDEK-v2.0-PÖÇ1',
        'description': data['outputs'][0]['title'], 'component_type': 'competency',
        'framework_family': 'MEDEK', 'framework_version': 'v2.0',
        'framework_component_code': 'PÖÇ1', 'required': True, 'evidence_refs': [],
    })
    assert mapped['framework_component_code'] == 'PÖÇ1'
    after = client.get(f"/api/quality360/programs/{p['id']}/medek-program-specific", params={
        'framework_id': v20['id'], 'academic_year': '2028-2029'
    })
    assert after.status_code == 200, after.text
    d = after.json()
    assert d['mapped_count'] == 1 and d['unmapped_count'] == 4 and d['coverage_percent'] == 20.0
    first = next(x for x in d['outputs'] if x['code'] == 'PÖÇ1')
    assert first['mapped'] is True and first['mappings'][0]['program_outcome_code'] == 'PÇ1'


def test_646_frontend_exposes_medek_route_and_program_specific_mapping():
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    html = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
    assert "'medek-route'" in js
    assert '/medek-program-specific' in js
    assert 'data-q646-map-medek-output' in js
    assert 'q646MedekProgramSpecific' in html
    assert 'MEDEK PROGRAMA ÖZGÜ ÇIKTILAR' in html
