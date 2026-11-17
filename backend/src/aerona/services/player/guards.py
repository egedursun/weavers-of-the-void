from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import Discovery
from aerona.engine.gods.essence import spend


async def son(session: AsyncSession, son_id: int) -> SonRow:
    found = await session.get(SonRow, son_id)
    if found is None:
        raise NotFoundError("No such son.")
    return found


async def living_son(session: AsyncSession, son_id: int) -> SonRow:
    found = await son(session, son_id)
    if found.status is SonStatus.DEAD:
        raise ValidationFailedError(f"{found.name} is dead.")
    return found


async def entity(session: AsyncSession, entity_id: int) -> EntityRow:
    found = await session.get(EntityRow, entity_id)
    if found is None:
        raise NotFoundError("No such entity.")
    return found


async def canon_entity(session: AsyncSession, entity_id: int, what: str = "This record") -> EntityRow:
    found = await entity(session, entity_id)
    if found.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{what} is not part of the living canon ({found.name} is {spoken(found.status)}).")
    return found


def of_types(found: EntityRow, types: Iterable[EntityType], message: str) -> EntityRow:
    if found.entity_type not in frozenset(types):
        raise ValidationFailedError(message)
    return found


async def world(session: AsyncSession, world_id: int) -> WorldRow:
    found = await session.get(WorldRow, world_id)
    if found is None:
        raise NotFoundError("No such world.")
    return found


async def open_world(session: AsyncSession, world_id: int) -> WorldRow:
    found = await world(session, world_id)
    if found.discovery is Discovery.FORGOTTEN:
        raise ValidationFailedError(f"{found.name} was forgotten and cannot be acted on.")
    return found


async def target_world(session: AsyncSession, world_id: int | None) -> WorldRow | None:
    if world_id is None:
        return None
    return await open_world(session, world_id)


async def star(session: AsyncSession, star_id: int) -> StarRow:
    found = await session.get(StarRow, star_id)
    if found is None:
        raise NotFoundError("No such star.")
    return found


async def route(session: AsyncSession, route_id: int) -> RouteRow:
    found = await session.get(RouteRow, route_id)
    if found is None:
        raise NotFoundError("No such route.")
    return found


async def foreign_god(session: AsyncSession, god_id: int) -> ForeignGodRow:
    found = await session.get(ForeignGodRow, god_id)
    if found is None:
        raise NotFoundError("No such foreign god.")
    return found


async def reachable(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    if first.world_id == second.world_id:
        return True
    return await WorldRepository(session).connected(first.world_id, second.world_id)


def charge(creator: CreatorRow, amount: int, rule_name: str) -> int:
    return spend(creator, amount, rule_name)


def clip(text: str | None, limit: int) -> str:
    return (text or "").strip()[:limit]


def optional_text(text: str | None) -> str | None:
    cleaned = (text or "").strip()
    return cleaned or None
