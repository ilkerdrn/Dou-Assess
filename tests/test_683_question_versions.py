from tests.test_674_evaluator_room import client, _setup  # noqa


def test_question_bank_versions_snapshot_compare_and_restore():
    program, course, exam, q, ws, hdr = _setup()
    r = client.post("/api/question-bank", json={"course_id": course["id"], "question_type": "mcq", "text": "2+2?", "default_points": 10,
                    "correct_answer": "B", "choices": {"A": "3", "B": "4"}, "learning_outcome_code": "Ö1"})
    assert r.status_code == 201, r.text
    qid = r.json()["id"]
    assert r.json()["version_no"] == 1
    r2 = client.patch(f"/api/question-bank/{qid}", json={"text": "2+3?", "correct_answer": "A"}); assert r2.status_code == 200, r2.text
    assert r2.json()["version_no"] == 2
    r3 = client.patch(f"/api/question-bank/{qid}", json={"difficulty": "hard"}); assert r3.json()["version_no"] == 3
    v = client.get(f"/api/question-bank/{qid}/versions").json()
    assert [x["version_no"] for x in v["versions"]] == [3, 2, 1] and v["versions"][0]["current"] is True
    assert "difficulty" in v["versions"][0]["changed_fields"]
    assert set(v["versions"][1]["changed_fields"]) >= {"text", "correct_answer"}
    old = client.get(f"/api/question-bank/{qid}/versions/1").json()
    assert old["content"]["text"] == "2+2?" and old["content"]["correct_answer"] == "B" and old["current"] is False
    assert client.get(f"/api/question-bank/{qid}/versions/99").status_code == 404
    assert client.post(f"/api/question-bank/{qid}/versions/3/restore").status_code == 409  # güncel sürüm
    rs = client.post(f"/api/question-bank/{qid}/versions/1/restore"); assert rs.status_code == 200, rs.text
    body = rs.json()
    assert body["version_no"] == 4 and body["text"] == "2+2?" and body["correct_answer"] == "B"
    v2 = client.get(f"/api/question-bank/{qid}/versions").json()
    assert [x["version_no"] for x in v2["versions"]] == [4, 3, 2, 1]  # geçmiş silinmedi
    assert client.get(f"/api/question-bank/{qid}/versions/3").json()["content"]["difficulty"] == "hard"
