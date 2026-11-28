import os
os.environ.setdefault('DOU_ASSESS_AUTH_DISABLED','true')
from fastapi.testclient import TestClient
from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION
from app.db import Base, engine, SessionLocal
from app import models as m


def seed():
    with SessionLocal() as db:
        p=m.Program(name='İnternet ve Ağ Teknolojileri',code='IAT653',faculty='Meslek Yüksekokulu',department='Bilgisayar Teknolojileri'); db.add(p); db.flush()
        f=m.QualityFrameworkProfile(code='MEDEK653',framework_family='MEDEK',version='v1.1',name='MEDEK v1.1',effective_from_year=2026,status='active',criteria=[],thresholds={},source_meta={},is_builtin=False); db.add(f); db.commit(); return p.id,f.id


def make_ready(c,pid,fid):
    r=c.post('/api/compliance/applications',json={'program_id':pid,'framework_profile_id':fid,'academic_year':'2026-2027','application_type':'general','stage':'preparation','evaluation_mode':'site_visit'}); assert r.status_code==201,r.text; aid=r.json()['id']
    for code in ['FORM1','FORM2','FORM3']:
        r=c.post('/api/compliance/medek-pdr-forms',json={'application_id':aid,'form_code':code,'subject_ref':'program','title':code,'analysis_payload':{'checked':True},'result':'satisfied','reviewer':'Takım','evidence_refs':['EV'], 'status':'confirmed'}); assert r.status_code==201,r.text
    for criterion,score in [('1','4'),('2','3'),('3','4'),('4','3'),('5','4'),('6','3'),('7','4'),('8','3'),('9','4')]:
        r=c.post('/api/compliance/medek-pdr-items',json={'application_id':aid,'report_phase':'final','criterion_code':criterion,'evaluator_name':'Takım','item_type':'assessment','narrative':f'Ölçüt {criterion} nihai değerlendirmesi','assessment_value':score,'evidence_refs':['EV'], 'status':'confirmed'}); assert r.status_code==201,r.text
    for st in ['submitted','pre_review','correction','visit_ready','site_visit']:
        r=c.patch(f'/api/compliance/applications/{aid}',json={'stage':st}); assert r.status_code==200,r.text
    r=c.post(f'/api/compliance/applications/{aid}/open-medek-7-day-response'); assert r.status_code==200,r.text
    return aid


def test_653_release_contract():
    assert APP_VERSION=='6.70-production-hardening'
    assert EXPECTED_SCHEMA_REVISION=='0048_question_bank_versions'
    assert hasattr(m.AccreditationFinalReport,'decision_basis')
    assert hasattr(m.AccreditationFinalReport,'institution_report_sha256')


def test_653_medek_final_decision_duration_exports_and_freeze():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine); c=TestClient(app); pid,fid=seed(); aid=make_ready(c,pid,fid)
    rd=c.get(f'/api/compliance/applications/{aid}/medek-final-readiness'); assert rd.status_code==200,rd.text; assert rd.json()['ready'] is True; assert 'full' in rd.json()['eligible_decision_options']
    dec=c.post(f'/api/compliance/applications/{aid}/medek-final-decision?decision_code=full&accreditation_start=2027-01-01&team_opinion=Uygun'); assert dec.status_code==200,dec.text
    rep=dec.json()['report']; assert rep['accreditation_term_years']==4; assert rep['accreditation_start']=='2027-01-01'; assert rep['accreditation_end']=='2030-12-31'; assert rep['next_review_type']=='reaccreditation'; assert rep['next_review_due']=='2029-12-31'
    docx=c.get(f'/api/compliance/applications/{aid}/medek-institution-report.docx'); assert docx.status_code==200,docx.text; assert docx.content[:2]==b'PK'; assert len(docx.headers.get('x-content-sha256',''))==64
    pdf=c.get(f'/api/compliance/applications/{aid}/medek-institution-report.pdf'); assert pdf.status_code==200,pdf.text; assert pdf.content.startswith(b'%PDF'); assert len(pdf.headers.get('x-content-sha256',''))==64
    frozen=c.post(f'/api/compliance/applications/{aid}/medek-finalize'); assert frozen.status_code==200,frozen.text; assert frozen.json()['report']['status']=='frozen'; assert len(frozen.json()['report']['snapshot_sha256'])==64; assert frozen.json()['application']['stage']=='closed'


def test_653_readiness_blocks_missing_forms():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine); c=TestClient(app); pid,fid=seed()
    r=c.post('/api/compliance/applications',json={'program_id':pid,'framework_profile_id':fid,'academic_year':'2026-2027','application_type':'general','stage':'response_7_day','evaluation_mode':'site_visit'}); assert r.status_code==201,r.text; aid=r.json()['id']
    rd=c.get(f'/api/compliance/applications/{aid}/medek-final-readiness'); assert rd.status_code==200; assert rd.json()['ready'] is False; assert rd.json()['gaps']
    dec=c.post(f'/api/compliance/applications/{aid}/medek-final-decision?decision_code=full'); assert dec.status_code==409
