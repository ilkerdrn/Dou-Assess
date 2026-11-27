from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import APP_VERSION, EXPECTED_SCHEMA_REVISION, app
from app import models as m

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def _post(path: str, payload: dict):
    r = client.post(path, json=payload)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def test_663_release_ui_and_schema_contract():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0045_outcome_thresholds"
    root = Path(__file__).resolve().parents[1]
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    css = (root / "app/static/styles.css").read_text(encoding="utf-8")
    migration = (root / "migrations/versions/0037_institutional_accreditation_readiness.py").read_text(encoding="utf-8")
    assert 'data-page="institutionalreadiness"' in html
    assert 'id="page-institutionalreadiness"' in html
    assert 'INSTITUTIONAL ACCREDITATION READINESS' in html
    assert 'prepareInstitutionalReadiness' in js
    assert '/api/quality360/institutional/readiness' in js
    assert '.ir-kpis' in css
    assert 'quality_accreditation_crosswalks' in migration
    assert 'quality_institutional_readiness_snapshots' in migration


def test_663_crosswalk_reuse_readiness_and_snapshot():
    program = _post('/api/programs', {
        'code':'IAT663','name':'İnternet ve Ağ Teknolojileri','faculty':'Meslek Yüksekokulu','department':'Bilgisayar Teknolojileri'
    })
    fw = client.get('/api/quality360/frameworks')
    assert fw.status_code == 200, fw.text
    medek = next(x for x in fw.json() if x['framework_family'] == 'MEDEK' and x['status'] == 'active')

    # Explicit assignment removes ambiguity from institutional readiness routing.
    r = client.post(f"/api/quality360/programs/{program['id']}/framework-override?framework_id={medek['id']}&is_primary=true")
    assert r.status_code == 201, r.text

    with SessionLocal() as db:
        db.add(m.QualityEvidenceAsset(
            program_id=program['id'], criterion_code='3.2', entity_type='program', entity_id=program['id'],
            kind='report', category='outcome_assessment', description='PÇ ölçme raporu',
            original_name='PC-Olcme-Raporu.pdf', stored_name='663-pc-olcme-raporu.pdf',
            mime_type='application/pdf', size_bytes=100, sha256='a'*64, version_no=1,
        ))
        db.commit()

    cross = _post('/api/quality360/institutional/crosswalks', {
        'source_framework_family':'MEDEK','source_framework_version':medek['version'],
        'source_criterion_code':'3.2','target_framework_family':'YÖKAK','target_framework_version':'2026',
        'target_criterion_code':'B.1.5','relationship':'supports',
        'rationale':'Program çıktısı ölçme raporu iki hazırlık alanında destekleyici kanıttır.'
    })
    assert cross['review_status'] == 'draft'

    before = client.get('/api/quality360/institutional/readiness?academic_year=2026-2027')
    assert before.status_code == 200, before.text
    assert before.json()['summary']['reusable_evidence_count'] == 0

    approved = client.patch(f"/api/quality360/institutional/crosswalks/{cross['id']}", json={'review_status':'approved'})
    assert approved.status_code == 200, approved.text
    assert approved.json()['review_status'] == 'approved'

    ready = client.get('/api/quality360/institutional/readiness?academic_year=2026-2027')
    assert ready.status_code == 200, ready.text
    data = ready.json()
    row = next(x for x in data['programs'] if x['program_id'] == program['id'])
    assert row['framework_family'] == 'MEDEK'
    assert data['summary']['approved_crosswalk_count'] == 1
    assert data['summary']['reusable_evidence_count'] == 1
    reuse = data['reusable_evidence'][0]
    assert reuse['source']['criterion_code'] == '3.2'
    assert reuse['targets'][0]['family'] == 'YÖKAK'
    assert reuse['targets'][0]['criterion_code'] == 'B.1.5'

    snap1 = _post('/api/quality360/institutional/readiness-snapshots', {
        'academic_year':'2026-2027','scope_type':'institution','scope_key':'DOGUS'
    })
    snap2 = _post('/api/quality360/institutional/readiness-snapshots', {
        'academic_year':'2026-2027','scope_type':'institution','scope_key':'DOGUS'
    })
    assert snap1['snapshot_no'] == 1
    assert snap2['snapshot_no'] == 2
    assert len(snap1['content_sha256']) == 64
    snaps = client.get('/api/quality360/institutional/readiness-snapshots?academic_year=2026-2027&scope_type=institution&scope_key=DOGUS')
    assert snaps.status_code == 200
    assert [x['snapshot_no'] for x in snaps.json()[:2]] == [2, 1]
