from dataclasses import replace

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.names import NameRepository
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.customs import NamingCustomRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.governance import HeadSelection
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind, LifeStage
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import revised
from aerona.domain.models.moment import Moment
from aerona.engine.childhood.life import at_age
from aerona.engine.context import AgingState, TickContext
from aerona.engine.customs.naming import NamingTally, name_the_dead
from aerona.engine.demography.peoples import HUMAN_LIFESPAN, biology_for
from aerona.engine.departures.book import DepartureTally, Seat
from aerona.engine.departures.leave import tenure_years
from aerona.engine.departures.weigh import weigh_seats
from aerona.engine.governance.heads import candidates
from aerona.engine.lifecycle.wounds import injury_year
from aerona.engine.mortal.course import grow_into_stage
from aerona.engine.mortal.life import fertility_window, folk_lifespan, folk_span, sex_of_stats, years_to_step, young_through
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.phases.births import couples_bear_children
from aerona.engine.phases.mortals import mortal_aging
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.maturity import past_office_age
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.births import date_born
from aerona.engine.recording.scope import phase_moment
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement, tuned_rules

YEARS = 50
NEWCOMER_AGE = 29
NEWCOMER_ARRIVES = 31
NEWCOMER_SPAN = 400


async def folk_town(session: AsyncSession, world: CoreWorld) -> int:
    if "folk_town" not in world.extra:
        town = await settlement(session, "Folk Hold", world, world.regions[0])
        await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
        world.extra["folk_town"] = town
    return int(world.extra["folk_town"].id)


async def biology(session: AsyncSession, world: CoreWorld) -> PeopleBiologyRow:
    row = await session.get(PeopleBiologyRow, world.people.id)
    if row is None:
        row = biology_for(Rules(), world.people, HUMAN_LIFESPAN, None)
        session.add(row)
        await session.flush()
    return row


async def test_a_wound_with_no_happening_is_never_dated_before_its_bearer(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    bearer = await mortal(session, "Late Comer", world, world.regions[0].id)
    start = epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    date_born(session, bearer.id, Moment(start + 31))
    await session.flush()
    assert await injury_year(ctx, None, bearer.id) == start + 31


async def test_a_couples_births_fall_on_their_own_years_inside_the_fertile_window(session: AsyncSession, world: CoreWorld) -> None:
    base = tuned_rules(world_engine={"birth_chance": 100})
    rules = replace(base, fertility=replace(base.fertility, stillbirth_pct=0.0, twins_pct=0.0))
    ctx = await manual_context(session, "couples", rules)
    folk = await biology(session, world)
    first = await mortal(session, "Ana", world, await folk_town(session, world), age=20, lifespan=71)
    second = await mortal(session, "Bo", world, await folk_town(session, world), age=20, lifespan=71)
    await bond(session, first.id, second.id, BondKind.SPOUSE_OF)
    await couples_bear_children(ctx)
    born = (
        select(IncidentParticipantRow.node_id)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .where(IncidentRow.kind == "births.child", IncidentParticipantRow.role == IncidentRole.CHILD)
    )
    years = list(await session.scalars(select(NodeBirthRow.year).where(NodeBirthRow.node_id.in_(born)).order_by(NodeBirthRow.year)))
    assert len(years) >= 2
    assert len(set(years)) == len(years)
    start = epoch_start_year(ctx.epoch, rules.time.years_per_epoch)
    for parent in (first, second):
        low, high = fertility_window(rules, folk, sex_of_stats(parent), 71)
        assert all(low <= 20 + (year - start) < high + rules.fertility.birth_spacing_years for year in years)
    twins = await session.scalars(select(IncidentFactRow.key).where(IncidentFactRow.key == "twin"))
    assert list(twins) == []


def test_lifespans_of_the_born_follow_their_peoples_span(rules: Rules) -> None:
    folk = PeopleBiologyRow(maturity_years=16, adult_years=40, elder_years=15)
    life = rules.deep_life
    typical = folk_lifespan(folk, life.birth_lifespan_base, (life.birth_lifespan_die + 1) // 2, life.birth_lifespan_die)
    assert abs(typical - folk_span(folk, 0)) <= 1
    assert all(fertility_window(rules, folk, kind, 300)[1] <= max(folk_span(folk, 0), fertility_window(rules, folk, kind, 300)[0] + 1) for kind in SexKind)


async def test_a_stage_is_told_in_the_year_it_was_reached(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    grown_at = (await biology(session, world)).maturity_years
    youth = await mortal(session, "Grown Late", world, await folk_town(session, world), age=13, lifespan=71)
    profile, _ = await ensure_profile(session, youth.id, ctx.epoch)
    assert profile.life_stage is LifeStage.YOUTH
    youth.stats = revised(youth.stats, {"age": 30})
    await grow_into_stage(ctx, youth)
    told = await session.scalar(
        select(IncidentRow)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind == "life.adult", IncidentParticipantRow.node_id == youth.id)
    )
    assert told is not None
    end = epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch) + ctx.rules.time.years_per_epoch - 1
    assert told.year == end - (30 - grown_at)
    age = await session.scalar(select(IncidentFactRow.number).where(IncidentFactRow.incident_id == told.id, IncidentFactRow.key == "age"))
    assert age == grown_at


async def test_a_childhood_milestone_falls_at_the_age_it_marks(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    child = await mortal(session, "Small One", world, world.regions[0].id, age=0)
    start = epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    date_born(session, child.id, Moment(start + 5))
    await session.flush()
    moment = await at_age(ctx, child, 8)
    assert moment is not None and moment.year == start + 13


async def test_a_child_of_this_epoch_stays_out_of_grown_acts(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await biology(session, world)
    child = await mortal(session, "Newborn", world, await folk_town(session, world), age=18)
    grown = await mortal(session, "Elder Kin", world, await folk_town(session, world), age=70)
    assert await young_through(session, ctx.rules, ctx.epoch, [child, grown], aged=True) == {child.id}


async def test_a_profile_starts_at_its_true_stage(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await biology(session, world)
    young = await mortal(session, "Young One", world, await folk_town(session, world), age=5)
    profile, created = await ensure_profile(session, young.id, ctx.epoch)
    assert created and profile.life_stage is LifeStage.CHILD


async def test_a_disgraced_elder_leaves_for_the_scandal_and_the_years_held_come_from_the_record(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "departures", Rules())
    old = await mortal(session, "Old Head", world, world.regions[0].id, age=69, lifespan=70)
    org = OrgGovernanceRow(org_node_id=world.people.id, head_node_id=old.id, since_epoch=1, locked=[])
    session.add(org)
    session.add(CrimeCaseRow(crime=CrimeKind.THEFT, accused_entity_id=old.id, opened_epoch=ctx.epoch))
    start = epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    session.add(
        StateChangeRow(
            epoch=ctx.epoch,
            year=start + 2,
            table_name="org_governance",
            row_key=f'{{"org_node_id": {world.people.id}}}',
            node_id=world.people.id,
            operation=LedgerOperation.UPDATE,
            field="head_node_id",
            after_node_id=old.id,
            actor_kind=ActorKind.ENGINE,
        )
    )
    await session.flush()
    seat = Seat(old, None, org)
    assert await tenure_years(ctx, seat) == max(0, (phase_moment(ctx.environment).year or start) - (start + 2))
    await weigh_seats(ctx, DepartureTally())
    why = list(
        await session.scalars(
            select(IncidentFactRow.name)
            .join(IncidentRow, IncidentRow.id == IncidentFactRow.incident_id)
            .where(IncidentRow.kind == "office.resigned", IncidentFactRow.key == "why")
        )
    )
    assert why == ["a scandal"]


async def test_a_name_given_after_death_is_held_in_the_register(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Grave Town", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    dead = await mortal(session, "Living Name", world, town.id)
    dead.status, dead.end_epoch = EntityStatus.DEAD, ctx.epoch
    custom = NamingCustomRow(people_entity_id=world.people.id, posthumous_names=True, taboo_epochs=1, locked=[])
    await session.flush()
    await name_the_dead(ctx, Namer(session, ctx.rules), world.people, custom, NamingTally())
    assert dead.name != "Living Name"
    assert await NameRepository(session).owner(dead.name) == dead.id


async def test_office_age_is_judged_at_the_moment_the_step_acts(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    late = TickContext(replace(ctx.environment, step=0.9), session, "late")
    elder = await mortal(session, "Near Retirement", world, world.regions[0].id, age=40, lifespan=70)
    org = OrgGovernanceRow(org_node_id=world.people.id, head_selection=HeadSelection.SENIORITY, locked=[])
    session.add(org)
    session.add(FactionMembershipRow(faction_entity_id=world.people.id, mortal_entity_id=elder.id, joined_epoch=1, locked=[]))
    await session.flush()
    assert years_to_step(late.environment) >= ctx.rules.time.years_per_epoch * 8 // 10
    assert not past_office_age(ctx.rules, elder, years_to_step(ctx.environment))
    assert past_office_age(ctx.rules, elder, years_to_step(late.environment))
    assert elder.id not in {being.id for being in await candidates(late, org)}


async def test_a_mortal_still_a_child_this_epoch_is_never_chosen_to_head_a_body(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await biology(session, world)
    aged = TickContext(replace(ctx.environment, aging=AgingState(done=True)), session, "heads")
    young = await mortal(session, "Grown By Year End", world, await folk_town(session, world), age=18)
    elder = await mortal(session, "Long Grown", world, await folk_town(session, world), age=60)
    org = OrgGovernanceRow(org_node_id=world.people.id, head_selection=HeadSelection.ELECTED_BY_MEMBERS, locked=[])
    session.add(org)
    for member in (young, elder):
        session.add(FactionMembershipRow(faction_entity_id=world.people.id, mortal_entity_id=member.id, joined_epoch=1, locked=[]))
    await session.flush()
    chosen = {being.id for being in await candidates(aged, org)}
    assert elder.id in chosen and young.id not in chosen


async def test_a_grown_newcomer_of_this_epoch_ages_from_when_it_came_not_from_its_birth(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await biology(session, world)
    start = epoch_start_year(ctx.epoch, YEARS)
    came = start + NEWCOMER_ARRIVES
    newcomer = await mortal(session, "Late Captain", world, await folk_town(session, world), age=NEWCOMER_AGE, lifespan=NEWCOMER_SPAN)
    newcomer.birth_epoch = ctx.epoch
    await session.execute(delete(NodeBirthRow).where(NodeBirthRow.node_id == newcomer.id))
    date_born(session, newcomer.id, Moment(came - NEWCOMER_AGE))
    await session.flush()
    await mortal_aging(ctx)
    assert stat(newcomer, "age") == NEWCOMER_AGE + (start + YEARS - came)
