from sqlalchemy import select
from tests.test_674_evaluator_room import client, _setup, _post  # noqa
from app.db import SessionLocal
from app import models as m
from app.services.operations import generate_due_notifications


def test_below_target_outcome_creates_deduplicated_instructor_notification():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    assert client.post(f"/api/exams/{eid}/status", json={"status": "ready"}).status_code == 200
    assert client.post(f"/api/exams/{eid}/status", json={"status": "grading"}).status_code == 200
    for es in client.get(f"/api/exams/{eid}/students").json():
        _post(f"/api/exams/{eid}/students/{es['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "A"}]})
    r = client.post(f"/api/exams/{eid}/status", json={"status": "approved"})
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        first = generate_due_notifications(db); db.commit()
        rows = db.scalars(select(m.OperationalNotification).where(m.OperationalNotification.notification_type == "below_target", m.OperationalNotification.source_entity_id == eid)).all()
        assert len(rows) == 1 and "Hedef altı" in rows[0].title and "%0" in rows[0].body
        assert rows[0].user_email == "hoca@dogus.edu.tr"
        generate_due_notifications(db); db.commit()
        assert len(db.scalars(select(m.OperationalNotification).where(m.OperationalNotification.notification_type == "below_target", m.OperationalNotification.source_entity_id == eid)).all()) == 1
