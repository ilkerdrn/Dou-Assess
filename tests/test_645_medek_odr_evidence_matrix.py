from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.test_641_accreditation_compliance_core import AY, context

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def _medek_v11() -> dict:
    r = client.get('/api/quality360/frameworks')
    assert r.status_code == 200, r.text
    return next(x for x in r.json() if x['framework_family'] == 'MEDEK' and x['version'] == 'v1.1')


def test_645_release_and_official_odr_matrix_contract():
    main = (ROOT / 'app/main.py').read_text(encoding='utf-8')
    assert 'APP_VERSION = "6.70-production-hardening"' in main
    ctx = context(); fw = _medek_v11()
    r = client.get(f"/api/quality360/programs/{ctx['pid']}/medek-odr-readiness", params={
        'academic_year': AY, 'framework_id': fw['id'], 'application_type': 'general'
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['source']['document_no'] == 'RP-002'
    assert data['summary']['official_prompt_count'] == 58
    assert len(data['items']) == 58
    assert len(data['groups']) == 9
    assert len(data['appendices']) == 11
    codes = {x['code'] for x in data['items']}
    for code in {'1.1.1','2.3.3','3.2.2','7.6.2','9.1'}:
        assert code in codes
    assert data['disclaimer']


def test_645_odr_item_manual_review_is_valid_framework_assessment():
    ctx = context(); fw = _medek_v11()
    r = client.put('/api/quality360/criterion-assessments', json={
        'program_id': ctx['pid'], 'framework_profile_id': fw['id'], 'academic_year': AY,
        'criterion_code': '1.1.1', 'maturity_level': 3, 'quality_status': 'implemented',
        'note': 'ÖDR satırı test doğrulaması', 'evidence_refs': [],
    })
    assert r.status_code == 200, r.text
    assert r.json()['criterion_code'] == '1.1.1'


def test_645_exact_odr_evidence_is_separate_from_parent_framework_evidence():
    ctx = context(); fw = _medek_v11()
    upload = client.post(
        f"/api/quality360/programs/{ctx['pid']}/evidence",
        data={'criterion_code':'3.2.2','category':'medek-odr','description':'ÖDR ayrıntılı satır kanıtı'},
        files={'file':('medek-3-2-2.txt', b'dogrulanabilir medek odr kaniti', 'text/plain')},
    )
    assert upload.status_code in {200,201}, upload.text
    r = client.get(f"/api/quality360/programs/{ctx['pid']}/medek-odr-readiness", params={
        'academic_year': AY, 'framework_id': fw['id'], 'application_type': 'general'
    })
    assert r.status_code == 200, r.text
    item = next(x for x in r.json()['items'] if x['code'] == '3.2.2')
    assert item['exact_evidence_count'] >= 1
    assert item['supporting_evidence_count'] >= 0


def test_645_interim_scope_does_not_fake_all_58_as_mandatory():
    ctx = context(); fw = _medek_v11()
    r = client.get(f"/api/quality360/programs/{ctx['pid']}/medek-odr-readiness", params={
        'academic_year': AY, 'framework_id': fw['id'], 'application_type': 'interim'
    })
    assert r.status_code == 200, r.text
    s = r.json()['summary']
    assert s['mandatory_prompt_count'] == 0
    assert s['conditional_prompt_count'] == 58
    assert 'önceki' in r.json()['scope_note'].casefold()


def test_645_medek_odr_docx_is_real_docx_and_frontend_exposes_workspace():
    ctx = context(); fw = _medek_v11()
    r = client.get(f"/api/quality360/programs/{ctx['pid']}/medek-odr.docx", params={
        'academic_year': AY, 'framework_id': fw['id'], 'application_type': 'general'
    })
    assert r.status_code == 200, r.text
    assert r.content[:2] == b'PK'
    assert 'wordprocessingml.document' in r.headers.get('content-type','')
    html = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    css = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')
    assert 'data-q360-workspace="medekodr"' in html
    assert 'q645MedekOdrMatrix' in html
    assert '/medek-odr-readiness' in js
    assert 'loadMedekOdrReadiness' in js
    assert '.medek-odr-matrix' in css
