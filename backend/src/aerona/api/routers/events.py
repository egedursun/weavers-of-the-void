import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, Query
from pydantic import TypeAdapter, ValidationError
from sse_starlette.sse import EventSourceResponse

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.events import SERVER_EVENT
from aerona.constants.http import EVENTS_PATH
from aerona.constants.timeouts import SSE_PING_SECONDS
from aerona.events.bus import Event
from aerona.events.kinds import EventKind
from aerona.services.live_log import world_key_of

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])

EVENT_ADAPTER: TypeAdapter[Any] = TypeAdapter(SERVER_EVENT)
EVENT_LIST: Any = list[SERVER_EVENT]


def typed(event: Event) -> Any | None:
    try:
        return EVENT_ADAPTER.validate_python(event.as_json())
    except ValidationError as error:
        logger.warning("event %s of kind %s does not match its payload schema: %s", event.id, event.kind.value, error.error_count())
        return None


@router.get(EVENTS_PATH, response_class=EventSourceResponse, responses={200: {"description": "Server-sent events, one ServerEvent per message."}})
async def stream_events(
    services: ServicesDep,
    last_event_id: int | None = Header(default=None),
    after: int | None = Query(default=None, ge=0),
) -> EventSourceResponse:
    resume_from = last_event_id if last_event_id is not None else after

    async def generate() -> AsyncIterator[dict[str, str]]:
        jobs = services.jobs
        world = await world_key_of(services.database)
        hello = {
            "id": services.bus.last_id,
            "kind": EventKind.STREAM_HELLO.value,
            "payload": {
                "busy": jobs.running_count > 0,
                "groups": jobs.active_groups(),
                "running_jobs": jobs.running_count,
                "last_event_id": services.bus.last_id,
                "world_key": world,
            },
            "at": datetime.now(UTC).isoformat(),
        }
        yield {"event": EventKind.STREAM_HELLO.value, "data": json.dumps(hello)}
        async for item in services.bus.subscribe(resume_from):
            yield {"id": str(item.id), "event": item.kind.value, "data": json.dumps(item.as_json())}

    return EventSourceResponse(generate(), ping=SSE_PING_SECONDS)


@router.get("/activity-log", response_model=EVENT_LIST)
async def activity_log(services: ServicesDep, after: int | None = Query(default=None, ge=0)) -> list[Any]:
    bus = services.bus
    history = services.rules.current.server.live_feed_history
    start = after if after is not None else max(0, bus.last_id - history)
    events = [typed(item) for item in bus.replay_after(start)[-history:]]
    return [item for item in events if item is not None]
