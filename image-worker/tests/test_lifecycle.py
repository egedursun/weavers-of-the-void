import asyncio

from httpx import AsyncClient

from tests.conftest import ClientFactory, eventually, job_body, read_events


async def wait_until_unloaded(client: AsyncClient) -> None:
    async def unloaded() -> bool:
        return (await client.get("/health")).json()["loaded"] is False

    await eventually(unloaded)


async def test_model_loads_lazily_and_is_released_after_the_idle_timeout(worker_client: ClientFactory) -> None:
    async with worker_client(idle_unload_seconds=0.05) as client:
        assert (await client.get("/health")).json()["loaded"] is False
        job_id = (await client.post("/jobs", json=job_body())).json()["job_id"]
        await read_events(client, job_id)
        assert (await client.get("/health")).json()["loaded"] is True
        await wait_until_unloaded(client)
        again = (await client.post("/jobs", json=job_body())).json()["job_id"]
        events = await read_events(client, again)
    assert "loading" in [event["kind"] for event in events]


async def test_zero_idle_timeout_keeps_the_model_loaded(worker_client: ClientFactory) -> None:
    async with worker_client(idle_unload_seconds=0.0) as client:
        await read_events(client, (await client.post("/jobs", json=job_body())).json()["job_id"])
        await asyncio.sleep(0.05)
        assert (await client.get("/health")).json()["loaded"] is True


async def test_request_can_override_the_idle_timeout(worker_client: ClientFactory) -> None:
    async with worker_client(idle_unload_seconds=0.0) as client:
        await read_events(client, (await client.post("/jobs", json=job_body(idle_unload_seconds=0.05))).json()["job_id"])
        assert (await client.get("/health")).json()["idle_unload_seconds"] == 0.05
        await wait_until_unloaded(client)


async def test_new_job_cancels_a_pending_idle_release(worker_client: ClientFactory) -> None:
    async with worker_client(idle_unload_seconds=0.2, fake_step_seconds=0.05) as client:
        await read_events(client, (await client.post("/jobs", json=job_body(steps=1))).json()["job_id"])
        events = await read_events(client, (await client.post("/jobs", json=job_body(steps=6))).json()["job_id"])
    assert "loading" not in [event["kind"] for event in events]


async def test_image_timeout_fails_the_job_and_restarts_the_worker(worker_client: ClientFactory) -> None:
    async with worker_client(fake_step_seconds=0.2) as client:
        slow = (await client.post("/jobs", json=job_body(steps=5, image_timeout_seconds=0.1))).json()["job_id"]
        events = await read_events(client, slow)
        health = (await client.get("/health")).json()
        status = (await client.get(f"/jobs/{slow}")).json()
        retry = await read_events(client, (await client.post("/jobs", json=job_body(steps=1))).json()["job_id"])
    assert events[-1]["kind"] == "error"
    assert "restarted" in events[-1]["message"]
    assert status["status"] == "error"
    assert health["loaded"] is False
    assert [event["kind"] for event in retry][:2] == ["queued", "loading"]
    assert retry[-1]["kind"] == "done"


async def test_load_timeout_fails_the_job(worker_client: ClientFactory) -> None:
    async with worker_client(fake_load_seconds=0.3) as client:
        events = await read_events(client, (await client.post("/jobs", json=job_body(load_timeout_seconds=0.05))).json()["job_id"])
        health = (await client.get("/health")).json()
    assert [event["kind"] for event in events] == ["queued", "loading", "error"]
    assert "did not load" in events[-1]["message"]
    assert health["loaded"] is False


async def test_backend_failure_fails_only_that_job(worker_client: ClientFactory) -> None:
    async with worker_client(fake_failure_prompt="forbidden") as client:
        failed = await read_events(client, (await client.post("/jobs", json=job_body(prompt="a forbidden gate"))).json()["job_id"])
        succeeded = await read_events(client, (await client.post("/jobs", json=job_body())).json()["job_id"])
        health = (await client.get("/health")).json()
    assert failed[-1]["kind"] == "error"
    assert "refused" in failed[-1]["message"]
    assert succeeded[-1]["kind"] == "done"
    assert health["loaded"] is True
