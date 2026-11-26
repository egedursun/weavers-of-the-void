import base64
import io
import math
import secrets
from datetime import UTC, datetime
from typing import Any

import httpx
from openai import APIStatusError, AsyncOpenAI, OpenAIError
from PIL import Image

from aerona.constants.imaging import PNG_SIGNATURE, WORKER_REQUEST_TIMEOUT_SECONDS
from aerona.constants.providers import CHAT_IMAGE_MODALITIES, IMAGE_SIZES
from aerona.imaging.client import ProgressCallback
from aerona.imaging.contract import GeneratedImage, ImageJobRequest, ImageProgress, ImageStage
from aerona.imaging.errors import ImageJobFailedError, ImageWorkerError, ImageWorkerUnavailableError

PERCENT_DONE = 100
UNREACHABLE_BELOW = 500
REFUSED_STATUSES = frozenset({401, 403, 408, 409, 429})


def image_failure(error: OpenAIError) -> ImageWorkerError:
    if isinstance(error, APIStatusError) and error.status_code < UNREACHABLE_BELOW and error.status_code not in REFUSED_STATUSES:
        return ImageJobFailedError(f"the provider refused the picture ({error.status_code}): {error.message}")
    return ImageWorkerUnavailableError(f"the provider could not draw now: {error}")


def nearest_size(width: int, height: int) -> tuple[int, int]:
    wanted = width / max(1, height)
    return min(IMAGE_SIZES, key=lambda size: (abs(size[0] / size[1] - wanted), size))


def as_png(data: bytes) -> bytes:
    if data.startswith(PNG_SIGNATURE):
        return data
    with Image.open(io.BytesIO(data)) as picture:
        out = io.BytesIO()
        picture.convert("RGBA").save(out, format="PNG")
        return out.getvalue()


class GatewayImages:
    def __init__(self, client: AsyncOpenAI, model: str, downloads: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._model = model
        self._downloads = downloads or httpx.AsyncClient(timeout=WORKER_REQUEST_TIMEOUT_SECONDS, follow_redirects=True)

    @property
    def enabled(self) -> bool:
        return True

    def model_name(self) -> str:
        return self._model

    async def aclose(self) -> None:
        await self._client.close()
        await self._downloads.aclose()

    async def _picture_bytes(self, answer: Any) -> bytes:
        first = answer.data[0] if answer.data else None
        if first is not None and first.b64_json:
            return base64.b64decode(first.b64_json)
        if first is not None and first.url:
            try:
                response = await self._downloads.get(first.url)
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise ImageWorkerUnavailableError(f"the picture could not be downloaded: {error}") from error
            return response.content
        raise ImageJobFailedError("the provider answered without a picture")

    async def generate(self, job: ImageJobRequest, on_progress: ProgressCallback | None = None) -> GeneratedImage:
        job_id = secrets.token_hex(8)
        await self._report(on_progress, job_id, 1, ImageStage.ENCODING, 0)
        width, height = nearest_size(job.width, job.height)
        try:
            generate: Any = self._client.images.generate
            answer = await generate(model=self._model, prompt=job.prompt, size=f"{width}x{height}", n=1)
        except OpenAIError as error:
            raise image_failure(error) from error
        png = as_png(await self._picture_bytes(answer))
        with Image.open(io.BytesIO(png)) as picture:
            width, height = picture.size
        await self._report(on_progress, job_id, 2, ImageStage.DONE, PERCENT_DONE)
        return GeneratedImage(job_id=job_id, png=png, width=width, height=height, steps=job.steps, seed=job.seed)

    @staticmethod
    async def _report(on_progress: ProgressCallback | None, job_id: str, sequence: int, kind: ImageStage, percent: int) -> None:
        if on_progress is not None:
            await on_progress(ImageProgress(job_id=job_id, sequence=sequence, kind=kind, step=0, total=0, percent=percent, at=datetime.now(UTC)))


def aspect_of(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def data_url_bytes(url: str) -> bytes:
    _, _, payload = url.partition(",")
    return base64.b64decode(payload)


class ChatImages:
    def __init__(self, client: AsyncOpenAI, model: str, downloads: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._model = model
        self._downloads = downloads or httpx.AsyncClient(timeout=WORKER_REQUEST_TIMEOUT_SECONDS, follow_redirects=True)

    @property
    def enabled(self) -> bool:
        return True

    def model_name(self) -> str:
        return self._model

    async def aclose(self) -> None:
        await self._client.close()
        await self._downloads.aclose()

    async def generate(self, job: ImageJobRequest, on_progress: ProgressCallback | None = None) -> GeneratedImage:
        job_id = secrets.token_hex(8)
        await GatewayImages._report(on_progress, job_id, 1, ImageStage.ENCODING, 0)
        width, height = nearest_size(job.width, job.height)
        try:
            create: Any = self._client.chat.completions.create
            answer = await create(
                model=self._model,
                messages=[{"role": "user", "content": job.prompt}],
                extra_body={"modalities": list(CHAT_IMAGE_MODALITIES), "image_config": {"aspect_ratio": aspect_of(width, height)}},
            )
        except OpenAIError as error:
            raise image_failure(error) from error
        png = as_png(await self._picture_bytes(answer))
        with Image.open(io.BytesIO(png)) as picture:
            width, height = picture.size
        await GatewayImages._report(on_progress, job_id, 2, ImageStage.DONE, PERCENT_DONE)
        return GeneratedImage(job_id=job_id, png=png, width=width, height=height, steps=job.steps, seed=job.seed)

    async def _picture_bytes(self, answer: Any) -> bytes:
        message = answer.choices[0].message if answer.choices else None
        extra = (message.model_extra or {}) if message is not None else {}
        images = extra.get("images") or []
        url = images[0].get("image_url", {}).get("url", "") if images else ""
        if url.startswith("data:"):
            return data_url_bytes(url)
        if url:
            try:
                response = await self._downloads.get(url)
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise ImageWorkerUnavailableError(f"the picture could not be downloaded: {error}") from error
            return response.content
        raise ImageJobFailedError("the model answered without a picture; it may not draw pictures")
