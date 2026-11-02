import httpx
import pytest

from aerona.imaging.client import ImageWorkerClient
from aerona.imaging.contract import ImageJobRequest, ImageJobStatus, ImagePriority, ImageProgress, ImageStage
from aerona.imaging.errors import (
    ImageGenerationDisabledError,
    ImageJobCancelledError,
    ImageJobConflictError,
    ImageJobFailedError,
    ImageJobNotFoundError,
    ImageJobRejectedError,
    ImageWorkerProtocolError,
    ImageWorkerUnavailableError,
)
from tests.imaging.fake_worker import FAKE_PNG, WORKER_URL, FakeWorker, progress_event, successful_events

REQUEST = ImageJobRequest(prompt="a lantern in the fog", width=720, height=720, steps=2, seed=11, priority=ImagePriority.MANUAL)


def client_for(worker: FakeWorker) -> ImageWorkerClient:
    return ImageWorkerClient(WORKER_URL, transport=worker.transport())


async def test_generate_enqueues_streams_progress_and_fetches_the_png() -> None:
    worker = FakeWorker()
    seen: list[ImageProgress] = []

    async def record(event: ImageProgress) -> None:
        seen.append(event)

    async with client_for(worker) as client:
        image = await client.generate(REQUEST, record)
    assert image.png == FAKE_PNG
    assert (image.job_id, image.width, image.height, image.steps, image.seed) == ("job-1", 720, 720, 2, 11)
    assert [event.kind for event in seen] == [
        ImageStage.QUEUED,
        ImageStage.LOADING,
        ImageStage.ENCODING,
        ImageStage.STEP,
        ImageStage.STEP,
        ImageStage.DECODING,
        ImageStage.DONE,
    ]
    assert worker.bodies == [{"prompt": "a lantern in the fog", "width": 720, "height": 720, "steps": 2, "seed": 11, "priority": "manual"}]


async def test_overrides_are_sent_only_when_set() -> None:
    worker = FakeWorker()
    async with client_for(worker) as client:
        await client.enqueue(REQUEST.model_copy(update={"image_timeout_seconds": 120.0, "idle_unload_seconds": 0.0}))
    assert worker.bodies[0]["image_timeout_seconds"] == 120.0
    assert worker.bodies[0]["idle_unload_seconds"] == 0.0
    assert "load_timeout_seconds" not in worker.bodies[0]


async def test_dropped_stream_resumes_from_the_last_event_id() -> None:
    worker = FakeWorker(drop_stream_after=3)
    async with client_for(worker) as client:
        final = await client.follow("job-1")
    resumed = [request.headers.get("last-event-id") for request in worker.requests if request.url.path.endswith("/events")]
    assert final.kind is ImageStage.DONE
    assert resumed == [None, "3"]


async def test_failed_and_cancelled_jobs_raise_domain_errors() -> None:
    failed = FakeWorker(events=[progress_event("job-1", 1, "queued"), progress_event("job-1", 2, "error", message="image did not finish within 300s")])
    async with client_for(failed) as client:
        with pytest.raises(ImageJobFailedError, match="did not finish"):
            await client.generate(REQUEST)
    cancelled = FakeWorker(events=[progress_event("job-1", 1, "queued"), progress_event("job-1", 2, "cancelled")])
    async with client_for(cancelled) as client:
        with pytest.raises(ImageJobCancelledError):
            await client.generate(REQUEST)


async def test_status_health_and_cancel_map_worker_responses() -> None:
    async with client_for(FakeWorker()) as client:
        health = await client.health()
        state = await client.status("job-1")
        with pytest.raises(ImageJobConflictError, match="can no longer be cancelled"):
            await client.cancel("job-1")
        with pytest.raises(ImageJobNotFoundError, match="does not exist"):
            await client.status("missing")
    assert health.model_id == "aerona/fake-gradient"
    assert state.status is ImageJobStatus.DONE
    assert state.last_event is not None
    assert state.last_event.terminal


async def test_rejected_request_and_bad_payloads_are_reported() -> None:
    async with client_for(FakeWorker(enqueue_status=422)) as client:
        with pytest.raises(ImageJobRejectedError, match="invalid width"):
            await client.enqueue(REQUEST)
    async with client_for(FakeWorker(image=b"not a png")) as client:
        with pytest.raises(ImageWorkerProtocolError):
            await client.fetch_image("job-1")
    broken = httpx.MockTransport(lambda _request: httpx.Response(200, text="not json"))
    async with ImageWorkerClient(WORKER_URL, transport=broken) as client:
        with pytest.raises(ImageWorkerProtocolError):
            await client.health()


async def test_unreachable_or_failing_worker_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with ImageWorkerClient(WORKER_URL, transport=httpx.MockTransport(refuse)) as client:
        with pytest.raises(ImageWorkerUnavailableError):
            await client.health()
        with pytest.raises(ImageWorkerUnavailableError):
            await client.follow("job-1")
    crashing = httpx.MockTransport(lambda _request: httpx.Response(500, text="boom"))
    async with ImageWorkerClient(WORKER_URL, transport=crashing) as client:
        with pytest.raises(ImageWorkerUnavailableError, match="500"):
            await client.health()


async def test_stream_without_a_final_event_is_a_protocol_error() -> None:
    worker = FakeWorker(events=successful_events("job-1")[:2])
    async with client_for(worker) as client:
        with pytest.raises(ImageWorkerProtocolError, match="without a final event"):
            await client.follow("job-1")


async def test_empty_url_disables_image_generation() -> None:
    async with ImageWorkerClient("") as client:
        assert client.enabled is False
        with pytest.raises(ImageGenerationDisabledError) as raised:
            await client.health()
    assert raised.value.status_code == 503
