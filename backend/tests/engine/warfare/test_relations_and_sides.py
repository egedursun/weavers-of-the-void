from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import CommunityRelationLabel
from aerona.engine.services.community_relations import (
    change_relation,
    end_blood_feud,
    has_blood_feud,
    initial_relation,
    refresh_relation,
    relation,
    relation_history,
    relation_list,
    set_relation,
    start_blood_feud,
)
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war_geography import Neighbourhood
from aerona.rules.registry import Rules
from tests.db.factories import make_son
from tests.engine.warfare.factories import bond, make, make_ctx


async def test_initial_relation_counts_shared_god_language_and_bonds(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    son = await make_son(session, "Thalor", world_id)
    first = await make(session, "Red Folk", EntityType.PEOPLE, world_id, population=900)
    second = await make(session, "Blue Folk", EntityType.PEOPLE, world_id, population=900)
    await bond(session, first.id, son.id, BondKind.WORSHIPS)
    await bond(session, second.id, son.id, BondKind.WORSHIPS)
    await bond(session, first.id, second.id, BondKind.TRADES_WITH)
    expected = rules.opinion.shared_god + rules.opinion.trade
    assert await initial_relation(session, rules, first.id, second.id) == expected
    assert await relation(session, rules, first.id, second.id) == expected
    assert await session.scalar(select(func.count()).select_from(CommunityRelationRow)) == 0


async def test_every_change_is_remembered_on_both_sides_and_clamps(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    ctx = make_ctx(session, rules)
    first = await make(session, "Ash", EntityType.SETTLEMENT, world_id, population=300)
    second = await make(session, "Oak", EntityType.SETTLEMENT, world_id, population=300)
    for delta in (-30, -40, -50):
        await change_relation(ctx, first.id, second.id, delta, MemoryKind.HARMED_ME, note="raid")
    assert await relation(session, rules, first.id, second.id) == -100
    rows = list(await session.scalars(select(MemoryRow)))
    assert {(row.holder_node_id, row.subject_node_id) for row in rows} == {(first.id, second.id), (second.id, first.id)}
    assert all(row.kind is MemoryKind.HARMED_ME and row.magnitude == -100 for row in rows)
    history = await relation_history(session, first.id, second.id)
    assert [event.event for event in history] == ["raid", "raid"]
    assert await set_relation(ctx, first.id, second.id, 20, "decree") == 20


async def test_blood_feud_penalty_and_labels(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    ctx = make_ctx(session, rules)
    first = await make(session, "Fen", EntityType.PEOPLE, world_id, population=500)
    second = await make(session, "Moor", EntityType.PEOPLE, world_id, population=500)
    value = await start_blood_feud(ctx, first.id, second.id, "a slain heir")
    assert value == -(rules.diplomacy.blood_feud + rules.opinion.blood_feud)
    assert await has_blood_feud(session, first.id, second.id)
    listed = await relation_list(session, rules, first.id)
    assert listed[0].entity_id == second.id
    assert listed[0].label in {CommunityRelationLabel.NEUTRAL, CommunityRelationLabel.COLD, CommunityRelationLabel.ENEMY}
    assert listed[0].blood_feud_since_epoch == ctx.epoch
    assert listed[0].history[-1].kind is MemoryKind.KILLED_KIN
    assert await end_blood_feud(session, first.id, second.id)


async def test_memories_fade_and_the_relation_follows(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    ctx = make_ctx(session, rules, epoch=10)
    first = await make(session, "North", EntityType.PEOPLE, world_id, population=500)
    second = await make(session, "South", EntityType.PEOPLE, world_id, population=500)
    assert await change_relation(ctx, first.id, second.id, 80, MemoryKind.GIFTED_ME, note="gifts") == 80
    later = await refresh_relation(session, rules, 15, first.id, second.id)
    expected = round(80 * (1 - rules.memory.decay_scale_pct * 15 / 100 / 100) ** 5)
    assert abs(later - expected) <= 1
    assert later < 80


async def test_sides_resolve_protected_ruled_and_located(session: AsyncSession, world_id: int) -> None:
    region = await make(session, "Vale", EntityType.REGION, world_id)
    people = await make(session, "Vale Folk", EntityType.PEOPLE, world_id, location_id=region.id, population=900)
    town = await make(session, "Stonegate", EntityType.SETTLEMENT, world_id, location_id=region.id, population=400)
    guard = await make(session, "Bren", EntityType.MORTAL, world_id, location_id=town.id, age=30)
    wanderer = await make(session, "Ilsa", EntityType.MORTAL, world_id, location_id=region.id, age=30)
    sworn = await make(session, "Corr", EntityType.MORTAL, world_id, location_id=town.id, age=30)
    await bond(session, sworn.id, people.id, BondKind.PROTECTS)
    sides = await SideIndex.load(session, await Neighbourhood.load(session, Rules()))
    assert sides.side_of(guard) == town.id
    assert sides.side_of(wanderer) == people.id
    assert sides.side_of(sworn) == people.id
    assert {hero.id for hero in sides.heroes_of(people.id)} == {wanderer.id, sworn.id}
