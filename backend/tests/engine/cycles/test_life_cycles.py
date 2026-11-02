from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.warfare import BattleRow, SiegeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.war import BattleOutcome, SiegeStatus
from aerona.domain.models.entity_stats import StructureStats, TraditionStats
from aerona.engine.phases.belief_memory import resisted_fade
from aerona.engine.phases.life_cycles import collapses, population_history, settlement_cycles, siege_wear
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, settlement
from tests.engine.cycles.factories import context, event, flags, snapshot, tune, war

CERTAIN = {"abandon_chance": 100, "collapse_chance": 100, "siege_damage_chance": 100, "siege_durability_loss": 100}


async def test_dwindling_settlement_is_abandoned_and_its_region_turns_desolate(session: AsyncSession, world: CoreWorld) -> None:
    home = await settlement(session, "Brightford", world, world.regions[1], population=3000)
    other = await settlement(session, "Oakhold", world, world.regions[1], population=2600)
    dwindling = await settlement(session, "Ashfall", world, world.regions[3], population=200, prosperity=20)
    await snapshot(session, world, 7, {home.id: 3000, other.id: 2600, dwindling.id: 900})
    await snapshot(session, world, 9, {home.id: 3000, other.id: 2600, dwindling.id: 400})
    ctx = context(session, world, tune(Rules(), life_cycles=CERTAIN), 10)
    await settlement_cycles(ctx)
    assert dwindling.status is EntityStatus.DEAD
    assert {EntityFlag.RUIN.value, EntityFlag.ABANDONED.value} <= await flags(session, dwindling.id)
    assert stat(home, "population") == 3000 + 120 or stat(other, "population") == 2600 + 120
    assert EntityFlag.DESOLATE.value in await flags(session, world.regions[3].id)


async def test_collapsing_people_loses_its_subjects(session: AsyncSession, world: CoreWorld) -> None:
    people = world.people
    people.stats = people.stats.model_copy(update={"population": 2000, "prosperity": 10})
    subject = await settlement(session, "Low Mill", world, world.regions[0])
    await bond(session, people.id, subject.id, BondKind.RULES)
    await snapshot(session, world, 7, {people.id: 6000})
    ctx = context(session, world, tune(Rules(), life_cycles=CERTAIN), 10)
    assert await collapses(ctx, await population_history(ctx)) == 1
    assert not await BondRepository(session).active_between(people.id, subject.id, [BondKind.RULES])
    assert EntityFlag.DISSOLVED.value in await flags(session, people.id)


async def test_siege_razes_a_structure_of_the_besieged_city(session: AsyncSession, world: CoreWorld) -> None:
    city = await settlement(session, "Highwall", world, world.regions[0])
    tower = await entity(
        session, "Old Tower", EntityType.STRUCTURE, StructureStats(splendor=40, durability=15, function=30), world_id=world.world.id, location_id=city.id
    )
    row = await war(session, world, world.people, city)
    siege = SiegeRow(war_id=row.id, besieged_entity_id=city.id, besieger_entity_id=world.people.id, status=SiegeStatus.ONGOING, started_epoch=10, rounds=1)
    session.add(siege)
    await session.flush()
    record = await event(session, world, "Siege of Highwall", EngineKind.SIEGE, birth_epoch=10)
    session.add(
        BattleRow(
            war_id=row.id,
            epoch=10,
            sequence=1,
            record_entity_id=record.id,
            winner_entity_id=world.people.id,
            loser_entity_id=city.id,
            outcome=BattleOutcome.SIEGE_STARVATION,
            gap=5.0,
            siege_id=siege.id,
        )
    )
    await session.flush()
    assert await siege_wear(context(session, world, tune(Rules(), life_cycles=CERTAIN), 10)) == 1
    assert tower.status is EntityStatus.DESTROYED
    assert EntityFlag.RAZED.value in await flags(session, tower.id)


async def test_rigid_tradition_resists_fading(session: AsyncSession, world: CoreWorld) -> None:
    rigid = await entity(session, "Stone Feast", EntityType.TRADITION, TraditionStats(spread=40, rigidity=100), world_id=world.world.id)
    loose = await entity(session, "Loose Feast", EntityType.TRADITION, TraditionStats(spread=40, rigidity=0), world_id=world.world.id)
    ctx = context(session, world, tune(Rules(), life_cycles={"tradition_rigidity_resistance_pct": 100}), 10)
    assert resisted_fade(ctx, rigid, 3) == 0
    assert resisted_fade(ctx, loose, 3) == 3
