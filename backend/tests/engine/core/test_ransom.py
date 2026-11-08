from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import CaptiveFate
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import HouseStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import wealth_points
from aerona.engine.military.captivity import ransom, sacrifice
from aerona.engine.military.ransom import (
    carry_language,
    cohort_ransom,
    draw_ransom,
    grow_ward,
    marry_captive,
    named_ransom,
    release_by_opinion,
    ward_returns,
)
from aerona.engine.phases.prisoners import pay_ransom
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import take_captive
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


def cohort(count: int, social_class: SocialClass, **values: object) -> CaptiveCohortRow:
    return CaptiveCohortRow(captor_entity_id=0, count=count, social_class=social_class, fate=CaptiveFate.HELD, since_epoch=1, **values)


async def kingdom(session: AsyncSession, world: CoreWorld, town: EntityRow, treasury: int = 0, name: str = "Kingdom of Vale") -> PolityProfileRow:
    polity = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    profile = PolityProfileRow(
        polity_entity_id=polity.id,
        government=next(iter(GovernmentKind)),
        decision_rule=next(iter(DecisionRule)),
        treasury=treasury,
        capital_entity_id=town.id,
        emblem={},
        legitimacy_parts={},
        locked=[],
    )
    session.add_all([profile, PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id)])
    await session.flush()
    return profile


async def noble(
    session: AsyncSession, world: CoreWorld, town: EntityRow, name: str, *, prestige: int = 50, wealth: int = 0
) -> tuple[EntityRow, HouseProfileRow]:
    house = await entity(session, f"House {name}", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    profile = HouseProfileRow(house_entity_id=house.id, prestige=prestige, wealth=wealth, traits=[], seats=[], locked=[])
    member = await mortal(session, name, world, town.id)
    session.add_all([profile, HouseMemberRow(house_entity_id=house.id, mortal_entity_id=member.id, joined_epoch=1, by_marriage=False)])
    await session.flush()
    return member, profile


async def test_nobles_and_named_captives_fetch_a_higher_price(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    assert cohort_ransom(ctx, cohort(100, SocialClass.NOBLE)) > cohort_ransom(ctx, cohort(100, SocialClass.FARMER)) >= 1
    town = await settlement(session, "Brookhold", world, world.regions[0])
    commoner = await mortal(session, "Tam", world, town.id)
    lord, _ = await noble(session, world, town, "Varn", prestige=90)
    assert await named_ransom(ctx, lord) > await named_ransom(ctx, commoner)


async def test_a_ransom_is_drawn_from_the_house_then_the_realm_then_the_folk(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    lord, house = await noble(session, world, town, "Varn", wealth=50)
    assert await draw_ransom(ctx, town, 30, captive=lord) == 30 and house.wealth == 20
    realm = await kingdom(session, world, town, treasury=40)
    assert await draw_ransom(ctx, town, 30, captive=lord) == 30 and realm.treasury == 10
    set_stats(world.people, wealth=60)
    cost = 3 * ctx.rules.taxation.wealth_per_treasury
    assert await draw_ransom(ctx, world.people, cost) == cost and stat(world.people, "wealth") == 57
    assert await draw_ransom(ctx, world.people, 100 * ctx.rules.taxation.wealth_per_treasury) == 0


async def test_a_ward_raised_at_court_grows_loyal_and_warms_its_home(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    ward = await mortal(session, "Bo", world, town.id)
    row = CaptiveRow(captive_entity_id=ward.id, captor_entity_id=town.id, home_entity_id=world.people.id, taken_epoch=1, loyalty=0, locked=[])
    session.add(row)
    await session.flush()
    assert await ward_returns(ctx, row, ward, town) == 0
    assert await grow_ward(ctx, row, ward, town) == ctx.rules.captive_depth.ward_loyalty
    before = await relation(session, ctx.rules, world.people.id, town.id)
    assert await ward_returns(ctx, row, ward, town) > 0
    assert await relation(session, ctx.rules, world.people.id, town.id) > before
    row.locked = ["loyalty"]
    assert await grow_ward(ctx, row, ward, town) == ctx.rules.captive_depth.ward_loyalty


async def test_friendly_captors_release_and_hostile_ones_hold(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    assert not await release_by_opinion(ctx, town, None)
    assert not await release_by_opinion(ctx, town, world.people)
    await change_relation(ctx, town.id, world.people.id, 90, MemoryKind.GOODWILL)
    assert await release_by_opinion(ctx, town, world.people)


async def test_many_captives_bring_their_tongue_to_the_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0], population=100)
    assert not await carry_language(ctx, cohort(50, SocialClass.FARMER, language_entity_id=world.language.id), None)
    assert not await carry_language(ctx, cohort(50, SocialClass.FARMER), town)
    assert await carry_language(ctx, cohort(50, SocialClass.FARMER, language_entity_id=world.language.id), town)
    assert await BondRepository(session).exists_between(town.id, world.language.id, BondKind.SPEAKS)
    assert not await carry_language(ctx, cohort(50, SocialClass.FARMER, language_entity_id=world.language.id), town)


async def test_a_noble_captive_may_be_wed_into_the_captors_house(session: AsyncSession, world: CoreWorld) -> None:
    ctx: TickContext = await manual_context(session, "test", rules=tuned_rules(captive_depth={"marriage_chance": 100}))
    home = await settlement(session, "Brookhold", world, world.regions[0])
    court = await settlement(session, "Highwall", world, world.regions[0])
    captive, _ = await noble(session, world, home, "Varn")
    row = CaptiveRow(captive_entity_id=captive.id, captor_entity_id=court.id, taken_epoch=1, loyalty=0, locked=[])
    session.add(row)
    await session.flush()
    assert await marry_captive(ctx, row, captive, court) is None
    realm = await kingdom(session, world, court)
    _, host = await noble(session, world, court, "Ost")
    host.polity_entity_id = realm.polity_entity_id
    await session.flush()
    spouse = await marry_captive(ctx, row, captive, court)
    assert spouse is not None and row.married_entity_id == spouse.id and row.loyalty > 0
    assert await marry_captive(ctx, row, captive, court) is None


async def test_a_cohort_ransom_fills_the_captors_treasury_in_coin(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "ransom")
    home = await settlement(session, "Brookhold", world, world.regions[0])
    payer = await kingdom(session, world, home, treasury=10000)
    captor = await settlement(session, "Stonegate", world, world.regions[1])
    keeper = await kingdom(session, world, captor, name="Kingdom of Stone")
    set_stats(captor, wealth=10)
    row = cohort(100, SocialClass.FARMER)
    row.captor_entity_id = captor.id
    session.add(row)
    await session.flush()
    price = cohort_ransom(ctx, row)
    assert await ransom(ctx, row, captor, home) > 0
    assert payer.treasury == 10000 - price and keeper.treasury == price
    assert stat(captor, "wealth") == 10


async def test_a_captor_without_a_realm_takes_the_ransom_as_wealth_points(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "ransom")
    home = await settlement(session, "Brookhold", world, world.regions[0])
    await kingdom(session, world, home, treasury=10000)
    set_stats(world.people, wealth=10)
    row = cohort(100, SocialClass.FARMER)
    row.captor_entity_id = world.people.id
    session.add(row)
    await session.flush()
    price = cohort_ransom(ctx, row)
    await ransom(ctx, row, world.people, home)
    assert stat(world.people, "wealth") == 10 + wealth_points(ctx.rules, price)


async def test_a_named_ransom_pays_the_captors_realm_and_lifts_prosperity_by_points(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "ransom")
    home = await settlement(session, "Brookhold", world, world.regions[0])
    payer = await kingdom(session, world, home, treasury=10000)
    captor = await settlement(session, "Stonegate", world, world.regions[1])
    keeper = await kingdom(session, world, captor, name="Kingdom of Stone")
    set_stats(captor, wealth=10, prosperity=40)
    prisoner = await mortal(session, "Hale", world, home.id)
    held = await take_captive(ctx, captor, prisoner, None, description="taken in a raid", home_id=home.id)
    price = await named_ransom(ctx, prisoner)
    await pay_ransom(ctx, held, prisoner, captor, home)
    assert payer.treasury == 10000 - price and keeper.treasury == price
    assert stat(captor, "wealth") == 10
    assert 40 <= (stat(captor, "prosperity") or 0) <= 40 + wealth_points(ctx.rules, price)


async def test_captives_given_to_the_captors_god_feed_its_essence(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "sacrifice")
    captor = await settlement(session, "Stonegate", world, world.regions[1])
    await BondRepository(session).connect(BondDraft(captor.id, world.son.id, BondKind.WORSHIPS, 1, None))
    world.son.essence = 10
    row = cohort(200, SocialClass.FARMER)
    row.captor_entity_id, row.origin_entity_id = captor.id, world.people.id
    session.add(row)
    await session.flush()
    assert await sacrifice(ctx, row, captor) == 200
    assert world.son.essence > 10
    lone = await settlement(session, "Hollow", world, world.regions[0])
    bare = cohort(100, SocialClass.FARMER)
    bare.captor_entity_id = lone.id
    session.add(bare)
    await session.flush()
    assert await sacrifice(ctx, bare, lone) == 100
