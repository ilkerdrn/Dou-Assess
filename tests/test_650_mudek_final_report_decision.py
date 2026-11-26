import os
os.environ.setdefault('DOU_ASSESS_AUTH_DISABLED','true')
from fastapi.testclient import TestClient
from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION
from app.db import Base, engine
from app import models as m

def seed(c):
    with __import__('app.db',fromlist=['SessionLocal']).SessionLocal() as db:
        p=m.Program(name='Bilgisayar Mühendisliği',code='BM650',faculty='Mühendislik Fakültesi',department='Bilgisayar Mühendisliği'); db.add(p); db.flush()
        f=m.QualityFrameworkProfile(code='MUDEK31-650',framework_family='MÜDEK',version='3.1',name='MÜDEK 3.1',effective_from_year=2026,status='active',criteria=[],thresholds={},source_meta={},is_builtin=False); db.add(f); db.commit(); return p.id,f.id

def test_650_version_contract():
    assert APP_VERSION=='6.70-production-hardening'; assert EXPECTED_SCHEMA_REVISION=='0042_performance_production_hardening'

def test_final_report_freeze_and_revision_history(tmp_path):
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine); c=TestClient(app); pid,fid=seed(c)
    a=c.post('/api/compliance/applications',json={'program_id':pid,'framework_profile_id':fid,'academic_year':'2027-2028','application_type':'general','stage':'preparation'}); assert a.status_code==201,a.text; aid=a.json()['id']
    # advance to response window
    for st in ['submitted','pre_review','correction','visit_ready','site_visit']:
        r=c.patch(f'/api/compliance/applications/{aid}',json={'stage':st}); assert r.status_code==200,r.text
    assert c.post(f'/api/compliance/applications/{aid}/open-30-day-response').status_code==200
    f=c.post('/api/compliance/findings',json={'application_id':aid,'criterion_code':'3.1','finding_type':'weakness','title':'PÇ ölçümü','description':'kanıt güçlendirilmeli'}); assert f.status_code==201; find=f.json()
    u=c.patch(f"/api/compliance/findings/{find['id']}",json={'status':'closed','evidence_refs':['EV-650'],'response_note':'Kurum yanıtı ve doğrulama tamamlandı'}); assert u.status_code==200,u.text
    hist=c.get(f"/api/compliance/findings/{find['id']}/history"); assert hist.status_code==200 and len(hist.json())==1
    assert c.patch(f'/api/compliance/applications/{aid}',json={'stage':'decision'}).status_code==200
    r=c.patch(f'/api/compliance/applications/{aid}/final-report',json={'team_opinion':'Takım değerlendirmesi tamamlandı','institution_response_summary':'30 gün yanıtı incelendi','final_decision_code':'ACCREDITED','accreditation_start':'2027-09-01','accreditation_end':'2032-08-31'}); assert r.status_code==200,r.text
    final=c.post(f'/api/compliance/applications/{aid}/finalize-decision'); assert final.status_code==200,final.text
    data=final.json(); assert data['application']['stage']=='closed'; assert data['report']['status']=='frozen'; assert len(data['report']['snapshot_sha256'])==64
    report=c.get(f'/api/compliance/applications/{aid}/final-report').json(); assert report['criterion_results'][0]['result']=='satisfied'
