from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app import models as m

Base.metadata.create_all(engine)
client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def _program_course_student(prefix: str = "H70") -> tuple[int, int, int]:
    token = uuid.uuid4().hex[:8]
    p = client.post("/api/programs", json={
        "code": f"{prefix}-{token}", "name": f"Hardening {token}",
        "faculty": "MYO", "department": "Bilgisayar",
    })
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    c = client.post("/api/courses", json={
        "program_id": pid, "code": f"C{token}", "name": "Performans Test Dersi",
        "academic_year": "2026-2027", "term": "Güz",
        "instructor_email": "pilot-admin@local", "instructor_name": "Pilot Admin",
        "pass_threshold_percent": 50,
    })
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    st = client.post("/api/students", json={
        "program_id": pid, "student_no": f"70{token[:6]}",
        "full_name": f"Performans Öğrencisi {token}", "class_name": "1. Sınıf",
    })
    assert st.status_code == 201, st.text
    return pid, cid, st.json()["id"]


def test_670_release_migration_and_index_contract():
    release = dict(
        line.split("=", 1)
        for line in (ROOT / "RELEASE.env").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    assert release["APP_VERSION"] == "6.70-production-hardening"
    assert release["EXPECTED_SCHEMA_REVISION"] == "0042_performance_production_hardening"
    migration = (ROOT / "migrations/versions/0042_performance_production_hardening.py").read_text(encoding="utf-8")
    assert 'revision = "0042_performance_production_hardening"' in migration
    assert 'down_revision = "0041_program_review_evidence_hub"' in migration
    for index_name in (
        "ix_courses_scope_period_instructor",
        "ix_courses_instructor_email",
        "ix_students_program_student_no",
        "ix_question_bank_course_active_review_id",
        "ix_operational_jobs_status_run_after_locked",
        "ix_program_reviews_program_year_status_id",
    ):
        assert index_name in migration


def test_670_directory_summary_and_students_are_server_paginated():
    pid, _, sid = _program_course_student("DIR")
    summary = client.get("/api/directory/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["programs"] >= 1 and body["courses"] >= 1 and body["students"] >= 1
    assert int(body["students_by_program"].get(str(pid), 0)) >= 1

    page = client.get(f"/api/students?program_id={pid}&q=Performans&limit=1&offset=0")
    assert page.status_code == 200, page.text
    assert len(page.json()) == 1 and page.json()[0]["id"] == sid
    assert client.get("/api/students?limit=0").status_code == 422
    assert client.get("/api/students?limit=2001").status_code == 422


def test_670_question_bank_search_review_and_pagination_are_db_side():
    _, cid, _ = _program_course_student("QB")
    marker = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        for i in range(7):
            db.add(m.QuestionBank(
                course_id=cid,
                question_type="mcq",
                text=f"H70-{marker} performans sorusu {i}",
                default_points=10.0,
                correct_answer="A",
                choices={"A": "Doğru", "B": "Yanlış"},
                learning_outcome_code="O1",
                tags=[], topic="Performans", unit="Ünite 1",
                difficulty="medium", bloom_level="remember",
                author="Hardening", reviewer="",
                version_no=1, image_data="", rubric=[], expected_answer="",
                usage_count=0, answer_lines=5, review_status="draft",
                review_note="", quality_status="unmeasured", is_active=True,
            ))
        db.commit()
    first = client.get(f"/api/question-bank?course_id={cid}&q={marker}&review_status=draft&limit=3&offset=0")
    second = client.get(f"/api/question-bank?course_id={cid}&q={marker}&review_status=draft&limit=3&offset=3")
    assert first.status_code == 200 and second.status_code == 200
    assert len(first.json()) == 3 and len(second.json()) == 3
    assert {x["id"] for x in first.json()}.isdisjoint({x["id"] for x in second.json()})
    assert all(marker in x["text"] for x in first.json() + second.json())


def test_670_frontend_runtime_is_modular_and_large_lists_are_not_bootstrapped():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    core_js = (ROOT / "app/static/runtime-core.js").read_text(encoding="utf-8")
    assert html.index("/runtime-core.js?v=6.70-production-hardening") < html.index("/app.js?v=6.70-production-hardening")
    assert "/styles.css?v=6.70-production-hardening" in html
    assert "window.state" in core_js and "async function api" in core_js
    assert app_js.startswith("const state = window.state;")
    assert "api('GET','/api/directory/summary')" in app_js
    assert "loadAcademicStudentsPage" in app_js
    assert "studentCardSearch" in html
    assert "bankPagePrev" in html and "bankPageNext" in html


def test_670_dependency_lock_and_sbom_contract():
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    pins = [x.strip() for x in lock.splitlines() if x.strip() and not x.lstrip().startswith("#")]
    assert len(pins) >= 35
    assert all("==" in x and not any(op in x for op in (">=", "<=", "~=", ">", "<")) for x in pins)
    assert any(x.startswith("fastapi==") for x in pins)
    assert any(x.startswith("psycopg==") for x in pins)
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "pip install --no-cache-dir -r requirements.lock" in docker
    assert "pip check" in docker
    sbom = json.loads((ROOT / "SBOM-6.70.cdx.json").read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["metadata"]["component"]["version"] == "6.70-production-hardening"
    assert len(sbom["components"]) == len(pins)


def test_670_sql_scope_preserves_instructor_visibility_without_cross_program_leak():
    token = uuid.uuid4().hex[:8]
    # Admin creates two isolated programs/courses.
    p1 = client.post('/api/programs', json={'code':f'S1-{token}','name':f'Scope One {token}','faculty':'MYO','department':'A'}).json()['id']
    p2 = client.post('/api/programs', json={'code':f'S2-{token}','name':f'Scope Two {token}','faculty':'MYO','department':'B'}).json()['id']
    email = f'instructor-{token}@dogus.edu.tr'
    c1r = client.post('/api/courses', json={'program_id':p1,'code':f'I1{token}','name':'Own Course','academic_year':'2026-2027','term':'Güz','instructor_email':email,'instructor_name':'Scope Instructor','pass_threshold_percent':50})
    c2r = client.post('/api/courses', json={'program_id':p2,'code':f'I2{token}','name':'Other Course','academic_year':'2026-2027','term':'Güz','instructor_email':'other@dogus.edu.tr','instructor_name':'Other','pass_threshold_percent':50})
    assert c1r.status_code == 201 and c2r.status_code == 201
    c1, c2 = c1r.json()['id'], c2r.json()['id']
    with SessionLocal() as db:
        user = m.AppUser(email=email, display_name='Scope Instructor', auth_source='pilot', is_active=True)
        db.add(user); db.flush(); db.add(m.UserRoleAssignment(user_id=user.id, role='instructor', course_id=c1)); db.commit()
    headers={'X-DOU-Pilot-User':email}
    programs = client.get('/api/programs?limit=2000', headers=headers); assert programs.status_code == 200, programs.text
    courses = client.get('/api/courses?limit=5000', headers=headers); assert courses.status_code == 200, courses.text
    assert p1 in {x['id'] for x in programs.json()} and p2 not in {x['id'] for x in programs.json()}
    assert c1 in {x['id'] for x in courses.json()} and c2 not in {x['id'] for x in courses.json()}
    summary=client.get('/api/directory/summary', headers=headers); assert summary.status_code==200,summary.text
    assert summary.json()['programs'] == 1 and summary.json()['courses'] == 1
