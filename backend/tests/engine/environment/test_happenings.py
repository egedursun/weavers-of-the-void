from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.happenings import EventCasualtyRow, EventFootprintRow, EventProfileRow, RegionGeomorphRow, RiverShiftRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, SexKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind, SoilKind, TerrainKind
from aerona.domain.enums.happening import EventPhase, RiverShiftCause
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.settlement import SizeTier, TreasuryEntry
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.environment.geomorph import reshape, shift_river
from aerona.engine.happenings.backfill import CASUALTIES_FIXUP, backfill_casualties, lives_in
from aerona.engine.happenings.control import EventDraft, create_event, set_phase
from aerona.engine.happenings.emergence import emerge
from aerona.engine.happenings.profile import cohort_split, toll_of
from aerona.engine.happenings.progression import advance, ensure_profiles
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.phases.disasters import region_candidates, strike
from aerona.engine.phases.environment import environment_derive, environment_survey
from aerona.engine.phases.remembrance import disaster_toll, plain_name
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.environment.test_environment import surveyed
from tests.engine.society.factories import Realm, context, make, settlement, tuned

RULES = Rules()


async def cohorts(realm: Realm, town: EntityRow) -> None:
    for age, count in ((AgeBand.INFANT, 200), (AgeBand.CHILD, 600), (AgeBand.YOUTH, 400), (AgeBand.ADULT, 1200), (AgeBand.ELDER, 500), (AgeBand.ANCIENT, 100)):
        for sex in SexKind:
            realm.session.add(
                CohortRow(
                    community_entity_id=town.id,
                    age_band=age,
                    sex_kind=sex,
                    social_class=SocialClass.FARMER,
                    condition=CohortCondition.NONE,
                    count=count // 2,
                    generation_epoch=1,
                )
            )
    await realm.session.flush()


async def test_a_great_flood_moves_the_river_and_the_new_course_survives_the_survey(realm: Realm) -> None:
    ground = await surveyed(realm, river=RiverClass.GREAT_RIVER)
    far = await realm.session.get(type(ground), realm.far_region.id)
    assert far is not None
    rules = tuned(RULES, geomorphology={"river_shift_chance": 100, "river_shift_severity": 10})
    ctx = context(realm.session, rules)
    await strike(ctx, realm.region, Disaster.FLOOD, 90)
    shift = await realm.session.scalar(select(RiverShiftRow))
    assert shift is not None and shift.cause is RiverShiftCause.FLOOD and shift.to_region_id == realm.far_region.id
    assert ground.river_class is RiverClass.STREAM and far.river_class is RiverClass.GREAT_RIVER
    await environment_survey(context(realm.session, rules))
    assert ground.river_class is RiverClass.STREAM and far.river_class is RiverClass.GREAT_RIVER


async def test_a_held_river_does_not_move(realm: Realm) -> None:
    ground = await surveyed(realm)
    ground.locked = ["river_class"]
    assert await shift_river(context(realm.session), realm.region.id, None, RiverShiftCause.PLAYER) is None


async def test_drought_and_overgrazing_turn_a_land_to_desert_and_rest_brings_it_back(realm: Realm) -> None:
    ground = await surveyed(realm)
    ground.locked = ["rainfall"]
    ground.rainfall, ground.grazed = 10, 80
    for epoch in range(3, 12):
        await reshape(context(realm.session, epoch=epoch))
    shape = await realm.session.get(RegionGeomorphRow, realm.region.id)
    assert shape is not None and shape.desertified
    assert ground.soil in (SoilKind.SAND, SoilKind.SALINE)
    ground.locked = []
    await environment_derive(context(realm.session, epoch=12))
    assert ground.dominant_terrain is TerrainKind.DESERT
    ground.locked = ["rainfall"]
    ground.rainfall, ground.grazed = 60, 0
    for epoch in range(13, 30):
        await reshape(context(realm.session, epoch=epoch))
    assert not shape.desertified and ground.soil not in (SoilKind.SAND, SoilKind.SALINE)


async def test_salted_earth_turns_the_soil_to_salt(realm: Realm) -> None:
    ground = await surveyed(realm)
    ground.scars = {ScarKind.MADE_BARREN.value: 80}
    await reshape(context(realm.session))
    assert ground.soil is SoilKind.SALINE
    ground.scars = {}
    await reshape(context(realm.session, epoch=4))
    assert ground.soil is not SoilKind.SALINE


async def test_an_eruption_buries_the_land_in_ash_that_weathers_into_volcanic_soil(realm: Realm) -> None:
    ground = await surveyed(realm)
    event, _ = await strike(context(realm.session), realm.region, Disaster.ERUPTION, 80)
    assert event.engine_kind is EngineKind.ERUPTION and ground.soil is SoilKind.TEPHRA
    assert ground.scars.get(ScarKind.BURNED.value, 0) > 0
    shape = await realm.session.get(RegionGeomorphRow, realm.region.id)
    assert shape is not None and shape.last_eruption_epoch == 3
    await reshape(context(realm.session, epoch=3 + RULES.geomorphology.ash_weathering_epochs))
    assert ground.soil is SoilKind.VOLCANIC


async def test_a_volcanic_land_quakes_volcanically_and_can_erupt(realm: Realm) -> None:
    ground = await surveyed(realm)
    ground.dominant_terrain = TerrainKind.VOLCANIC
    await reshape(context(realm.session))
    shape = await realm.session.get(RegionGeomorphRow, realm.region.id)
    assert shape is not None and shape.volcanic and shape.volcanic_pressure > 0
    candidates = dict(
        region_candidates(context(realm.session), realm.region, await RegionAtlas.load(realm.session), 0, LawBook({}), ground=ground, shape=shape)
    )
    assert Disaster.VOLCANIC_QUAKE in candidates and Disaster.ERUPTION in candidates and Disaster.EARTHQUAKE not in candidates


async def test_disaster_losses_are_recorded_by_cohort_and_read_by_remembrance(realm: Realm) -> None:
    await surveyed(realm)
    town = await settlement(realm, "Ashmere", population=6000)
    await cohorts(realm, town)
    ctx = context(realm.session)
    event, impact = await strike(ctx, town, Disaster.EARTHQUAKE, 90)
    lost = impact.losses.get(town.id) or 0
    rows = list(await realm.session.scalars(select(EventCasualtyRow).where(EventCasualtyRow.event_entity_id == event.id)))
    assert lost > 0 and sum(row.count for row in rows) == lost
    assert {row.age_band for row in rows} == set(AgeBand)
    toll, struck = await disaster_toll(ctx, event)
    assert toll == lost and town in struck
    assert await realm.session.get(EventProfileRow, event.id) is not None


def test_plague_kills_more_elders_than_adults() -> None:
    rows = {
        (age, SexKind.BEGETTER, SocialClass.FARMER, CohortCondition.NONE): CohortRow(
            community_entity_id=1,
            age_band=age,
            sex_kind=SexKind.BEGETTER,
            social_class=SocialClass.FARMER,
            condition=CohortCondition.NONE,
            count=1000,
            generation_epoch=1,
        )
        for age in AgeBand
    }
    split = cohort_split(rows, FlowCategory.PLAGUE, 300, {})
    assert sum(split.values()) == 300
    elders = split[(AgeBand.ELDER, SexKind.BEGETTER, SocialClass.FARMER, CohortCondition.NONE)]
    adults = split[(AgeBand.ADULT, SexKind.BEGETTER, SocialClass.FARMER, CohortCondition.NONE)]
    assert elders > adults
    assert all(row.count == 1000 for row in rows.values())


async def test_a_famine_deepens_kills_at_its_height_and_leaves_sickness_behind(realm: Realm) -> None:
    ground = await surveyed(realm)
    town = await settlement(realm, "Greyfield", population=5000)
    await cohorts(realm, town)
    ground.harvest_pct = 40
    ctx = context(realm.session, epoch=3)
    event, profile = await create_event(ctx, EventDraft(EngineKind.FAMINE, "the Long Hunger", realm.region.id, 60))
    atlas = await RegionAtlas.load(realm.session)
    await advance(context(realm.session, epoch=4), atlas)
    assert profile.phase is EventPhase.PEAK
    peak = list(
        await realm.session.scalars(select(EventCasualtyRow).where(EventCasualtyRow.event_entity_id == event.id, EventCasualtyRow.phase == EventPhase.PEAK))
    )
    assert sum(row.count for row in peak) > 0
    ground.harvest_pct = 100
    await advance(context(realm.session, epoch=5), atlas)
    assert profile.phase is EventPhase.AFTERMATH and ground.scars.get(ScarKind.PLAGUE_GROUND.value, 0) > 0
    await advance(context(realm.session, epoch=6), atlas)
    assert profile.end_epoch == 6 and profile.end_year is not None and profile.end_year >= (profile.start_year or 0)


async def test_a_held_phase_does_not_turn(realm: Realm) -> None:
    ground = await surveyed(realm)
    ground.harvest_pct = 100
    ctx = context(realm.session)
    event, profile = await create_event(ctx, EventDraft(EngineKind.FAMINE, "the Held Hunger", realm.region.id, 50))
    await set_phase(ctx, event.id, EventPhase.PEAK, held=True)
    await advance(context(realm.session, epoch=7), await RegionAtlas.load(realm.session))
    assert profile.phase is EventPhase.PEAK and "phase" in profile.locked


async def test_old_events_gain_profiles_and_footprints_as_if_always(realm: Realm) -> None:
    await surveyed(realm)
    old = await make(
        realm.session,
        "the Old Storm",
        EntityType.EVENT,
        EventStats(severity=40),
        world_id=realm.world.id,
        location_id=realm.region.id,
        engine_kind=EngineKind.STORM,
    )
    counts = await ensure_profiles(context(realm.session, epoch=9), await RegionAtlas.load(realm.session))
    profile = await realm.session.get(EventProfileRow, old.id)
    footprint = list(await realm.session.scalars(select(EventFootprintRow.region_entity_id).where(EventFootprintRow.event_entity_id == old.id)))
    assert counts["backfilled"] == 1 and profile is not None and profile.end_epoch == profile.start_epoch == 1
    assert footprint == [realm.region.id]


async def test_old_casualty_records_are_read_once(realm: Realm) -> None:
    await surveyed(realm)
    town = await settlement(realm, "Oldtown")
    event = await make(
        realm.session,
        "the Old Quake",
        EntityType.EVENT,
        EventStats(severity=40),
        world_id=realm.world.id,
        location_id=realm.region.id,
        engine_kind=EngineKind.EARTHQUAKE,
    )
    await BondRepository(realm.session).connect(BondDraft(event.id, town.id, BondKind.CAUSED, 1, "120 lives lost"))
    assert lives_in("120 lives lost") == 120 and lives_in("struck") == 0
    assert await backfill_casualties(context(realm.session)) == 120
    assert await toll_of(realm.session, event.id) == 120
    assert await realm.session.get(AppliedFixupRow, CASUALTIES_FIXUP) is not None
    assert await backfill_casualties(context(realm.session)) == 0


async def test_festivals_and_riots_rise_from_the_life_of_towns(realm: Realm) -> None:
    await surveyed(realm)
    town = await settlement(realm, "Brightwater", population=9000)
    angry = await settlement(realm, "Smokeford", population=4000)
    await cohorts(realm, angry)
    realm.session.add(SettlementTreasuryRow(settlement_entity_id=town.id, epoch=3, entry=TreasuryEntry.FESTIVAL, amount=-10, balance=0))
    realm.session.add(SettlementProfileRow(settlement_entity_id=angry.id, size_tier=SizeTier.TOWN, unrest=90))
    await realm.session.flush()
    counts = await emerge(context(realm.session), await RegionAtlas.load(realm.session))
    assert counts["festivals"] == 1 and counts["riots"] == 1
    kinds = set(await realm.session.scalars(select(EntityRow.engine_kind).where(EntityRow.entity_type == EntityType.EVENT)))
    assert {EngineKind.FESTIVAL_OF_NOTE, EngineKind.RIOT} <= kinds
    profile = await realm.session.get(SettlementProfileRow, angry.id)
    assert profile is not None and profile.unrest == 90 - RULES.events.riot_unrest_vent
    assert (stat(angry, "population") or 0) < 4000
    again = await emerge(context(realm.session), await RegionAtlas.load(realm.session))
    assert again["festivals"] == 0 and again["riots"] == 0


def test_plain_names_lose_their_epoch_mark() -> None:
    assert plain_name("Ashmere Flood (Epoch 12)") == "Ashmere Flood"
    assert plain_name("the (Epoch x) thing") == "the (Epoch x) thing"
