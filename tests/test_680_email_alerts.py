import smtplib
from sqlalchemy import select
from tests.test_674_evaluator_room import client, _setup, _post  # noqa
from app.db import SessionLocal
from app import models as m
from app.services import mailer
from app.services.operations import generate_due_notifications


def _approved_low_exam():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    for es in client.get(f"/api/exams/{eid}/students").json():
        _post(f"/api/exams/{eid}/students/{es['id']}/responses", {"responses": [{"question_id": q["id"], "answer_text": "A"}]})
    assert client.post(f"/api/exams/{eid}/status", json={"status": "approved"}).status_code == 200
    return eid


def test_mailer_disabled_by_default_and_never_raises(monkeypatch):
    assert mailer.send_mail("a@b.co", "x", "y") is False  # kapalı
    from types import SimpleNamespace
    monkeypatch.setattr(mailer, "settings", SimpleNamespace(email_notifications_enabled=True, smtp_host="smtp.invalid", smtp_port=587,
                                                            smtp_user="", smtp_password="", smtp_from="dou@dogus.edu.tr", smtp_starttls=False))

    class Boom:
        def __init__(self, *a, **k): raise OSError("ağ yok")
    monkeypatch.setattr(smtplib, "SMTP", Boom)
    assert mailer.send_mail("a@b.co", "x", "y") is False  # hata yutulur
    assert mailer.send_mail("geçersiz", "x", "y") is False


def test_below_target_sends_email_once(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send_mail", lambda to, subject, body: sent.append((to, subject)) or True)
    eid = _approved_low_exam()
    with SessionLocal() as db:
        generate_due_notifications(db); db.commit()
        generate_due_notifications(db); db.commit()
    mine = [x for x in sent if x[0] == "hoca@dogus.edu.tr" and "Hedef altı" in x[1]]
    assert len(mine) >= 1
    with SessionLocal() as db:
        rows = db.scalars(select(m.OperationalNotification).where(m.OperationalNotification.source_entity_id == eid, m.OperationalNotification.notification_type == "below_target")).all()
        assert len(rows) == 1
