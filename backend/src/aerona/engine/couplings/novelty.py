from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.couplings import NoveltyStockRow
from aerona.db.tables.cuisine import CommunityDishRow, DishRow
from aerona.db.tables.discovery import ArtFormPractitionerRow, ArtFormProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import count_societies
from aerona.engine.recording.record import record


async def novelty_of(session: AsyncSession, holder_id: int | None) -> int:
    row = await session.get(NoveltyStockRow, holder_id) if holder_id is not None else None
    return row.novelty if row is not None else PERCENT


async def ubiquity(ctx: TickContext) -> Counter[int]:
    found: Counter[int] = Counter()
    rows = await ctx.session.execute(select(ArtFormPractitionerRow.art_form_entity_id, func.count()).group_by(ArtFormPractitionerRow.art_form_entity_id))
    for form_id, count in rows:
        found[form_id] = int(count)
    dishes = await ctx.session.execute(
        select(DishRow.entity_id, func.count())
        .join(CommunityDishRow, CommunityDishRow.dish_id == DishRow.id)
        .where(DishRow.entity_id.is_not(None))
        .group_by(DishRow.entity_id)
    )
    for entity_id, count in dishes:
        if entity_id is not None:
            found[entity_id] = int(count)
    return found


async def fashion_holders(ctx: TickContext) -> list[int]:
    forms = list(await ctx.session.scalars(select(ArtFormProfileRow.art_form_entity_id)))
    dishes = [entity for entity in await ctx.session.scalars(select(DishRow.entity_id).where(DishRow.retired.is_(False))) if entity is not None]
    return sorted({*forms, *dishes})


@reads(
    "table.art_form_practitioners", "table.art_form_profiles", "table.community_dishes", "table.dishes", "table.entities", "table.nodes", "table.novelty_stocks"
)
@writes("table.novelty_stocks")
async def novelty(ctx: TickContext) -> None:
    table = ctx.rules.fashion
    counts = await ubiquity(ctx)
    everywhere = max(1, await count_societies(ctx.session) * table.saturation // PERCENT)
    rows = {row.holder_entity_id: row for row in await ctx.session.scalars(select(NoveltyStockRow))}
    for holder_id in await fashion_holders(ctx):
        entity = await ctx.session.get(EntityRow, holder_id)
        if entity is None or entity.status is not EntityStatus.CANON or held(holder_id):
            continue
        row = rows.get(holder_id)
        if row is None:
            row = NoveltyStockRow(holder_entity_id=holder_id, novelty=table.start, adoption=0, revivals=0, updated_epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
        adoption = await lagged(ctx, BalanceLoop.NOVELTY_DRAIN, holder_id, clamp_percent(counts[holder_id] * PERCENT // everywhere))
        if "adoption" not in row.locked:
            if adoption > row.adoption:
                row.peak_epoch = ctx.epoch
            row.adoption = adoption
        if "novelty" not in row.locked:
            before = row.novelty
            change = (table.recovery * (PERCENT - row.adoption) - table.drain * row.adoption) // PERCENT
            row.novelty = clamp_percent(row.novelty + change)
            if before < table.revival_floor <= row.novelty and "revivals" not in row.locked:
                row.revivals += 1
                ctx.count("fashion_revivals")
                await record(ctx, "fashion.revival", roles={IncidentRole.SUBJECT: entity.id}, facts={"novelty": row.novelty, "revivals": row.revivals})
        row.updated_epoch = ctx.epoch
    await ctx.session.flush()
