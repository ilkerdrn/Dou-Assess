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


def test_660_release_contract():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0043_response_grade_revisions"


def test_660_project_rubric_outcome_and_student_result_flow():
    program = _post('/api/programs', {'code':'PRG660','name':'Program 660','faculty':'MYO','department':'Test'})
    course = _post('/api/courses', {'program_id':program['id'],'code':'BLP660','name':'Proje Dersi','academic_year':'2026-2027','term':'Güz','instructor_email':'hoca660@dogus.edu.tr','instructor_name':'Hoca 660'})
    lo = _post(f"/api/courses/{course['id']}/learning-outcomes", {'code':'Ö1','description':'Öğrenci çalışan bir çözüm tasarlar','target_percent':60})
    student = _post('/api/students', {'program_id':program['id'],'student_no':'660001','full_name':'Öğrenci 660','class_name':'1. Sınıf'})
    _post(f"/api/courses/{course['id']}/enrollments/bulk", {'student_ids':[student['id']]})

    rubric = _post(f"/api/courses/{course['id']}/rubrics", {
        'title':'Proje Rubriği','max_points':100,'criteria':[
            {'code':'K1','title':'Teknik doğruluk','learning_outcome_id':lo['id'],'order_no':1,'max_points':60,'weight_percent':60,'levels':[
                {'code':'4','title':'Üstün','description':'Tam','score_percent':100,'order_no':1},
                {'code':'3','title':'Yeterli','description':'Yeterli','score_percent':75,'order_no':2}
            ]},
            {'code':'K2','title':'Dokümantasyon','order_no':2,'max_points':40,'weight_percent':40,'levels':[
                {'code':'4','title':'Üstün','description':'Tam','score_percent':100,'order_no':1}
            ]}
        ]
    })
    assert len(rubric['criteria']) == 2
    rubric = _post(f"/api/rubrics/{rubric['id']}/activate", {})
    assert rubric['status'] == 'active'

    measure = _post(f"/api/courses/{course['id']}/assessment-measures", {
        'code':'PRJ-01','title':'Dönem Projesi','measure_type':'project','directness':'direct',
        'rubric_template_id':rubric['id'],'weight_percent':30,'max_points':100,'target_percent':60
    })
    assert measure['measure_type'] == 'project'
    assert measure['rubric_title'] == 'Proje Rubriği'

    linked = _put(f"/api/assessment-measures/{measure['id']}/outcomes", {'items':[{'learning_outcome_id':lo['id'],'weight_percent':100}]})
    assert linked['outcomes'][0]['code'] == 'Ö1'

    criteria = {x['code']: x['id'] for x in rubric['criteria']}
    result = _put(f"/api/assessment-measures/{measure['id']}/results", {
        'student_id':student['id'], 'rubric_scores':{str(criteria['K1']):50, str(criteria['K2']):30}, 'feedback':'İyi çalışma', 'status':'final'
    })
    assert result['raw_score'] == 80
    assert result['percent'] == 80

    summary = client.get(f"/api/assessment-measures/{measure['id']}/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body['result_count'] == 1
    assert body['average_percent'] == 80
    assert body['target_achievement_percent'] == 100
    assert body['ready_for_outcome_analysis'] is True


def test_660_server_rejects_invalid_rubric_score_and_ui_contract():
    root = Path(__file__).resolve().parents[1]
    html = (root/'app/static/index.html').read_text(encoding='utf-8')
    js = (root/'app/static/app.js').read_text(encoding='utf-8')
    css = (root/'app/static/styles.css').read_text(encoding='utf-8')
    assert 'data-page="assessmentmeasures"' in html
    assert 'id="page-assessmentmeasures"' in html
    assert 'GENERIC ASSESSMENT ENGINE' in html
    assert 'prepareAssessmentMeasures' in js
    assert '/assessment-measures' in js
    assert '.assessment-measure-layout' in css
