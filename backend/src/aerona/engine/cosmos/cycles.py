from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.climate import climate_profile
from aerona.catalog.life.cosmos import AIR
from aerona.catalog.planetary_cycles import CYCLES, SCALES, CycleFlow, cycles_moving
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import TrophicLevelRow, WorldCycleRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.evolution import CycleEffect, CycleSource, PlanetaryCycle, TrophicLevel
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.environment.long_seasons import made_spell
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
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
    industry: float = 0.0
    uplift: float = 0.0

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
            CycleSource.INDUSTRY: self.industry / PERCENT,
            CycleSource.UPLIFT: self.uplift / PERCENT,
            CycleSource.BURIAL: self.erosion / PERCENT,
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


def state_of(
    land: list[RegionEnvironmentRow], physics: WorldPhysicsRow | None, animals: int, epoch: int, *, industry: float = 0.0, era_heat: int = 0
) -> WorldState:
    burned = mean([ground.cleared for ground in land]) + PERCENT * sum(1 for ground in land if ground.burned_epoch == epoch) / len(land)
    return WorldState(
        volcanism=physics.volcanism if physics is not None else 0,
        burned=burned,
        animals=min(PERCENT, animals / len(land)),
        forest=mean([ground.forest_cover for ground in land]),
        ocean=physics.hydrosphere if physics is not None else 0,
        roughness=mean([ground.roughness for ground in land]),
        warmth=mean([ground.temperature_shift for ground in land]) + era_heat,
        rivers=sum(1 for ground in land if ground.river_class is not RiverClass.NONE) / len(land),
        erosion=mean([ground.erosion for ground in land]),
        industry=industry,
        uplift=physics.tectonics if physics is not None else 0,
    )


async def raise_seas(ctx: TickContext, world_id: int, physics: WorldPhysicsRow | None, cycles: WorldCycles, tally: CycleTally) -> None:
    table = ctx.rules.world_cycles
    for cycle in cycles_moving(CycleEffect.SEA_LEVEL):
        row = cycles.get(cycle)
        if row is None or physics is None or "hydrosphere" in physics.locked or abs(row.stock - BALANCE) < STEP:
            continue
        rise = table.sea_level if (row.stock > BALANCE) is not CYCLES[cycle].inverse else -table.sea_level
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


def first_stock(cycle: PlanetaryCycle, state: WorldState) -> int:
    sources = sorted(CYCLES[cycle].seeded_by)
    if not sources:
        return BALANCE
    return clamp_int(round_half_up(sum(state.driver(source) for source in sources) / len(sources) * PERCENT), 0, PERCENT)


def band_word(rules: Rules, stock: int) -> str:
    table = rules.cycles
    return "low" if stock < table.band_low else "high" if stock > table.band_high else "balanced"


async def note_band(ctx: TickContext, world_id: int, row: WorldCycleRow, before: int) -> None:
    now, was = band_word(ctx.rules, row.stock), band_word(ctx.rules, before)
    if now == was:
        return
    await record(
        ctx,
        "world.cycle_shifted",
        roles={IncidentRole.SUBJECT: world_id},
        facts={"cycle": row.cycle, "stock": row.stock, "inflow": row.inflow, "outflow": row.outflow},
        world_id=world_id,
    )


async def cool_core(ctx: TickContext, world_id: int, physics: WorldPhysicsRow | None, cycles: WorldCycles) -> None:
    if physics is None or "volcanism" in physics.locked or physics.volcanism <= 0:
        return
    for cycle, spec in CYCLES.items():
        row = cycles.get(cycle)
        if not spec.cools or row is None or row.stock >= ctx.rules.cycles.band_low:
            continue
        with explaining():
            term("cycles.heat_volcano_step", -ctx.rules.cycles.heat_volcano_step, source_node_id=world_id)
            physics.volcanism = clamp_int(physics.volcanism - ctx.rules.cycles.heat_volcano_step, 0, PERCENT)
        await record(
            ctx, "world.core_cooled", roles={IncidentRole.SUBJECT: world_id}, facts={"volcanism": physics.volcanism, "heat": row.stock}, world_id=world_id
        )


def held_draw(drawn: int, stock: int) -> int:
    return round_half_up(drawn * min(stock, BALANCE) / BALANCE)


def breathable_target(rules: Rules, world: WorldRow, stock: int) -> int:
    base = AIR[world.atmosphere][1]["oxygen"]
    floor = max(1, rules.cycles.oxygen_breath_floor)
    return round_half_up(base * min(stock, floor) / floor)


async def thin_air(ctx: TickContext, world: WorldRow, physics: WorldPhysicsRow | None, cycles: WorldCycles) -> None:
    air = next((row for cycle in cycles_moving(CycleEffect.BREATH) if (row := cycles.get(cycle)) is not None), None)
    if air is None or physics is None or "oxygen" in physics.locked:
        return
    target = breathable_target(ctx.rules, world, air.stock)
    step = ctx.rules.cycles.air_thin_step
    if physics.oxygen > target:
        physics.oxygen = max(target, physics.oxygen - step)
        await record(ctx, "world.air_thinned", roles={IncidentRole.SUBJECT: world.id}, facts={"oxygen": physics.oxygen, "stock": air.stock}, world_id=world.id)
    elif physics.oxygen < target:
        physics.oxygen = min(target, physics.oxygen + step)
        await record(
            ctx, "world.air_freshened", roles={IncidentRole.SUBJECT: world.id}, facts={"oxygen": physics.oxygen, "stock": air.stock}, world_id=world.id
        )


async def foul_air(session: AsyncSession) -> dict[int, float]:
    found: dict[int, list[int]] = defaultdict(list)
    for world_id, air in await session.execute(
        select(RegionEnvironmentRow.world_id, RegionPollutionRow.air).join(
            RegionPollutionRow, RegionPollutionRow.region_node_id == RegionEnvironmentRow.entity_id
        )
    ):
        found[world_id].append(air)
    return {world_id: sum(values) / len(values) for world_id, values in found.items()}


async def turn_cycles(ctx: TickContext, tally: CycleTally) -> None:
    grounds: dict[int, list[RegionEnvironmentRow]] = defaultdict(list)
    for ground in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        grounds[ground.world_id].append(ground)
    known = await cycles_by_world(ctx.session)
    living = await animal_biomass(ctx.session)
    fumes = await foul_air(ctx.session)
    for world_id in sorted(grounds):
        world = await ctx.session.get(WorldRow, world_id)
        if world is None or held(world_id):
            continue
        physics = await ctx.session.get(WorldPhysicsRow, world_id)
        era_heat = climate_profile(ctx.rules, world.climate_era).temperature_shift if world.climate_era is not None else 0
        state = state_of(grounds[world_id], physics, living.get(world_id, 0), ctx.epoch, industry=fumes.get(world_id, 0.0), era_heat=era_heat)
        cycles = known[world_id]
        for cycle, spec in CYCLES.items():
            row = cycles.get(cycle)
            if row is None:
                row = cycles[cycle] = WorldCycleRow(world_id=world_id, cycle=cycle, stock=first_stock(cycle, state), locked=[])
                ctx.session.add(row)
            before = row.stock
            gain, loss = SCALES[cycle]
            drawn = flowed(ctx.rules, spec.sinks, state) * loss(ctx.rules) // PERCENT
            settle_pool(row, flowed(ctx.rules, spec.sources, state) * gain(ctx.rules) // PERCENT, held_draw(drawn, row.stock) if spec.drawn_as_held else drawn)
            row.updated_epoch = ctx.epoch
            await note_band(ctx, world_id, row, before)
        tally.turned += 1
        await raise_seas(ctx, world_id, physics, cycles, tally)
        await thin_air(ctx, world, physics, cycles)
        await cool_core(ctx, world_id, physics, cycles)
        carbon = cycles.get(PlanetaryCycle.CARBON)
        if carbon is not None and carbon.stock >= ctx.rules.long_seasons.made_threshold:
            await made_spell(ctx, world, winter=False, severity=carbon.stock - BALANCE, incident_id=None)
    await ctx.session.flush()
