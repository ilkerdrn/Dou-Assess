from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from openpyxl import Workbook
from io import BytesIO

from app.db import Base, engine
from app.main import app

Base.metadata.create_all(engine)
client = TestClient(app)


def _post(path, data):
    r = client.post(path, json=data)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def _workbook(code):
    wb = Workbook(); ws = wb.active; ws.title = "Programlar"
    ws.append(["program_code", "program_name", "faculty", "department"]); ws.append([code, "Oda Programı", "MYO", "Bölüm"])
    ws = wb.create_sheet("Dersler"); ws.append(["program_code", "course_code", "course_name", "academic_year", "term", "instructor_email"])
    ws.append([code, "ODA 101", "Oda Dersi", "2026-2027", "Güz", "hoca@dogus.edu.tr"])
    ws = wb.create_sheet("Ogrenciler"); ws.append(["program_code", "student_no", "full_name", "class_name"])
    ws.append([code, f"{code}01", "Ayşe Yılmaz", "1"]); ws.append([code, f"{code}02", "Mehmet Kaya", "1"])
    ws = wb.create_sheet("Ders_Kayitlari"); ws.append(["program_code", "course_code", "academic_year", "term", "student_no"])
    ws.append([code, "ODA 101", "2026-2027", "Güz", f"{code}01"]); ws.append([code, "ODA 101", "2026-2027", "Güz", f"{code}02"])
    ws = wb.create_sheet("OC_PC")
    ws.append(["program_code", "course_code", "academic_year", "term", "learning_outcome_code", "learning_outcome_description", "target", "program_outcome_code", "program_outcome_description", "contribution"])
    ws.append([code, "ODA 101", "2026-2027", "Güz", "Ö1", "Temel bilgi", 70, "PÇ1", "Alan bilgisi", 5])
    buf = BytesIO(); wb.save(buf); return buf.getvalue()


def _setup():
    code = "ER" + uuid.uuid4().hex[:6].upper()
    r = client.post("/api/import/pilot-workbook", files={"file": ("x.xlsx", _workbook(code), "application/octet-stream")})
    assert r.status_code == 200, r.text
    program = next(p for p in client.get("/api/programs").json() if p["code"] == code)
    course = next(c for c in client.get("/api/courses").json() if c["program_id"] == program["id"])
    fw = next(x for x in client.get("/api/quality360/frameworks").json() if x["framework_family"] == "MÜDEK" and x["version"] == "3.1")
    app_row = _post("/api/compliance/applications", {"program_id": program["id"], "framework_profile_id": fw["id"], "academic_year": "2026-2027", "application_type": "general", "stage": "preparation", "status": "active", "owner": "PB", "notes": "", "evaluation_mode": "site_visit"})
    ws = _post("/api/compliance/evaluator-workspaces", {"application_id": app_row["id"], "evaluator_email": f"ev-{uuid.uuid4().hex[:6]}@example.org", "evaluator_name": "Ev", "access_mode": "read_only", "expires_at": None})
    exam = _post("/api/exams", {"course_id": course["id"], "title": "Vize", "exam_type": "Vize", "exam_date": "2026-11-01", "duration_minutes": 50, "instructions": "", "sync_students": True})
    q = _post(f"/api/exams/{exam['id']}/questions", {"order_no": 1, "question_type": "mcq", "text": "2+2?", "points": 100, "correct_answer": "B", "choices": {"A": "3", "B": "4"}, "learning_outcome_code": "Ö1"})
    return program, course, exam, q, ws, {"X-DOU-Evaluator-Token": ws["invitation_token"]}


def test_evaluator_room_requires_token_and_masks_students():
    program, course, exam, q, ws, hdr = _setup()
    base = f"/api/public/evaluator-workspaces/{ws['id']}/room"
    assert client.get(base).status_code == 401
    assert client.get(base, headers={"X-DOU-Evaluator-Token": "wrong"}).status_code == 401
    ov = client.get(base, headers=hdr); assert ov.status_code == 200, ov.text
    d = ov.json()
    assert d["program"]["id"] == program["id"] and d["student_count"] == 2
    assert any(c["id"] == course["id"] and c["outcome_count"] == 1 for c in d["courses"])
    assert [p["code"] for p in d["program_outcomes"]] == ["PÇ1"]
    mx = client.get(base + "/outcome-matrix", headers=hdr).json()
    assert mx["rows"][0]["contributions"][str(mx["program_outcomes"][0]["id"])] == 5
    cd = client.get(f"{base}/courses/{course['id']}", headers=hdr).json()
    assert cd["learning_outcomes"][0]["program_outcomes"][0]["code"] == "PÇ1"
    assert {s["name"] for s in cd["students"]} == {"A*** Y***", "M*** K***"}
    assert "Ayşe" not in client.get(base + "/students", headers=hdr).text
    # draft exam is hidden until approved
    assert client.get(f"{base}/exams/{exam['id']}", headers=hdr).status_code == 404


def test_evaluator_room_exam_paper_student_answers_and_scope():
    program, course, exam, q, ws, hdr = _setup()
    base = f"/api/public/evaluator-workspaces/{ws['id']}/room"
    assert client.post(f"/api/exams/{exam['id']}/status", json={"status": "ready"}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={"status": "grading"}).status_code == 200
    es = client.get(f"/api/exams/{exam['id']}/students").json()[0]; sid = es['id']
    _post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "B"}]})
    ed = client.get(f"{base}/exams/{exam['id']}", headers=hdr); assert ed.status_code == 200, ed.text
    body = ed.json()
    assert body["questions"][0]["correct_answer"] == "B" and len(body["students"]) == 2
    assert all("***" in s["name"] for s in body["students"])
    pdf = client.get(f"{base}/exams/{exam['id']}/paper.pdf", headers=hdr)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    sx = client.get(f"{base}/exams/{exam['id']}/students/{sid}", headers=hdr).json()
    assert sx["answers"][0]["awarded_points"] == 100 and sx["total_score"] == 100
    card = client.get(f"{base}/students/{sid}/outcome-card", headers=hdr)
    assert card.status_code == 200 and "Ayşe" not in card.text and "Mehmet" not in card.text
    # another program's data is out of scope
    other_program, other_course, other_exam, *_ = _setup()
    assert client.get(f"{base}/courses/{other_course['id']}", headers=hdr).status_code == 404
    assert client.get(f"{base}/exams/{other_exam['id']}", headers=hdr).status_code == 404
    # deactivated workspace is closed
    client.patch(f"/api/compliance/evaluator-workspaces/{ws['id']}/access", json={"active": False})
    assert client.get(base, headers=hdr).status_code == 410


def test_readiness_flags_uncovered_outcomes_duplicates_and_uniform_key():
    program, course, exam, q, ws, hdr = _setup()
    r = client.get(f"/api/exams/{exam['id']}/readiness").json()
    assert not any("ölçülmüyor" in w for w in r["warnings"])  # single LO fully covered
    for n in range(2, 7):
        _post(f"/api/exams/{exam['id']}/questions", {"order_no": n, "question_type": "mcq", "text": "2+2?", "points": 1, "correct_answer": "B", "choices": {"A": "3", "B": "4"}, "learning_outcome_code": "Ö1"})
    r = client.get(f"/api/exams/{exam['id']}/readiness").json()
    assert any("aynı metne" in w for w in r["warnings"])
    assert any("aynı şık" in w for w in r["warnings"])


def test_scan_coverage_lists_students_without_scanned_paper():
    program, course, exam, q, ws, hdr = _setup()
    r = client.get(f"/api/exams/{exam['id']}/scan-coverage"); assert r.status_code == 200, r.text
    d = r.json()
    assert d["attended"] == 2 and d["scanned"] == 0 and d["missing_count"] == 2
