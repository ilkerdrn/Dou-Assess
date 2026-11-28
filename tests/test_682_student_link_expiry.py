import re
from datetime import datetime, timedelta, timezone

from tests.test_674_evaluator_room import client, _setup, _post  # noqa
from app.db import SessionLocal
from app import models as m


def _locked_exam():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    for es in client.get(f"/api/exams/{eid}/students").json():
        _post(f"/api/exams/{eid}/students/{es['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "B"}]})
    assert client.post(f"/api/exams/{eid}/grade-lock", json={"note": "ok"}).status_code == 200
    link = client.get(f"/api/exams/{eid}/student-links").json()["links"][0]
    e, s, t = re.match(r"/student\.html\?exam=(\d+)&student=(\d+)#t=(\w+)", link["path"]).groups()
    return eid, f"/api/public/student-exam/{e}/{s}", {"X-DOU-Student-Token": t}


def test_student_link_works_then_expires_after_appeal_plus_view_window():
    eid, url, hdr = _locked_exam()
    assert client.get(url, headers=hdr).status_code == 200
    # 7 gün itiraz + 60 gün görüntüleme penceresi: 30 gün sonra hâlâ açık, 70 gün sonra kapalı
    with SessionLocal() as db:
        ex = db.get(m.Exam, eid); ex.grade_locked_at = datetime.now(timezone.utc) - timedelta(days=30); db.commit()
    assert client.get(url, headers=hdr).status_code == 200
    with SessionLocal() as db:
        ex = db.get(m.Exam, eid); ex.grade_locked_at = datetime.now(timezone.utc) - timedelta(days=70); db.commit()
    r = client.get(url, headers=hdr)
    assert r.status_code == 410 and "süresi doldu" in r.text
