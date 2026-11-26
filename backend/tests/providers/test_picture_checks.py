from datetime import UTC, datetime

import httpx

from aerona.imaging.client import ImageWorkerClient
from aerona.imaging.contract import GeneratedImage, ImageJobRequest
from aerona.imaging.errors import ImageJobFailedError
from aerona.services.providers.checks import check_drawing, check_worker, picture_model

NOW = datetime(2026, 11, 26, tzinfo=UTC)


class Drawer:
    def __init__(self, refusal: str = "") -> None:
        self.refusal = refusal
        self.asked: list[ImageJobRequest] = []

    @property
    def enabled(self) -> bool:
        return True

    def model_name(self) -> str:
        return "test"

    async def aclose(self) -> None:
        return None

    async def generate(self, job: ImageJobRequest, on_progress: object = None) -> GeneratedImage:
        self.asked.append(job)
        if self.refusal:
            raise ImageJobFailedError(self.refusal)
        return GeneratedImage(job_id="check", png=b"", width=job.width, height=job.height, steps=job.steps, seed=job.seed)


async def test_a_model_that_draws_passes_the_check() -> None:
    drawer = Drawer()
    result = await check_drawing(drawer, NOW)
    assert result.tools_work is True
    assert len(drawer.asked) == 1


async def test_a_text_model_in_the_picture_slot_fails_with_the_reason() -> None:
    result = await check_drawing(Drawer("gpt-6-luna is not a picture model"), NOW)
    assert result.tools_work is False
    assert "gpt-6-luna is not a picture model" in result.note


async def test_the_local_worker_is_checked_by_its_health() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        body = {"status": "ok", "backend": "diffusers", "model_id": "Tongyi-MAI/Z-Image-Turbo", "loaded": False, "loading": False}
        body |= {"queue_length": 0, "idle_unload_seconds": 600.0}
        return httpx.Response(200, json=body)

    async with ImageWorkerClient("http://image-worker:8100", transport=httpx.MockTransport(answer)) as worker:
        result = await check_worker(worker, NOW)
    assert result.tools_work is True
    assert "Tongyi-MAI/Z-Image-Turbo" in result.note


async def test_a_worker_that_is_down_fails_the_check() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nothing listens here", request=request)

    async with ImageWorkerClient("http://image-worker:8100", transport=httpx.MockTransport(refuse)) as worker:
        result = await check_worker(worker, NOW)
    assert result.tools_work is False


def test_only_picture_models_are_offered_for_images() -> None:
    assert picture_model("gpt-image-1")
    assert picture_model("dall-e-3")
    assert picture_model("imagen-4.0-generate-001")
    assert not picture_model("gpt-6-luna")
    assert not picture_model("claude-sonnet-5-5")
