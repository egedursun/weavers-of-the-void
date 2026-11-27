from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.cosmos import AIR
from aerona.catalog.planetary_cycles import CYCLES, cycles_moving
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.evolution import WorldCycleRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.domain.enums.evolution import CycleEffect
from aerona.engine.context import TickContext
from aerona.engine.cosmos.cycles import BALANCE, CycleTally, WorldState, breathable_target, first_stock, note_band, thin_air, turn_cycles
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules

RULES = Rules()
STATE = WorldState(volcanism=40, burned=10, animals=30, forest=60, ocean=70, roughness=20, warmth=0.5, rivers=0.5, erosion=20, industry=10, uplift=50)


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "cycles", rules=tuned_rules(**rules))


async def physics_of(session: AsyncSession, world: CoreWorld) -> WorldPhysicsRow:
    found = await session.get(WorldPhysicsRow, world.world.id)
    if found is None:
        found = WorldPhysicsRow(world_id=world.world.id, locked=[])
        session.add(found)
        await session.flush()
    return found


def test_a_cycle_starts_from_what_seeds_it_or_at_balance() -> None:
    for cycle, spec in CYCLES.items():
        stock = first_stock(cycle, STATE)
        if not spec.seeded_by:
            assert stock == BALANCE
        else:
            expected = round(sum(STATE.driver(source) for source in spec.seeded_by) / len(spec.seeded_by) * 100)
            assert abs(stock - min(100, max(0, expected))) <= 1


async def test_a_world_turns_one_row_per_cycle_and_its_scales_set_the_flows(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await at(session, 2))
    await physics_of(session, world)
    tally = CycleTally()
    await turn_cycles(await at(session, 3), tally)
    rows = list(await session.scalars(select(WorldCycleRow).where(WorldCycleRow.world_id == world.world.id)))
    assert {row.cycle for row in rows} == set(CYCLES) and tally.turned == 1
    assert all(row.updated_epoch == 3 for row in rows)
    stopped = {f"{cycle.value}_source_pct": 0 for cycle in CYCLES} | {f"{cycle.value}_sink_pct": 0 for cycle in CYCLES}
    before = {row.cycle: row.stock for row in rows}
    await turn_cycles(await at(session, 4, cycles=stopped), CycleTally())
    assert all(row.inflow == 0 and row.outflow == 0 and row.stock == before[row.cycle] for row in rows)


async def test_a_cycle_crossing_a_band_is_told_and_thin_air_thins_the_world(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    air_cycle = next(iter(cycles_moving(CycleEffect.BREATH)))
    row = WorldCycleRow(world_id=world.world.id, cycle=air_cycle, stock=RULES.cycles.band_high + 5, inflow=8, outflow=2, locked=[])
    await note_band(ctx, world.world.id, row, RULES.cycles.band_high - 5)
    await note_band(ctx, world.world.id, row, RULES.cycles.band_high + 1)
    await session.flush()
    told = list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind == "world.cycle_shifted")))
    assert len(told) == 1
    physics = await physics_of(session, world)
    base = AIR[world.world.atmosphere][1]["oxygen"]
    physics.oxygen = base
    row.stock = RULES.cycles.oxygen_breath_floor - 1
    await thin_air(ctx, world.world, physics, {air_cycle: row})
    assert physics.oxygen == base - RULES.cycles.air_thin_step
    row.stock = RULES.cycles.oxygen_breath_floor + 1
    await thin_air(ctx, world.world, physics, {air_cycle: row})
    assert physics.oxygen == base
    row.stock = RULES.cycles.oxygen_breath_floor // 2
    for _ in range(base * 3):
        await thin_air(ctx, world.world, physics, {air_cycle: row})
    assert physics.oxygen == breathable_target(RULES, world.world, row.stock) > 0
    physics.locked = ["oxygen"]
    row.stock = 0
    held = physics.oxygen
    await thin_air(ctx, world.world, physics, {air_cycle: row})
    assert physics.oxygen == held
    await session.flush()
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert {"world.air_thinned", "world.air_freshened"} <= kinds
