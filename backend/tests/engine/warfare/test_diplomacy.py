from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import WarEnding, WarStatus
from aerona.engine.mind.memories import memories_about
from aerona.engine.phases.diplomacy import (
    decree_alliance,
    decree_betrayal,
    decree_peace,
    diplomacy,
    expire_truces_phase,
    forget_mortal_grudges,
    grudge_limits,
)
from aerona.engine.services.community_relations import relation, set_relation
from aerona.engine.services.war import declare_war, open_war
from aerona.rules.registry import Rules
from tests.db.factories import seed_world
from tests.engine.warfare.factories import bond, make, make_ctx, tune

CALM = {
    "war_declaration_chance": 0,
    "peace_chance": 0,
    "alliance_chance": 0,
    "betrayal_chance": 0,
    "grudge_forget_epochs": 0,
    "exhaustion_cap_pct": 0,
    "neighbor_exhaustion_cap_pct": 0,
}


async def neighbours(session: AsyncSession, world_id: int) -> tuple[int, int]:
    region = await make(session, "Vale", EntityType.REGION, world_id)
    first = await make(session, "Red Folk", EntityType.PEOPLE, world_id, location_id=region.id, population=900)
    second = await make(session, "Blue Folk", EntityType.PEOPLE, world_id, location_id=region.id, population=900)
    return first.id, second.id


def texts(rows: list[ChronicleRow]) -> list[str]:
    return [row.text for row in rows]


async def test_grudging_neighbours_declare_war(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={**CALM, "war_declaration_chance": 100})
    first, second = await neighbours(session, world_id)
    await set_relation(make_ctx(session, rules), first, second, -90, "insult")
    await diplomacy(make_ctx(session, rules))
    assert await BondRepository(session).exists_between(first, second, BondKind.ENEMY)
    lines = texts(list(await session.scalars(select(ChronicleRow))))
    assert any("turned into open enmity" in line for line in lines)


async def test_softened_enemies_make_peace_and_end_their_war(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={**CALM, "peace_chance": 100})
    ctx = make_ctx(session, rules)
    first, second = await neighbours(session, world_id)
    await declare_war(ctx, first, second, "grudge")
    first_row, second_row = await EntityRepository(session).get(first), await EntityRepository(session).get(second)
    assert first_row is not None and second_row is not None
    war = await open_war(ctx, first_row, second_row)
    await set_relation(ctx, first, second, 0, "envoys")
    await diplomacy(ctx)
    assert war.status is WarStatus.ENDED and war.ending is WarEnding.PEACE
    assert not await BondRepository(session).exists_between(first, second, BondKind.ENEMY)
    assert await BondRepository(session).exists_between(first, second, BondKind.TRUCE)


async def test_friendly_neighbours_form_marriage_alliance(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={**CALM, "alliance_chance": 100, "marriage_alliance_share_pct": 100})
    first, second = await neighbours(session, world_id)
    bride = await make(session, "Ara", EntityType.MORTAL, world_id, age=20)
    groom = await make(session, "Bel", EntityType.MORTAL, world_id, age=22)
    await bond(session, bride.id, first, BondKind.PROTECTS)
    await bond(session, groom.id, second, BondKind.PROTECTS)
    await set_relation(make_ctx(session, rules), first, second, 80, "friendship")
    await diplomacy(make_ctx(session, rules))
    repository = BondRepository(session)
    assert await repository.exists_between(first, second, BondKind.ALLY)
    assert await repository.exists_between(bride.id, groom.id, BondKind.SPOUSE_OF)


async def test_betrayal_in_a_multi_world_cosmos_goes_to_the_cosmic_court(session: AsyncSession, world_id: int) -> None:
    await seed_world(session, "Second", "Second Sun")
    rules = Rules()
    ctx = make_ctx(session, rules)
    first, second = await neighbours(session, world_id)
    await bond(session, first, second, BondKind.ALLY)
    traitor = await decree_betrayal(ctx, first, second, war=True)
    repository = BondRepository(session)
    assert not await repository.exists_between(first, second, BondKind.ALLY)
    assert await repository.exists_between(first, second, BondKind.ENEMY)
    assert await EntityRepository(session).has_flag(traitor.id, EntityFlag.OATHBREAKER)


async def test_betrayal_mid_war_loses_the_abandoned_ally_its_war(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={"betrayal_war_collapse_chance": 100})
    ctx = make_ctx(session, rules)
    first, second = await neighbours(session, world_id)
    enemy = await make(session, "Grey Folk", EntityType.PEOPLE, world_id, population=900)
    await bond(session, first, second, BondKind.ALLY)
    first_row, second_row = await EntityRepository(session).get(first), await EntityRepository(session).get(second)
    assert first_row is not None and second_row is not None
    await declare_war(ctx, enemy.id, first, "old raids")
    await declare_war(ctx, enemy.id, second, "old raids")
    first_war = await open_war(ctx, enemy, first_row)
    second_war = await open_war(ctx, enemy, second_row)
    traitor = await decree_betrayal(ctx, first, second, war=False)
    betrayed, survived = (second_war, first_war) if traitor.id == first else (first_war, second_war)
    assert betrayed.ending is WarEnding.BETRAYAL and betrayed.victor_entity_id == enemy.id
    assert survived.status is not WarStatus.ENDED


async def test_old_grudges_fade_when_relations_improve(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={**CALM, "grudge_fade_min_age": 2, "grudge_fade_relation": 0})
    first, second = await neighbours(session, world_id)
    await bond(session, first, second, BondKind.ENEMY, epoch=1)
    await set_relation(make_ctx(session, rules), first, second, 10, "time")
    await diplomacy(make_ctx(session, rules, epoch=10))
    assert not await BondRepository(session).exists_between(first, second, BondKind.ENEMY)
    assert not await BondRepository(session).exists_between(first, second, BondKind.TRUCE)


async def test_long_wars_end_in_exhaustion_peace(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={**CALM, "exhaustion_cap_pct": 100, "exhaustion_growth_pct": 100, "exhaustion_start_epoch": 1})
    first, second = await neighbours(session, world_id)
    start = make_ctx(session, rules, epoch=2)
    await declare_war(start, first, second, "grudge")
    first_row, second_row = await EntityRepository(session).get(first), await EntityRepository(session).get(second)
    assert first_row is not None and second_row is not None
    war = await open_war(start, first_row, second_row)
    before = await relation(session, rules, first, second)
    await diplomacy(make_ctx(session, rules, epoch=6))
    assert war.ending is WarEnding.EXHAUSTION
    assert await relation(session, rules, first, second) >= before + rules.diplomacy.exhaustion_peace_relation
    peace = await memories_about(session, first, second)
    assert any(row.kind is MemoryKind.MADE_PEACE for row in peace)


async def test_mortal_grudges_are_forgotten(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), diplomacy={"mortal_grudge_forget_epochs": 3})
    hero = await make(session, "Ara", EntityType.MORTAL, world_id)
    rival = await make(session, "Bel", EntityType.MORTAL, world_id)
    await bond(session, hero.id, rival.id, BondKind.ENEMY, epoch=1)
    assert await forget_mortal_grudges(make_ctx(session, rules, epoch=9)) == 1


async def test_grudge_pool_widens_fading_when_hostility_overflows() -> None:
    rules = tune(
        Rules(), diplomacy={"world_war_cap": 2, "grudge_pool_pct": 100, "grudge_fade_cap": 1, "grudge_overflow_share_pct": 50, "grudge_forget_epochs": 12}
    )
    fade_cap, forget_age = grudge_limits(rules, 10, 0)
    assert fade_cap == 1 + 4
    wider_cap, _ = grudge_limits(rules, 10, 10)
    assert wider_cap > fade_cap
    assert forget_age == max(rules.diplomacy.grudge_fade_min_age, round(12 * 2 / 10))


async def test_decrees_for_peace_alliance_and_truce_expiry(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await neighbours(session, world_id)
    await declare_war(ctx, first, second, "grudge")
    assert await decree_peace(ctx, first, second)
    assert await BondRepository(session).exists_between(first, second, BondKind.TRUCE)
    await expire_truces_phase(make_ctx(session, epoch=ctx.epoch + ctx.rules.diplomacy.truce_epochs))
    await decree_alliance(ctx, first, second)
    assert await BondRepository(session).exists_between(first, second, BondKind.ALLY)
