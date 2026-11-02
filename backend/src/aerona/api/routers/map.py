import asyncio

from fastapi import APIRouter, Path, Query
from pydantic import ValidationError
from sqlalchemy import select

from aerona.agents.context.geography import geography_lines
from aerona.agents.context.scope import load_scope
from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import Done
from aerona.api.schemas.entities import MapPositionRequest
from aerona.api.schemas.maps import GeographyPreview, MapPoint, MapRelation, MapRoad, MapTime, MapView, MapWar, RelationLineKind
from aerona.api.schemas.records import EntitySummary, MapNoteRecord, WorldRecord
from aerona.cartography.generator import generate_map
from aerona.cartography.model import MARKER_TYPES, WorldMap
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldMapRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.cosmos.maps import MAPPED_STATUSES, map_is_stale, map_request, store_world_map, world_entities
from aerona.engine.primitives.stats import stat
from aerona.services.container import Services
from aerona.services.images.records import covers_of
from aerona.services.map_lines import region_creators, relation_lines, routed_roads, war_sites
from aerona.services.wiki import event_markers, historical_view, map_notes, political_map, region_dominance, road_network, settlement_tiers, snapshot_epochs

router = APIRouter(tags=["map"])

NO_WORLD = "No such world."
NO_ENTITY = "No such entity."
POSITION_TOOL = "map:position"
POPULATED = (EntityType.PEOPLE, EntityType.SETTLEMENT)

ALIASES = (
    Alias("POST", "/map-notes", "map_note:add"),
    Alias("DELETE", "/map-notes/{note_id}", "map_note:remove", path_fields={"note_id": "note_id"}),
)


def stored_map(row: WorldMapRow | None) -> WorldMap | None:
    if row is None:
        return None
    try:
        return WorldMap.model_validate(row.geometry)
    except ValidationError:
        return None


async def geometry(services: Services, world_id: int) -> WorldMap:
    writable = not services.application.discovery.active
    async with reader(services) as session:
        world = await session.get(WorldRow, world_id)
        if world is None:
            raise NotFoundError(NO_WORLD)
        current = None if await map_is_stale(session, world_id) else stored_map(await session.get(WorldMapRow, world_id))
        if current is not None:
            return current
        rules = await world_rules(services, session)
        request = map_request(world, await world_entities(session, world_id))
    if writable:
        async with services.database.write() as session:
            fresh = await session.get(WorldRow, world_id)
            if fresh is None:
                raise NotFoundError(NO_WORLD)
            epoch = (await CosmosRepository(session).require_cosmos()).epoch
            return await store_world_map(session, rules, fresh, epoch)
    return (await asyncio.to_thread(generate_map, request, rules)).world_map


@router.get("/worlds/{world_id}/map", response_model=MapView)
async def read_map(services: ServicesDep, world_id: int = Path(ge=1), epoch: int | None = Query(default=None, ge=1)) -> MapView:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError(NO_WORLD)
    shape = await geometry(services, world_id)
    async with reader(services) as session:
        rules = await world_rules(services, session)
        world = await session.get(WorldRow, world_id)
        if world is None:
            raise NotFoundError(NO_WORLD)
        current = (await CosmosRepository(session).require_cosmos()).epoch
        shown = epoch if epoch is not None and epoch < current else current
        entities = list(
            await session.scalars(
                select(EntityRow)
                .where(
                    EntityRow.world_id == world_id, EntityRow.status.in_(MAPPED_STATUSES), EntityRow.entity_type.in_(list(MARKER_TYPES | {EntityType.REGION}))
                )
                .order_by(EntityRow.id)
            )
        )
        population = {entity.id: round(stat(entity, "population") or 0) for entity in entities if entity.entity_type in POPULATED}
        past = await historical_view(session, world_id, shown) if shown != current else None
        if past is not None:
            entities = past.entities
            population = past.population
            political = past.political
        else:
            if shown != current:
                entities = [entity for entity in entities if entity.birth_epoch <= shown and (entity.end_epoch is None or entity.end_epoch > shown)]
            political = await political_map(session, rules, world_id)
        positions = {row.id: (row.map_x, row.map_y) for row in entities if row.map_x is not None and row.map_y is not None}
        roads = await road_network(session, world_id)
        routed = await asyncio.to_thread(routed_roads, shape, roads, positions)
        lines = await relation_lines(session, shape, positions, roads)
        covers = await covers_of(session, [row.id for row in entities])
        return MapView(
            world=WorldRecord.model_validate(world),
            geometry=shape,
            points=[MapPoint(entity=EntitySummary.model_validate(row), x=row.map_x, y=row.map_y, cover=covers.get(row.id)) for row in entities],
            political=political,
            roads=[MapRoad(first=item.road.first, second=item.road.second, kind=item.road.kind, length=item.road.length, path=item.path) for item in routed],
            relations=[
                MapRelation(source=line.source, target=line.target, kind=RelationLineKind(line.kind), description=line.description, path=line.path)
                for line in lines
            ],
            wars=[MapWar.model_validate(site) for site in await war_sites(session, world_id, shown, current)],
            region_creators=region_creators(entities),
            settlements=await settlement_tiers(session, rules, world_id, shown),
            markers=await event_markers(session, world_id),
            dominance=await region_dominance(session, world_id),
            population=population,
            notes=[MapNoteRecord.model_validate(row) for row in await map_notes(session, world_id)],
            time=MapTime(current=current, shown=shown, snapshots=await snapshot_epochs(session, world_id)),
        )


@router.get("/worlds/{world_id}/geography", response_model=GeographyPreview)
async def geography_preview(services: ServicesDep, world_id: int = Path(ge=1)) -> GeographyPreview:
    await geometry(services, world_id)
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError(NO_WORLD)
        scope = await load_scope(session, await world_rules(services, session))
        return GeographyPreview(world_id=world_id, text=await geography_lines(scope, world_id))


@router.get("/map-notes", response_model=list[MapNoteRecord])
async def list_map_notes(services: ServicesDep, world_id: int | None = Query(default=None, ge=1)) -> list[MapNoteRecord]:
    async with reader(services) as session:
        return [MapNoteRecord.model_validate(row) for row in await map_notes(session, world_id)]


@router.put("/entities/{entity_id}/map-position", response_model=Done)
async def set_map_position(request: MapPositionRequest, services: ServicesDep, entity_id: int = Path(ge=1)) -> Done:
    async with (
        services.database.write() as session,
        services.application.ledger.creator_action(session, POSITION_TOOL, ActionKind.EDIT_RECORD, {"entity_id": entity_id}),
    ):
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError(NO_ENTITY)
        entity.map_x = round(request.x)
        entity.map_y = round(request.y)
        await session.flush()
    return Done()


mount_all(router, ALIASES, tag="map")
