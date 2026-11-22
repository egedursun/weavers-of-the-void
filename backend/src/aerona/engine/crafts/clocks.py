from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.crafts import LADDER, PRECISION
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import PublicClockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import ClockKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.crafts.chemistry import knows
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record


@dataclass
class ClockTally:
    built: int = 0
    improved: int = 0
    disciplined: int = 0


async def best_clock(ctx: TickContext, town: EntityRow) -> ClockKind | None:
    for kind, techniques in LADDER:
        if await knows(ctx, town, techniques):
            return kind
    return None


async def keep_clocks(ctx: TickContext, tally: ClockTally) -> None:
    table = ctx.rules.clocks
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        row = await ctx.session.get(PublicClockRow, town.id)
        best = await best_clock(ctx, town)
        if best is not None and (row is None or PRECISION[best] > row.precision) and ctx.rng(seed_of("clock", town.id, ctx.epoch)).chance(table.build_chance):
            if row is None:
                row = PublicClockRow(settlement_entity_id=town.id, kind=best, precision=PRECISION[best], built_epoch=ctx.epoch, locked=[])
                ctx.session.add(row)
                tally.built += 1
            elif "kind" not in row.locked:
                row.kind, row.precision, row.built_epoch = best, PRECISION[best], ctx.epoch
                tally.improved += 1
            await record(ctx, "clocks.built", roles={IncidentRole.MAKER: town.id}, facts={"clock": best, "precision": PRECISION[best]}, place=town.id)
        if row is None:
            continue
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if profile is not None and "unrest" not in profile.locked:
            profile.unrest = clamp_int(profile.unrest + round_half_up(table.discipline_unrest * row.precision / PERCENT), 0, PERCENT)
            tally.disciplined += 1
    await ctx.session.flush()
