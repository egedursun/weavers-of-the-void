from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import Discovery
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

LIVING_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL)
HIDDEN_DISCOVERY = frozenset({Discovery.FORGOTTEN, Discovery.UNKNOWN})
DEFAULT_FERTILITY = 50


@dataclass(frozen=True)
class HabitableRegion:
    id: int
    name: str
    subtype: str | None
    fertility: int


@dataclass(frozen=True)
class EmptyWorld:
    id: int
    name: str
    world_type: str
    empty_epochs: int
    regions: list[HabitableRegion]


async def has_living(session: AsyncSession, world_id: int) -> bool:
    statement = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(LIVING_TYPES))
    return await session.scalar(statement.limit(1)) is not None


async def habitable_regions(session: AsyncSession, rules: Rules, world_id: int) -> list[HabitableRegion]:
    regions = await session.scalars(
        select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
    )
    threshold = rules.deep_life.life_min_fertility
    found = [
        HabitableRegion(region.id, region.name, region.subtype, fertility)
        for region in regions
        if (fertility := stat(region, "fertility") or DEFAULT_FERTILITY) >= threshold
    ]
    return sorted(found, key=lambda region: (-region.fertility, region.id))


async def empty_since(session: AsyncSession, world: WorldRow, epoch: int) -> int:
    last_end = await session.scalar(
        select(func.max(func.coalesce(EntityRow.end_epoch, epoch))).where(EntityRow.world_id == world.id, EntityRow.entity_type.in_(LIVING_TYPES))
    )
    anchor = max(world.created_epoch or 1, int(last_end) if last_end is not None else 1)
    return epoch - anchor


async def empty_worlds(session: AsyncSession, rules: Rules, epoch: int) -> list[EmptyWorld]:
    found: list[EmptyWorld] = []
    for world in await session.scalars(select(WorldRow).order_by(WorldRow.id)):
        if world.discovery in HIDDEN_DISCOVERY or await has_living(session, world.id):
            continue
        regions = await habitable_regions(session, rules, world.id)
        if not regions:
            continue
        found.append(EmptyWorld(world.id, world.name, world.world_type.value, await empty_since(session, world, epoch), regions))
    return found
