from __future__ import annotations

import uuid
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.db import Base, engine

Base.metadata.create_all(engine)
client = TestClient(app)


def _post(path, payload):
    r = client.post(path, json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _patch(path, payload):
    r = client.patch(path, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _framework(version: str):
    rows = client.get('/api/quality360/frameworks').json()
    return next(x for x in rows if x['framework_family'] == 'MÜDEK' and x['version'] == version)


def _program():
    suffix = uuid.uuid4().hex[:8]
    return _post('/api/programs', {
        'code': f'BM648-{suffix}', 'name': 'Bilgisayar Mühendisliği',
        'faculty': 'Mühendislik Fakültesi', 'department': 'Bilgisayar Mühendisliği'
    })


def test_648_release_schema_and_frontend_contract():
    from app.main import APP_VERSION
    assert APP_VERSION == '6.70-production-hardening'
    assert 'quality_accreditation_findings' in Base.metadata.tables
    assert 'quality_accreditation_visit_notes' in Base.metadata.tables
    html = open('app/static/index.html', encoding='utf-8').read()
    js = open('app/static/app.js', encoding='utf-8').read()
    assert 'q648VisitCenter' in html and 'MÜDEK DEĞERLENDİRME RAPORU / NİHAİ KARAR' in html
    assert '/visit-control-center' in js and '/open-30-day-response' in js


def test_648_previous_weakness_becomes_interim_primary_scope_and_is_carried_forward():
    p = _program(); fw31 = _framework('3.1')
    general = _post('/api/compliance/applications', {
        'program_id': p['id'], 'framework_profile_id': fw31['id'], 'academic_year': '2026-2027',
        'application_type': 'general', 'stage': 'preparation', 'status': 'active',
        'owner': 'Program Başkanı', 'notes': '', 'evaluation_mode': 'site_visit'
    })
    _post('/api/compliance/findings', {
        'application_id': general['id'], 'criterion_code': '3.1', 'finding_type': 'weakness',
        'title': 'PÇ ölçme süreci tutarlılığı', 'description': 'Önceki genel değerlendirme bulgusu',
        'status': 'open', 'owner': 'Program Başkanı', 'due_date': None, 'evidence_refs': [], 'response_note': ''
    })
    _post('/api/compliance/findings', {
        'application_id': general['id'], 'criterion_code': '5.2', 'finding_type': 'observation',
        'title': 'Seçmeli ders çeşitliliği', 'description': '', 'status': 'open', 'owner': '',
        'due_date': None, 'evidence_refs': [], 'response_note': ''
    })
    interim = _post('/api/compliance/applications', {
        'program_id': p['id'], 'framework_profile_id': fw31['id'], 'academic_year': '2027-2028',
        'application_type': 'interim', 'stage': 'preparation', 'status': 'active',
        'owner': 'Program Başkanı', 'notes': '', 'evaluation_mode': 'site_visit'
    })
    assert interim['previous_application_id'] == general['id']
    cc = client.get(f"/api/compliance/applications/{interim['id']}/visit-control-center")
    assert cc.status_code == 200, cc.text
    data = cc.json()
    assert data['interim_primary_scope_codes'] == ['3.1']
    carried = [x for x in data['findings'] if x['carried_forward']]
    assert len(carried) == 1 and carried[0]['criterion_code'] == '3.1'
    assert carried[0]['finding_type'] == 'weakness' and carried[0]['status'] == 'monitoring'


def test_648_visit_notes_document_request_sla_and_evaluator_snapshot():
    p = _program(); fw31 = _framework('3.1')
    approw = _post('/api/compliance/applications', {
        'program_id': p['id'], 'framework_profile_id': fw31['id'], 'academic_year': '2026-2027',
        'application_type': 'general', 'stage': 'preparation', 'status': 'active',
        'owner': 'Program Başkanı', 'notes': '', 'evaluation_mode': 'site_visit'
    })
    note = _post('/api/compliance/visit-notes', {
        'application_id': approw['id'], 'criterion_code': '4.1', 'note_type': 'interview',
        'title': 'Öğrenci görüşmesi', 'note': 'Ölçme süreci hakkında görüşme',
        'recorded_by': 'Takım Üyesi', 'visibility': 'evaluator', 'evidence_refs': [], 'occurred_at': None
    })
    assert note['note_type'] == 'interview'
    req = _post('/api/compliance/document-requests', {
        'application_id': approw['id'], 'criterion_code': '4.1', 'title': 'Ek örnek öğrenci çalışması',
        'description': 'Ziyaret öncesi ek kanıt', 'requested_by': 'Değerlendirici',
        'due_date': date.today().isoformat(), 'evidence_refs': []
    })
    answered = _patch(f"/api/compliance/document-requests/{req['id']}", {
        'status': 'answered', 'response_note': 'Kanıt odasına eklendi', 'evidence_refs': ['BBO/4.1/ornek.pdf']
    })
    assert answered['answered_at'] and answered['sla_state'] == 'answered'
    ws = _post('/api/compliance/evaluator-workspaces', {
        'application_id': approw['id'], 'evaluator_email': f"evaluator-{uuid.uuid4().hex[:6]}@example.org",
        'evaluator_name': 'Program Değerlendiricisi', 'access_mode': 'read_only', 'expires_at': None
    })
    snap = client.get(f"/api/compliance/evaluator-workspaces/{ws['id']}/snapshot")
    assert snap.status_code == 200, snap.text
    body = snap.json()
    assert body['read_only'] is True and body['snapshot_sha256']
    assert any(x['id'] == req['id'] and x['status'] == 'answered' for x in body['document_requests'])
    assert any(x['id'] == note['id'] for x in body['visit_notes'])


def test_648_30_day_response_only_opens_from_site_visit_and_sets_due_date():
    p = _program(); fw31 = _framework('3.1')
    row = _post('/api/compliance/applications', {
        'program_id': p['id'], 'framework_profile_id': fw31['id'], 'academic_year': '2026-2027',
        'application_type': 'general', 'stage': 'preparation', 'status': 'active',
        'owner': 'Program Başkanı', 'notes': '', 'evaluation_mode': 'site_visit'
    })
    bad = client.post(f"/api/compliance/applications/{row['id']}/open-30-day-response", json={})
    assert bad.status_code == 409
    stages = ['submitted', 'pre_review', 'correction', 'visit_ready', 'site_visit']
    for stage in stages:
        row = _patch(f"/api/compliance/applications/{row['id']}", {'stage': stage})
    opened = client.post(f"/api/compliance/applications/{row['id']}/open-30-day-response", json={})
    assert opened.status_code == 200, opened.text
    data = opened.json()
    assert data['stage'] == 'response_30_day'
    due = date.fromisoformat(data['correction_due'])
    assert (due - date.today()).days == 30


def test_648_resolving_finding_records_resolution_time():
    p = _program(); fw31 = _framework('3.1')
    approw = _post('/api/compliance/applications', {
        'program_id': p['id'], 'framework_profile_id': fw31['id'], 'academic_year': '2026-2027',
        'application_type': 'general', 'stage': 'preparation', 'status': 'active',
        'owner': '', 'notes': '', 'evaluation_mode': 'site_visit'
    })
    finding = _post('/api/compliance/findings', {
        'application_id': approw['id'], 'criterion_code': '2.2', 'finding_type': 'concern',
        'title': 'Paydaş geri bildirim döngüsü', 'description': '', 'status': 'open', 'owner': '',
        'due_date': None, 'evidence_refs': [], 'response_note': ''
    })
    closed = _patch(f"/api/compliance/findings/{finding['id']}", {'status': 'resolved', 'response_note': 'PUKÖ ve kurul kararı ile kapatıldı'})
    assert closed['status'] == 'resolved' and closed['resolved_at']
