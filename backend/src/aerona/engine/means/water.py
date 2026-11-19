from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.means import LIFTS, MINE_PUMPS
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.means import WaterLiftRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.means import WaterLift
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import era_techniques
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record


@dataclass
class WaterTally:
    built: int = 0


def best_lift(known: frozenset[object], mine: bool) -> WaterLift | None:
    fitting = [lift for lift, spec in LIFTS.items() if spec.needs in known and (not mine or lift in MINE_PUMPS)]
    return max(fitting, key=lambda lift: (LIFTS[lift].capacity, lift.value), default=None)


async def deep_mine_near(ctx: TickContext, town: EntityRow) -> bool:
    found = await ctx.session.scalar(
        select(ResourceProfileRow.resource_entity_id)
        .join(EntityRow, EntityRow.id == ResourceProfileRow.resource_entity_id)
        .where(
            EntityRow.location_id.in_([place for place in (town.id, town.location_id) if place is not None]),
            ResourceProfileRow.extraction_difficulty >= ctx.rules.water_lifting.deep_from,
            ResourceProfileRow.reserve > 0,
        )
        .limit(1)
    )
    return found is not None


async def dry_land(ctx: TickContext, town: EntityRow) -> bool:
    ground = await ctx.session.get(RegionEnvironmentRow, town.location_id) if town.location_id is not None else None
    return ground is not None and ground.rainfall < ctx.rules.water_lifting.dry_below


async def build_lifts(ctx: TickContext, tally: WaterTally) -> None:
    table = ctx.rules.water_lifting
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        dry, deep = await dry_land(ctx, town), await deep_mine_near(ctx, town)
        if not dry and not deep:
            continue
        lift = best_lift(await era_techniques(ctx.session, town.id), mine=deep and not dry)
        if lift is None or not ctx.rng(seed_of("water.lift", town.id, ctx.epoch)).chance(table.build_chance):
            continue
        row = await ctx.session.get(WaterLiftRow, (town.id, lift))
        if row is None:
            ctx.session.add(WaterLiftRow(settlement_entity_id=town.id, device=lift, count=1, since_epoch=ctx.epoch, locked=[]))
            await record(ctx, "water.lift", roles={IncidentRole.MAKER: town.id}, facts={"device": lift, "for_mine": int(deep and not dry)}, place=town.id)
        elif "count" not in row.locked and row.count < table.most_devices + table.devices_per_thousand * stat_or(town, "population", 0) // PER_MILLE:
            row.count += 1
        else:
            continue
        tally.built += 1
    await ctx.session.flush()


async def lifted_in(ctx: TickContext, town_ids: list[int]) -> int:
    rows = await ctx.session.scalars(select(WaterLiftRow).where(WaterLiftRow.settlement_entity_id.in_(town_ids)))
    return sum(row.count * LIFTS[row.device].capacity for row in rows)


async def irrigation_lift(ctx: TickContext, env: RegionEnvironmentRow) -> float:
    table = ctx.rules.water_lifting
    if env.rainfall >= table.dry_below:
        return 1.0
    towns = list(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.location_id == env.entity_id, EntityRow.entity_type == EntityType.SETTLEMENT)))
    lifted = await lifted_in(ctx, towns) if towns else 0
    return 1 + min(table.irrigation_cap, lifted * table.irrigation_pct) / PERCENT


async def drained(ctx: TickContext, community_id: int) -> bool:
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(WaterLiftRow)
        .where(WaterLiftRow.settlement_entity_id == community_id, WaterLiftRow.device.in_(list(MINE_PUMPS)), WaterLiftRow.count > 0)
    )
    return bool(found)


async def flooded_yield(ctx: TickContext, community_id: int, difficulty: int, output: int) -> int:
    table = ctx.rules.water_lifting
    if difficulty < table.deep_from or await drained(ctx, community_id):
        return output
    return round_half_up(output * (PERCENT - table.flooded_pct) / PERCENT)


async def lifted_water(ctx: TickContext, town_id: int) -> int:
    rows = await ctx.session.scalars(select(WaterLiftRow).where(WaterLiftRow.settlement_entity_id == town_id))
    return sum(row.count for row in rows) * ctx.rules.water_lifting.sanitation_gain
