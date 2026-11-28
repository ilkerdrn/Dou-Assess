from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import APP_VERSION, EXPECTED_SCHEMA_REVISION, app

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def _post(path: str, payload: dict):
    r = client.post(path, json=payload)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def _put(path: str, payload: dict):
    r = client.put(path, json=payload)
    assert r.status_code == 200, (path, r.status_code, r.text)
    return r.json()


def test_662_release_contract_and_ui():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0048_question_bank_versions"
    root = Path(__file__).resolve().parents[1]
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    css = (root / "app/static/styles.css").read_text(encoding="utf-8")
    assert 'data-page="assessmentassurance"' in html
    assert 'id="page-assessmentassurance"' in html
    assert 'PROGRAM ASSESSMENT ASSURANCE' in html
    assert 'prepareAssessmentAssurance' in js
    assert '/assessment-plans/' in js
    assert '.assessment-assurance-row' in css


def test_662_autobuild_dashboard_and_review_snapshot():
    program = _post('/api/programs', {'code':'PRG662','name':'Program 662','faculty':'MYO','department':'Test'})
    course = _post('/api/courses', {'program_id':program['id'],'code':'BLP662','name':'Güvence Dersi','academic_year':'2026-2027','term':'Güz','instructor_email':'hoca662@dogus.edu.tr','instructor_name':'Hoca 662'})
    lo = _post(f"/api/courses/{course['id']}/learning-outcomes", {'code':'Ö1','description':'Analiz eder','target_percent':60})
    po = _post(f"/api/programs/{program['id']}/program-outcomes", {'academic_year':'2026-2027','code':'PÇ1','description':'Mesleki analiz yapar'})
    _post('/api/outcome-mappings', {'learning_outcome_id':lo['id'],'program_outcome_id':po['id'],'contribution':5})
    student = _post('/api/students', {'program_id':program['id'],'student_no':'662001','full_name':'Öğrenci 662','class_name':'1. Sınıf'})
    _post(f"/api/courses/{course['id']}/enrollments/bulk", {'student_ids':[student['id']]})

    measure = _post(f"/api/courses/{course['id']}/assessment-measures", {'code':'PRJ-662','title':'Dönem Projesi','measure_type':'project','directness':'direct','weight_percent':30,'max_points':100,'target_percent':60})
    r = client.patch(f"/api/assessment-measures/{measure['id']}", json={'status':'active'})
    assert r.status_code == 200, r.text
    _put(f"/api/assessment-measures/{measure['id']}/outcomes", {'items':[{'learning_outcome_id':lo['id'],'weight_percent':100}]})
    _put(f"/api/assessment-measures/{measure['id']}/results", {'student_id':student['id'],'raw_score':80,'rubric_scores':{},'feedback':'','status':'final'})

    survey = _post(f"/api/programs/{program['id']}/surveys", {'code':'MEZ-662','title':'Mezun PÇ Anketi','survey_type':'graduate','target_percent':60,'anonymous':True,'questions':[{'code':'S1','prompt':'Analiz yapabilirim','question_type':'likert','required':True,'order_no':1,'scale_min':1,'scale_max':5,'options':[],'weight_percent':100}]})
    q = survey['questions'][0]
    _put(f"/api/survey-questions/{q['id']}/targets", {'items':[{'target_type':'program_outcome','program_outcome_id':po['id'],'objective_id':None,'framework_family':'','criterion_code':'','weight_percent':100}]})
    _post(f"/api/surveys/{survey['id']}/activate", {})
    campaign = _post(f"/api/surveys/{survey['id']}/campaigns", {'code':'CMP-662','academic_year':'2026-2027','term':'','audience_type':'graduate','start_date':None,'end_date':None})
    campaign = _post(f"/api/survey-campaigns/{campaign['id']}/open", {})
    rr = client.post(campaign['public_path']+'/responses', json={'respondent_key':'','respondent_type':'graduate','respondent_meta':{},'answers':[{'question_id':q['id'],'numeric_value':4,'text_value':'','selected_options':[]}]})
    assert rr.status_code == 201, rr.text

    plan = _post(f"/api/programs/{program['id']}/assessment-plans/autobuild", {'academic_year':'2026-2027','title':'2026-2027 Ölçme Güvence Planı','version_no':1,'direct_weight':70,'indirect_weight':30,'owner':'Program Başkanı / Kalite','review_date':None,'notes':''})
    assert plan['status'] == 'active'
    assert plan['autobuilt_item_count'] == 2
    assert {x['channel'] for x in plan['items']} == {'direct','indirect'}

    direct_item = next(x for x in plan['items'] if x['channel'] == 'direct')
    patched = client.patch(f"/api/assessment-plan-items/{direct_item['id']}", json={'owner':'Ölçme Sorumlusu','target_percent':65})
    assert patched.status_code == 200, patched.text
    assert next(x for x in patched.json()['items'] if x['id'] == direct_item['id'])['owner'] == 'Ölçme Sorumlusu'

    bad_source = client.post(f"/api/assessment-plans/{plan['id']}/items", json={
        'program_outcome_id':po['id'],'channel':'direct','source_type':'survey','source_entity_id':survey['id'],
        'method_label':'Yanlış kanal','owner':'','term':'','frequency':'annual','target_percent':60,'due_date':None,'evidence_required':'','status':'planned'
    })
    assert bad_source.status_code == 422, bad_source.text

    dash = client.get(f"/api/assessment-plans/{plan['id']}/dashboard")
    assert dash.status_code == 200, dash.text
    data = dash.json()
    assert data['summary']['plan_coverage_percent'] == 100
    assert data['summary']['evidence_completeness_percent'] == 100
    row = data['program_outcomes'][0]
    assert row['direct_percent'] == 80
    assert row['indirect_percent'] == 80
    assert row['combined_percent'] == 80
    assert row['status'] == 'achieved'

    review = _post(f"/api/assessment-plans/{plan['id']}/reviews", {'decision':'PÇ sonuçları gözden geçirildi.','final':True})
    assert review['status'] == 'final'
    assert review['snapshot']['summary']['plan_coverage_percent'] == 100

    frozen_plan = client.patch(f"/api/assessment-plans/{plan['id']}", json={'owner':'Sonradan değişmesin'})
    assert frozen_plan.status_code == 409, frozen_plan.text
    frozen_item = client.patch(f"/api/assessment-plan-items/{direct_item['id']}", json={'owner':'Sonradan değişmesin'})
    assert frozen_item.status_code == 409, frozen_item.text
    frozen_autobuild = client.post(f"/api/programs/{program['id']}/assessment-plans/autobuild", json={'academic_year':'2026-2027','title':'2026-2027 Ölçme Güvence Planı','version_no':1,'direct_weight':70,'indirect_weight':30,'owner':'','review_date':None,'notes':''})
    assert frozen_autobuild.status_code == 409, frozen_autobuild.text

    plans = client.get(f"/api/programs/{program['id']}/assessment-plans?academic_year=2026-2027")
    assert plans.status_code == 200
    assert plans.json()[0]['status'] == 'reviewed'
