from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.departures import DepartureCondition, DepartureKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.governance import GoverningBody
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.departures.book import DepartureTally, Seat
from aerona.engine.departures.leave import leave
from aerona.engine.departures.returns import return_to, tend_departed
from aerona.engine.departures.weigh import weigh, weigh_seats
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat_or
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def realm_with(
    session: AsyncSession, world: CoreWorld, kind: OfficeKind, *, age: int = 40, treasury: int = 500
) -> tuple[EntityRow, OfficeRow, EntityRow]:
    town = await settlement(session, "Seatholm", world, world.regions[0], population=3000)
    realm = await entity(session, "The Seated Crown", EntityType.POLITY, PolityStats(stability=60), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=realm.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            core_entity_id=town.id,
            capital_entity_id=town.id,
            treasury=treasury,
            stability=60,
        )
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    holder = await mortal(session, "Ilsa Venn", world, town.id)
    set_stats(holder, age=age)
    office = OfficeRow(polity_entity_id=realm.id, kind=kind, holder_entity_id=holder.id, since_epoch=0, powers=[])
    session.add(office)
    await session.flush()
    return realm, office, holder


async def test_an_abdication_hands_rule_to_the_chosen_heir_and_keeps_standing(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _realm, office, holder = await realm_with(session, world, OfficeKind.RULER)
    heir = await mortal(session, "Tamsin Venn", world, holder.location_id)
    row = await leave(ctx, Seat(holder, office, None), DepartureKind.ABDICATION, heir=heir.id, conditions=[DepartureCondition.KEEP_TITLE], why="by choice")
    assert office.holder_entity_id == heir.id and row.in_favour_of_node_id == heir.id and row.standing > 0
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "office.abdicated")) is not None


async def test_a_scandal_weighs_toward_resignation_and_custom_retires_the_old(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "weigh", tuned_rules())
    _realm, office, holder = await realm_with(session, world, OfficeKind.TREASURER, age=70)
    seat = Seat(holder, office, None)
    weight, kind, customary = await weigh(ctx, seat)
    assert kind is DepartureKind.RETIREMENT and customary and weight > 0
    session.add(CrimeCaseRow(settlement_entity_id=holder.location_id, crime=next(iter(CrimeKind)), accused_entity_id=holder.id, opened_epoch=ctx.epoch))
    await session.flush()
    _weight, kind, _customary = await weigh(ctx, seat)
    assert kind is DepartureKind.RESIGNATION


async def test_custom_retires_an_old_official_with_a_pension_the_realm_pays(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "retire", tuned_rules())
    _realm, office, holder = await realm_with(session, world, OfficeKind.TREASURER, age=70)
    tally = DepartureTally()
    await weigh_seats(ctx, tally)
    row = await session.scalar(select(DepartureRow).where(DepartureRow.holder_node_id == holder.id))
    assert tally.left == 1 and row is not None and row.kind is DepartureKind.RETIREMENT and office.holder_entity_id is None
    await tend_departed(ctx, tally)
    assert tally.pensions == 1


async def test_one_who_resigned_comes_back_to_an_empty_office(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "return", tuned_rules(departures={"return_chance_pct": 100}))
    _realm, office, holder = await realm_with(session, world, OfficeKind.TREASURER)
    row = await leave(ctx, Seat(holder, office, None), DepartureKind.RESIGNATION, heir=None, conditions=[], why="a scandal")
    assert office.holder_entity_id is None
    tally = DepartureTally()
    await tend_departed(ctx, tally)
    assert tally.returned == 1 and office.holder_entity_id == holder.id and row.returned_epoch == ctx.epoch
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "office.returned")) is not None


async def test_an_abdicated_ruler_with_standing_rallies_against_the_realm(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "rally", tuned_rules(departures={"return_chance_pct": 0}))
    realm, office, holder = await realm_with(session, world, OfficeKind.RULER)
    heir = await mortal(session, "Orrin Venn", world, holder.location_id)
    row = await leave(ctx, Seat(holder, office, None), DepartureKind.ABDICATION, heir=heir.id, conditions=[], why="by choice")
    row.standing = 90
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None
    before = profile.stability
    tally = DepartureTally()
    await tend_departed(ctx, tally)
    assert tally.rallies == 1 and profile.stability == before - ctx.rules.departures.rally_stability_loss
    assert await return_to(ctx, row, holder) is True and office.holder_entity_id == holder.id


async def test_the_head_of_an_organisation_steps_down_and_the_record_names_the_seat(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Headford", world, world.regions[0])
    head = await mortal(session, "Brannoc Hale", world, town.id)
    org = await entity(session, "The Hale Company", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    row = OrgGovernanceRow(org_node_id=org.id, decision_body=GoverningBody.ASSEMBLY_OF_MEMBERS, head_node_id=head.id, locked=[])
    session.add(row)
    await session.flush()
    left = await leave(ctx, Seat(head, None, row), DepartureKind.RETIREMENT, heir=None, conditions=[], why="age")
    assert row.head_node_id is None and left.org_node_id == org.id and left.office_id is None
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "office.retired")) is not None


async def test_years_held_count_the_holders_own_tenure_not_the_successors(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _realm, office, holder = await realm_with(session, world, OfficeKind.RULER)
    heir = await mortal(session, "Wren Venn", world, holder.location_id)
    row = await leave(ctx, Seat(holder, office, None), DepartureKind.ABDICATION, heir=heir.id, conditions=[], why="by choice")
    assert row.years_held == min(ctx.epoch * ctx.rules.time.years_per_epoch, stat_or(holder, "age", 0)) > 0
    assert office.holder_entity_id == heir.id and office.since_epoch == ctx.epoch
