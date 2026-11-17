from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.transform import StarModifierRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.cosmography import PhenomenonCause, PhenomenonKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.transform import StarModifierSource
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.phenomena import form_phenomenon
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int


async def anchored_gods(ctx: TickContext, *, world_id: int | None = None, star_id: int | None = None) -> list[ForeignGodRow]:
    statement = select(ForeignGodRow).where(ForeignGodRow.death_epoch.is_(None))
    if world_id is not None:
        statement = statement.where(ForeignGodRow.anchor_world_id == world_id)
    if star_id is not None:
        statement = statement.where(ForeignGodRow.anchor_star_id == star_id)
    return list(await ctx.session.scalars(statement.order_by(ForeignGodRow.id)))


def harm_of(ctx: TickContext, severity: float) -> int:
    return clamp_int(round(severity * PERCENT * ctx.rules.transform.world_soul_harm_pct / PERCENT), 0, PERCENT)


async def world_harmed(ctx: TickContext, world_id: int | None, severity: float) -> int:
    if world_id is None:
        return 0
    hurt = 0
    for god in await anchored_gods(ctx, world_id=world_id):
        amount = harm_of(ctx, severity)
        if amount > 0:
            await apply_hits(ctx, god, Harm(amount, HarmCause.DISASTER, "was hurt through the harm done to its world"))
            hurt += 1
    return hurt


async def star_god_died(ctx: TickContext, god: ForeignGodRow) -> StarModifierRow | None:
    if god.anchor_star_id is None:
        return None
    table = ctx.rules.transform
    star = await ctx.session.get(StarRow, god.anchor_star_id)
    if star is None:
        return None
    row = StarModifierRow(
        star_id=star.id,
        source=StarModifierSource.GOD_DEATH,
        luminosity_pct=-table.star_god_dim_pct,
        age_epochs=table.star_god_age_epochs,
        aged=False,
        decay=table.star_god_dim_decay,
        epoch=ctx.epoch,
        cause_node_id=god.id,
        locked=[],
    )
    ctx.session.add(row)
    region = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.world_id == god.world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if region is not None:
        await form_phenomenon(ctx, PhenomenonKind.DIVINE_RESIDUE, region, PhenomenonCause.GOD_DEATH, cause_node_id=god.id)
    await note(ctx, f"{god.name} died, and {star.name} dims for it.", key="transform.star_god_death", world_id=god.world_id)
    await ctx.session.flush()
    return row
