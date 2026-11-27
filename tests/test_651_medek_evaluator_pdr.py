import os, uuid
os.environ.setdefault('DOU_ASSESS_AUTH_DISABLED','true')
from fastapi.testclient import TestClient
from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION
from app.db import Base, engine, SessionLocal
from app import models as m


def seed():
    with SessionLocal() as db:
        p=m.Program(name='İnternet ve Ağ Teknolojileri',code='IAT651',faculty='Meslek Yüksekokulu',department='Bilgisayar Teknolojileri'); db.add(p); db.flush()
        f=m.QualityFrameworkProfile(code='MEDEK651',framework_family='MEDEK',version='v1.1',name='MEDEK v1.1',effective_from_year=2026,status='active',criteria=[],thresholds={},source_meta={},is_builtin=False); db.add(f); db.commit(); return p.id,f.id


def create_app(c,pid,fid,typ='general',prev=None):
    body={'program_id':pid,'framework_profile_id':fid,'academic_year':'2026-2027','application_type':typ,'stage':'preparation','evaluation_mode':'site_visit'}
    if prev: body['previous_application_id']=prev
    r=c.post('/api/compliance/applications',json=body); assert r.status_code==201,r.text; return r.json()


def test_651_version_contract():
    assert APP_VERSION=='6.70-production-hardening'
    assert EXPECTED_SCHEMA_REVISION=='0043_response_grade_revisions'


def test_medek_pdr_phases_seven_day_response_and_final_decision():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine); c=TestClient(app); pid,fid=seed(); a=create_app(c,pid,fid); aid=a['id']
    ws=c.post('/api/compliance/evaluator-workspaces',json={'application_id':aid,'evaluator_email':f'eval-{uuid.uuid4().hex[:6]}@example.org','evaluator_name':'Program Değerlendiricisi','access_mode':'read_only','expires_at':None}); assert ws.status_code==201,ws.text
    wid=ws.json()['id']
    for phase,typ,text in [('individual','site_question','Öğrenci işlerini sahada doğrulayın'),('pre_consensus','strength','Uygulama altyapısı güçlü'),('site_draft','improvement_area','PÇ ölçüm kanıtı güçlendirilmeli'),('final','improvement_area','PÇ ölçüm kanıtı sistematikleştirilmeli')]:
        r=c.post('/api/compliance/medek-pdr-items',json={'application_id':aid,'workspace_id':wid,'report_phase':phase,'criterion_code':'3.2','evaluator_name':'Program Değerlendiricisi','item_type':typ,'narrative':text,'assessment_value':'takım görüşü','evidence_refs':['EV-651'],'status':'confirmed'}); assert r.status_code==201,r.text
    center=c.get(f'/api/compliance/applications/{aid}/medek-pdr-center'); assert center.status_code==200,center.text
    d=center.json(); assert d['summary']['items']==4 and d['summary']['improvement_areas']==1 and d['summary']['site_questions']==1
    for st in ['submitted','pre_review','correction','visit_ready','site_visit']:
        r=c.patch(f'/api/compliance/applications/{aid}',json={'stage':st}); assert r.status_code==200,r.text
    resp=c.post(f'/api/compliance/applications/{aid}/open-medek-7-day-response'); assert resp.status_code==200,resp.text; assert resp.json()['stage']=='response_7_day'
    pack=c.get(f'/api/compliance/applications/{aid}/medek-response-package'); assert pack.status_code==200; assert len(pack.json()['improvement_areas'])>=1
    assert c.patch(f'/api/compliance/applications/{aid}',json={'stage':'decision'}).status_code==200
    rep=c.patch(f'/api/compliance/applications/{aid}/final-report',json={'team_opinion':'MEDEK takım nihai görüşü','institution_response_summary':'+7 gün kurum yanıtı incelendi','final_decision_code':'ACCREDITED','accreditation_start':'2027-01-01','accreditation_end':'2031-12-31'}); assert rep.status_code==200,rep.text
    frozen=c.post(f'/api/compliance/applications/{aid}/finalize-decision'); assert frozen.status_code==200,frozen.text; assert frozen.json()['report']['status']=='frozen'


def test_medek_interim_carries_only_confirmed_final_improvement_areas():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine); c=TestClient(app); pid,fid=seed(); general=create_app(c,pid,fid); gid=general['id']
    for typ,status in [('improvement_area','confirmed'),('strength','confirmed'),('improvement_area','draft')]:
        r=c.post('/api/compliance/medek-pdr-items',json={'application_id':gid,'report_phase':'final','criterion_code':'5.1','evaluator_name':'Takım','item_type':typ,'narrative':f'{typ}-{status}','assessment_value':'','evidence_refs':[],'status':status}); assert r.status_code==201,r.text
    # prior year is required by routing; use a later academic year and allow explicit previous application id.
    with SessionLocal() as db:
        g=db.get(m.AccreditationApplication,gid); g.academic_year='2025-2026'; db.commit()
    r=c.post('/api/compliance/applications',json={'program_id':pid,'framework_profile_id':fid,'academic_year':'2026-2027','application_type':'interim','stage':'preparation','previous_application_id':gid,'evaluation_mode':'site_visit'}); assert r.status_code==201,r.text
    iid=r.json()['id']; center=c.get(f'/api/compliance/applications/{iid}/medek-pdr-center'); assert center.status_code==200
    scope=center.json()['interim_scope']; assert len(scope)==1 and scope[0]['item_type']=='improvement_area' and scope[0]['carried_forward'] is True
