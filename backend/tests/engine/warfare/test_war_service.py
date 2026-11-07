from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import CasusBelliRow, TributeRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import CasusBelliKind, TributeStatus, WarEnding, WarSide, WarStatus
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import (
    WarBlock,
    can_open_war,
    current_war,
    declare_war,
    expire_truces,
    has_truce,
    hostile_pair_count,
    ongoing_war_count,
    open_war,
    raise_army,
    soldier_count,
)
from aerona.engine.services.war_geography import Neighbourhood
from aerona.engine.services.war_resolution import close_stale_wars, close_wars_over_caps, end_war, make_peace, relation_effect
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make, make_ctx, society, tune


async def two_peoples(session: AsyncSession, world_id: int) -> tuple[EntityRow, EntityRow]:
    first = await make(session, "Red Folk", EntityType.PEOPLE, world_id, population=4000, martiality=40, prosperity=50, wealth=50)
    second = await make(session, "Blue Folk", EntityType.PEOPLE, world_id, population=4000, martiality=40, prosperity=50, wealth=50)
    return first, second


async def test_declare_war_breaks_alliance_and_blocks_repeat(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await two_peoples(session, world_id)
    await bond(session, first.id, second.id, BondKind.ALLY)
    await bond(session, first.id, second.id, BondKind.TRADES_WITH)
    assert await declare_war(ctx, first.id, second.id, "insult")
    repository = BondRepository(session)
    assert not await repository.exists_between(first.id, second.id, BondKind.ALLY)
    assert not await repository.exists_between(first.id, second.id, BondKind.TRADES_WITH)
    assert await can_open_war(session, ctx.rules, first.id, second.id, ctx.epoch) is WarBlock.ALREADY_ENEMIES
    assert await hostile_pair_count(session) == 1


async def test_subjects_and_same_party_cannot_fight(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    first, second = await two_peoples(session, world_id)
    await bond(session, first.id, second.id, BondKind.RULES)
    assert await can_open_war(session, rules, first.id, first.id, 1) is WarBlock.SAME_PARTY
    assert await can_open_war(session, rules, first.id, second.id, 1) is WarBlock.SUBJECT


async def test_truce_only_after_a_fought_war_and_expires(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, epoch=10)
    first, second = await two_peoples(session, world_id)
    await declare_war(ctx, first.id, second.id, "grudge")
    assert not await make_peace(ctx, first.id, second.id, "grudge faded")
    assert not await has_truce(session, ctx.rules, first.id, second.id, ctx.epoch)
    await declare_war(ctx, first.id, second.id, "grudge")
    await open_war(ctx, first, second)
    assert await make_peace(ctx, first.id, second.id, "peace")
    assert await has_truce(session, ctx.rules, first.id, second.id, ctx.epoch)
    assert await can_open_war(session, ctx.rules, first.id, second.id, ctx.epoch) is WarBlock.TRUCE
    assert await expire_truces(session, ctx.rules, ctx.epoch + ctx.rules.diplomacy.truce_epochs) == 1


async def test_open_war_records_typed_rows_sides_and_armies(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"army_morale_die": 1})
    ctx = make_ctx(session, rules)
    first, second = await two_peoples(session, world_id)
    await society(session, first.id, warrior=20.0)
    hero = await make(session, "Bren", EntityType.MORTAL, world_id, strength=60, charisma=50)
    await bond(session, hero.id, first.id, BondKind.PROTECTS)
    session.add(CasusBelliRow(holder_entity_id=first.id, target_entity_id=second.id, kind=CasusBelliKind.CLAIM, justification=100, since_epoch=1, locked=[]))
    war = await open_war(ctx, first, second)
    assert war.status is WarStatus.MOBILIZING and war.justified
    sides = list(await session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id)))
    assert {(row.entity_id, row.side) for row in sides} == {(first.id, WarSide.ATTACKER), (second.id, WarSide.DEFENDER)}
    strength = await MilitaryStrength.load(session, rules)
    assert soldier_count(rules, strength, first) == 800
    army, row = await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, rules)), first, war)
    assert row.commander_entity_id == hero.id
    assert army.stats.model_dump()["size"] == 800
    assert army.stats.model_dump()["morale"] == rules.campaigns.army_morale_base + 1
    assert await current_war(session, first.id, second.id) is not None


async def test_victory_over_settlement_by_people_is_conquest(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"conquest_conversion_chance": 0})
    ctx = make_ctx(session, rules)
    people = await make(session, "Horde", EntityType.PEOPLE, world_id, population=4000)
    town = await make(session, "Walltown", EntityType.SETTLEMENT, world_id, population=600, defense=20, prosperity=50)
    await declare_war(ctx, people.id, town.id, "greed")
    war = await open_war(ctx, people, town)
    settlement = await end_war(ctx, war, WarEnding.VICTORY, victor_id=people.id, loser_id=town.id)
    assert settlement.ending is WarEnding.CONQUEST
    assert war.status is WarStatus.ENDED and war.ending is WarEnding.CONQUEST and war.victor_entity_id == people.id
    assert await BondRepository(session).exists_between(people.id, town.id, BondKind.RULES)
    assert not await BondRepository(session).exists_between(people.id, town.id, BondKind.ENEMY)
    assert await ongoing_war_count(session) == 0


async def test_victory_otherwise_imposes_tribute_row_and_bond(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"tribute_conversion_chance": 0})
    ctx = make_ctx(session, rules)
    first, second = await two_peoples(session, world_id)
    war = await open_war(ctx, first, second)
    settlement = await end_war(ctx, war, WarEnding.VICTORY, victor_id=first.id, loser_id=second.id)
    assert settlement.ending is WarEnding.TRIBUTE
    row = await session.scalar(select(TributeRow))
    assert row is not None and row.status is TributeStatus.ACTIVE and row.payer_entity_id == second.id
    assert row.bond_id is not None
    bonds = await BondRepository(session).outgoing(second.id, BondKind.PAYS_TRIBUTE)
    assert [item.id for item in bonds] == [row.bond_id]


async def test_relation_effect_table_covers_every_peaceful_ending() -> None:
    rules = Rules()
    assert relation_effect(rules, WarEnding.CONQUEST) == -rules.campaigns.conquest_relation
    assert relation_effect(rules, WarEnding.WHITE_PEACE) == rules.campaigns.white_peace_relation
    assert relation_effect(rules, WarEnding.EXHAUSTION) == rules.diplomacy.exhaustion_peace_relation
    assert relation_effect(rules, WarEnding.SAME_FRONT) == 0


async def test_stale_wars_close_duplicates_and_peaceful_pairs(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await two_peoples(session, world_id)
    third = await make(session, "Green Folk", EntityType.PEOPLE, world_id, population=4000)
    await declare_war(ctx, first.id, second.id, "grudge")
    duplicate_a = await open_war(ctx, first, second)
    duplicate_b = await open_war(ctx, second, first)
    calm = await open_war(ctx, first, third)
    assert await close_stale_wars(ctx) == 2
    assert duplicate_a.status is WarStatus.MOBILIZING
    assert duplicate_b.ending is WarEnding.SAME_FRONT
    assert calm.ending is WarEnding.PEACE


async def test_war_caps_close_quietest_wars(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={"community_war_cap": 1, "world_war_cap": 5})
    ctx = make_ctx(session, rules)
    hub = await make(session, "Hub", EntityType.PEOPLE, world_id, population=4000)
    rims = [await make(session, f"Rim {index}", EntityType.PEOPLE, world_id, population=4000) for index in range(3)]
    wars = [await open_war(ctx, hub, rim) for rim in rims]
    wars[2].last_clash_epoch = ctx.epoch
    assert await close_wars_over_caps(ctx) == 2
    assert [war.status for war in wars] == [WarStatus.ENDED, WarStatus.ENDED, WarStatus.MOBILIZING]
    assert all(entity.status is EntityStatus.CANON for entity in rims)
