from types import ModuleType

from fastapi import APIRouter, Depends

from aerona.api.dependencies import guard_writes
from aerona.api.routers import (
    actions,
    backups,
    body,
    books,
    bulk,
    catalogue,
    celestial,
    changes,
    chronicle,
    cosmos,
    council,
    creator,
    depth_society,
    discovery,
    economy,
    engine,
    entities,
    environment,
    epochs,
    events,
    exchange,
    expeditions,
    faith,
    fate,
    foreign_gods,
    genesis,
    goals,
    graph,
    health,
    images,
    jobs,
    languages,
    ledger,
    lore,
    maintenance,
    map,
    mechanics,
    metrics,
    military,
    military_depth,
    mind,
    notes,
    notifications,
    player,
    prayers,
    previews,
    profiles,
    prompt_context,
    realms,
    relations,
    rules,
    search,
    settings,
    sons,
    state,
    wars,
    wilds,
)
from aerona.api.security import BodyLimit
from aerona.constants.api import IMAGE_UPLOAD_MAX_BYTES, PACKAGE_UPLOAD_MAX_BYTES
from aerona.constants.http import API_PREFIX
from aerona.core.errors import NotFoundError

ROUTERS: tuple[ModuleType, ...] = (
    health,
    jobs,
    rules,
    events,
    state,
    changes,
    catalogue,
    search,
    genesis,
    epochs,
    creator,
    sons,
    entities,
    previews,
    engine,
    relations,
    wars,
    foreign_gods,
    cosmos,
    celestial,
    expeditions,
    map,
    chronicle,
    books,
    prayers,
    council,
    graph,
    languages,
    images,
    bulk,
    notes,
    notifications,
    ledger,
    goals,
    settings,
    player,
    backups,
    exchange,
    discovery,
    metrics,
    maintenance,
    prompt_context,
    fate,
    environment,
    body,
    mind,
    mechanics,
    profiles,
    economy,
    depth_society,
    realms,
    military,
    military_depth,
    faith,
    lore,
    wilds,
    actions,
)
IMAGE_UPLOAD_SUFFIX = "/images"
PACKAGE_UPLOAD_SUFFIX = "/world/import"
UNKNOWN_ENDPOINT = "Unknown endpoint."


def body_limits() -> tuple[BodyLimit, ...]:
    return (
        BodyLimit(f"{API_PREFIX}{IMAGE_UPLOAD_SUFFIX}", IMAGE_UPLOAD_MAX_BYTES, binary=True),
        BodyLimit(f"{API_PREFIX}{PACKAGE_UPLOAD_SUFFIX}", PACKAGE_UPLOAD_MAX_BYTES, binary=True),
    )


def build_api_router() -> APIRouter:
    api = APIRouter(prefix=API_PREFIX, dependencies=[Depends(guard_writes)])
    for module in ROUTERS:
        api.include_router(module.router)

    @api.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    async def unknown(path: str) -> None:
        raise NotFoundError(UNKNOWN_ENDPOINT)

    return api
