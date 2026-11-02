from aerona.domain.enums.job import JobStatus
from tests.api.conftest import ApiWorld


async def test_engine_only_epoch_runs_as_a_job(api: ApiWorld) -> None:
    started = await api.http.post("/api/epochs/current/complete")
    assert started.status_code == 202
    job = await api.wait_job(started.json()["job_id"])
    assert job["status"] == JobStatus.SUCCEEDED.value, job
    assert (await api.http.get("/api/epochs")).status_code == 200
    assert (await api.http.get("/api/state")).json()["world"]["epoch"] == 2
    stats = (await api.http.get("/api/stats/epochs")).json()
    assert stats
    breakdown = await api.http.get(f"/api/epochs/{stats[0]['epoch']}/breakdown")
    assert breakdown.status_code == 200
    estimate = (await api.http.get("/api/epochs/current/estimate")).json()
    assert estimate["samples"] >= 1


async def test_lore_totals_count_history_beyond_canon(api: ApiWorld) -> None:
    totals = (await api.http.get("/api/stats/lore")).json()
    state = (await api.http.get("/api/state")).json()
    canon = sum(state["counts"].values())
    assert totals["records"] == sum(totals["by_type"].values())
    assert totals["records"] >= canon
    assert totals["bonds"] >= totals["wars"] >= 0


async def test_epoch_errors_map_to_statuses(api: ApiWorld) -> None:
    assert (await api.http.post("/api/epochs/current/stop")).status_code == 409
    assert (await api.http.get("/api/epochs/999/breakdown")).status_code == 404


async def test_epoch_needs_a_world(empty_api: ApiWorld) -> None:
    response = await empty_api.http.post("/api/epochs/current/complete")
    assert response.status_code == 400
    assert (await empty_api.http.get("/api/stats/epochs")).json() == []
    assert (await empty_api.http.get("/api/stats/lore")).json()["records"] == 0
