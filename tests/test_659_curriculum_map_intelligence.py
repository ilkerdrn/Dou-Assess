from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION
from app.db import Base, engine

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


def test_659_release_contract():
    assert APP_VERSION == '6.70-production-hardening'
    assert EXPECTED_SCHEMA_REVISION == '0043_response_grade_revisions'


def test_659_irm_curriculum_map_and_gap_engine():
    root = _post('/api/academic-units', {'code':'DOGUS659','name':'Doğuş Üniversitesi 659','unit_type':'institution'})
    school = _post('/api/academic-units', {'code':'MYO659','name':'MYO 659','unit_type':'vocational_school','parent_id':root['id']})
    program = _post('/api/programs', {'code':'PRG659','name':'Program 659','faculty':'MYO','department':'Test','academic_unit_id':school['id']})
    cv = _post(f"/api/programs/{program['id']}/curriculum-versions", {'code':'CV659','name':'Müfredat 659','academic_year_start':'2026-2027'})
    _post(f"/api/curriculum-versions/{cv['id']}/activate", {})

    cats=[]
    for code,name,sem in [('C1-659','Temel Ders',1),('C2-659','Orta Ders',2),('C3-659','İleri Ders',4),('C4-659','Bağlantısız Ders',3)]:
        cat=_post(f"/api/programs/{program['id']}/course-catalog", {'code':code,'name':name,'ects':5,'default_semester_no':sem,'course_type':'required'})
        _post(f"/api/curriculum-versions/{cv['id']}/courses", {'catalog_item_id':cat['id'],'semester_no':sem,'course_type':'required'})
        cats.append(cat)

    pos=[]
    for code in ['PÇ1','PÇ2','PÇ3']:
        pos.append(_post(f"/api/programs/{program['id']}/program-outcomes", {'academic_year':'2026-2027','code':code,'description':f'{code} açıklaması'}))

    # PÇ1 has full I -> R -> M progression.
    _put(f"/api/curriculum-versions/{cv['id']}/outcome-map", {'catalog_item_id':cats[0]['id'],'program_outcome_id':pos[0]['id'],'coverage_level':'I'})
    _put(f"/api/curriculum-versions/{cv['id']}/outcome-map", {'catalog_item_id':cats[1]['id'],'program_outcome_id':pos[0]['id'],'coverage_level':'R'})
    _put(f"/api/curriculum-versions/{cv['id']}/outcome-map", {'catalog_item_id':cats[2]['id'],'program_outcome_id':pos[0]['id'],'coverage_level':'M'})
    # PÇ2 only one course and no mastery -> two risks.
    _put(f"/api/curriculum-versions/{cv['id']}/outcome-map", {'catalog_item_id':cats[0]['id'],'program_outcome_id':pos[1]['id'],'coverage_level':'I'})
    # PÇ3 stays completely uncovered.

    matrix = client.get(f"/api/curriculum-versions/{cv['id']}/outcome-map")
    assert matrix.status_code == 200, matrix.text
    body = matrix.json()
    assert len(body['courses']) == 4
    assert len(body['program_outcomes']) == 3

    gaps = client.get(f"/api/curriculum-versions/{cv['id']}/outcome-map/gaps")
    assert gaps.status_code == 200, gaps.text
    g = gaps.json()
    assert g['summary']['coverage_percent'] == 66.7
    assert g['summary']['mastery_percent'] == 33.3
    assert 'PÇ3' in g['gaps']['outcomes_without_coverage']
    assert 'PÇ2' in g['gaps']['outcomes_without_mastery']
    assert 'PÇ2' in g['gaps']['single_course_dependencies']
    assert any(x['code'] == 'C4-659' for x in g['gaps']['courses_without_outcome_mapping'])


def test_659_curriculum_map_workspace_ui_contract():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    css = (root / "app/static/styles.css").read_text(encoding="utf-8")
    assert 'data-page="curriculummap"' in html
    assert 'id="page-curriculummap"' in html
    assert 'I / R / M MATRİSİ' in html
    assert 'prepareCurriculumMap' in js
    assert '/outcome-map/gaps' in js
    assert '.curriculum-map-table' in css
