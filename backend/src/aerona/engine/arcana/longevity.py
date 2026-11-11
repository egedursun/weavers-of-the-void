from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.arcana import LongevityRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.arcana.vis import burn_for
from aerona.engine.body.afflictions import afflict, cure
from aerona.engine.context import TickContext
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat


@dataclass
class LongevityTally:
    dosed: int = 0
    lapsed: int = 0
    ended: int = 0


async def begin_longevity(ctx: TickContext, mortal: EntityRow, form: SpellForm) -> LongevityRow | None:
    if mortal.entity_type is not EntityType.MORTAL or held(mortal.id):
        return None
    row = await ctx.session.get(LongevityRow, mortal.id)
    if row is None:
        row = LongevityRow(mortal_entity_id=mortal.id, form=form, dose=1, dependence=0, years_gained=0, lapsed_epochs=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    await afflict(ctx, mortal, PackageKind.VIS_DEPENDENCE, Transmission.RITE)
    await ctx.session.flush()
    return row


def dose_for(ctx: TickContext, row: LongevityRow) -> int:
    if "dose" in row.locked:
        return row.dose
    return 1 + row.dependence // ctx.rules.longevity.dose_step_at


async def end_longevity(ctx: TickContext, mortal: EntityRow, row: LongevityRow) -> None:
    dependence = await ctx.session.scalar(
        select(AfflictionRow).where(
            AfflictionRow.bearer_node_id == mortal.id, AfflictionRow.package == PackageKind.VIS_DEPENDENCE, AfflictionRow.cured_epoch.is_(None)
        )
    )
    if dependence is not None:
        await cure(ctx, mortal, dependence, None)
    await ctx.session.delete(row)


async def dose(ctx: TickContext, mortal: EntityRow, row: LongevityRow, tally: LongevityTally) -> None:
    table = ctx.rules.longevity
    row.dose = dose_for(ctx, row)
    if await burn_for(ctx, mortal, row.form, row.dose):
        shift_stat(mortal, "lifespan", table.years, ctx.rules.society.default_stat)
        if "years_gained" not in row.locked:
            row.years_gained += table.years
        if "dependence" not in row.locked:
            row.dependence = clamp_int(row.dependence + table.dependence_gain, 0, PERCENT)
        row.lapsed_epochs = 0
        tally.dosed += 1
        return
    lost = min(row.years_gained, table.lapse_years)
    shift_stat(mortal, "lifespan", -lost, ctx.rules.society.default_stat)
    if "years_gained" not in row.locked:
        row.years_gained -= lost
    row.lapsed_epochs += 1
    await add_stress(ctx.session, mortal.id, table.lapse_stress, ctx.epoch)
    tally.lapsed += 1
    if row.years_gained <= 0:
        await end_longevity(ctx, mortal, row)
        tally.ended += 1


async def tend_longevity(ctx: TickContext, tally: LongevityTally) -> None:
    for row in list(await ctx.session.scalars(select(LongevityRow).order_by(LongevityRow.mortal_entity_id))):
        mortal = await ctx.session.get(EntityRow, row.mortal_entity_id)
        if mortal is None or mortal.status is not EntityStatus.CANON or held(mortal.id):
            continue
        await dose(ctx, mortal, row, tally)
    await ctx.session.flush()
