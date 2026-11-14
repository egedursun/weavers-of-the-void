from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.climes import ClimateOscillationRow, MonsoonSeasonRow, RegionWindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.climes import OscillationPhase
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.engine.context import TickContext
from aerona.engine.environment.notable import year_in
from aerona.engine.notes import note
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat

THIRDS = 3


@dataclass
class SeasonTally:
    monsoons: int = 0
    failed: int = 0
    oscillations: int = 0
    turned: int = 0


def phase_at(row: ClimateOscillationRow) -> OscillationPhase:
    part = row.step * THIRDS // max(1, row.period)
    return (OscillationPhase.WARM, OscillationPhase.NEUTRAL, OscillationPhase.COLD)[min(part, THIRDS - 1)]


async def keep_monsoons(ctx: TickContext, world: WorldRow, tally: SeasonTally) -> None:
    table = ctx.rules.monsoons
    regions = list(
        await ctx.session.scalars(
            select(RegionWindRow.region_entity_id)
            .join(EntityRow, EntityRow.id == RegionWindRow.region_entity_id)
            .where(EntityRow.world_id == world.id, RegionWindRow.monsoon > 0)
        )
    )
    if not regions:
        return
    row = await ctx.session.get(MonsoonSeasonRow, (world.id, ctx.epoch))
    if row is None:
        swing = ctx.rng(seed_of("monsoon", world.id, ctx.epoch)).below(table.swing * 2 + 1) - table.swing
        row = MonsoonSeasonRow(world_id=world.id, epoch=ctx.epoch, strength=clamp_int(PERCENT + swing, 0, PERCENT * 2), locked=[])
        row.failed = row.strength < table.fail_below
        ctx.session.add(row)
    tally.monsoons += 1
    if not row.failed:
        return
    tally.failed += 1
    towns = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(regions))
        )
    )
    for town in towns:
        if not held(town.id):
            shift_stat(town, "prosperity", -table.famine_prosperity, low=0, high=PERCENT)
    ctx.session.add(
        NotableYearRow(
            world_id=world.id,
            region_entity_id=regions[0],
            epoch=max(1, ctx.epoch),
            year=year_in(ctx, ctx.epoch, f"monsoon.{world.id}"),
            kind=NotableYearKind.HUNGER,
            weather=None,
            name=f"The year the monsoon failed over {world.name}",
            magnitude=clamp_int(PERCENT - row.strength, 0, PERCENT),
        )
    )
    await note(ctx, f"The monsoon failed over {world.name}, and hunger followed on its coasts.", key="monsoons.failed", ids=regions[:3])


async def keep_oscillation(ctx: TickContext, world: WorldRow, tally: SeasonTally) -> None:
    table = ctx.rules.oscillations
    row = await ctx.session.get(ClimateOscillationRow, world.id)
    if row is None:
        physics = await ctx.session.get(WorldPhysicsRow, world.id)
        rng = ctx.rng(seed_of("oscillation", world.id))
        if physics is None or physics.hydrosphere <= 0 or not rng.chance(table.seed_chance):
            return
        row = ClimateOscillationRow(
            world_id=world.id, period=table.period_min + rng.below(max(1, table.period_max - table.period_min + 1)), strength=table.strength, locked=[]
        )
        ctx.session.add(row)
    tally.oscillations += 1
    if "step" not in row.locked:
        row.step = (row.step + 1) % max(1, row.period)
    turned = phase_at(row)
    if turned is not row.phase and "phase" not in row.locked:
        row.phase = turned
        tally.turned += 1
        if turned is not OscillationPhase.NEUTRAL:
            await note(
                ctx, f"The seas of {world.name} turned to their {turned.value} phase, and the rains shifted with them.", key="oscillations.turned", ids=[]
            )


async def keep_seasons(ctx: TickContext, tally: SeasonTally) -> None:
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if held(world.id):
            continue
        await keep_monsoons(ctx, world, tally)
        await keep_oscillation(ctx, world, tally)
    await ctx.session.flush()
