import re
from pathlib import Path

import httpx

from aerona.services.providers.legacy import reachable_worker, worker_candidates

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "docker-compose.yml"
BACKEND_WORKER = re.compile(r"AERONA_IMAGE_WORKER_URL:\s*\$\{AERONA_DOCKER_IMAGE_WORKER_URL:-([^}]*)\}")
HOST_WORKER = "http://host.docker.internal:8100"
CONTAINER_WORKER = "http://image-worker:8100"


def only_up(*healthy: str) -> httpx.MockTransport:
    def answer(request: httpx.Request) -> httpx.Response:
        origin = f"{request.url.scheme}://{request.url.host}:{request.url.port}"
        if origin in healthy:
            return httpx.Response(200, json={"status": "ok"})
        raise httpx.ConnectError("nothing listens here", request=request)

    return httpx.MockTransport(answer)


def test_docker_reaches_an_image_worker_without_any_setting() -> None:
    found = BACKEND_WORKER.search(COMPOSE.read_text(encoding="utf-8"))
    assert found is not None, "docker-compose.yml no longer hands the backend an image worker address"
    candidates = worker_candidates(found[1])
    assert HOST_WORKER in candidates, "a worker running on the host is never found by the backend in Docker"
    assert CONTAINER_WORKER in candidates, "the gpu image-worker service is never found by the backend in Docker"


async def test_the_first_worker_that_answers_is_chosen() -> None:
    configured = f"{HOST_WORKER},{CONTAINER_WORKER}"
    assert await reachable_worker(configured, only_up(CONTAINER_WORKER)) == CONTAINER_WORKER
    assert await reachable_worker(configured, only_up(HOST_WORKER, CONTAINER_WORKER)) == HOST_WORKER


async def test_a_worker_that_is_not_up_yet_is_still_connected() -> None:
    assert await reachable_worker(f"{HOST_WORKER}, {CONTAINER_WORKER}/", only_up()) == HOST_WORKER


async def test_no_configured_worker_stays_empty() -> None:
    assert await reachable_worker("", only_up(HOST_WORKER)) == ""
