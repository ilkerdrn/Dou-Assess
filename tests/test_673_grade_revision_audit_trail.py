from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app import models as m

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def _post(path, payload):
    r = client.post(path, json=payload)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def _setup_graded_exam(tag):
    program = _post("/api/programs", {"code": f"GRA673{tag}", "name": "Grade Audit Program", "faculty": "MYO", "department": "BT"})
    course = _post("/api/courses", {
        "program_id": program["id"], "code": f"GRA673C{tag}", "name": "Grade Audit Course",
        "academic_year": "2026-2027", "term": "Güz", "instructor_email": f"hoca673{tag}@dogus.edu.tr", "instructor_name": "Hoca 673",
    })
    student = _post("/api/students", {"program_id": program["id"], "student_no": f"673{tag}001", "full_name": "Öğrenci 673", "class_name": "2. Sınıf"})
    _post(f"/api/courses/{course['id']}/enrollments/bulk", {"student_ids": [student["id"]]})
    lo = _post(f"/api/courses/{course['id']}/learning-outcomes", {"code": f"Ö673{tag}", "description": "Audit trail outcome", "target_percent": 70})
    exam = _post("/api/exams", {
        "course_id": course["id"], "title": "Final 673", "exam_type": "Final",
        "exam_date": "2026-06-10", "duration_minutes": 50, "location": "Derslik 1", "instructions": "Test", "sync_students": True,
    })
    assert exam["student_count"] == 1
    q_mcq = _post(f"/api/exams/{exam['id']}/questions", {
        "order_no": 1, "question_type": "mcq", "text": "2+2?", "points": 40,
        "correct_answer": "4", "choices": {"A": "3", "B": "4"}, "learning_outcome_code": lo["code"],
    })
    q_classic = _post(f"/api/exams/{exam['id']}/questions", {
        "order_no": 2, "question_type": "classic", "text": "Analiz yap", "points": 60,
        "expected_answer": "Analiz adımları açıklanmalıdır.", "bloom_level": "analyze", "learning_outcome_code": lo["code"],
        "rubric": {"criteria": [{"id": "analysis", "label": "Analiz", "max_points": 60, "outcome_codes": [lo["code"]]}]},
    })
    assert client.post(f"/api/exams/{exam['id']}/status", json={"status": "ready"}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={"status": "grading"}).status_code == 200
    students = client.get(f"/api/exams/{exam['id']}/students").json()
    es = students[0]
    return exam, es, q_mcq, q_classic


def test_673_new_grade_is_not_logged_as_a_revision():
    exam, es, q_mcq, q_classic = _setup_graded_exam("A")
    r = client.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", json={"responses": [
        {"question_id": q_mcq["id"], "answer_text": "4"},
        {"question_id": q_classic["id"], "answer_text": "x", "rubric_scores": {"analysis": 60}},
    ]})
    assert r.status_code == 200, r.text
    history = client.get(f"/api/exams/{exam['id']}/students/{es['id']}/grade-history").json()
    assert history == []


def test_673_regrade_is_logged_with_old_and_new_values():
    exam, es, q_mcq, q_classic = _setup_graded_exam("B")
    client.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", json={"responses": [
        {"question_id": q_mcq["id"], "answer_text": "4"},
        {"question_id": q_classic["id"], "answer_text": "x", "rubric_scores": {"analysis": 60}},
    ]})
    # Regrade the classic question down from 60 to 20.
    r = client.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", json={"responses": [
        {"question_id": q_classic["id"], "answer_text": "x (revize)", "rubric_scores": {"analysis": 20}},
    ]})
    assert r.status_code == 200, r.text

    history = client.get(f"/api/exams/{exam['id']}/students/{es['id']}/grade-history").json()
    assert len(history) == 1
    entry = history[0]
    assert entry["question_id"] == q_classic["id"]
    assert entry["previous_awarded_points"] == 60.0
    assert entry["new_awarded_points"] == 20.0
    assert entry["previous_rubric_scores"] == {"analysis": 60.0}
    assert entry["new_rubric_scores"] == {"analysis": 20.0}
    assert entry["source"] == "manual"
    assert entry["changed_by"]
    assert entry["changed_at"]


def test_673_unchanged_resubmission_does_not_add_a_duplicate_entry():
    exam, es, q_mcq, q_classic = _setup_graded_exam("C")
    client.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", json={"responses": [
        {"question_id": q_classic["id"], "answer_text": "x", "rubric_scores": {"analysis": 60}},
    ]})
    client.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", json={"responses": [
        {"question_id": q_classic["id"], "answer_text": "x", "rubric_scores": {"analysis": 10}},
    ]})
    # Resubmitting the exact same (already-current) score should not log a second entry.
    client.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", json={"responses": [
        {"question_id": q_classic["id"], "answer_text": "x", "rubric_scores": {"analysis": 10}},
    ]})
    history = client.get(f"/api/exams/{exam['id']}/students/{es['id']}/grade-history").json()
    assert len(history) == 1
    assert history[0]["previous_awarded_points"] == 60.0
    assert history[0]["new_awarded_points"] == 10.0


def test_673_answer_key_regrade_is_logged():
    exam, es, q_mcq, q_classic = _setup_graded_exam("D")
    client.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses", json={"responses": [
        {"question_id": q_mcq["id"], "answer_text": "4"},
    ]})
    r = client.post(f"/api/exams/{exam['id']}/answer-key/regrade", json={
        "corrections": {str(q_mcq["id"]): "3"}, "reason": "Soru anahtarı hatalıydı",
    })
    assert r.status_code == 200, r.text
    history = client.get(f"/api/exams/{exam['id']}/students/{es['id']}/grade-history").json()
    entry = next(x for x in history if x["question_id"] == q_mcq["id"])
    assert entry["previous_awarded_points"] == 40.0
    assert entry["new_awarded_points"] == 0.0
    assert entry["source"] == "answer_key_regrade"
