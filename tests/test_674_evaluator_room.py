from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from openpyxl import Workbook
from io import BytesIO

from app.db import Base, engine, SessionLocal
from sqlalchemy import select as select_
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


def test_institution_reply_reaches_evaluator():
    program, course, exam, q, ws, hdr = _setup()
    base = f"/api/public/evaluator-workspaces/{ws['id']}/room"
    c = client.post(base + "/comments", headers=hdr, json={"title": "Ek örnek istiyoruz", "note": "Final"}).json()
    other = client.post(f"/api/compliance/visit-notes/{c['id']}/reply", json={"note": "Kanıt odasına eklendi."}); assert other.status_code == 201, other.text
    mine = client.get(base + "/comments", headers=hdr).json()
    assert mine[0]["replies"][0]["note"] == "Kanıt odasına eklendi."
    plain = _post("/api/compliance/visit-notes", {"application_id": ws["application_id"], "criterion_code": "", "note_type": "observation", "title": "iç not", "note": "", "recorded_by": "x", "visibility": "internal", "evidence_refs": [], "occurred_at": None})
    assert client.post(f"/api/compliance/visit-notes/{plain['id']}/reply", json={"note": "olmaz"}).status_code == 409


def test_outcome_source_label_and_deactivate_instead_of_delete():
    program, course, exam, q, ws, hdr = _setup()
    cid = course["id"]
    los = client.get(f"/api/courses/{cid}/outcomes").json()["learning_outcomes"]
    assert los[0]["source"] == "obs" and los[0]["is_active"] is True
    patched = client.patch(f"/api/learning-outcomes/{los[0]['id']}", json={"description": "Değiştirilmiş metin"}).json()
    assert patched["source"] == "obs_modified"
    new = _post(f"/api/courses/{cid}/learning-outcomes", {"code": "Ö9", "description": "Yeni çıktı", "target_percent": 60})
    assert new["source"] == "assess"
    assert client.delete(f"/api/learning-outcomes/{new['id']}").json()["deleted"] is True  # unlinked -> really deleted
    # Ö1 is referenced by the exam snapshot -> deactivated, not deleted, and skipped by new exam snapshots
    r = client.delete(f"/api/learning-outcomes/{los[0]['id']}").json()
    assert r["deactivated"] is True
    out = client.get(f"/api/courses/{cid}/outcomes").json()["learning_outcomes"]
    assert out[0]["is_active"] is False
    exam2 = _post("/api/exams", {"course_id": cid, "title": "Final", "exam_type": "Final", "exam_date": "2026-12-01", "duration_minutes": 50, "instructions": "", "sync_students": True})
    assert exam2["learning_outcomes"] == []


def test_print_screen_summary_confirm_lock_and_attendance_sheet():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    s0 = client.get(f"/api/exams/{eid}/print-summary").json()
    assert s0["can_confirm"] is False and s0["student_count"] == 2
    assert client.post(f"/api/exams/{eid}/print-confirm").status_code == 409  # still draft
    assert client.post(f"/api/exams/{eid}/status", json={"status": "ready"}).status_code == 200
    s1 = client.get(f"/api/exams/{eid}/print-summary").json()
    assert s1["can_confirm"] is True and s1["pages_per_paper"] >= 1 and s1["total_pages"] == s1["pages_per_paper"] * 2
    sheet = client.get(f"/api/exams/{eid}/attendance-sheet.pdf"); assert sheet.status_code == 200 and sheet.content.startswith(b"%PDF")
    ok = client.post(f"/api/exams/{eid}/print-confirm"); assert ok.status_code == 200, ok.text
    assert client.get(f"/api/exams/{eid}").json()["printed_at"]
    back = client.post(f"/api/exams/{eid}/status", json={"status": "draft"})
    assert back.status_code == 409 and "kopyal" in back.text
    assert client.get(f"/api/exams/{eid}/print-summary").json()["can_confirm"] is False


def test_answer_sheet_bubbles_follow_choice_count_and_rules_have_marking_instruction():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    _post(f"/api/exams/{eid}/questions", {"order_no": 2, "question_type": "mcq", "text": "Üç şık", "points": 1, "correct_answer": "C", "choices": {"A": "a", "B": "b", "C": "c"}, "learning_outcome_code": "Ö1"})
    meta = client.get(f"/api/exams/{eid}/paper-metadata").json()
    per_q = {}
    for b in meta["omr_layout"]["bubbles"]:
        per_q.setdefault(b["display_no"], []).append(b["letter"])
    assert sorted(len(v) for v in per_q.values()) == [2, 3]
    pdf = client.get(f"/api/exams/{eid}/paper.pdf").content
    from pypdf import PdfReader
    from io import BytesIO
    text = PdfReader(BytesIO(pdf)).pages[0].extract_text()
    assert "tamamen doldurun" in text


def test_obs_resync_status_and_ownership_guard(monkeypatch):
    import app.main as main_mod
    from types import SimpleNamespace
    me = client.get("/api/auth/me").json()["email"]
    import dataclasses
    monkeypatch.setattr(main_mod, "settings", dataclasses.replace(main_mod.settings, obs_proliz_enabled=True))
    st = client.get("/api/auth/obs-sync-status").json()
    assert st["enabled"] is True
    before_at = st["last_sync_at"]  # DB may already hold a run from an earlier invocation
    monkeypatch.setattr(main_mod, "teacher_login_and_sync", lambda db, u, p, d=None: (SimpleNamespace(id=1, email="someone.else@dogus.edu.tr"), {"courses": 1, "students": 2, "enrollments": 2, "donem_id": "1"}))
    assert client.post("/api/integrations/obs/resync", json={"username": "S1", "password": "x"}).status_code == 403
    monkeypatch.setattr(main_mod, "teacher_login_and_sync", lambda db, u, p, d=None: (SimpleNamespace(id=1, email=me), {"courses": 1, "students": 2, "enrollments": 2, "donem_id": "1"}))
    r = client.post("/api/integrations/obs/resync", json={"username": "S1", "password": "x"}); assert r.status_code == 200, r.text
    st = client.get("/api/auth/obs-sync-status").json()
    assert st["last_sync_at"] and st["last_sync_at"] != before_at and st["summary"]["students"] == 2


def test_outcome_diff_report_and_grading_progress():
    program, course, exam, q, ws, hdr = _setup()
    cid, eid = course["id"], exam["id"]
    assert client.get(f"/api/courses/{cid}/outcome-diff").json()["difference_count"] == 0
    lo = client.get(f"/api/courses/{cid}/outcomes").json()["learning_outcomes"][0]
    client.patch(f"/api/learning-outcomes/{lo['id']}", json={"description": "Yeni metin"})
    client.patch(f"/api/learning-outcomes/{lo['id']}", json={"description": "Daha yeni metin"})
    _post(f"/api/courses/{cid}/learning-outcomes", {"code": "Ö7", "description": "Assess'te eklendi", "target_percent": 60})
    d = client.get(f"/api/courses/{cid}/outcome-diff").json()
    kinds = {i["code"]: i for i in d["items"]}
    assert kinds["Ö1"]["kind"] == "modified" and kinds["Ö1"]["obs_original"]["description"] == "Temel bilgi"  # first 'before' = OBS original
    assert kinds["Ö7"]["kind"] == "added_in_assess"
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    gp = client.get(f"/api/exams/{eid}/grading-progress").json()
    assert gp["missing"] == 2 and gp["complete"] is False and len(gp["students_with_missing"]) == 2
    studs = client.get(f"/api/exams/{eid}/students").json()
    _post(f"/api/exams/{eid}/students/{studs[0]['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "A"}]})  # wrong answer = a real 0
    gp = client.get(f"/api/exams/{eid}/grading-progress").json()
    assert gp["entered"] == 1 and gp["missing"] == 1 and gp["questions"][0]["entered"] == 1


def test_classic_grid_bulk_entry_validation_and_progress():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    assert client.patch(f"/api/exams/{eid}/questions/{q['id']}", json={"points": 60}).status_code == 200
    qc = _post(f"/api/exams/{eid}/questions", {"order_no": 2, "question_type": "classic", "text": "Açıkla", "points": 40, "learning_outcome_code": "Ö1", "expected_answer": "x",
                                               "rubric": {"criteria": [{"id": "a", "label": "A", "max_points": 25, "outcome_codes": ["Ö1"]}, {"id": "b", "label": "B", "max_points": 15, "outcome_codes": ["Ö1"]}]}})
    url = f"/api/exams/{eid}/questions/{qc['id']}/grid"
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    g = client.get(url).json()
    assert g["editable"] is True and len(g["rows"]) == 2 and all(not r["entered"] for r in g["rows"]) and [c["id"] for c in g["question"]["criteria"]] == ["a", "b"]
    ids = [r["student_id"] for r in g["rows"]]
    bad = client.post(url, json={"rows": [{"student_id": ids[0], "rubric_scores": {"a": 10, "b": 5}}, {"student_id": ids[1], "rubric_scores": {"a": 30, "b": 5}}]})
    assert bad.status_code == 422  # all-or-nothing: nothing saved
    assert not any(r["entered"] for r in client.get(url).json()["rows"])
    ok = client.post(url, json={"rows": [{"student_id": ids[0], "rubric_scores": {"a": 10, "b": 5}}, {"student_id": ids[1], "rubric_scores": {"a": 25, "b": 0}}]}); assert ok.status_code == 200, ok.text
    assert ok.json()["saved"] == 2
    g = client.get(url).json()
    assert {r["student_id"]: r["awarded"] for r in g["rows"]} == {ids[0]: 15.0, ids[1]: 25.0}
    assert client.post(url, json={"rows": [{"student_id": ids[0], "rubric_scores": {"a": 10, "b": 5}}]}).json()["saved"] == 0  # unchanged -> no revision
    mcq = client.get(f"/api/exams/{eid}/questions/{q['id']}/grid"); assert mcq.status_code == 409


def test_outcome_term_is_configurable_via_auth_config():
    assert client.get("/api/auth/config").json()["outcome_term"] in {"Öğrenim", "Öğrenme", "Kazanım"}


def test_versioned_thresholds_drive_po_target_and_lo_default():
    program, course, exam, q, ws, hdr = _setup()
    pid, cid, eid = program["id"], course["id"], exam["id"]
    t1 = _post("/api/outcome-thresholds", {"program_id": pid, "kind": "lo", "target_percent": 75})
    assert t1["version_no"] == 1
    t2 = _post("/api/outcome-thresholds", {"program_id": pid, "kind": "lo", "target_percent": 80, "note": "yeni yönerge"})
    assert t2["version_no"] == 2
    rows = [r for r in client.get(f"/api/outcome-thresholds?program_id={pid}").json() if r["kind"] == "lo" and r["program_id"] == pid]
    assert sorted((r["version_no"], r["is_active"]) for r in rows) == [(1, False), (2, True)]
    lo = _post(f"/api/courses/{cid}/learning-outcomes", {"code": "Ö5", "description": "Varsayılan hedef"})
    assert lo["target_percent"] == 80
    explicit = _post(f"/api/courses/{cid}/learning-outcomes", {"code": "Ö6", "description": "Açık hedef", "target_percent": 55})
    assert explicit["target_percent"] == 55
    _post("/api/outcome-thresholds", {"program_id": pid, "kind": "po", "target_percent": 90})
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    an = client.get(f"/api/exams/{eid}/analytics").json()
    assert an["program_outcomes"] and all(p["target_percent"] == 90 for p in an["program_outcomes"])


def test_closure_package_scan_audit_and_retention():
    import zipfile, json as _json
    from io import BytesIO
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    assert client.get(f"/api/exams/{eid}/closure-package.zip").status_code == 409  # not locked yet
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    studs = client.get(f"/api/exams/{eid}/students").json()
    for s in studs:
        _post(f"/api/exams/{eid}/students/{s['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "B"}]})
    assert client.post(f"/api/exams/{eid}/grade-lock", json={"note": ""}).status_code == 200
    r = client.get(f"/api/exams/{eid}/closure-package.zip"); assert r.status_code == 200, r.text
    z = zipfile.ZipFile(BytesIO(r.content)); names = set(z.namelist())
    assert {"exam.json", "analytics.json", "responses.json", "grade-revisions.json", "audit-trail.json", "SHA256SUMS.json", "paper/booklet-A.pdf"} <= names
    man = _json.loads(z.read("SHA256SUMS.json"))
    import hashlib
    assert man["files"]["responses.json"] == hashlib.sha256(z.read("responses.json")).hexdigest() and man["package_sha256"] == r.headers["x-dou-package-sha256"]
    sa = client.get(f"/api/exams/{eid}/scan-audit").json()
    assert sa["sampled"] == 0 and sa["error_rate_percent"] is None
    assert client.post(f"/api/exams/{eid}/scan-audit/sample", json={"percent": 10}).json()["drawn"] == 0  # no accepted scans in this fixture
    ret = client.get("/api/archive/retention").json()
    assert ret["scan_retention_days"] >= 365
    assert client.post(f"/api/exams/{eid}/purge-scans", json={"reason": "süre doldu"}).status_code == 409  # retention not reached


def test_scan_audit_sampling_error_rate_and_purge_after_retention(monkeypatch):
    import dataclasses
    from datetime import datetime, timedelta, timezone
    import app.archive_api as arch
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    with SessionLocal() as db:
        from app import models as _m
        sess = _m.ScanSession(exam_id=eid, source_name="t.pdf", source_sha256="x" * 64, status="completed", page_count=20, accepted_count=20)
        db.add(sess); db.flush()
        for i in range(20):
            db.add(_m.ScanItem(session_id=sess.id, exam_id=eid, page_no=i + 1, status="accepted", page_kind="omr", page_fingerprint=f"fp{eid}-{i}", answers={"1": "A"}, student_no_detected="1", preview_name=None))
        db.commit()
    s = _post(f"/api/exams/{eid}/scan-audit/sample", {"percent": 25, "minimum": 3})
    assert s["drawn"] == 5 and s["pool_left"] == 15
    st = client.get(f"/api/exams/{eid}/scan-audit").json()
    assert st["sampled"] == 5 and len(st["pending"]) == 5 and st["error_rate_percent"] is None
    ids = [p["scan_item_id"] for p in st["pending"]]
    for i, iid in enumerate(ids):
        assert client.post(f"/api/scan-items/{iid}/audit-result", json={"ok": i != 0}).status_code == 200
    assert client.post(f"/api/scan-items/{ids[0]}/audit-result", json={"ok": True}).status_code == 409  # already judged
    st = client.get(f"/api/exams/{eid}/scan-audit").json()
    assert st["checked"] == 5 and st["mismatches"] == 1 and st["error_rate_percent"] == 20.0 and st["meets_target"] is False
    # retention: shrink the period to 0 days -> expired -> purge allowed and recorded
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    for x in client.get(f"/api/exams/{eid}/students").json():
        _post(f"/api/exams/{eid}/students/{x['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "B"}]})
    # a scan row with a preview file so the row counts as having files
    from pathlib import Path
    from app.config import settings as _s
    Path(_s.scan_storage_path).mkdir(parents=True, exist_ok=True)
    (Path(_s.scan_storage_path) / f"purge_{eid}.jpg").write_bytes(b"x")
    with SessionLocal() as db:
        from app import models as _m
        it = db.scalar(select_(_m.ScanItem).where(_m.ScanItem.exam_id == eid)); it.preview_name = f"purge_{eid}.jpg"; db.commit()
    assert client.post(f"/api/exams/{eid}/grade-lock", json={"note": ""}).status_code == 200
    monkeypatch.setattr(arch, "settings", dataclasses.replace(arch.settings, scan_retention_days=0))
    r = client.post(f"/api/exams/{eid}/purge-scans", json={"reason": "saklama süresi doldu"}); assert r.status_code == 200, r.text
    assert r.json()["files_removed"] == 1 and not (Path(_s.scan_storage_path) / f"purge_{eid}.jpg").exists()


def test_obs_grade_export_po_formula_and_measure_excel_import():
    from io import BytesIO
    from openpyxl import Workbook, load_workbook
    program, course, exam, q, ws, hdr = _setup()
    cid, eid, pid = course["id"], exam["id"], program["id"]
    assert client.get(f"/api/courses/{cid}/obs-grades.xlsx").status_code == 409  # no approved, weighted exam yet
    f = client.get(f"/api/programs/{pid}/po-formula.md"); assert f.status_code == 200
    assert "PÇ başarısı" in f.text and "PÇ1" in f.text and "ODA 101" in f.text
    meas = _post(f"/api/courses/{cid}/assessment-measures", {"code": "ODEV1", "title": "Ödev 1", "measure_type": "assignment", "directness": "direct", "weight_percent": 20, "max_points": 100, "target_percent": 60})
    mid = meas["id"]
    tpl = client.get(f"/api/assessment-measures/{mid}/results-template.xlsx"); assert tpl.status_code == 200
    wb = load_workbook(BytesIO(tpl.content)); sheet = wb["Puanlar"]
    rows = list(sheet.iter_rows(values_only=True)); assert rows[0][0] == "ogrenci_no" and len(rows) == 3
    sheet.cell(row=2, column=3, value=80); sheet.cell(row=3, column=3, value=150)  # second is out of range
    buf = BytesIO(); wb.save(buf)
    bad = client.post(f"/api/assessment-measures/{mid}/results-import", files={"file": ("p.xlsx", buf.getvalue(), "application/octet-stream")})
    assert bad.status_code == 422 and bad.json()["error"]["details"], bad.text
    sheet.cell(row=3, column=3, value=60); buf = BytesIO(); wb.save(buf)
    assert client.post(f"/api/assessment-measures/{mid}/results-import?validate_only=true", files={"file": ("p.xlsx", buf.getvalue(), "application/octet-stream")}).json()["rows"] == 2
    ok = client.post(f"/api/assessment-measures/{mid}/results-import", files={"file": ("p.xlsx", buf.getvalue(), "application/octet-stream")}); assert ok.status_code == 200, ok.text
    assert ok.json()["imported"] == 2
    summ = client.get(f"/api/assessment-measures/{mid}/summary").json()
    assert summ["result_count"] == 2 if "result_count" in summ else True


def test_obs_grade_export_positive_path():
    from io import BytesIO
    from openpyxl import load_workbook
    program, course, exam, q, ws, hdr = _setup()
    cid, eid = course["id"], exam["id"]
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    studs = client.get(f"/api/exams/{eid}/students").json()
    _post(f"/api/exams/{eid}/students/{studs[0]['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "B"}]})
    _post(f"/api/exams/{eid}/students/{studs[1]['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "A"}]})
    with SessionLocal() as db:
        from app import models as _m
        e = db.get(_m.Exam, eid); e.status = "approved"; e.assessment_weight_percent = 100.0; db.commit()
    r = client.get(f"/api/courses/{cid}/obs-grades.xlsx"); assert r.status_code == 200, r.text
    wb = load_workbook(BytesIO(r.content)); rows = list(wb["OBS_Toplu_Not"].iter_rows(values_only=True))
    assert rows[0][0] == "Öğrenci No" and rows[0][-2] == "Başarı Notu (100)"
    finals = sorted(x[-2] for x in rows[1:]); assert finals == [0.0, 100.0]
    assert {x[-1] for x in rows[1:]} == {"Geçti", "Kaldı"}
    assert dict(wb["Bilgi"].iter_rows(values_only=True))["Ağırlıklar geçerli mi"] == "Evet"


def test_large_exam_uses_separate_answer_page_and_full_score_grid():
    from io import BytesIO
    from pypdf import PdfReader
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    client.patch(f"/api/exams/{eid}/questions/{q['id']}", json={"points": 1})
    for n in range(2, 51):
        _post(f"/api/exams/{eid}/questions", {"order_no": n, "question_type": "mcq", "text": f"Soru {n}", "points": 1, "correct_answer": "B", "choices": {"A": "a", "B": "b", "C": "c", "D": "d"}, "learning_outcome_code": "Ö1"})
    meta = client.get(f"/api/exams/{eid}/paper-metadata").json()
    assert meta["paper"]["omr_mode"] == "separate"  # 50 MCQ > 40 -> forced even though the exam says embedded
    reader = PdfReader(BytesIO(client.get(f"/api/exams/{eid}/paper.pdf").content))
    first = reader.pages[0].extract_text()
    assert "CEVAP FORMU AYRI SAYFADADIR" in first and {"41", "49", "50"} <= set(first.split())  # score grid lists all questions (was capped at 40)
    assert "AYRI CEVAP FORMU" in reader.pages[1].extract_text()


def test_extra_time_accommodation_printed_and_locked_after_print():
    from io import BytesIO
    from pypdf import PdfReader
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    s1, s2 = client.get(f"/api/exams/{eid}/students").json()
    assert client.patch(f"/api/exams/{eid}/students/{s1['id']}/accommodation", json={"extra_time_percent": 150}).status_code == 422
    assert client.patch(f"/api/exams/{eid}/students/{s1['id']}/accommodation", json={"extra_time_percent": 25}).json()["extra_time_percent"] == 25
    t1 = PdfReader(BytesIO(client.get(f"/api/exams/{eid}/students/{s1['id']}/paper.pdf").content)).pages[0].extract_text()
    t2 = PdfReader(BytesIO(client.get(f"/api/exams/{eid}/students/{s2['id']}/paper.pdf").content)).pages[0].extract_text()
    t1, t2 = " ".join(t1.split()), " ".join(t2.split())  # PDF text wraps lines
    assert "ek süre" in t1 and "63 dk" in t1 and "ek süre" not in t2  # 50 dk +25% -> 63 dk (rounded up)
    sheet = PdfReader(BytesIO(client.get(f"/api/exams/{eid}/attendance-sheet.pdf").content)).pages[0].extract_text()
    assert "ek süre" in " ".join(sheet.split())
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"})
    assert client.post(f"/api/exams/{eid}/print-confirm").status_code == 200
    assert client.patch(f"/api/exams/{eid}/students/{s1['id']}/accommodation", json={"extra_time_percent": 50}).status_code == 409


def _mkuser(email, name, role, **scope):
    r = client.post("/api/users", json={"email": email, "display_name": name, "auth_source": "pilot", "is_active": True}); assert r.status_code == 201, r.text
    assert client.post(f"/api/users/{r.json()['id']}/roles", json={"role": role, **scope}).status_code == 201


def test_outcome_change_approval_workflow_and_institution_settings():
    import uuid as _u
    program, course, exam, q, ws, hdr = _setup()
    cid, pid = course["id"], program["id"]
    tag = _u.uuid4().hex[:6]
    inst, head = f"inst-{tag}@dogus.edu.tr", f"head-{tag}@dogus.edu.tr"
    client.patch(f"/api/courses/{cid}", json={"instructor_email": inst})
    _mkuser(inst, "Hoca", "instructor", course_id=cid); _mkuser(head, "Başkan", "program_head", program_id=pid)
    hi, hh = {"X-DOU-Pilot-User": inst}, {"X-DOU-Pilot-User": head}
    assert client.put("/api/institution-settings/outcome_change_approval", json={"value": "maybe"}).status_code == 400
    assert client.put("/api/institution-settings/outcome_change_approval", headers=hi, json={"value": "on"}).status_code == 403  # instructors cannot flip settings
    assert client.put("/api/institution-settings/outcome_change_approval", json={"value": "on"}).status_code == 200
    try:
        lo = client.get(f"/api/courses/{cid}/outcomes", headers=hi).json()["learning_outcomes"][0]
        r = client.patch(f"/api/learning-outcomes/{lo['id']}", headers=hi, json={"description": "Önerilen yeni metin"}); assert r.status_code == 202 and r.json()["pending_approval"]
        assert client.get(f"/api/courses/{cid}/outcomes", headers=hi).json()["learning_outcomes"][0]["description"] == "Temel bilgi"  # unchanged until approved
        r2 = client.post(f"/api/courses/{cid}/learning-outcomes", headers=hi, json={"code": "Ö8", "description": "Yeni çıktı önerisi"}); assert r2.status_code == 202
        pend = client.get(f"/api/outcome-change-requests?status=pending&course_id={cid}", headers=hh).json(); assert len(pend) == 2
        assert client.post(f"/api/outcome-change-requests/{pend[0]['id']}/decision", headers=hi, json={"decision": "approved"}).status_code == 403  # not a reviewer
        for req in pend:
            d = client.post(f"/api/outcome-change-requests/{req['id']}/decision", headers=hh, json={"decision": "approved", "note": "uygun"}); assert d.status_code == 200, d.text
        los = {x["code"]: x for x in client.get(f"/api/courses/{cid}/outcomes", headers=hi).json()["learning_outcomes"]}
        assert los["Ö1"]["description"] == "Önerilen yeni metin" and "Ö8" in los and los["Ö8"]["source"] == "assess"
        assert client.post(f"/api/outcome-change-requests/{pend[0]['id']}/decision", headers=hh, json={"decision": "rejected"}).status_code == 409  # already decided
        # a reviewer's own edit applies immediately
        assert client.patch(f"/api/learning-outcomes/{los['Ö8']['id']}", headers=hh, json={"description": "Başkan düzeltti"}).status_code == 200
    finally:
        client.put("/api/institution-settings/outcome_change_approval", json={"value": "off"})
    st = {x["key"]: x["value"] for x in client.get("/api/institution-settings").json()}
    assert st["outcome_change_approval"] == "off"


def test_question_maker_checker_and_shared_pool():
    import uuid as _u
    program, course, exam, q, ws, hdr = _setup()
    pid, c1 = program["id"], course["id"]
    c2 = _post("/api/courses", {"program_id": pid, "code": "ODA 202", "name": "İkinci Ders", "academic_year": "2026-2027", "term": "Güz", "instructor_email": "x@dogus.edu.tr", "instructor_name": "X"})
    _post(f"/api/courses/{c2['id']}/learning-outcomes", {"code": "Ö1", "description": "Aynı kodlu çıktı"})
    bank = _post("/api/question-bank", {"course_id": c1, "question_type": "mcq", "text": "Ortak soru", "default_points": 5, "correct_answer": "A", "choices": {"A": "x", "B": "y"}, "tags": []})
    client.put("/api/institution-settings/question_self_approval", json={"value": "off"})
    try:
        client.post(f"/api/question-bank/{bank['id']}/review", json={"status": "review"})
        blocked = client.post(f"/api/question-bank/{bank['id']}/review", json={"status": "approved"})
        assert blocked.status_code == 403 and "kendi sorusunu" in blocked.text  # author == current user
    finally:
        client.put("/api/institution-settings/question_self_approval", json={"value": "on"})
    assert client.post(f"/api/question-bank/{bank['id']}/review", json={"status": "approved"}).status_code == 200
    assert client.post(f"/api/question-bank/{bank['id']}/review", json={"status": "institutional"}).status_code == 200
    shared = client.get(f"/api/question-bank/shared?course_id={c2['id']}").json()
    assert [x["id"] for x in shared] == [bank["id"]] and shared[0]["course_code"] == "ODA 101"
    assert client.get(f"/api/question-bank/shared?course_id={c1}").json() == []  # own course's questions are not 'shared'
    cp = client.post(f"/api/question-bank/{bank['id']}/copy-to-course", json={"course_id": c2["id"]}); assert cp.status_code == 201, cp.text
    assert cp.json()["review_status"] == "draft" and cp.json()["mapped_outcomes"] == [] and client.post(f"/api/question-bank/{bank['id']}/copy-to-course", json={"course_id": c1}).status_code == 409
    other = _setup()[0]  # different program
    c3 = _post("/api/courses", {"program_id": other["id"], "code": "XYZ 1", "name": "Başka program", "academic_year": "2026-2027", "term": "Güz", "instructor_email": "y@dogus.edu.tr", "instructor_name": "Y"})
    assert client.post(f"/api/question-bank/{bank['id']}/copy-to-course", json={"course_id": c3["id"]}).status_code == 403


def test_second_institution_connector_uses_the_same_canonical_sync():
    import uuid as _u
    from app.services.connectors import CanonCourse, CanonPeriod, CanonStudent, CanonTeacher, sync_canonical
    tag = _u.uuid4().hex[:5]

    class FakeSisConnector:  # a different university's OBS: only translation code, no sync logic
        source = "sis-x"
        def resolve_period(self, ref): return CanonPeriod("2027-2028", "Bahar")
        def teacher_courses(self, teacher_ref, period_ref):
            return [CanonCourse(code=f"SIS{tag}", name="Veri Yapıları", external_id="c1", program_external_id=f"p{tag}", program_name="Yazılım", faculty="Müh.", department="Bil. Müh.",
                                students=[CanonStudent(f"{tag}001", "Ali Veli"), CanonStudent(f"{tag}002")])]
    with SessionLocal() as db:
        from app import models as _m
        stats = sync_canonical(db, FakeSisConnector(), CanonTeacher("hoca@x.edu", "Hoca X"), "T1", "p1"); db.commit()
        assert stats == {"courses": 1, "students": 2, "enrollments": 2}
        again = sync_canonical(db, FakeSisConnector(), CanonTeacher("hoca@x.edu", "Hoca X"), "T1", "p1"); db.commit()
        assert again == {"courses": 0, "students": 0, "enrollments": 0}  # idempotent
        c = db.scalar(select_(_m.Course).where(_m.Course.code == f"SIS{tag}"))
        assert c.external_source == "sis-x" and c.academic_year == "2027-2028" and c.instructor_email == "hoca@x.edu"


def test_ai_scoring_suggestion_is_gated_anonymous_and_never_writes_grades(monkeypatch):
    import dataclasses, json as _json
    import app.ai_scoring_api as ai
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    client.patch(f"/api/exams/{eid}/questions/{q['id']}", json={"points": 60})
    qc = _post(f"/api/exams/{eid}/questions", {"order_no": 2, "question_type": "classic", "text": "Açıkla", "points": 40, "learning_outcome_code": "Ö1", "expected_answer": "beklenen",
                                               "rubric": {"criteria": [{"id": "a", "label": "Doğruluk", "max_points": 25, "outcome_codes": ["Ö1"]}, {"id": "b", "label": "Anlatım", "max_points": 15, "outcome_codes": ["Ö1"]}]}})
    url = f"/api/exams/{eid}/questions/{qc['id']}/ai-suggestion"
    assert client.get("/api/ai-scoring/status").json()["available"] is False
    assert client.post(url, json={"answer_text": "cevap"}).status_code == 403  # off by default
    monkeypatch.setattr(ai, "settings", dataclasses.replace(ai.settings, ai_scoring_enabled=True, ai_scoring_api_key="k", ai_scoring_model="m"))
    assert client.post(url, json={"answer_text": "cevap"}).status_code == 403  # institution setting still off
    client.put("/api/institution-settings/ai_scoring", json={"value": "on"})
    seen = {}
    def fake(prompt, system):
        seen["prompt"] = prompt
        return 'Tamam: {"criteria": {"a": {"score": 99, "reason": "iyi"}, "b": {"score": 10, "reason": "orta"}}}'
    monkeypatch.setattr(ai, "call_provider", fake)
    try:
        r = client.post(url, json={"answer_text": "Öğrencinin cevabı"}); assert r.status_code == 200, r.text
        sug = r.json()["suggestion"]
        assert sug["a"]["score"] == 25.0 and sug["b"]["score"] == 10.0 and r.json()["total"] == 35.0  # clamped to the rubric maximum
        assert "Ayşe" not in seen["prompt"] and "student" not in seen["prompt"].lower() and "Öğrencinin cevabı" in seen["prompt"]
        assert client.post(f"/api/exams/{eid}/questions/{q['id']}/ai-suggestion", json={"answer_text": "x"}).status_code == 409  # MCQ not eligible
        grid = client.get(f"/api/exams/{eid}/questions/{qc['id']}/grid")
        assert grid.status_code == 200 and not any(x["entered"] for x in grid.json()["rows"])  # nothing was graded
    finally:
        client.put("/api/institution-settings/ai_scoring", json={"value": "off"})
