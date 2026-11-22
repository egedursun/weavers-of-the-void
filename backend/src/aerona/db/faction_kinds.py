from collections.abc import Iterable

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import KIND_OF_ENGINE, FactionKind


def of_kinds(kinds: Iterable[FactionKind]) -> ColumnElement[bool]:
    wanted = sorted(set(kinds))
    engines = sorted(engine for engine, kind in KIND_OF_ENGINE.items() if kind in wanted)
    profiled = select(FactionProfileRow.faction_entity_id)
    return or_(
        EntityRow.id.in_(profiled.where(FactionProfileRow.kind.in_(wanted))),
        and_(EntityRow.entity_type == EntityType.FACTION, EntityRow.engine_kind.in_(engines), EntityRow.id.not_in(profiled)),
    )


@memoized(FactionProfileRow, EntityRow)
async def kinds_by_faction(session: AsyncSession) -> dict[int, FactionKind]:
    unprofiled = select(EntityRow.id, EntityRow.engine_kind).where(
        EntityRow.entity_type == EntityType.FACTION, EntityRow.engine_kind.in_(sorted(KIND_OF_ENGINE))
    )
    found = {faction: kind for faction, engine in await session.execute(unprofiled) if engine is not None and (kind := KIND_OF_ENGINE.get(engine)) is not None}
    found.update({faction: kind for faction, kind in await session.execute(select(FactionProfileRow.faction_entity_id, FactionProfileRow.kind))})
    return found


async def kind_of(session: AsyncSession, faction_id: int) -> FactionKind | None:
    return (await kinds_by_faction(session)).get(faction_id)
