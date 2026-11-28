from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.main import APP_VERSION, EXPECTED_SCHEMA_REVISION, app
from app import models as m

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def _post(path: str, payload: dict):
    r=client.post(path,json=payload); assert r.status_code in (200,201),(path,r.status_code,r.text); return r.json()

def _put(path: str, payload: dict):
    r=client.put(path,json=payload); assert r.status_code==200,(path,r.status_code,r.text); return r.json()


def test_661_release_contract():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0047_institution_settings_outcome_approval"


def test_661_direct_indirect_outcome_evidence_flow_and_anonymity():
    program=_post('/api/programs',{'code':'PRG661','name':'Program 661','faculty':'MYO','department':'Test'})
    course=_post('/api/courses',{'program_id':program['id'],'code':'BLP661','name':'Kalite Dersi','academic_year':'2026-2027','term':'Güz','instructor_email':'hoca661@dogus.edu.tr','instructor_name':'Hoca 661'})
    lo=_post(f"/api/courses/{course['id']}/learning-outcomes",{'code':'Ö1','description':'Problem çözer','target_percent':60})
    po=_post(f"/api/programs/{program['id']}/program-outcomes",{'academic_year':'2026-2027','code':'PÇ1','description':'Mesleki problemleri çözer'})
    _post('/api/outcome-mappings',{'learning_outcome_id':lo['id'],'program_outcome_id':po['id'],'contribution':5})
    student=_post('/api/students',{'program_id':program['id'],'student_no':'661001','full_name':'Öğrenci 661','class_name':'1. Sınıf'})
    _post(f"/api/courses/{course['id']}/enrollments/bulk",{'student_ids':[student['id']]})

    measure=_post(f"/api/courses/{course['id']}/assessment-measures",{'code':'PRJ-661','title':'Proje','measure_type':'project','directness':'direct','weight_percent':30,'max_points':100,'target_percent':60})
    r=client.patch(f"/api/assessment-measures/{measure['id']}",json={'status':'active'}); assert r.status_code==200,r.text
    _put(f"/api/assessment-measures/{measure['id']}/outcomes",{'items':[{'learning_outcome_id':lo['id'],'weight_percent':100}]})
    _put(f"/api/assessment-measures/{measure['id']}/results",{'student_id':student['id'],'raw_score':80,'rubric_scores':{},'feedback':'','status':'final'})

    survey=_post(f"/api/programs/{program['id']}/surveys",{'code':'MEZ-661','title':'Mezun Değerlendirmesi','survey_type':'graduate','target_percent':60,'anonymous':True,'questions':[{'code':'S1','prompt':'Mesleki problemleri çözebilirim','question_type':'likert','required':True,'order_no':1,'scale_min':1,'scale_max':5,'options':[],'weight_percent':100}]})
    q=survey['questions'][0]
    _put(f"/api/survey-questions/{q['id']}/targets",{'items':[{'target_type':'program_outcome','program_outcome_id':po['id'],'objective_id':None,'framework_family':'','criterion_code':'','weight_percent':100}]})
    _post(f"/api/surveys/{survey['id']}/activate",{})
    campaign=_post(f"/api/surveys/{survey['id']}/campaigns",{'code':'CMP-661','academic_year':'2026-2027','term':'','audience_type':'graduate','start_date':None,'end_date':None})
    campaign=_post(f"/api/survey-campaigns/{campaign['id']}/open",{})

    public=client.get(campaign['public_path']); assert public.status_code==200, public.text
    submitted=client.post(campaign['public_path']+'/responses',json={'respondent_key':'SHOULD-NOT-BE-STORED','respondent_type':'graduate','respondent_meta':{'email':'secret@example.com'},'answers':[{'question_id':q['id'],'numeric_value':4,'text_value':'','selected_options':[]}]})
    assert submitted.status_code==201,submitted.text
    assert submitted.json()['anonymous'] is True

    analytics=client.get(f"/api/survey-campaigns/{campaign['id']}/analytics"); assert analytics.status_code==200,analytics.text
    assert analytics.json()['overall_percent']==80
    mix=client.get(f"/api/programs/{program['id']}/outcome-evidence-mix?academic_year=2026-2027&direct_weight=70&indirect_weight=30"); assert mix.status_code==200,mix.text
    row=mix.json()['program_outcomes'][0]
    assert row['direct_percent']==80
    assert row['indirect_percent']==80
    assert row['combined_percent']==80
    assert row['evidence_status']=='complete'

    with SessionLocal() as db:
        stored=db.scalar(select(m.SurveyResponse).where(m.SurveyResponse.campaign_id==campaign['id']))
        assert stored.respondent_key_hash == ''
        assert stored.respondent_meta == {}


def test_661_nonanonymous_duplicate_guard_and_ui_contract():
    root=Path(__file__).resolve().parents[1]
    html=(root/'app/static/index.html').read_text(encoding='utf-8')
    js=(root/'app/static/app.js').read_text(encoding='utf-8')
    css=(root/'app/static/styles.css').read_text(encoding='utf-8')
    assert 'data-page="surveys"' in html
    assert 'id="page-surveys"' in html
    assert 'DOLAYLI ÖLÇME MOTORU' in html
    assert 'prepareSurveys' in js
    assert 'outcome-evidence-mix' in js
    assert '.survey-layout' in css
