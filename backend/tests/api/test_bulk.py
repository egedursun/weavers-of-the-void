from tests.api.conftest import ApiWorld


async def test_batch_deepening_status_and_controls(api: ApiWorld) -> None:
    status = (await api.http.get("/api/batch-deepen")).json()
    assert status["state"]["running"] is False
    assert (await api.http.post("/api/batch-deepen/start")).status_code == 409
    assert (await api.http.post("/api/batch-deepen/stop")).status_code == 409
    assert (await api.http.post("/api/names/assign-missing")).status_code == 409
