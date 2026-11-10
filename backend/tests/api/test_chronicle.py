from tests.api.conftest import ApiWorld


async def test_chronicle_pages_and_threads(api: ApiWorld) -> None:
    opened = await api.http.post("/api/threads", json={"text": "Who poisoned the wells?"})
    assert opened.status_code == 200, opened.text
    threads = (await api.http.get("/api/threads")).json()
    assert threads[0]["text"] == "Who poisoned the wells?"
    closed = await api.http.post(f"/api/threads/{threads[0]['id']}/close", json={"how": "The wells ran clean again."})
    assert closed.status_code == 200, closed.text
    page = (await api.http.get("/api/chronicle")).json()
    assert page["total"] >= len(page["items"])
    if page["items"]:
        older = await api.http.get("/api/chronicle", params={"before": page["items"][0]["id"], "limit": 5})
        assert older.status_code == 200
    assert (await api.http.get("/api/chronicle/epochs")).status_code == 200
    assert (await api.http.get("/api/chronicle/perspectives", params={"epoch": 1})).status_code == 200
    assert (await api.http.get("/api/chronicle/cosmic", params={"last": 0})).status_code == 400
    assert (await api.http.post("/api/threads/999999/close", json={"how": "never"})).status_code == 404
