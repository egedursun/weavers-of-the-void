from tests.api.conftest import ApiWorld


async def test_jobs_are_listed_and_unknown_jobs_are_404(api: ApiWorld) -> None:
    started = (await api.http.post("/api/epochs/current/complete")).json()
    await api.wait_job(started["job_id"])
    jobs = (await api.http.get("/api/jobs")).json()
    assert started["job_id"] in [job["id"] for job in jobs]
    assert (await api.http.get("/api/jobs/missing")).status_code == 404
    assert (await api.http.post("/api/jobs/missing/cancel")).status_code == 404
