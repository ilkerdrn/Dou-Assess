from pathlib import Path
from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION

Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
client=TestClient(app)

def test_666_release_and_ui_contract():
    assert APP_VERSION=='6.70-production-hardening'
    assert EXPECTED_SCHEMA_REVISION=='0045_outcome_thresholds'
    root=Path(__file__).resolve().parents[1]
    assert 'institution_acceptance_records' in (root/'migrations/versions/0038_institution_acceptance_gate.py').read_text(encoding='utf-8')
    html=(root/'app/static/index.html').read_text(encoding='utf-8')
    js=(root/'app/static/app.js').read_text(encoding='utf-8')
    assert 'data-page="acceptance"' in html and 'page-acceptance' in html
    assert '/api/production-acceptance' in js

def test_666_acceptance_requires_explicit_signoff_and_evidence():
    r=client.get('/api/production-acceptance')
    assert r.status_code==200, r.text
    data=r.json(); assert data['required_total']>=6; assert data['release_ready'] is False
    gate=next(x for x in data['gates'] if x['key']=='tls_dns_proxy')
    assert gate['manual_status']=='pending'
    p=client.patch('/api/production-acceptance/tls_dns_proxy',json={'status':'passed','evidence_ref':'CHANGE-2026-0915','note':'HTTPS/DNS acceptance'})
    assert p.status_code==200,p.text
    assert p.json()['status']=='passed' and p.json()['evidence_ref']=='CHANGE-2026-0915'
    again=client.get('/api/production-acceptance').json()
    assert next(x for x in again['gates'] if x['key']=='tls_dns_proxy')['effective_status']=='passed'
