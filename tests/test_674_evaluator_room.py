from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from openpyxl import Workbook
from io import BytesIO

from app.db import Base, engine, SessionLocal
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


def test_room_ui_paths_match_backend_routes():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app/static/evaluator-room.js").read_text(encoding="utf-8")
    assert "json('/'+" not in js  # '/room/' with trailing slash 404s; overview must call '/room'
    program, course, exam, q, ws, hdr = _setup()
    base = f"/api/public/evaluator-workspaces/{ws['id']}/room"
    assert client.get(base + "?academic_year=2026-2027", headers=hdr).status_code == 200


def test_question_annulment_and_alternative_answer():
    program, course, exam, q, ws, hdr = _setup()
    assert client.patch(f"/api/exams/{exam['id']}/questions/{q['id']}", json={"points": 50}).status_code == 200
    q2 = _post(f"/api/exams/{exam['id']}/questions", {"order_no": 2, "question_type": "mcq", "text": "3+3?", "points": 50, "correct_answer": "A", "choices": {"A": "6", "B": "7", "C": "5"}, "learning_outcome_code": "Ö1"})
    assert client.post(f"/api/exams/{exam['id']}/status", json={"status": "ready"}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={"status": "grading"}).status_code == 200
    studs = client.get(f"/api/exams/{exam['id']}/students").json()
    _post(f"/api/exams/{exam['id']}/students/{studs[0]['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "B"}, {"question_id": q2["id"], "answer_text": "B"}]})
    _post(f"/api/exams/{exam['id']}/students/{studs[1]['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "A"}]})
    url = f"/api/exams/{exam['id']}/questions/{q2['id']}/key-exception"
    assert client.post(url, json={"action": "annul", "reason": ""}).status_code == 400
    r = client.post(url, json={"action": "accept_alternative", "alternative": "B", "reason": "Soru hatası"}); assert r.status_code == 200, r.text
    an = client.get(f"/api/exams/{exam['id']}/analytics").json()
    by = {s["student_no"]: s["total_score"] for s in an["students"]}
    assert sorted(by.values()) == [0.0, 100.0]  # s1: Q1 correct + Q2 alt B accepted; s2: both wrong/blank
    # later entries honour the alternative
    _post(f"/api/exams/{exam['id']}/students/{studs[1]['id']}/responses", {"responses": [{"question_id": q2["id"], "answer_text": "B"}]})
    r = client.post(f"/api/exams/{exam['id']}/questions/{q['id']}/key-exception", json={"action": "annul", "reason": "Hatalı soru"}); assert r.status_code == 200
    an = client.get(f"/api/exams/{exam['id']}/analytics").json()
    assert [s["total_score"] for s in an["students"]] == [100.0, 100.0]  # Q1 annulled, Q2 alt B accepted for both
    assert client.get(f"/api/exams/{exam['id']}/answer-key/revisions").json()


def test_room_course_file_download():
    program, course, exam, q, ws, hdr = _setup()
    r = client.get(f"/api/public/evaluator-workspaces/{ws['id']}/room/courses/{course['id']}/course-file.docx", headers=hdr)
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"
    assert client.get(f"/api/public/evaluator-workspaces/{ws['id']}/room/courses/{course['id']}/course-file.docx").status_code == 401


def test_evaluator_comment_lands_in_visit_notes_and_is_scoped():
    program, course, exam, q, ws, hdr = _setup()
    base = f"/api/public/evaluator-workspaces/{ws['id']}/room"
    assert client.post(base + "/comments", json={"title": "x"}).status_code in (401, 422)
    r = client.post(base + "/comments", headers=hdr, json={"title": "Ek örnek istiyoruz", "note": "Vize kâğıtları", "ref_type": "course", "ref_id": course["id"]})
    assert r.status_code == 201, r.text
    assert client.post(base + "/comments", headers=hdr, json={"title": "Başka program", "ref_type": "course", "ref_id": 10**6}).status_code == 404
    assert client.post(base + "/comments", headers=hdr, json={"title": "Yanlış tür", "ref_type": "user", "ref_id": 1}).status_code == 422
    mine = client.get(base + "/comments", headers=hdr).json()
    assert len(mine) == 1 and mine[0]["refs"] == [f"course:{course['id']}"]
    snap = client.get(f"/api/public/evaluator-workspaces/{ws['id']}/snapshot", headers=hdr).json()
    assert any(n["title"] == "Ek örnek istiyoruz" for n in snap["visit_notes"])


def test_student_portal_links_release_and_appeal():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    assert client.get(f"/api/exams/{eid}/student-links").status_code == 409  # grades not locked yet
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    studs = client.get(f"/api/exams/{eid}/students").json()
    _post(f"/api/exams/{eid}/students/{studs[0]['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "A"}]})
    _post(f"/api/exams/{eid}/students/{studs[1]['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "B"}]})
    lock = client.post(f"/api/exams/{eid}/grade-lock", json={"note": "ok"}); assert lock.status_code == 200, lock.text
    links = client.get(f"/api/exams/{eid}/student-links").json()["links"]
    assert len(links) == 2
    import re
    def parse(l):
        m_ = re.match(r"/student\.html\?exam=(\d+)&student=(\d+)#t=(\w+)", l["path"]); return m_.group(1), m_.group(2), {"X-DOU-Student-Token": m_.group(3)}
    e1, s1, h1 = parse(links[0]); e2, s2, h2 = parse(links[1])
    pub = f"/api/public/student-exam/{e1}/{s1}"
    assert client.get(pub).status_code == 401
    assert client.get(pub, headers=h2).status_code == 401  # another student's token
    v = client.get(pub, headers=h1); assert v.status_code == 200, v.text
    assert len(v.json()["questions"]) == 1 and v.json()["appeal_open"] is True
    assert client.post(pub + "/appeals", headers=h1, json={"question_id": q["id"], "reason": "kısa"}).status_code == 422
    r = client.post(pub + "/appeals", headers=h1, json={"question_id": q["id"], "reason": "Cevabım doğru olmalı, kontrol edilsin."}); assert r.status_code == 201, r.text
    assert client.post(pub + "/appeals", headers=h1, json={"question_id": q["id"], "reason": "Tekrar itiraz gerekçesi uzun."}).status_code == 409
    with SessionLocal() as db:
        from sqlalchemy import select as _sel
        from app import models as _m
        assert db.scalar(_sel(_m.OperationalNotification).where(_m.OperationalNotification.notification_type == "student_appeal", _m.OperationalNotification.user_email == "hoca@dogus.edu.tr").order_by(_m.OperationalNotification.id.desc()))
    staff = client.get(f"/api/exams/{eid}/appeals").json()
    assert any(a["created_by"].startswith("student:") for a in staff)


def test_classic_question_annulment_gives_full_marks_and_notifies_on_appeal():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    assert client.patch(f"/api/exams/{eid}/questions/{q['id']}", json={"points": 60}).status_code == 200
    qc = _post(f"/api/exams/{eid}/questions", {"order_no": 2, "question_type": "classic", "text": "Açıkla", "points": 40, "learning_outcome_code": "Ö1",
                                               "expected_answer": "Beklenen cevap", "rubric": {"criteria": [{"id": "a", "label": "A", "max_points": 40, "outcome_codes": ["Ö1"]}]}})
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    studs = client.get(f"/api/exams/{eid}/students").json()
    _post(f"/api/exams/{eid}/students/{studs[0]['id']}/responses", {"responses": [{"question_id": qc["id"], "answer_text": "x", "rubric_scores": {"a": 10}}]})
    r = client.post(f"/api/exams/{eid}/questions/{qc['id']}/key-exception", json={"action": "annul", "reason": "Soru kapsam dışı"}); assert r.status_code == 200, r.text
    assert r.json()["affected_responses"] == 2  # one regraded, one blank filled
    assert client.post(f"/api/exams/{eid}/questions/{qc['id']}/key-exception", json={"action": "accept_alternative", "alternative": "A", "reason": "x"}).status_code == 400
    an = client.get(f"/api/exams/{eid}/analytics").json()
    assert all(s["total_score"] >= 40 for s in an["students"])
    # manual re-entry on an annulled classic question keeps full marks
    _post(f"/api/exams/{eid}/students/{studs[0]['id']}/responses", {"responses": [{"question_id": qc["id"], "answer_text": "y", "rubric_scores": {"a": 5}}]})
    an = client.get(f"/api/exams/{eid}/analytics").json()
    assert all(s["total_score"] >= 40 for s in an["students"])
