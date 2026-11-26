from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

c=TestClient(app)

def ensure_program(code,name,faculty,department):
    rows=c.get('/api/programs').json()
    found=next((x for x in rows if x['code']==code),None)
    if found:return found
    r=c.post('/api/programs',json={'code':code,'name':name,'faculty':faculty,'department':department})
    assert r.status_code in (200,201),r.text
    return r.json()

def test_627_framework_catalog_is_university_wide():
    r=c.get('/api/quality360/frameworks'); assert r.status_code==200,r.text
    fam={x['framework_family'] for x in r.json()}
    assert {'MEDEK','MÜDEK','TURAK','YÖKAK','ESG','ACQUIN'} <= fam

def test_627_program_framework_routing():
    myo=ensure_program('Q627-MYO','İnternet ve Ağ Teknolojileri','Meslek Yüksekokulu','Bilgisayar Teknolojileri')
    eng=ensure_program('Q627-ENG','Bilgisayar Mühendisliği','Mühendislik Fakültesi','Bilgisayar Mühendisliği')
    tur=ensure_program('Q627-TUR','Turizm ve Otel İşletmeciliği','Uygulamalı Bilimler Fakültesi','Turizm')
    assert next(x for x in c.get(f"/api/quality360/programs/{myo['id']}/framework-routing").json()['recommendations'] if x['is_primary'])['family']=='MEDEK'
    assert next(x for x in c.get(f"/api/quality360/programs/{eng['id']}/framework-routing").json()['recommendations'] if x['is_primary'])['family']=='MÜDEK'
    assert next(x for x in c.get(f"/api/quality360/programs/{tur['id']}/framework-routing").json()['recommendations'] if x['is_primary'])['family']=='TURAK'

def test_627_university_dashboard_and_ui_contract():
    r=c.get('/api/quality360/university/dashboard?academic_year=2026-2027'); assert r.status_code==200,r.text
    d=r.json(); assert 'summary' in d and 'faculties' in d and 'programs' in d and 'framework_distribution' in d
    root=Path(__file__).resolve().parents[1]
    html=(root/'app/static/index.html').read_text(encoding='utf-8')
    js=(root/'app/static/app.js').read_text(encoding='utf-8')
    css=(root/'app/static/styles.css').read_text(encoding='utf-8')
    assert 'ÜNİVERSİTE KALİTE NABZI' in html and 'AKILLI KALİTE EŞLEŞTİRME' in js
    assert '/api/quality360/university/dashboard' in js and '.quality-executive-strip' in css

def test_627_version_contract():
    from app.main import APP_VERSION, EXPECTED_SCHEMA_REVISION
    assert APP_VERSION=='6.70-production-hardening'
    assert EXPECTED_SCHEMA_REVISION=='0042_performance_production_hardening'
