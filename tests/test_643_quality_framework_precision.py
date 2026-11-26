from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.authz import set_current_user, reset_current_user
from app.main import app
from app.services.quality360 import _criterion_signals, curriculum_check, seed_builtin_frameworks
from tests.test_641_accreditation_compliance_core import AY, context

client = TestClient(app)


def _framework(code: str) -> dict:
    rows = client.get('/api/quality360/frameworks')
    assert rows.status_code == 200, rows.text
    return next(x for x in rows.json() if x['code'] == code)


def test_643_official_medek_v11_and_mudek_v31_structure():
    medek = _framework('MEDEK-2026')
    assert medek['version'] == 'v1.1'
    assert len(medek['criteria']) == 9
    assert sum(len(x.get('subcriteria') or []) for x in medek['criteria']) == 46
    assert len(next(x for x in medek['criteria'] if x['code'] == '3')['program_outcomes']) == 10
    assert medek['source_meta']['official_criteria_count'] == 9
    assert medek['source_meta']['official_subcriteria_count'] == 46

    mudek = _framework('MUDEK-CORE')
    assert mudek['version'] == '3.1'
    assert len(mudek['criteria']) == 9
    assert sum(len(x.get('subcriteria') or []) for x in mudek['criteria']) == 32
    assert len(next(x for x in mudek['criteria'] if x['code'] == '3')['program_outcomes']) == 11
    assert not any(x['code'] == '10' for x in mudek['criteria'])
    c5 = next(x for x in mudek['criteria'] if x['code'] == '5')
    assert c5['annex']['code'] == 'EK-1'
    assert c5['annex']['is_separate_criterion'] is False


def test_643_mudek_signal_engine_has_no_phantom_criterion_10():
    ctx = context()
    token = set_current_user({'id': 1, 'email': 'test-admin@dogus.edu.tr', 'display_name': 'Test Admin', 'role_names': ['admin'], 'roles': []})
    try:
        with SessionLocal() as db:
            frameworks = seed_builtin_frameworks(db)
            mudek = next(x for x in frameworks if x.code == 'MUDEK-CORE')
            program = db.get(__import__('app.models', fromlist=['Program']).Program, ctx['pid'])
            curriculum = curriculum_check(db, ctx['pid'], AY, thresholds=mudek.thresholds or {})
            signals = _criterion_signals(db, program, AY, curriculum, mudek)
            assert set(signals).issubset({str(i) for i in range(1, 10)})
            assert '10' not in signals
    finally:
        reset_current_user(token)


def test_643_exact_subcriterion_evidence_is_not_inherited_from_parent():
    ctx = context(); pid = ctx['pid']
    medek = _framework('MEDEK-2026')

    parent = client.post(
        f'/api/quality360/programs/{pid}/evidence',
        data={'criterion_code': '3', 'category': 'quality', 'description': 'Üst ölçüt kanıtı'},
        files={'file': ('criterion-3.txt', b'parent evidence', 'text/plain')},
    )
    assert parent.status_code == 201, parent.text

    before = client.get(
        f'/api/quality360/programs/{pid}/accreditation-readiness',
        params={'academic_year': AY, 'framework_id': medek['id']},
    )
    assert before.status_code == 200, before.text
    c3 = next(x for x in before.json()['matrix'] if x['criterion_code'] == '3')
    s32 = next(x for x in c3['subcriteria'] if x['subcriterion_code'] == '3.2')
    assert s32['parent_evidence_count'] >= 1
    assert s32['evidence_count'] == 0
    assert s32['status'] != 'ready'

    exact = client.post(
        f'/api/quality360/programs/{pid}/evidence',
        data={'criterion_code': '3.2', 'category': 'assessment', 'description': 'PÇ dönemsel ölçüm kanıtı'},
        files={'file': ('criterion-3-2.txt', b'exact subcriterion evidence', 'text/plain')},
    )
    assert exact.status_code == 201, exact.text

    after = client.get(
        f'/api/quality360/programs/{pid}/accreditation-readiness',
        params={'academic_year': AY, 'framework_id': medek['id']},
    )
    assert after.status_code == 200, after.text
    payload = after.json()
    c3 = next(x for x in payload['matrix'] if x['criterion_code'] == '3')
    s32 = next(x for x in c3['subcriteria'] if x['subcriterion_code'] == '3.2')
    assert s32['evidence_count'] >= 1
    assert payload['summary']['subcriteria_total'] == 46
    assert 'subcriteria_gaps' in payload['summary']
    assert 'subcriteria_manual_review' in payload['summary']


def test_643_frontend_exposes_subcriterion_drilldown_and_exact_evidence_selector():
    js = open('app/static/app.js', encoding='utf-8').read()
    css = open('app/static/styles.css', encoding='utf-8').read()
    assert 'critOptions=crit.flatMap' in js
    assert 'q360-subcriteria' in js
    assert 'subcriterion_code' in js
    assert '.q360-subcriterion-row' in css

def test_643_manual_subcriterion_review_can_be_recorded_without_fake_auto_pass():
    ctx = context(); pid = ctx['pid']
    medek = _framework('MEDEK-2026')
    body = {
        'program_id': pid,
        'framework_profile_id': medek['id'],
        'academic_year': AY,
        'criterion_code': '1.3',
        'maturity_level': 4,
        'quality_status': 'measured',
        'note': 'Yetkili kalite kullanıcısı tarafından prosedür ve uygulama doğrulandı.',
        'evidence_refs': [],
    }
    r = client.put('/api/quality360/criterion-assessments', json=body)
    assert r.status_code == 200, r.text
    ready = client.get(
        f'/api/quality360/programs/{pid}/accreditation-readiness',
        params={'academic_year': AY, 'framework_id': medek['id']},
    )
    assert ready.status_code == 200, ready.text
    c1 = next(x for x in ready.json()['matrix'] if x['criterion_code'] == '1')
    s13 = next(x for x in c1['subcriteria'] if x['subcriterion_code'] == '1.3')
    assert s13['auto_ok'] is None
    assert s13['manual_review_completed'] is True
    assert s13['manual_review_required'] is False
    assert s13['manual_maturity'] == 4
