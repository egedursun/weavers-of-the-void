import asyncio
import hashlib
import os
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.generator import GeneratedMap, generate_map
from aerona.cartography.model import MARKER_TYPES, MapRequest, MarkerInput, PositionUpdate, RegionInput, WorldMap, placement_preference
from aerona.cartography.terrain import TerrainOverrides
from aerona.constants.cartography import MAP_BATCH_SIZE, MAP_GENERATOR_VERSION
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldMapRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import Discovery
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules

MAPPED_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD, EntityStatus.FULFILLED)


@dataclass(frozen=True)
class MapRefresh:
    world_id: int
    regions: int
    regenerated: bool


def terrain_of(world: WorldRow) -> TerrainOverrides:
    return TerrainOverrides(
        sea_pct=round_half_up(world.terrain_sea * PERCENT),
        mountains_pct=round_half_up(world.terrain_mountains * PERCENT),
        moisture_pct=round_half_up(world.terrain_humidity * PERCENT),
    )


def _position(entity: EntityRow) -> tuple[float, float] | None:
    if entity.map_x is None or entity.map_y is None:
        return None
    return (entity.map_x, entity.map_y)


def map_request(world: WorldRow, entities: Sequence[EntityRow]) -> MapRequest:
    regions = [entity for entity in entities if entity.entity_type is EntityType.REGION]
    region_ids = {region.id for region in regions}
    marker_ids = {entity.id for entity in entities if entity.entity_type in MARKER_TYPES}
    return MapRequest(
        seed=world.terrain_seed,
        world_type=world.world_type,
        terrain=terrain_of(world),
        regions=tuple(
            RegionInput(
                id=region.id,
                parent_id=region.location_id if region.location_id in region_ids else None,
                is_water=region.is_water,
                position=_position(region),
            )
            for region in regions
        ),
        markers=tuple(
            MarkerInput(
                id=entity.id,
                parent_id=entity.location_id if entity.location_id in region_ids or entity.location_id in marker_ids else None,
                position=_position(entity),
                preference=placement_preference(entity.entity_type),
            )
            for entity in entities
            if entity.id in marker_ids
        ),
    )


def map_signature(request: MapRequest) -> str:
    return hashlib.sha256(request.model_dump_json().encode()).hexdigest()


async def world_entities(session: AsyncSession, world_id: int) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status.in_(MAPPED_STATUSES)).order_by(EntityRow.id)
    return list(await session.scalars(statement))


def _apply_positions(entities: dict[int, EntityRow], updates: Sequence[PositionUpdate]) -> None:
    for update in updates:
        found = entities.get(update.id)
        if found is not None:
            found.map_x, found.map_y = update.x, update.y


def _generate_all(requests: list[MapRequest], rules: Rules) -> list[GeneratedMap]:
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        return list(pool.map(partial(generate_map, rules=rules), requests, chunksize=MAP_BATCH_SIZE))


async def generated_maps(requests: Sequence[MapRequest], rules: Rules) -> list[GeneratedMap]:
    if not requests:
        return []
    return await asyncio.to_thread(_generate_all, list(requests), rules)


async def apply_world_map(session: AsyncSession, world: WorldRow, entities: list[EntityRow], generated: GeneratedMap, epoch: int) -> WorldMap:
    world_map = generated.world_map
    by_id = {entity.id: entity for entity in entities}
    _apply_positions(by_id, generated.new_positions)
    _apply_positions(by_id, generated.relocated_positions)
    payload = world_map.model_dump(mode="json")
    signature = map_signature(map_request(world, entities))
    existing = await session.get(WorldMapRow, world.id)
    if existing is None:
        session.add(WorldMapRow(world_id=world.id, generator_version=MAP_GENERATOR_VERSION, epoch=epoch, signature=signature, geometry=payload))
    else:
        existing.generator_version = MAP_GENERATOR_VERSION
        existing.epoch = epoch
        existing.signature = signature
        existing.geometry = payload
    await session.flush()
    return world_map


async def store_world_map(session: AsyncSession, rules: Rules, world: WorldRow, epoch: int) -> WorldMap:
    entities = await world_entities(session, world.id)
    (generated,) = await generated_maps([map_request(world, entities)], rules)
    return await apply_world_map(session, world, entities, generated, epoch)


async def regenerate_world_map(session: AsyncSession, rules: Rules, world_id: int, epoch: int) -> WorldMap:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    return await store_world_map(session, rules, world, epoch)


async def map_is_stale(session: AsyncSession, world_id: int) -> bool:
    stored = await session.get(WorldMapRow, world_id)
    world = await session.get(WorldRow, world_id)
    if stored is None or world is None or stored.generator_version != MAP_GENERATOR_VERSION:
        return True
    return stored.signature != map_signature(map_request(world, await world_entities(session, world_id)))


async def refresh_world_maps(session: AsyncSession, rules: Rules, epoch: int) -> list[MapRefresh]:
    refreshed: list[MapRefresh] = []
    statement = select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)
    stale = [world for world in list(await session.scalars(statement)) if await map_is_stale(session, world.id)]
    members = {world.id: await world_entities(session, world.id) for world in stale}
    maps = await generated_maps([map_request(world, members[world.id]) for world in stale], rules)
    for world, generated in zip(stale, maps, strict=True):
        world_map = await apply_world_map(session, world, members[world.id], generated, epoch)
        refreshed.append(MapRefresh(world_id=world.id, regions=len(world_map.regions), regenerated=True))
    return refreshed
