from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def _post(path: str, payload: dict):
    r = client.post(path, json=payload)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def test_658_release_contract():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0046_exam_student_extra_time"


def test_658_academic_hierarchy_curriculum_catalog_and_sections_api():
    root = _post('/api/academic-units', {'code':'DOGUS658','name':'Doğuş Üniversitesi 658','unit_type':'institution'})
    school = _post('/api/academic-units', {'code':'MYO658','name':'Meslek Yüksekokulu 658','unit_type':'vocational_school','parent_id':root['id']})
    dept = _post('/api/academic-units', {'code':'BT658','name':'Bilgisayar Teknolojileri 658','unit_type':'department','parent_id':school['id']})
    program = _post('/api/programs', {'code':'IAT658','name':'İnternet ve Ağ Teknolojileri 658','faculty':'MYO','department':'Bilgisayar Teknolojileri','academic_unit_id':dept['id']})
    cv = _post(f"/api/programs/{program['id']}/curriculum-versions", {'code':'2026-V1','name':'2026 Müfredatı','academic_year_start':'2026-2027','decision_ref':'Kurul-658'})
    act = _post(f"/api/curriculum-versions/{cv['id']}/activate", {})
    assert act['status'] == 'active'
    catalog = _post(f"/api/programs/{program['id']}/course-catalog", {'code':'BLP658','name':'Python Programlama','ects':5,'local_credits':3,'default_semester_no':1,'course_type':'required'})
    link = _post(f"/api/curriculum-versions/{cv['id']}/courses", {'catalog_item_id':catalog['id'],'semester_no':1,'course_type':'required'})
    assert link['catalog_item_id'] == catalog['id']
    course = _post('/api/courses', {'program_id':program['id'],'catalog_item_id':catalog['id'],'code':'BLP658','name':'Python Programlama','academic_year':'2026-2027','term':'Güz','instructor_email':'hoca658@dogus.edu.tr','instructor_name':'Hoca 658'})
    offering = _post(f"/api/courses/{course['id']}/offerings", {'section_code':'B','catalog_item_id':catalog['id'],'curriculum_version_id':cv['id'],'campus':'Çengelköy','delivery_mode':'face_to_face','language':'TR','capacity':40})
    assignment = _post(f"/api/course-offerings/{offering['id']}/teaching-assignments", {'instructor_email':'hoca658@dogus.edu.tr','instructor_name':'Hoca 658','role':'lead','workload_hours':3})
    assert assignment['role'] == 'lead'
    structure = client.get(f"/api/programs/{program['id']}/academic-structure")
    assert structure.status_code == 200, structure.text
    body = structure.json()
    assert [x['code'] for x in body['unit_chain']] == ['DOGUS658','MYO658','BT658']
    assert body['catalog_item_count'] == 1
    assert body['offering_count'] == 1


def test_658_upgrade_backfills_legacy_flat_structure(tmp_path):
    db_path = tmp_path / 'legacy658.db'
    env = os.environ.copy()
    env['DATABASE_URL'] = f'sqlite+pysqlite:///{db_path}'
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', '0031_medek_final_decision'], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    con = sqlite3.connect(db_path)
    con.execute("insert into programs(code,name,faculty,department,external_source,created_at) values(?,?,?,?,?,CURRENT_TIMESTAMP)", ('IAT-LEG658','İnternet ve Ağ Teknolojileri','Meslek Yüksekokulu','Bilgisayar Teknolojileri',''))
    pid = con.execute("select id from programs where code='IAT-LEG658'").fetchone()[0]
    con.execute("insert into courses(program_id,code,name,academic_year,term,instructor_email,instructor_name,pass_threshold_percent,external_source,created_at) values(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", (pid,'BLP-LEG658','Python Programlama','2026-2027','Güz','legacy658@dogus.edu.tr','Legacy Hoca',50,''))
    cid = con.execute("select id from courses where code='BLP-LEG658'").fetchone()[0]
    con.commit(); con.close()
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    con = sqlite3.connect(db_path)
    assert con.execute('select version_num from alembic_version').fetchone()[0] == '0046_exam_student_extra_time'
    assert con.execute('select academic_unit_id from programs where id=?',(pid,)).fetchone()[0] is not None
    cat_id = con.execute('select catalog_item_id from courses where id=?',(cid,)).fetchone()[0]
    assert cat_id is not None
    offering = con.execute("select id from course_offerings where course_id=? and section_code='A'",(cid,)).fetchone()
    assert offering is not None
    assert con.execute('select count(*) from curriculum_versions where program_id=?',(pid,)).fetchone()[0] == 1
    con.close()
