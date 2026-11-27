from dataclasses import replace

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.bond_texts import MENTIONED_IN_FATE
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import DiasporaRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.society import ReverenceRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.models.entity_stats import EventStats, MortalStats
from aerona.engine.body.customs import people_id_of
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.bonds import BondService
from aerona.services.chronicle import ChronicleWriter
from aerona.services.integrity import network
from aerona.services.integrity.age_consistency import raise_lifespans
from aerona.services.integrity.containment import close_mismatched_inside
from aerona.services.integrity.data_repairs import (
    HISTORY_REPAIRS_KEY,
    STATS_TABLE_QUERY,
    DataRepairs,
    close_duplicate_bonds,
    history_signed,
    mark_rejected_bonds,
    refresh_planner_statistics,
)
from aerona.services.integrity.epoch_years import align_epoch_years
from aerona.services.integrity.location_bonds import add_missing_inside_bonds
from aerona.services.integrity.single_ruler import homeland_to_lives_in, restore_homelands, single_rule
from aerona.services.integrity.war_truces import close_unfought_truces
from aerona.services.notifications import Notifier
from tests.services.app.factories import Cosmos, make_entity


async def test_bond_level_repairs(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    other = await make_entity(session, "Duskfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    session.add_all(
        [
            BondRow(source_node_id=world.people.id, target_node_id=other.id, kind=BondKind.RELATED, description="kin", epoch=1),
            BondRow(source_node_id=world.people.id, target_node_id=other.id, kind=BondKind.TRUCE, epoch=1),
            BondRow(source_node_id=world.people.id, target_node_id=world.region.id, kind=BondKind.RULES, role=BondRole.HOMELAND, epoch=1),
        ]
    )
    await session.flush()
    assert await close_duplicate_bonds(session, 2) == 0
    assert await close_unfought_truces(session, rules, 2) == 1
    assert await homeland_to_lives_in(session, 2) == 1
    assert await BondRepository(session).active_between(world.people.id, world.region.id, [BondKind.LIVES_IN])
    await EntityRepository(session).set_status(other, EntityStatus.REJECTED, 2)
    marked = await mark_rejected_bonds(session, 2)
    assert marked >= 1
    assert await close_mismatched_inside(session, 2) == 0
    assert await single_rule(session, 2) == 0


async def test_homeland_repairs_keep_each_town_s_own_people(session: AsyncSession, world: Cosmos) -> None:
    ruled = await make_entity(session, "Harbourmouth", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    stray = await make_entity(session, "Lowtown", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    settled = await make_entity(session, "Upland Steading", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    guests = await make_entity(session, "Farfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    session.add_all(
        [
            BondRow(source_node_id=world.people.id, target_node_id=ruled.id, kind=BondKind.RULES, role=BondRole.HOMELAND, epoch=1),
            BondRow(source_node_id=guests.id, target_node_id=stray.id, kind=BondKind.LIVES_IN, epoch=1),
            BondRow(source_node_id=world.people.id, target_node_id=stray.id, kind=BondKind.LIVES_IN, epoch=1),
            DiasporaRow(people_entity_id=guests.id, host_entity_id=stray.id, locked=[]),
            BondRow(source_node_id=world.people.id, target_node_id=world.region.id, kind=BondKind.LIVES_IN, epoch=1),
        ]
    )
    await session.flush()
    assert await homeland_to_lives_in(session, 2) == 1
    assert await restore_homelands(session) >= 1
    assert await people_id_of(session, ruled) == world.people.id
    assert await people_id_of(session, stray) == world.people.id
    assert await people_id_of(session, settled) == world.people.id
    assert await restore_homelands(session) == 0


async def test_missing_inside_and_epoch_years(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    inside = await BondRepository(session).outgoing(world.people.id, BondKind.INSIDE)
    for bond in inside:
        await BondRepository(session).deactivate(bond, 1)
    assert await add_missing_inside_bonds(session, 2) == 1
    session.add(EpochRow(epoch=2, year_start=0, year_end=10))
    await session.flush()
    assert await align_epoch_years(session, rules) >= 1
    row = await session.get(EpochRow, 2)
    assert row is not None
    assert (row.year_start, row.year_end) == (rules.time.years_per_epoch, 2 * rules.time.years_per_epoch - 1)


async def test_age_consistency(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    elder = await make_entity(
        session, "Elder", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id, stats=MortalStats(age=120, lifespan=70)
    )
    await EntityRepository(session).set_status(elder, EntityStatus.DEAD, 2)
    assert await raise_lifespans(session, rules) == 1
    assert elder.stats.model_dump()["lifespan"] <= 120
    assert await raise_lifespans(session, rules) == 0


async def test_network_health_and_repair(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    flood = await make_entity(session, "Great Flood", EntityType.EVENT, world_id=world.world.id, location_id=world.region.id, stats=EventStats())
    knowledge = await make_entity(session, "Salt Lore", EntityType.KNOWLEDGE, world_id=world.world.id)
    await EntityRepository(session).add_flag(flood.id, EntityFlag.DISASTER, 1)
    log = network.RepairLog()
    before = await network.health(session, rules, log, 1)
    assert before.nodes >= 5
    bus = EventBus()
    counters = await network.repair_dangling_ends(session, rules, 1, log, bus)
    assert counters.lost == 1
    assert await EntityRepository(session).has_flag(knowledge.id, EntityFlag.LOST)
    assert counters.event >= 1
    caused = await BondRepository(session).outgoing(flood.id, BondKind.CAUSED)
    assert world.people.id in {bond.target_node_id for bond in caused}
    assert bus.replay_after(0)[-1].kind is EventKind.NETWORK_REPAIRED
    after = await network.health(session, rules, log, 1)
    assert after.log[0].kind == "rule"
    weak = await network.weak_records(session, rules, 1)
    assert all(entity.status is EntityStatus.CANON for entity in weak)
    candidates = await network.candidate_neighbours(session, rules, knowledge)
    assert candidates
    await network.mark_reviewed(session, [knowledge.id], 1)
    assert knowledge.id not in {entity.id for entity in await network.weak_records(session, rules, 1, 50)}


async def test_full_startup_maintenance(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    repairs = DataRepairs(BondService(ChronicleWriter(Notifier())), network.RepairLog())
    counters = await repairs.startup(session, rules)
    assert "graph_ends" in counters
    assert counters["certain_facts"] >= 1
    assert await session.scalar(select(EntityRow.importance).where(EntityRow.id == world.people.id)) is not None
    states = set(await session.scalars(select(BondRow.state)))
    assert BondState.ACTIVE in states


async def test_planner_statistics_analyze_once_then_optimize(session: AsyncSession) -> None:
    assert await session.scalar(text(STATS_TABLE_QUERY)) is None
    await refresh_planner_statistics(session)
    assert await session.scalar(text(STATS_TABLE_QUERY)) is not None
    await refresh_planner_statistics(session)
    assert await session.scalar(text(STATS_TABLE_QUERY)) is not None


async def test_truces_without_war_survive_when_the_rule_allows_them(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    other = await make_entity(session, "Duskfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    truce = BondRow(source_node_id=world.people.id, target_node_id=other.id, kind=BondKind.TRUCE, epoch=1)
    session.add(truce)
    await session.flush()
    allowing = replace(rules, diplomacy=replace(rules.diplomacy, truce_without_war=1))
    assert await close_unfought_truces(session, allowing, 2) == 0
    assert truce.state is BondState.ACTIVE
    assert await close_unfought_truces(session, rules, 2) == 1
    assert truce.state is not BondState.ACTIVE


async def test_duplicate_rulers_keep_only_the_newest_non_homeland_rule(session: AsyncSession, world: Cosmos) -> None:
    town = await make_entity(session, "Brookhold", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    first = await make_entity(session, "Ana", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bo", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    older = BondRow(source_node_id=first.id, target_node_id=town.id, kind=BondKind.RULES, epoch=1)
    newer = BondRow(source_node_id=second.id, target_node_id=town.id, kind=BondKind.RULES, epoch=1)
    session.add_all([older, newer])
    await session.flush()
    assert await single_rule(session, 2) == 1
    assert older.state is not BondState.ACTIVE and newer.state is BondState.ACTIVE
    assert await single_rule(session, 2) == 0


async def test_history_repairs_run_once_per_code_signature(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    repairs = DataRepairs(BondService(ChronicleWriter(Notifier())), network.RepairLog())
    assert not await history_signed(session)
    first = await repairs.startup(session, rules)
    assert "endings" in first
    assert await history_signed(session)
    row = await session.get(AppliedFixupRow, HISTORY_REPAIRS_KEY)
    assert row is not None
    row.result = {"signature": "old"}
    await session.flush()
    assert not await history_signed(session)
    light = await repairs.startup(session, rules, history=False)
    assert "endings" not in light
    assert not await history_signed(session)


async def test_repair_covers_every_derivable_bond(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    bonds = BondRepository(session)
    ghost = await make_entity(session, "Orlen Vey", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    await EntityRepository(session).set_status(ghost, EntityStatus.DEAD, 1)
    pilgrim = await make_entity(session, "Tamsin Rook", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    session.add(ReverenceRow(entity_id=pilgrim.id, god_node_id=world.son.id, since_epoch=1))
    moon = await make_entity(session, "Ilmeth Moon", EntityType.KNOWLEDGE, world_id=world.world.id)
    singer = await make_entity(session, "Ballad of Tides", EntityType.TRADITION, world_id=world.world.id, description="They sing of Ilmeth Moon.")
    flood = await make_entity(session, "Great Flood", EntityType.EVENT, world_id=world.world.id, location_id=world.region.id, stats=EventStats())
    witness = await make_entity(session, "Corra Dune", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    witness.fate_note = "Corra Dune survived the Great Flood."
    await bonds.connect(BondDraft(flood.id, witness.id, BondKind.CAUSED, 1, "swept away"))
    duplicate = await bonds.connect(BondDraft(witness.id, flood.id, BondKind.RELATED, 1, MENTIONED_IN_FATE, role=BondRole.MENTIONED_IN_FATE))
    legacy = await bonds.connect(BondDraft(world.people.id, world.son.id, BondKind.RELATED, 1, "tapar"))
    await session.flush()
    counters = await network.repair_dangling_ends(session, rules, 2, network.RepairLog())
    past_inside = await bonds.outgoing(ghost.id, BondKind.INSIDE, active_only=False)
    assert [bond.state for bond in past_inside] == [BondState.PAST]
    assert world.son.id in {bond.target_node_id for bond in await bonds.outgoing(pilgrim.id, BondKind.WORSHIPS)}
    assert duplicate.state is BondState.HIDDEN_CLOSED
    assert legacy.kind is BondKind.WORSHIPS and legacy.description is None
    assert singer.id in {bond.source_node_id for bond in await bonds.incoming(moon.id, active_only=False)}
    assert counters.structure >= 1 and counters.cleaned >= 1 and counters.related_converted >= 1


async def test_a_people_is_never_a_diaspora_in_its_own_homeland(session: AsyncSession, world: Cosmos) -> None:
    town = await make_entity(session, "Founded Quay", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.RULES, 1))
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, 1))
    session.add(DiasporaRow(people_entity_id=world.people.id, host_entity_id=town.id, locked=[]))
    await session.flush()
    await restore_homelands(session)
    assert await restore_homelands(session) == 0
    role = await session.scalar(
        select(BondRow.role).where(BondRow.source_node_id == world.people.id, BondRow.target_node_id == town.id, BondRow.kind == BondKind.LIVES_IN)
    )
    assert role is BondRole.HOMELAND
