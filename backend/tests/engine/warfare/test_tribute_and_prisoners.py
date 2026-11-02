from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import CaptiveRow, TributeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import CaptiveStatus, TributeStatus
from aerona.engine.phases.prisoners import free_prisoner, prisoners
from aerona.engine.phases.tribute import decree_tribute, forgive_tribute, tribute
from aerona.engine.services.community_relations import has_blood_feud, relation, set_relation
from aerona.engine.services.war import take_captive
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make, make_ctx, society, tune

NEVER = {"ransom_chance": 0, "execution_chance": 0, "captive_defection_chance": 0, "escape_agility_divisor": 100000, "escape_intellect_divisor": 100000}


async def test_tribute_flows_through_diminishing_returns(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"tribute_flow": 10, "tribute_revolt_chance": 0}, world_effects={"prosperity_target": 50})
    payer = await make(session, "Payer", EntityType.PEOPLE, world_id, population=900, prosperity=60, wealth=40)
    receiver = await make(session, "Receiver", EntityType.PEOPLE, world_id, population=900, prosperity=75, wealth=40)
    await society(session, payer.id)
    await society(session, receiver.id)
    await decree_tribute(make_ctx(session, rules, epoch=4), payer.id, receiver.id)
    await tribute(make_ctx(session, rules, epoch=5))
    assert payer.stats.model_dump()["prosperity"] == 50
    assert receiver.stats.model_dump()["prosperity"] == 80
    assert receiver.stats.model_dump()["wealth"] == 50


async def test_tribute_ends_after_its_term_and_revolts_close_the_row(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"tribute_epochs": 2, "tribute_revolt_chance": 100, "tribute_revolt_strength_pct": 100})
    payer = await make(session, "Old Payer", EntityType.PEOPLE, world_id, population=900, martiality=10)
    receiver = await make(session, "Old Lord", EntityType.PEOPLE, world_id, population=900, martiality=10)
    rebel = await make(session, "Strong Payer", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    lord = await make(session, "Weak Lord", EntityType.PEOPLE, world_id, population=900, martiality=5)
    await decree_tribute(make_ctx(session, rules, epoch=1), payer.id, receiver.id)
    await decree_tribute(make_ctx(session, rules, epoch=3), rebel.id, lord.id)
    await tribute(make_ctx(session, rules, epoch=4))
    rows = {row.payer_entity_id: row for row in await session.scalars(select(TributeRow))}
    assert rows[payer.id].status is TributeStatus.ENDED
    assert rows[rebel.id].status is TributeStatus.REVOLTED
    repository = BondRepository(session)
    assert not await repository.exists_between(payer.id, receiver.id, BondKind.PAYS_TRIBUTE)
    assert await repository.exists_between(rebel.id, lord.id, BondKind.ENEMY)


async def test_forgiving_tribute_closes_row_and_bond(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    payer = await make(session, "Payer", EntityType.PEOPLE, world_id, population=900)
    receiver = await make(session, "Receiver", EntityType.PEOPLE, world_id, population=900)
    row = await decree_tribute(ctx, payer.id, receiver.id)
    await forgive_tribute(ctx, row.id)
    assert row.status is TributeStatus.ENDED
    assert not await BondRepository(session).exists_between(payer.id, receiver.id, BondKind.PAYS_TRIBUTE)


async def held(session: AsyncSession, world_id: int, rules: Rules, epoch: int = 5) -> tuple[CaptiveRow, int, int, int]:
    home = await make(session, "Home", EntityType.PEOPLE, world_id, population=900, wealth=80, prosperity=80)
    captor = await make(session, "Captor", EntityType.PEOPLE, world_id, population=900, wealth=10, prosperity=40)
    hero = await make(session, "Tam", EntityType.MORTAL, world_id, agility=40, intellect=40, age=30)
    await bond(session, hero.id, home.id, BondKind.PROTECTS)
    row = await take_captive(make_ctx(session, rules, epoch=epoch), captor, hero, None, description="raid", home_id=home.id)
    return row, home.id, captor.id, hero.id


async def test_ransom_pays_captor_and_frees_prisoner(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**NEVER, "ransom_chance": 100})
    row, home, captor, hero = await held(session, world_id, rules)
    await prisoners(make_ctx(session, rules, epoch=6))
    assert row.status is CaptiveStatus.RANSOMED and row.ransom_paid == rules.campaigns.ransom_cost
    assert not await BondRepository(session).exists_between(captor, hero, BondKind.HOLDS_CAPTIVE)
    assert await relation(session, rules, home, captor) > 0


async def test_execution_kills_prisoner_and_starts_feud(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**NEVER, "execution_chance": 100, "ransom_min_wealth": 100, "ransom_min_prosperity": 100})
    row, home, captor, hero = await held(session, world_id, rules)
    await set_relation(make_ctx(session, rules), home, captor, -90, "hatred")
    await prisoners(make_ctx(session, rules, epoch=6))
    assert row.status is CaptiveStatus.EXECUTED
    mortal = await session.get(EntityRow, hero)
    assert mortal is not None and mortal.status is EntityStatus.DEAD
    assert await has_blood_feud(session, home, captor)


async def test_long_captivity_turns_prisoner(session: AsyncSession, world_id: int) -> None:
    rules = tune(
        Rules(), campaigns={**NEVER, "captive_defection_chance": 100, "captive_defection_epochs": 2, "ransom_min_wealth": 100, "ransom_min_prosperity": 100}
    )
    row, home, captor, hero = await held(session, world_id, rules, epoch=1)
    await prisoners(make_ctx(session, rules, epoch=4))
    assert row.status is CaptiveStatus.TURNCOAT
    repository = BondRepository(session)
    assert await repository.exists_between(hero, captor, BondKind.PROTECTS)
    assert not await repository.exists_between(hero, home, BondKind.PROTECTS)


async def test_creator_frees_prisoner(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    row, _, captor, hero = await held(session, world_id, rules)
    await free_prisoner(make_ctx(session, rules), row.id)
    assert row.status is CaptiveStatus.RESCUED
    assert not await BondRepository(session).exists_between(captor, hero, BondKind.HOLDS_CAPTIVE)
