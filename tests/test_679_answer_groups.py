from tests.test_674_evaluator_room import client, _setup, _post  # noqa


def test_answer_groups_cluster_and_apply_same_rubric_score():
    program, course, exam, q, ws, hdr = _setup()
    eid = exam["id"]
    client.patch(f"/api/exams/{eid}/questions/{q['id']}", json={"points": 60})
    qc = _post(f"/api/exams/{eid}/questions", {"order_no": 2, "question_type": "classic", "text": "Veri tabanı nedir?", "points": 40, "learning_outcome_code": "Ö1",
               "expected_answer": "Verilerin düzenli saklandığı sistem", "rubric": {"criteria": [{"id": "a", "label": "Doğruluk", "max_points": 40, "outcome_codes": ["Ö1"]}]}})
    client.post(f"/api/exams/{eid}/status", json={"status": "ready"}); client.post(f"/api/exams/{eid}/status", json={"status": "grading"})
    studs = client.get(f"/api/exams/{eid}/students").json()
    texts = ["Veri tabanı verilerin düzenli saklandığı sistemdir", "Verilerin düzenli saklandığı sistem veri tabanıdır"]
    for es, t in zip(studs, texts):
        _post(f"/api/exams/{eid}/students/{es['id']}/responses", {"responses": [
            {"question_id": q["id"], "answer_text": "B"},
            {"question_id": qc["id"], "answer_text": t, "rubric_scores": {"a": 10}}]})
    g = client.get(f"/api/exams/{eid}/questions/{qc['id']}/answer-groups").json()
    assert g["total"] == 2 and g["group_count"] == 1 and g["groups"][0]["size"] == 2
    ids = [x["response_id"] for x in g["groups"][0]["members"]]
    bad = client.post(f"/api/exams/{eid}/questions/{qc['id']}/answer-groups/apply", json={"response_ids": ids, "rubric_scores": {"a": 99}})
    assert bad.status_code == 400
    ok = client.post(f"/api/exams/{eid}/questions/{qc['id']}/answer-groups/apply", json={"response_ids": ids, "rubric_scores": {"a": 35}})
    assert ok.status_code == 200 and ok.json() == {"applied": 2, "awarded_points": 35.0}
    g2 = client.get(f"/api/exams/{eid}/questions/{qc['id']}/answer-groups").json()
    assert {x["awarded_points"] for x in g2["groups"][0]["members"]} == {35.0}
    # MCQ soru gruplanmaz; başka sınavın cevabı uygulanamaz
    assert client.get(f"/api/exams/{eid}/questions/{q['id']}/answer-groups").status_code == 404
    assert client.post(f"/api/exams/{eid}/questions/{qc['id']}/answer-groups/apply", json={"response_ids": [999999], "rubric_scores": {"a": 5}}).status_code == 400
    # puanlar kilitlenince uygulanamaz
    client.post(f"/api/exams/{eid}/grade-lock", json={"note": "ok"})
    assert client.post(f"/api/exams/{eid}/questions/{qc['id']}/answer-groups/apply", json={"response_ids": ids, "rubric_scores": {"a": 1}}).status_code == 409
