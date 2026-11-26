from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import APP_VERSION, EXPECTED_SCHEMA_REVISION, app
from app.services.framework_lifecycle_catalog import lifecycle_profiles

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def test_665_release_ui_and_source_controlled_catalog():
    assert APP_VERSION == '6.70-production-hardening'
    assert EXPECTED_SCHEMA_REVISION == '0042_performance_production_hardening'
    root=Path(__file__).resolve().parents[1]
    html=(root/'app/static/index.html').read_text(encoding='utf-8')
    js=(root/'app/static/app.js').read_text(encoding='utf-8')
    assert 'RESMÎ SÜREÇ TAKVİMİ' in html
    assert 'irTimeline' in html
    assert '/api/compliance/framework-lifecycle-profiles' in js

    data=lifecycle_profiles(2026, as_of=date(2026,9,15))
    families={x['framework_family']:x for x in data['frameworks']}
    assert set(families) == {'TURAK','SABAK','EPDAD'}
    assert families['TURAK']['document_profile'].startswith('ÖDR Sürüm 7')
    assert any(x.get('date')=='2026-09-30' and x['code']=='team_objection' for x in families['TURAK']['events'])
    assert any(x.get('start')=='2026-09-18' and x.get('end')=='2026-10-16' for x in families['SABAK']['events'])
    assert any(x.get('date')=='2026-09-25' and x['code']=='corrected_report' for x in families['EPDAD']['events'])
    assert 'programa özel' in data['disclaimer'].lower()


def test_665_lifecycle_api():
    r=client.get('/api/compliance/framework-lifecycle-profiles?cycle_year=2026')
    assert r.status_code==200, r.text
    body=r.json()
    assert body['cycle_year']==2026
    assert len(body['frameworks'])==3
    assert all(x.get('source_url','').startswith('https://') for x in body['frameworks'])
    bad=client.get('/api/compliance/framework-lifecycle-profiles?cycle_year=1900')
    assert bad.status_code==422
