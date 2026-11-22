from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.planetary_cycles import CYCLES, CycleFlow, cycles_moving
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import TrophicLevelRow, WorldCycleRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.evolution import CycleEffect, CycleSource, PlanetaryCycle, TrophicLevel
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

BALANCE = PERCENT // 2
STEP = 10


@dataclass
class CycleTally:
    turned: int = 0
    seas: int = 0


WorldCycles = dict[PlanetaryCycle, WorldCycleRow]


@dataclass(frozen=True)
class WorldState:
    volcanism: float
    burned: float
    animals: float
    forest: float
    ocean: float
    roughness: float
    warmth: float
    rivers: float
    erosion: float

    def driver(self, source: CycleSource) -> float:
        return {
            CycleSource.VOLCANOES: self.volcanism / PERCENT,
            CycleSource.FIRES: min(PERCENT, self.burned) / PERCENT,
            CycleSource.LIFE: self.animals / PERCENT,
            CycleSource.FORESTS: self.forest / PERCENT,
            CycleSource.OCEANS: self.ocean / PERCENT,
            CycleSource.WEATHERING: self.roughness / PERCENT,
            CycleSource.MELTING: max(0.0, self.warmth),
            CycleSource.EVAPORATION: max(0.0, self.warmth) * self.ocean / PERCENT,
            CycleSource.FREEZING: max(0.0, -self.warmth),
            CycleSource.RIVERS: self.rivers,
            CycleSource.EROSION: self.erosion / PERCENT,
        }[source]


async def cycles_by_world(session: AsyncSession) -> dict[int, WorldCycles]:
    found: dict[int, WorldCycles] = defaultdict(dict)
    for row in await session.scalars(select(WorldCycleRow).order_by(WorldCycleRow.world_id, WorldCycleRow.cycle)):
        found[row.world_id][row.cycle] = row
    return found


async def animal_biomass(session: AsyncSession) -> dict[int, int]:
    found: dict[int, int] = defaultdict(int)
    for row, world_id in await session.execute(
        select(TrophicLevelRow, RegionEnvironmentRow.world_id)
        .join(RegionEnvironmentRow, RegionEnvironmentRow.entity_id == TrophicLevelRow.region_entity_id)
        .where(TrophicLevelRow.level != TrophicLevel.PRODUCER)
    ):
        found[world_id] += row.biomass
    return found


def flux_of(cycles: WorldCycles | None, effect: CycleEffect) -> int | None:
    rows = [row for cycle in cycles_moving(effect) if cycles is not None and (row := cycles.get(cycle)) is not None]
    if not rows:
        return None
    gained, lost = sum(row.inflow for row in rows), sum(row.outflow for row in rows)
    return (gained > lost) - (lost > gained)


def swing_of(cycles: WorldCycles | None, effect: CycleEffect, share: int) -> int:
    rows = [row for cycle in cycles_moving(effect) if cycles is not None and (row := cycles.get(cycle)) is not None]
    return sum(round_half_up((row.stock - BALANCE) * share / PERCENT) for row in rows)


def rain_swing(rules: Rules, cycles: WorldCycles | None) -> int:
    return swing_of(cycles, CycleEffect.RAIN, rules.world_cycles.rain_pct)


def soil_swing(rules: Rules, cycles: WorldCycles | None) -> int:
    return swing_of(cycles, CycleEffect.SOIL, rules.world_cycles.fertility_pct)


def mean(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def flowed(rules: Rules, flows: tuple[CycleFlow, ...], state: WorldState) -> int:
    return round_half_up(sum(flow.rate(rules) * state.driver(flow.source) for flow in flows))


def settle_pool(row: WorldCycleRow, gained: int, lost: int) -> None:
    row.inflow, row.outflow = gained, lost
    if "stock" not in row.locked:
        row.stock = clamp_int(row.stock + gained - lost, 0, PERCENT)


def state_of(land: list[RegionEnvironmentRow], physics: WorldPhysicsRow | None, animals: int, epoch: int) -> WorldState:
    burned = mean([ground.cleared for ground in land]) + PERCENT * sum(1 for ground in land if ground.burned_epoch == epoch) / len(land)
    return WorldState(
        volcanism=physics.volcanism if physics is not None else 0,
        burned=burned,
        animals=min(PERCENT, animals / len(land)),
        forest=mean([ground.forest_cover for ground in land]),
        ocean=physics.hydrosphere if physics is not None else 0,
        roughness=mean([ground.roughness for ground in land]),
        warmth=mean([ground.temperature_shift for ground in land]),
        rivers=sum(1 for ground in land if ground.river_class is not RiverClass.NONE) / len(land),
        erosion=mean([ground.erosion for ground in land]),
    )


async def raise_seas(ctx: TickContext, world_id: int, physics: WorldPhysicsRow | None, cycles: WorldCycles, tally: CycleTally) -> None:
    table = ctx.rules.world_cycles
    for cycle in cycles_moving(CycleEffect.SEA_LEVEL):
        row = cycles.get(cycle)
        if row is None or physics is None or "hydrosphere" in physics.locked or abs(row.stock - BALANCE) < STEP:
            continue
        rise = table.sea_level if row.stock > BALANCE else -table.sea_level
        before = physics.hydrosphere
        physics.hydrosphere = clamp_int(physics.hydrosphere + rise, 0, PERCENT)
        if physics.hydrosphere == before:
            continue
        tally.seas += 1
        if abs(row.stock - BALANCE) >= STEP * 3:
            await record(
                ctx,
                "climate.water_cycle" if rise > 0 else "climate.ice_grew",
                roles={IncidentRole.SUBJECT: world_id},
                facts={"water": row.stock, "hydrosphere": physics.hydrosphere, "rise": rise},
                world_id=world_id,
            )


async def turn_cycles(ctx: TickContext, tally: CycleTally) -> None:
    grounds: dict[int, list[RegionEnvironmentRow]] = defaultdict(list)
    for ground in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        grounds[ground.world_id].append(ground)
    known = await cycles_by_world(ctx.session)
    living = await animal_biomass(ctx.session)
    for world_id in sorted(grounds):
        world = await ctx.session.get(WorldRow, world_id)
        if world is None or held(world_id):
            continue
        physics = await ctx.session.get(WorldPhysicsRow, world_id)
        state = state_of(grounds[world_id], physics, living.get(world_id, 0), ctx.epoch)
        cycles = known[world_id]
        for cycle, spec in CYCLES.items():
            row = cycles.get(cycle)
            if row is None:
                row = cycles[cycle] = WorldCycleRow(world_id=world_id, cycle=cycle, stock=BALANCE, locked=[])
                ctx.session.add(row)
            settle_pool(row, flowed(ctx.rules, spec.sources, state), flowed(ctx.rules, spec.sinks, state))
            row.updated_epoch = ctx.epoch
        tally.turned += 1
        await raise_seas(ctx, world_id, physics, cycles, tally)
    await ctx.session.flush()
