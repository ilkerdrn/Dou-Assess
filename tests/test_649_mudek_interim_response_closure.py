from __future__ import annotations
import uuid
from fastapi.testclient import TestClient
from app.main import app, APP_VERSION
from app.db import Base, engine
Base.metadata.create_all(engine)
client=TestClient(app)

def post(path,payload=None):
    r=client.post(path,json=payload or {}); assert r.status_code in (200,201),r.text; return r.json()
def patch(path,payload):
    r=client.patch(path,json=payload); assert r.status_code==200,r.text; return r.json()
def framework():
    return next(x for x in client.get('/api/quality360/frameworks').json() if x['framework_family']=='MÜDEK' and x['version']=='3.1')
def program():
    s=uuid.uuid4().hex[:8]
    return post('/api/programs',{'code':f'BM649-{s}','name':'Bilgisayar Mühendisliği','faculty':'Mühendislik Fakültesi','department':'Bilgisayar Mühendisliği'})
def approw(mode='report_only',typ='general'):
    p=program(); fw=framework()
    return post('/api/compliance/applications',{'program_id':p['id'],'framework_profile_id':fw['id'],'academic_year':'2026-2027','application_type':typ,'stage':'preparation','status':'active','owner':'Program Başkanı','notes':'','evaluation_mode':mode})

def test_649_release_contract_and_schema():
    assert APP_VERSION=='6.70-production-hardening'
    assert 'quality_accreditation_decision_history' in Base.metadata.tables

def test_report_only_skips_visit_stages_and_rejects_visit_notes():
    a=approw('report_only')
    for st in ['submitted','pre_review','correction']:
        a=patch(f"/api/compliance/applications/{a['id']}",{'stage':st})
    bad=client.patch(f"/api/compliance/applications/{a['id']}",json={'stage':'visit_ready'})
    assert bad.status_code==409
    note=client.post('/api/compliance/visit-notes',json={'application_id':a['id'],'criterion_code':'3.1','note_type':'observation','title':'Olmamalı','note':'','recorded_by':'','visibility':'internal','evidence_refs':[],'occurred_at':None})
    assert note.status_code==409
    opened=client.post(f"/api/compliance/applications/{a['id']}/open-30-day-response",json={})
    assert opened.status_code==200,opened.text
    assert opened.json()['stage']=='response_30_day'

def test_site_visit_flow_still_requires_visit():
    a=approw('site_visit')
    for st in ['submitted','pre_review','correction']:
        a=patch(f"/api/compliance/applications/{a['id']}",{'stage':st})
    bad=client.post(f"/api/compliance/applications/{a['id']}/open-30-day-response",json={})
    assert bad.status_code==409
    for st in ['visit_ready','site_visit']:
        a=patch(f"/api/compliance/applications/{a['id']}",{'stage':st})
    ok=client.post(f"/api/compliance/applications/{a['id']}/open-30-day-response",json={})
    assert ok.status_code==200

def test_closure_matrix_requires_closed_status_evidence_and_response_note():
    a=approw()
    f=post('/api/compliance/findings',{'application_id':a['id'],'criterion_code':'3.1','finding_type':'weakness','title':'Ölçüm bulgusu','description':'','status':'open','owner':'Program Başkanı','due_date':None,'evidence_refs':[],'response_note':''})
    matrix=client.get(f"/api/compliance/applications/{a['id']}/closure-matrix").json()
    assert matrix['rows'][0]['closure_ready'] is False
    patch(f"/api/compliance/findings/{f['id']}",{'status':'resolved','evidence_refs':['BBO/3.1/kanit.pdf'],'response_note':'Düzeltici faaliyet tamamlandı'})
    matrix=client.get(f"/api/compliance/applications/{a['id']}/closure-matrix").json()
    assert matrix['rows'][0]['closure_ready'] is True and matrix['summary']['open']==0

def test_decision_history_records_stage_and_manual_decision():
    a=approw()
    patch(f"/api/compliance/applications/{a['id']}",{'stage':'submitted'})
    post(f"/api/compliance/applications/{a['id']}/decisions",{'action':'decision_recorded','decision_code':'CONTINUE','note':'Ara değerlendirme devam','payload':{'committee':'MÜDEK'}})
    hist=client.get(f"/api/compliance/applications/{a['id']}/decision-history").json()
    assert any(x['action']=='stage_transition' and x['to_stage']=='submitted' for x in hist)
    assert any(x['decision_code']=='CONTINUE' for x in hist)

def test_response_package_reports_readiness():
    a=approw()
    for st in ['submitted','pre_review','correction']:
        a=patch(f"/api/compliance/applications/{a['id']}",{'stage':st})
    client.post(f"/api/compliance/applications/{a['id']}/open-30-day-response",json={})
    f=post('/api/compliance/findings',{'application_id':a['id'],'criterion_code':'4.1','finding_type':'concern','title':'Kanıt bulgusu','description':'','status':'open','owner':'','due_date':None,'evidence_refs':[],'response_note':''})
    pkg=client.get(f"/api/compliance/applications/{a['id']}/response-package").json()
    assert pkg['submission_ready'] is False
    patch(f"/api/compliance/findings/{f['id']}",{'status':'resolved','evidence_refs':['kanit.pdf'],'response_note':'Tamamlandı'})
    pkg=client.get(f"/api/compliance/applications/{a['id']}/response-package").json()
    assert pkg['submission_ready'] is True
