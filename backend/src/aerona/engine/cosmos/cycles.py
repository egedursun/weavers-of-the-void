from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import TrophicLevelRow, WorldCycleRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.evolution import TrophicLevel
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

BALANCE = PERCENT // 2
STEP = 10


@dataclass
class CycleTally:
    turned: int = 0
    seas: int = 0


async def cycles_by_world(session: AsyncSession) -> dict[int, WorldCycleRow]:
    return {row.world_id: row for row in await session.scalars(select(WorldCycleRow))}


async def animal_biomass(session: AsyncSession) -> dict[int, int]:
    found: dict[int, int] = defaultdict(int)
    for row, world_id in await session.execute(
        select(TrophicLevelRow, RegionEnvironmentRow.world_id)
        .join(RegionEnvironmentRow, RegionEnvironmentRow.entity_id == TrophicLevelRow.region_entity_id)
        .where(TrophicLevelRow.level != TrophicLevel.PRODUCER)
    ):
        found[world_id] += row.biomass
    return found


def carbon_flux(cycle: WorldCycleRow | None) -> int | None:
    if cycle is None:
        return None
    return (cycle.carbon_in > cycle.carbon_out) - (cycle.carbon_out > cycle.carbon_in)


def rain_swing(rules: Rules, cycle: WorldCycleRow | None) -> int:
    return 0 if cycle is None else round_half_up((cycle.water - BALANCE) * rules.world_cycles.rain_pct / PERCENT)


def soil_swing(rules: Rules, cycle: WorldCycleRow | None) -> int:
    return 0 if cycle is None else round_half_up((cycle.nutrients - BALANCE) * rules.world_cycles.fertility_pct / PERCENT)


def mean(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def settle_pool(cycle: WorldCycleRow, key: str, gained: int, lost: int) -> None:
    setattr(cycle, f"{key}_in", gained)
    setattr(cycle, f"{key}_out", lost)
    if key not in cycle.locked:
        setattr(cycle, key, clamp_int(getattr(cycle, key) + gained - lost, 0, PERCENT))


async def turn_cycles(ctx: TickContext, tally: CycleTally) -> None:
    table = ctx.rules.world_cycles
    grounds: dict[int, list[RegionEnvironmentRow]] = defaultdict(list)
    for ground in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        grounds[ground.world_id].append(ground)
    cycles = await cycles_by_world(ctx.session)
    living = await animal_biomass(ctx.session)
    for world_id in sorted(grounds):
        world = await ctx.session.get(WorldRow, world_id)
        if world is None or held(world_id):
            continue
        land = grounds[world_id]
        physics = await ctx.session.get(WorldPhysicsRow, world_id)
        volcanism = physics.volcanism if physics is not None else 0
        ocean = physics.hydrosphere if physics is not None else 0
        cycle = cycles.get(world_id)
        if cycle is None:
            cycle = WorldCycleRow(world_id=world_id, carbon=BALANCE, water=BALANCE, nutrients=BALANCE, locked=[])
            ctx.session.add(cycle)
        burned = mean([ground.cleared for ground in land]) + PERCENT * sum(1 for ground in land if ground.burned_epoch == ctx.epoch) / len(land)
        animals = min(PERCENT, living.get(world_id, 0) / len(land))
        settle_pool(
            cycle,
            "carbon",
            round_half_up(
                table.volcanic_carbon * volcanism / PERCENT + table.burning_carbon * min(PERCENT, burned) / PERCENT + table.respiration * animals / PERCENT
            ),
            round_half_up(
                table.forest_uptake * mean([ground.forest_cover for ground in land]) / PERCENT
                + table.ocean_uptake * ocean / PERCENT
                + table.weathering * mean([ground.roughness for ground in land]) / PERCENT
            ),
        )
        warmth = mean([ground.temperature_shift for ground in land])
        rivers = sum(1 for ground in land if ground.river_class is not RiverClass.NONE) / len(land)
        settle_pool(
            cycle,
            "water",
            round_half_up(max(0.0, warmth) * (table.water_from_heat + table.evaporation * ocean / PERCENT)),
            round_half_up(max(0.0, -warmth) * table.water_from_heat + table.discharge * rivers),
        )
        settle_pool(
            cycle,
            "nutrients",
            round_half_up(table.ash_gain * volcanism / PERCENT + table.river_gain * rivers),
            round_half_up(table.erosion_loss * mean([ground.erosion for ground in land]) / PERCENT),
        )
        cycle.updated_epoch = ctx.epoch
        tally.turned += 1
        if physics is not None and "hydrosphere" not in physics.locked and abs(cycle.water - BALANCE) >= STEP:
            rise = table.sea_level if cycle.water > BALANCE else -table.sea_level
            before = physics.hydrosphere
            physics.hydrosphere = clamp_int(physics.hydrosphere + rise, 0, PERCENT)
            if physics.hydrosphere != before:
                tally.seas += 1
                if abs(cycle.water - BALANCE) >= STEP * 3:
                    text = f"The seas of {world.name} rise as its ice melts." if rise > 0 else f"The seas of {world.name} fall as its ice grows."
                    await note(ctx, text, key="climate.water_cycle", world_id=world_id)
    await ctx.session.flush()
