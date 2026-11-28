from tests.test_674_evaluator_room import client, _setup, _post  # noqa


def _ids(course):
    d = client.get(f"/api/courses/{course['id']}/outcomes").json()
    return d["learning_outcomes"], d["program_outcomes"]


def test_bulk_matrix_update_and_remove_all_or_nothing():
    program, course, exam, q, ws, hdr = _setup()
    los, pos = _ids(course)
    lo, po = los[0]["id"], pos[0]["id"]
    r = client.put("/api/outcome-mappings/bulk", json={"items": [{"learning_outcome_id": lo, "program_outcome_id": po, "contribution": 2}]})
    assert r.status_code == 200 and r.json()["updated"] == 1 and r.json()["created"] == 0
    r = client.put("/api/outcome-mappings/bulk", json={"items": [{"learning_outcome_id": lo, "program_outcome_id": po, "contribution": None}]})
    assert r.json()["removed"] == 1
    r = client.put("/api/outcome-mappings/bulk", json={"items": [{"learning_outcome_id": lo, "program_outcome_id": po, "contribution": 4}]})
    assert r.json()["created"] == 1
    # geçersiz hücre -> hiçbiri uygulanmaz
    bad = client.put("/api/outcome-mappings/bulk", json={"items": [
        {"learning_outcome_id": lo, "program_outcome_id": po, "contribution": 1},
        {"learning_outcome_id": lo, "program_outcome_id": 999999, "contribution": 3}]})
    assert bad.status_code == 400
    m_ = client.get(f"/api/courses/{course['id']}/outcomes").json()
    assert [x["contribution"] for x in m_["mappings"] if x["learning_outcome_id"] == lo and x["program_outcome_id"] == po] == [4]
    assert client.put("/api/outcome-mappings/bulk", json={"items": []}).status_code == 422
    assert client.put("/api/outcome-mappings/bulk", json={"items": [{"learning_outcome_id": lo, "program_outcome_id": po, "contribution": 9}]}).status_code == 422
