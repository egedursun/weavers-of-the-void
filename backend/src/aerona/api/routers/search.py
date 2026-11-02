from fastapi import APIRouter, Query

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.constants.api import SEARCH_MIN_LENGTH
from aerona.services.search import NameEntry, SearchHit, names_index, search

router = APIRouter(tags=["search"])


@router.get("/names", response_model=list[NameEntry])
async def list_names(services: ServicesDep) -> list[NameEntry]:
    async with reader(services) as session:
        return await names_index(session)


@router.get("/search", response_model=list[SearchHit])
async def search_world(services: ServicesDep, q: str = Query(default="", max_length=200)) -> list[SearchHit]:
    query = q.strip()
    if len(query) < SEARCH_MIN_LENGTH:
        return []
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await search(session, rules, services.application.search, query, services.application.feed.version)
