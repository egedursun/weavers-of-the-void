import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from aerona.constants.imaging import PNG_SIGNATURE

FAKE_PNG = PNG_SIGNATURE + b"fake-image-body"
WORKER_URL = "http://image-worker:8100"
TIMESTAMP = "2026-10-31T12:00:00Z"


def progress_event(job_id: str, sequence: int, kind: str, step: int = 0, *, total: int = 2, message: str | None = None) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "sequence": sequence,
        "kind": kind,
        "step": step,
        "total": total,
        "percent": 0,
        "position": None,
        "message": message,
        "at": TIMESTAMP,
    }


def sse_body(events: list[dict[str, Any]]) -> str:
    blocks = [": ping"]
    blocks.extend(f"id: {event['sequence']}\nevent: {event['kind']}\ndata: {json.dumps(event)}" for event in events)
    return "\n\n".join(blocks) + "\n\n"


def successful_events(job_id: str) -> list[dict[str, Any]]:
    return [
        progress_event(job_id, 1, "queued"),
        progress_event(job_id, 2, "loading"),
        progress_event(job_id, 3, "encoding"),
        progress_event(job_id, 4, "step", 1),
        progress_event(job_id, 5, "step", 2),
        progress_event(job_id, 6, "decoding", 2),
        progress_event(job_id, 7, "done", 2),
    ]


@dataclass
class FakeWorker:
    events: list[dict[str, Any]] = field(default_factory=lambda: successful_events("job-1"))
    image: bytes = FAKE_PNG
    enqueue_status: int = 202
    drop_stream_after: int | None = None
    requests: list[httpx.Request] = field(default_factory=list)
    bodies: list[dict[str, Any]] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path, method = request.url.path, request.method
        if method == "GET" and path == "/health":
            return httpx.Response(200, json=health_body())
        if method == "POST" and path == "/jobs":
            self.bodies.append(json.loads(request.content))
            if self.enqueue_status != 202:
                return httpx.Response(self.enqueue_status, json={"detail": "invalid width"})
            return httpx.Response(202, json={"job_id": "job-1", "status": "queued", "position": 0})
        if path.startswith("/jobs/job-1"):
            return self.handle_job(request)
        return httpx.Response(404, json={"error": f"image job {path.split('/')[2]} does not exist"})

    def handle_job(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if path.endswith("/events"):
            after = int(request.headers.get("last-event-id", "0"))
            remaining = [event for event in self.events if event["sequence"] > after]
            if self.drop_stream_after is not None and after == 0:
                remaining = remaining[: self.drop_stream_after]
            return httpx.Response(200, text=sse_body(remaining), headers={"content-type": "text/event-stream"})
        if path.endswith("/image"):
            return httpx.Response(200, content=self.image, headers={"content-type": "image/png"})
        if method == "DELETE":
            return httpx.Response(409, json={"error": "image job job-1 is running and can no longer be cancelled"})
        return httpx.Response(200, json=job_state_body())


def health_body() -> dict[str, Any]:
    return {
        "status": "ok",
        "backend": "fake",
        "model_id": "aerona/fake-gradient",
        "loaded": False,
        "loading": False,
        "queue_length": 0,
        "running_job_id": None,
        "idle_unload_seconds": 600.0,
    }


def job_state_body() -> dict[str, Any]:
    return {
        "job_id": "job-1",
        "status": "done",
        "priority": "manual",
        "width": 720,
        "height": 720,
        "steps": 2,
        "seed": 11,
        "position": None,
        "last_event": progress_event("job-1", 7, "done", 2),
        "error": None,
        "created_at": TIMESTAMP,
        "started_at": TIMESTAMP,
        "finished_at": TIMESTAMP,
    }
