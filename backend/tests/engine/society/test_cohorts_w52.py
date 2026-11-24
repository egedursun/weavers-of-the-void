from aerona.agents.context.thin_b_lines import class_change_lines, mortal_depth_lines
from aerona.catalog.life.demography import AGE_BANDS, AGE_ORDER, EMERGING_CONDITIONS, GROWN_BANDS, MINOR_BANDS, NEW_TRADES
from aerona.catalog.mobility import MOBILITY_EVENTS
from aerona.db.tables.demography import CohortRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, Job, SexKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import MobilityEvent
from aerona.engine.demography.cohorts import band_years, orphan, pyramid, settle_displaced
from aerona.engine.demography.events import log_event
from aerona.engine.demography.labour import jobs_for
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, settlement

RULES = Rules()


def test_five_bands_in_order_with_edges_from_life_stages() -> None:
    assert AGE_ORDER == (AgeBand.INFANT, AgeBand.CHILD, AgeBand.YOUTH, AgeBand.ADULT, AgeBand.ELDER, AgeBand.ANCIENT)
    assert {AgeBand.INFANT, AgeBand.CHILD} == MINOR_BANDS and AgeBand.YOUTH in GROWN_BANDS
    assert band_years(AgeBand.INFANT, (18, 40)) == 3 and band_years(AgeBand.ADULT, (18, 40)) == 40
    assert abs(sum(pyramid(RULES).values()) - 1) < 1e-9 and set(pyramid(RULES)) == set(AgeBand)
    assert all(spec.label for spec in AGE_BANDS.values())


async def test_deaths_of_parents_leave_orphans_who_grow_out_of_it(realm: Realm) -> None:
    town = await settlement(realm, "Ash", population=1000)
    key = (AgeBand.CHILD, SexKind.BEARER, SocialClass.FARMER, CohortCondition.NONE)
    rows = {key: CohortRow(community_entity_id=town.id, age_band=key[0], sex_kind=key[1], social_class=key[2], condition=key[3], count=100, generation_epoch=0)}
    moved = orphan(realm.session, town, rows, 50, 100, epoch=3)
    assert moved == 50
    assert rows[(AgeBand.CHILD, SexKind.BEARER, SocialClass.FARMER, CohortCondition.ORPHANED)].count == 50
    assert {CohortCondition.ORPHANED, CohortCondition.DISPLACED, CohortCondition.INDEBTED} == EMERGING_CONDITIONS


async def test_the_displaced_settle_among_their_hosts(realm: Realm) -> None:
    town = await settlement(realm, "Haven", population=1000)
    key = (AgeBand.ADULT, SexKind.BEGETTER, SocialClass.FARMER, CohortCondition.DISPLACED)
    rows = {key: CohortRow(community_entity_id=town.id, age_band=key[0], sex_kind=key[1], social_class=key[2], condition=key[3], count=40, generation_epoch=0)}
    assert settle_displaced(realm.session, town, rows, 50, 3) == 20


def test_seventeen_kinds_of_work_and_seven_class_moves() -> None:
    assert len(Job) == 19 and set(NEW_TRADES) == {Job.TRANSPORT, Job.ADMINISTRATION, Job.GATHERING, Job.INDUSTRY, Job.ARTS}
    merchants = jobs_for(RULES, SocialClass.MERCHANT)
    assert abs(merchants[Job.TRANSPORT] - RULES.labour.transport_base_share / 100) < 1e-9 and abs(sum(merchants.values()) - 1) < 1e-9
    assert len(MOBILITY_EVENTS) == 9 and MOBILITY_EVENTS[MobilityEvent.ORDAINED].lands_in is SocialClass.PRIEST


async def test_a_mortal_is_told_how_its_standing_changed(realm: Realm) -> None:
    town = await settlement(realm, "Rise", population=500)
    climber = await mortal(realm, "Ivo", location_id=town.id)
    await log_event(context(realm.session, RULES), MobilityEvent.ENRICHED, community=town, count=1, mortal=climber)
    lines = await class_change_lines(realm.session, climber.id)
    assert lines == ["your standing changed in epoch 3: enriched"]
    assert any("enriched" in line for line in await mortal_depth_lines(realm.session, climber))
