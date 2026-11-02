from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.motifs import MotifOverrideMode, MotifOverrideRow
from aerona.engine.primitives.tired_motifs import MotifCache, set_override
from aerona.rules.registry import Rules
from aerona.services.prompt_preview.models import MotifOverrideView, TiredMotifReport, TiredMotifView

NO_WORLD = "No such world."


async def require_scope(session: AsyncSession, world_id: int | None) -> None:
    if world_id is not None and await session.get(WorldRow, world_id) is None:
        raise NotFoundError(NO_WORLD)


async def report(session: AsyncSession, rules: Rules, cache: MotifCache, world_id: int | None) -> TiredMotifReport:
    await require_scope(session, world_id)
    motifs = await cache.for_world(session, rules, world_id)
    statement = select(MotifOverrideRow).order_by(MotifOverrideRow.motif)
    rows = list(await session.scalars(statement.where(MotifOverrideRow.world_id.is_(None) if world_id is None else MotifOverrideRow.world_id == world_id)))
    return TiredMotifReport(
        world_id=world_id,
        motifs=[TiredMotifView(key=motif.key, percent=motif.percent, pinned=motif.pinned) for motif in motifs],
        foreign_images=await cache.foreign_images(session, rules, world_id),
        overrides=[MotifOverrideView(id=row.id, world_id=row.world_id, motif=row.motif, mode=row.mode) for row in rows],
    )


async def override(session: AsyncSession, cache: MotifCache, world_id: int | None, motif: str, mode: MotifOverrideMode | None) -> None:
    await require_scope(session, world_id)
    await set_override(session, world_id, motif, mode)
    cache.clear()
