from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import change_religion, first_faith_god, foreign_patron, patron_node, patron_son, son_faith, worship_creator
from aerona.engine.primitives.first_bonds import bind_first_faith
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import living_entity
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class PatronView:
    entity_id: int
    patron_node_id: int | None
    patron_son_id: int | None
    foreign_god_id: int | None


async def require_living(session: AsyncSession, entity_id: int) -> EntityRow:
    found = await living_entity(session, entity_id)
    if found is None:
        raise NotFoundError("No such living record.")
    return found


async def patron_of(session: AsyncSession, entity_id: int) -> PatronView:
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        raise NotFoundError("No such record.")
    son = await patron_son(session, entity)
    foreign = await foreign_patron(session, entity)
    return PatronView(
        entity_id=entity.id,
        patron_node_id=await patron_node(session, entity),
        patron_son_id=son.id if son is not None else None,
        foreign_god_id=foreign.id if foreign is not None else None,
    )


async def set_patron(
    session: AsyncSession, rules: Rules, entity_id: int, son_id: int, *, syncretic: bool = False, reason: str = "by the Creator's will"
) -> bool:
    entity = await require_living(session, entity_id)
    son = await session.get(SonRow, son_id)
    if son is None:
        raise NotFoundError("No such son.")
    ctx = await manual_context(session, "set_patron", rules)
    changed = await change_religion(session, entity, son.id, ctx.epoch, reason, syncretic=syncretic)
    if not changed:
        raise ValidationFailedError(f"{entity.name} cannot turn to {son.name}.")
    return changed


async def worship_the_creator(session: AsyncSession, rules: Rules, entity_id: int, reason: str = "by the Creator's will") -> bool:
    entity = await require_living(session, entity_id)
    ctx = await manual_context(session, "worship_creator", rules)
    return await worship_creator(session, entity, ctx.epoch, reason)


async def suggested_first_god(session: AsyncSession, rules: Rules, entity_id: int) -> SonRow | None:
    entity = await require_living(session, entity_id)
    ctx = await manual_context(session, "first_god", rules)
    return await first_faith_god(session, rules, entity, await RegionAtlas.load(session), ctx.rng().random())


async def give_first_faith(session: AsyncSession, rules: Rules, entity_id: int, source_id: int | None = None) -> PatronView:
    entity = await require_living(session, entity_id)
    if entity.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living community can take a first faith.")
    source = await living_entity(session, source_id) if source_id is not None else None
    ctx = await manual_context(session, "first_faith", rules)
    await bind_first_faith(ctx, entity, await RegionAtlas.load(session), source)
    return await patron_of(session, entity.id)


async def live_faith(session: AsyncSession, rules: Rules, son_id: int) -> int:
    son = await session.get(SonRow, son_id)
    if son is None:
        raise NotFoundError("No such son.")
    return await son_faith(session, rules, son)
