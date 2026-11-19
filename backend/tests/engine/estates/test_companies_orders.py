from sqlalchemy import select

from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow, CompanyShareRow, HolyOrderProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause, WarSide
from aerona.domain.models.entity_stats import CultStats, EventStats, FactionStats
from aerona.engine.factions.companies import CompanyTally, collapse, found_dominion, hire_guards, pay_dividends
from aerona.engine.factions.orders import OrderTally, serve_holy_wars, take_vows
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, bonded, context, link, make, mortal, settlement, son, trade_route, tuned


async def company_at(realm: Realm, wealth: int, strength: int = 20) -> tuple[EntityRow, CompanyProfileRow, EntityRow, EntityRow]:
    home = await settlement(realm, "Harrowgate")
    far = await settlement(realm, "Isleby")
    road = await trade_route(realm, home, far)
    company = await make(
        realm.session,
        "the Chartered Company of Harrowgate",
        EntityType.FACTION,
        FactionStats(wealth=wealth, strength=strength, sway=10),
        world_id=realm.world.id,
    )
    realm.session.add(
        FactionProfileRow(faction_entity_id=company.id, kind=FactionKind.CHARTERED_COMPANY, home_entity_id=home.id, influence_over={}, armed=True, locked=[])
    )
    row = CompanyProfileRow(faction_entity_id=company.id, route_entity_id=road.id, dividend_pct=100, value=wealth, chartered_epoch=1, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    return company, row, home, far


async def test_dividends_come_out_of_the_company_s_coffers(realm: Realm) -> None:
    ctx = context(realm.session, tuned(companies={"dividend_wealth": 10}))
    company, row, _, _ = await company_at(realm, wealth=8)
    holder = await make(realm.session, "Merchants of Harrowgate", EntityType.FACTION, FactionStats(wealth=0), world_id=realm.world.id)
    realm.session.add(CompanyShareRow(company_entity_id=company.id, holder_node_id=holder.id, share=100))
    await realm.session.flush()
    await pay_dividends(ctx, company, row, CompanyTally())
    assert (stat(company, "wealth"), stat(holder, "wealth")) == (0, 8)


async def test_a_rich_company_hires_guards_from_its_coffers(realm: Realm) -> None:
    ctx = context(realm.session, tuned(companies={"guard_wealth": 30, "guard_wage": 3, "guard_strength": 5}))
    company, _, _, _ = await company_at(realm, wealth=40)
    tally = CompanyTally()
    await hire_guards(ctx, company, tally)
    assert (stat(company, "wealth"), stat(company, "strength"), tally.guarded) == (37, 25, 1)


async def test_a_collapsing_company_defaults_on_its_loans(realm: Realm) -> None:
    ctx = context(realm.session, tuned(banking={"default_bank_loss": 7}))
    company, row, _, _ = await company_at(realm, wealth=2)
    bank = await make(realm.session, "House of Coin", EntityType.FACTION, FactionStats(wealth=50), world_id=realm.world.id)
    loan = LoanRow(
        lender_entity_id=bank.id,
        borrower_entity_id=company.id,
        principal=10,
        interest_pct=10,
        issued_epoch=1,
        due_epoch=9,
        status=LoanStatus.OPEN,
        purpose="company",
    )
    realm.session.add(loan)
    await realm.session.flush()
    tally = CompanyTally()
    await collapse(ctx, company, row, tally)
    assert loan.status is LoanStatus.DEFAULTED and stat(bank, "wealth") == 43 and tally.defaulted == 1


async def test_a_company_that_holds_the_far_land_rules_it_as_a_realm(realm: Realm) -> None:
    ctx = context(realm.session, tuned(companies={"dominion_years": 150}), epoch=10)
    company, row, _, far = await company_at(realm, wealth=40)
    assert far.location_id is not None
    realm.session.add(OccupationRow(region_entity_id=far.location_id, occupier_entity_id=company.id, since_epoch=2))
    row.region_entity_id = far.location_id
    await realm.session.flush()
    tally = CompanyTally()
    assert await found_dominion(ctx, company, row, tally)
    dominion = await realm.session.scalar(select(PolityProfileRow).where(PolityProfileRow.core_entity_id == far.id))
    assert dominion is not None and tally.dominions == 1
    assert company.status is not EntityStatus.CANON
    assert await realm.session.get(OccupationRow, far.location_id) is None


async def order_of(realm: Realm) -> tuple[EntityRow, HolyOrderProfileRow, EntityRow, EntityRow]:
    keep = await settlement(realm, "Wardenhold")
    god = await son(realm.session, "Ilmar", realm.world.id)
    cult = await make(
        realm.session, "Choir of Ilmar", EntityType.CULT, CultStats(followers=500, zeal=50, influence=50), world_id=realm.world.id, location_id=keep.id
    )
    await link(realm.session, cult.id, god.id, BondKind.WORSHIPS)
    await link(realm.session, keep.id, god.id, BondKind.WORSHIPS)
    order = await make(
        realm.session,
        "the Holy Order of Ilmar",
        EntityType.FACTION,
        FactionStats(strength=40, wealth=20, sway=10),
        world_id=realm.world.id,
        location_id=keep.id,
    )
    row = HolyOrderProfileRow(faction_entity_id=order.id, cult_entity_id=cult.id, fortress_entity_id=keep.id, tithe_share=10, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    return order, row, cult, keep


async def test_warriors_of_the_faith_take_the_vows_of_its_holy_order(realm: Realm) -> None:
    ctx = context(realm.session, tuned(holy_orders={"recruit_pct": 100}))
    order, row, cult, keep = await order_of(realm)
    knight = await mortal(realm, "Jory", location_id=keep.id)
    knight.social_class = SocialClass.WARRIOR
    await link(realm.session, knight.id, cult.id, BondKind.MEMBER_OF)
    tally = OrderTally()
    await take_vows(ctx, order, row, cult, tally)
    assert tally.sworn == 1 and await bonded(realm.session, knight.id, order.id, BondKind.MEMBER_OF)


async def test_a_holy_order_rides_to_its_faith_s_holy_war(realm: Realm) -> None:
    ctx = context(realm.session, tuned(holy_orders={"host_per_strength": 5}))
    order, row, cult, keep = await order_of(realm)
    faithful = await settlement(realm, "Kellmoor")
    heathen = await settlement(realm, "Lorn")
    god = await patron_node(realm.session, cult)
    assert god is not None
    await link(realm.session, faithful.id, god, BondKind.WORSHIPS)
    event = await make(realm.session, "War of the Faith", EntityType.EVENT, EventStats(), world_id=realm.world.id)
    war = WarRow(event_entity_id=event.id, world_id=realm.world.id, cause=WarCause.HOLY_WAR, started_epoch=1)
    realm.session.add(war)
    await realm.session.flush()
    realm.session.add(WarSideRow(war_id=war.id, entity_id=faithful.id, side=WarSide.DEFENDER, joined_epoch=1))
    realm.session.add(WarSideRow(war_id=war.id, entity_id=heathen.id, side=WarSide.ATTACKER, joined_epoch=1))
    await realm.session.flush()
    tally = OrderTally()
    await serve_holy_wars(ctx, order, row, cult, tally)
    joined = await realm.session.get(WarSideRow, (war.id, keep.id))
    host = await realm.session.scalar(select(ArmyRow).where(ArmyRow.war_id == war.id, ArmyRow.owner_entity_id == keep.id))
    assert tally.hosts == 1 and joined is not None and joined.side is WarSide.DEFENDER and host is not None
    await serve_holy_wars(ctx, order, row, cult, tally)
    assert tally.hosts == 1
