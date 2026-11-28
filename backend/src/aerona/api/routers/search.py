from fastapi import APIRouter, Query, Response
from pydantic import TypeAdapter

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.constants.api import JSON_CONTENT_TYPE, SEARCH_MIN_LENGTH
from aerona.services.search import NameEntry, SearchHit, names_index, search
from aerona.services.state_memo import per_state

router = APIRouter(tags=["search"])
NAMES_KEY = "names"
NAMES_ADAPTER = TypeAdapter(list[NameEntry])


@router.get("/names", response_model=list[NameEntry])
async def list_names(services: ServicesDep) -> Response:
    async def built() -> bytes:
        async with reader(services) as session:
            return NAMES_ADAPTER.dump_json(await names_index(session), by_alias=True)

    return Response(await per_state(services.database, NAMES_KEY, built), media_type=JSON_CONTENT_TYPE)


@router.get("/search", response_model=list[SearchHit])
async def search_world(services: ServicesDep, q: str = Query(default="", max_length=200)) -> list[SearchHit]:
    query = q.strip()
    if len(query) < SEARCH_MIN_LENGTH:
        return []
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await search(session, rules, services.application.search, query, services.application.feed.version)
