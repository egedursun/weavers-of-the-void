from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import CivilizationTier, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.war import DebtStatus
from aerona.domain.models.entity_stats import ItemStats, PeopleStats
from aerona.engine.phases.civilization import federations, spontaneous_adoption, spontaneous_barter, spontaneous_loans
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, entity, mortal, tuned_rules


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def folk(session: AsyncSession, name: str, world_id: int, location_id: int, **stats: int) -> EntityRow:
    values = {"population": 3000, "wealth": 40, "prosperity": 50} | stats
    created = await entity(session, name, EntityType.PEOPLE, PeopleStats(**values), world_id=world_id, location_id=location_id)
    created.civ_tier = CivilizationTier.KINGDOM
    return created


async def test_allied_communities_across_worlds_found_one_federation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "federation", tuned_rules(civilization={"federation_chance": 100, "federation_min_members": 3}))
    other, other_regions = await add_empty_world(session)
    first = world.people
    first.civ_tier = CivilizationTier.KINGDOM
    second = await folk(session, "Ostren", world.world.id, world.regions[1].id)
    third = await folk(session, "Velfolk", other.id, other_regions[0].id)
    await bond(session, first.id, second.id, BondKind.ALLY)
    await bond(session, first.id, third.id, BondKind.ALLY)
    federation = await federations(ctx)
    assert federation is not None and federation.engine_kind is EngineKind.INTERWORLD_FEDERATION
    assert await has_flag(session, federation.id, EntityFlag.FEDERATION)
    repository = BondRepository(session)
    for member in (first, second, third):
        assert await repository.exists_between(member.id, federation.id, BondKind.MEMBER_OF)
    assert "civilization.federation" in await keys(session)


async def test_federation_cap_and_single_membership_block_a_second_federation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "federation", tuned_rules(civilization={"federation_chance": 100, "federation_min_members": 3, "federation_max": 1}))
    other, other_regions = await add_empty_world(session)
    world.people.civ_tier = CivilizationTier.KINGDOM
    second = await folk(session, "Ostren", world.world.id, world.regions[1].id)
    third = await folk(session, "Velfolk", other.id, other_regions[0].id)
    await bond(session, world.people.id, second.id, BondKind.ALLY)
    await bond(session, world.people.id, third.id, BondKind.ALLY)
    assert await federations(ctx) is not None
    assert await federations(ctx) is None
    loose = await manual_context(session, "federation", tuned_rules(civilization={"federation_chance": 100, "federation_min_members": 2, "federation_max": 5}))
    fourth = await folk(session, "Newcomers", other.id, other_regions[1].id)
    await bond(session, fourth.id, third.id, BondKind.ALLY)
    assert await federations(loose) is None


async def test_federation_needs_members_in_enough_worlds(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "federation", tuned_rules(civilization={"federation_chance": 100, "federation_min_members": 2}))
    world.people.civ_tier = CivilizationTier.KINGDOM
    neighbour = await folk(session, "Ostren", world.world.id, world.regions[1].id)
    await bond(session, world.people.id, neighbour.id, BondKind.ALLY)
    assert await federations(ctx) is None


async def test_wealthy_community_lends_to_a_poor_neighbour_on_its_own(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "loan", tuned_rules(civilization={"loan_chance": 100}))
    lender = await folk(session, "Goldfolk", world.world.id, world.regions[0].id, wealth=90)
    borrower = await folk(session, "Pennyfolk", world.world.id, world.regions[1].id, wealth=10)
    await spontaneous_loans(ctx)
    amount = ctx.rules.civilization.loan_amount
    assert stat(lender, "wealth") == 90 - amount and stat(borrower, "wealth") == 10 + amount
    debt = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.OWES))
    assert debt is not None and debt.debt_status is DebtStatus.OPEN and debt.debt_amount == amount
    recorded = await keys(session)
    assert "civilization.loan" in recorded and "civilization.loan_note" in recorded


async def test_no_spontaneous_loan_when_the_chance_is_zero(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "loan", tuned_rules(civilization={"loan_chance": 0}))
    await folk(session, "Goldfolk", world.world.id, world.regions[0].id, wealth=90)
    await folk(session, "Pennyfolk", world.world.id, world.regions[1].id, wealth=10)
    await spontaneous_loans(ctx)
    assert await session.scalar(select(BondRow).where(BondRow.kind == BondKind.OWES)) is None


async def test_trade_partners_barter_goods_of_similar_value(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "barter", tuned_rules(civilization={"barter_chance": 100}))
    seller = await folk(session, "Sellers", world.world.id, world.regions[0].id)
    buyer = await folk(session, "Buyers", world.world.id, world.regions[1].id)
    await bond(session, seller.id, buyer.id, BondKind.TRADES_WITH)
    sword = await entity(session, "Sword", EntityType.ITEM, ItemStats(damage=50, might=40), world_id=world.world.id, location_id=world.regions[0].id)
    shield = await entity(session, "Shield", EntityType.ITEM, ItemStats(protection=55, might=45), world_id=world.world.id, location_id=world.regions[1].id)
    await bond(session, seller.id, sword.id, BondKind.OWNS)
    await bond(session, buyer.id, shield.id, BondKind.OWNS)
    await spontaneous_barter(ctx)
    repository = BondRepository(session)
    assert await repository.active_between(seller.id, shield.id, [BondKind.OWNS])
    assert await repository.active_between(buyer.id, sword.id, [BondKind.OWNS])
    assert not await repository.active_between(seller.id, sword.id, [BondKind.OWNS])
    recorded = await keys(session)
    assert "civilization.barter" in recorded and "civilization.barter_note" in recorded


async def test_barter_is_refused_when_values_are_too_far_apart(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "barter", tuned_rules(civilization={"barter_chance": 100, "barter_max_value_diff": 5}))
    seller = await folk(session, "Sellers", world.world.id, world.regions[0].id)
    buyer = await folk(session, "Buyers", world.world.id, world.regions[1].id)
    await bond(session, seller.id, buyer.id, BondKind.TRADES_WITH)
    junk = await entity(session, "Junk", EntityType.ITEM, ItemStats(damage=5, might=0), world_id=world.world.id, location_id=world.regions[0].id)
    crown = await entity(session, "Crown", EntityType.ITEM, ItemStats(damage=90, might=90), world_id=world.world.id, location_id=world.regions[1].id)
    await bond(session, seller.id, junk.id, BondKind.OWNS)
    await bond(session, buyer.id, crown.id, BondKind.OWNS)
    await spontaneous_barter(ctx)
    assert "civilization.barter" not in await keys(session)


async def test_an_elder_adopts_a_nearby_orphan_on_their_own(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "adoption", tuned_rules(civilization={"adoption_chance": 100}))
    region = world.regions[0].id
    elder = await mortal(session, "Orrin", world, region, age=50)
    child = await mortal(session, "Pell", world, region, age=8)
    await spontaneous_adoption(ctx)
    assert await BondRepository(session).exists_between(child.id, elder.id, BondKind.FOSTERED_BY)
    recorded = await keys(session)
    assert "civilization.adoption" in recorded and "civilization.adoption_note" in recorded


async def test_no_spontaneous_adoption_when_the_chance_is_zero(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "adoption", tuned_rules(civilization={"adoption_chance": 0}))
    region = world.regions[0].id
    elder = await mortal(session, "Orrin", world, region, age=50)
    child = await mortal(session, "Pell", world, region, age=8)
    await spontaneous_adoption(ctx)
    assert not await BondRepository(session).exists_between(child.id, elder.id, BondKind.DESCENDS_FROM)
