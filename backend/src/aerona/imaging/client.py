from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Self

import httpx
from pydantic import BaseModel, ValidationError

from aerona.constants.imaging import (
    PNG_SIGNATURE,
    WORKER_CONNECT_TIMEOUT_SECONDS,
    WORKER_HEALTH_PATH,
    WORKER_JOB_EVENTS_PATH,
    WORKER_JOB_IMAGE_PATH,
    WORKER_JOB_PATH,
    WORKER_JOBS_PATH,
    WORKER_LAST_EVENT_ID_HEADER,
    WORKER_REQUEST_TIMEOUT_SECONDS,
    WORKER_STREAM_READ_TIMEOUT_SECONDS,
    WORKER_STREAM_RECONNECTS,
)
from aerona.core.grammar import several
from aerona.imaging.contract import GeneratedImage, ImageJobAccepted, ImageJobRequest, ImageJobState, ImageProgress, ImageStage, WorkerHealth
from aerona.imaging.errors import (
    ImageGenerationDisabledError,
    ImageJobCancelledError,
    ImageJobConflictError,
    ImageJobFailedError,
    ImageJobNotFoundError,
    ImageJobRejectedError,
    ImageWorkerError,
    ImageWorkerProtocolError,
    ImageWorkerUnavailableError,
)
from aerona.imaging.sse import parse_sse

ProgressCallback = Callable[[ImageProgress], Awaitable[None]]

STATUS_ERRORS: dict[int, type[ImageWorkerError]] = {
    httpx.codes.NOT_FOUND: ImageJobNotFoundError,
    httpx.codes.CONFLICT: ImageJobConflictError,
    httpx.codes.UNPROCESSABLE_ENTITY: ImageJobRejectedError,
}


class ImageWorkerClient:
    def __init__(self, base_url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = (
            httpx.AsyncClient(
                base_url=self._base_url,
                transport=transport,
                timeout=httpx.Timeout(WORKER_REQUEST_TIMEOUT_SECONDS, connect=WORKER_CONNECT_TIMEOUT_SECONDS),
            )
            if self._base_url
            else None
        )

    @property
    def enabled(self) -> bool:
        return self._http is not None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    async def health(self) -> WorkerHealth:
        return parse_model(WorkerHealth, await self._request("GET", WORKER_HEALTH_PATH))

    async def enqueue(self, job: ImageJobRequest) -> ImageJobAccepted:
        response = await self._request("POST", WORKER_JOBS_PATH, json=job.model_dump(mode="json", exclude_none=True))
        return parse_model(ImageJobAccepted, response)

    async def status(self, job_id: str) -> ImageJobState:
        return parse_model(ImageJobState, await self._request("GET", WORKER_JOB_PATH.format(job_id=job_id)))

    async def cancel(self, job_id: str) -> None:
        await self._request("DELETE", WORKER_JOB_PATH.format(job_id=job_id))

    async def fetch_image(self, job_id: str) -> bytes:
        response = await self._request("GET", WORKER_JOB_IMAGE_PATH.format(job_id=job_id))
        if not response.content.startswith(PNG_SIGNATURE):
            raise ImageWorkerProtocolError(f"image worker returned a non-PNG body for job {job_id}")
        return response.content

    async def progress(self, job_id: str, after: int = 0) -> AsyncIterator[ImageProgress]:
        headers = {WORKER_LAST_EVENT_ID_HEADER: str(after)} if after else {}
        limits = httpx.Timeout(WORKER_REQUEST_TIMEOUT_SECONDS, connect=WORKER_CONNECT_TIMEOUT_SECONDS, read=WORKER_STREAM_READ_TIMEOUT_SECONDS)
        async with self._stream(WORKER_JOB_EVENTS_PATH.format(job_id=job_id), headers, limits) as response:
            async for message in parse_sse(response.aiter_lines()):
                try:
                    event = ImageProgress.model_validate_json(message.data)
                except ValidationError as error:
                    raise ImageWorkerProtocolError(
                        f"image worker sent an unreadable progress event: {several(error.error_count(), 'error', 'errors')}"
                    ) from error
                yield event
                if event.terminal:
                    return

    async def follow(self, job_id: str, on_progress: ProgressCallback | None = None) -> ImageProgress:
        last_sequence = 0
        for attempt in range(WORKER_STREAM_RECONNECTS + 1):
            try:
                async for event in self.progress(job_id, after=last_sequence):
                    last_sequence = event.sequence
                    if on_progress is not None:
                        await on_progress(event)
                    if event.terminal:
                        return event
            except ImageWorkerUnavailableError:
                if attempt == WORKER_STREAM_RECONNECTS:
                    raise
        raise ImageWorkerProtocolError(f"progress stream for image job {job_id} ended without a final event")

    async def generate(self, job: ImageJobRequest, on_progress: ProgressCallback | None = None) -> GeneratedImage:
        accepted = await self.enqueue(job)
        final = await self.follow(accepted.job_id, on_progress)
        if final.kind is ImageStage.ERROR:
            raise ImageJobFailedError(final.message or f"image job {accepted.job_id} failed")
        if final.kind is ImageStage.CANCELLED:
            raise ImageJobCancelledError(f"image job {accepted.job_id} was cancelled")
        png = await self.fetch_image(accepted.job_id)
        return GeneratedImage(job_id=accepted.job_id, png=png, width=job.width, height=job.height, steps=job.steps, seed=job.seed)

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise ImageGenerationDisabledError("Image generation is disabled: no image worker URL is configured.")
        return self._http

    async def _request(self, method: str, path: str, *, json: object | None = None) -> httpx.Response:
        client = self._client()
        try:
            response = await client.request(method, path, json=json)
        except httpx.TransportError as error:
            raise ImageWorkerUnavailableError(f"image worker at {self._base_url} is unreachable: {type(error).__name__}") from error
        raise_for_status(response)
        return response

    @asynccontextmanager
    async def _stream(self, path: str, headers: dict[str, str], limits: httpx.Timeout) -> AsyncIterator[httpx.Response]:
        client = self._client()
        try:
            async with client.stream("GET", path, headers=headers, timeout=limits) as response:
                if response.is_error:
                    await response.aread()
                    raise_for_status(response)
                yield response
        except httpx.TransportError as error:
            raise ImageWorkerUnavailableError(f"image worker at {self._base_url} is unreachable: {type(error).__name__}") from error


def raise_for_status(response: httpx.Response) -> None:
    if not response.is_error:
        return
    detail = error_detail(response)
    error_type = STATUS_ERRORS.get(response.status_code)
    if error_type is not None:
        raise error_type(detail)
    if response.status_code >= httpx.codes.INTERNAL_SERVER_ERROR:
        raise ImageWorkerUnavailableError(f"image worker failed with status {response.status_code}: {detail}")
    raise ImageWorkerError(f"image worker rejected the request with status {response.status_code}: {detail}")


def error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    if isinstance(body, dict):
        for key in ("error", "detail"):
            if key in body:
                return str(body[key])
    return str(body)


def parse_model[M: BaseModel](model: type[M], response: httpx.Response) -> M:
    try:
        return model.model_validate(response.json())
    except (ValueError, ValidationError) as error:
        raise ImageWorkerProtocolError(f"image worker returned an unreadable {model.__name__}") from error
