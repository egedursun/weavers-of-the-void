import io

from PIL import Image

from tests.conftest import ClientFactory, eventually, job_body, read_events


async def test_health_reports_backend_model_and_queue(worker_client: ClientFactory) -> None:
    async with worker_client() as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["backend"] == "fake"
    assert body["model_id"] == "aerona/fake-gradient"
    assert body["loaded"] is False
    assert body["queue_length"] == 0
    assert body["running_job_id"] is None


async def test_progress_stream_follows_the_stage_sequence(worker_client: ClientFactory) -> None:
    async with worker_client() as client:
        job_id = (await client.post("/jobs", json=job_body(steps=3))).json()["job_id"]
        first = await read_events(client, job_id)
        second_id = (await client.post("/jobs", json=job_body(steps=2))).json()["job_id"]
        second = await read_events(client, second_id)
    assert [(event["kind"], event["step"]) for event in first] == [
        ("queued", 0),
        ("loading", 0),
        ("encoding", 0),
        ("step", 1),
        ("step", 2),
        ("step", 3),
        ("decoding", 3),
        ("done", 3),
    ]
    assert [event["percent"] for event in first] == [0, 0, 0, 40, 60, 80, 80, 100]
    assert [event["sequence"] for event in first] == list(range(1, 9))
    assert [event["kind"] for event in second] == ["queued", "encoding", "step", "step", "decoding", "done"]


async def test_last_event_id_resumes_the_stream(worker_client: ClientFactory) -> None:
    async with worker_client() as client:
        job_id = (await client.post("/jobs", json=job_body(steps=1))).json()["job_id"]
        await read_events(client, job_id)
        resumed = await read_events(client, job_id, last_event_id=4)
    assert [event["kind"] for event in resumed] == ["decoding", "done"]


async def test_finished_job_serves_a_deterministic_png(worker_client: ClientFactory) -> None:
    async with worker_client() as client:
        images = []
        for _ in range(2):
            job_id = (await client.post("/jobs", json=job_body(width=320, height=272, seed=99))).json()["job_id"]
            await read_events(client, job_id)
            response = await client.get(f"/jobs/{job_id}/image")
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            images.append(response.content)
        status = (await client.get(f"/jobs/{job_id}")).json()
    assert images[0] == images[1]
    assert Image.open(io.BytesIO(images[0])).size == (320, 272)
    assert status["status"] == "done"
    assert status["last_event"]["kind"] == "done"


async def test_queued_job_can_be_cancelled_but_a_running_one_cannot(worker_client: ClientFactory) -> None:
    async with worker_client(fake_step_seconds=0.05) as client:
        running = (await client.post("/jobs", json=job_body(steps=6))).json()["job_id"]
        queued = (await client.post("/jobs", json=job_body(priority="bulk"))).json()
        assert queued["position"] == 1

        async def is_running() -> bool:
            return bool((await client.get("/health")).json()["running_job_id"] == running)

        await eventually(is_running)
        assert (await client.delete(f"/jobs/{queued['job_id']}")).status_code == 204
        assert (await client.delete(f"/jobs/{running}")).status_code == 409
        cancelled = await read_events(client, queued["job_id"])
        image = await client.get(f"/jobs/{queued['job_id']}/image")
        finished = await read_events(client, running)
        status = (await client.get(f"/jobs/{queued['job_id']}")).json()
    assert [event["kind"] for event in cancelled] == ["queued", "cancelled"]
    assert image.status_code == 409
    assert finished[-1]["kind"] == "done"
    assert status["status"] == "cancelled"


async def test_unknown_job_and_invalid_request_are_rejected(worker_client: ClientFactory) -> None:
    async with worker_client() as client:
        assert (await client.get("/jobs/missing")).status_code == 404
        assert (await client.get("/jobs/missing/events")).status_code == 404
        assert (await client.delete("/jobs/missing")).status_code == 404
        assert (await client.post("/jobs", json=job_body(width=10))).status_code == 422
        assert (await client.post("/jobs", json=job_body(steps=0))).status_code == 422
        assert (await client.post("/jobs", json=job_body(priority="urgent"))).status_code == 422
        assert (await client.post("/jobs", json=job_body(unknown=True))).status_code == 422
