import pytest
from sqlalchemy import select

from aerona.cartography.model import ElevationClass
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.climate import ClimateOrderRow
from aerona.db.tables.entities import EntityFlagRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.society import Commodity, KnowledgeBranch, NaturalLaw
from aerona.domain.enums.world import ClimateEra, WorldType
from aerona.domain.models.entity_stats import CultStats, PlaceStats, StructureStats
from aerona.engine.environment.profile import Geography, Surroundings, rainfall_of, temperature_of
from aerona.engine.phases.climate import climate_of, climate_transition, impose_climate, law_fertility
from aerona.engine.phases.disasters import apply_disaster, joined_names, natural_disasters, record_disaster_event, send_disaster
from aerona.engine.phases.society_economy import set_stores
from aerona.engine.primitives.modifiers import ModifierIndex, live_modifiers
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import (
    Realm,
    bonded,
    chronicle_keys,
    context,
    knowledge,
    link,
    make,
    mortal,
    named,
    natural_law,
    region_record,
    settlement,
    store_map,
    trade_route,
    tuned,
)

RULES = Rules()


GEOGRAPHY = Geography(
    biome_mix=[0] * 10, elevation_mean=20, roughness=20, latitude=30, moisture=50, base_forest=20, base_wetland=10, river_class=RiverClass.NONE
)


def around(era: ClimateEra | None, *, coastal: bool = False, highland: bool = False) -> Surroundings:
    return Surroundings(world_type=WorldType.ORDINARY, era=era, coastal=coastal, highland=highland)


def test_climate_ages_shift_temperature_and_rainfall() -> None:
    settings = RULES.climate_effects
    calm = rainfall_of(RULES, GEOGRAPHY, around(None))
    assert rainfall_of(RULES, GEOGRAPHY, around(ClimateEra.DROUGHT)) == calm + settings.drought_century_rain
    coastal = rainfall_of(RULES, GEOGRAPHY, around(None, coastal=True))
    assert rainfall_of(RULES, GEOGRAPHY, around(ClimateEra.RAIN, coastal=True)) == min(100, coastal + settings.rain_age_rain + settings.coast_rain_bonus)
    assert rainfall_of(RULES, GEOGRAPHY, around(ClimateEra.DROUGHT, coastal=True)) == coastal + round(
        settings.drought_century_rain / settings.coast_drought_divisor
    )
    warm = temperature_of(RULES, GEOGRAPHY, around(None, highland=True))
    assert temperature_of(RULES, GEOGRAPHY, around(ClimateEra.ICE_AGE, highland=True)) == warm + settings.ice_age_temperature - settings.mountain_ice_loss


def test_names_join_in_english() -> None:
    assert joined_names(["A"]) == "A"
    assert joined_names(["A", "B", "C"]) == "A, B and C"


async def test_first_climate_and_era_change(realm: Realm) -> None:
    rules = tuned(climate_effects={"first_duration": 0, "first_die": 1, "temperate_weight": 0})
    ctx = context(realm.session, rules)
    await climate_transition(ctx)
    world = realm.world
    assert world.climate_era is not ClimateEra.TEMPERATE
    assert world.climate_epochs_left is not None and world.climate_epochs_left > 0
    assert "climate.era" in await chronicle_keys(realm.session)
    state = await climate_of(realm.session, rules, world.id)
    assert state is not None and state.era is world.climate_era


async def test_imposed_climate_applies_once_more_at_transition(realm: Realm) -> None:
    ctx = context(realm.session)
    state = await impose_climate(ctx, realm.world.id, ClimateEra.ICE_AGE, 3)
    assert state.era is ClimateEra.ICE_AGE and state.population_loss_pct > 0
    town = await settlement(realm, "Frost", population=10000)
    await climate_transition(context(realm.session, epoch=4))
    assert await realm.session.get(ClimateOrderRow, realm.world.id) is None
    kept = 100 - RULES.climate_effects.ice_age_population_loss
    assert stat(town, "population") == round(round(10000 * kept / 100) * kept / 100)
    assert realm.world.climate_epochs_left == 2
    with pytest.raises(ValidationFailedError):
        await impose_climate(ctx, realm.world.id, ClimateEra.RAIN, 0)


async def test_laws_shift_land_fertility(realm: Realm) -> None:
    await natural_law(realm, "Plenty", NaturalLaw.BOUNTY)
    ctx = context(realm.session)
    await law_fertility(ctx)
    with live_modifiers(await ModifierIndex.load(realm.session, ctx.epoch), ctx.epoch, RULES):
        assert stat(realm.region, "fertility") == round(60 * (1 + RULES.climate_effects.bounty_law_fertility / 100))


async def test_disaster_effects_protection_and_collapse(realm: Realm) -> None:
    town = await settlement(realm, "Quake Town", population=10000)
    shrine = await make(realm.session, "Shrine", EntityType.STRUCTURE, StructureStats(durability=5), world_id=realm.world.id, location_id=town.id)
    sheltered = await settlement(realm, "Sheltered", population=10000)
    realm.session.add(EntityFlagRow(entity_id=sheltered.id, flag=EntityFlag.PROTECTED_FROM_DISASTER, epoch=1))
    await realm.session.flush()
    ctx = context(realm.session)
    impact = await apply_disaster(ctx, town, Disaster.EARTHQUAKE, 1.0)
    assert stat(town, "population") == 10000 - 10000 * RULES.intervention_effects.earthquake_population_loss // 100
    assert shrine.status is EntityStatus.DESTROYED
    assert any("collapsed" in note for note in impact.notes)
    guarded = await apply_disaster(ctx, sheltered, Disaster.PLAGUE, 1.0)
    assert stat(sheltered, "population") == 10000
    assert guarded.notes == ["Sheltered was protected"]


async def test_medicine_softens_plague(realm: Realm) -> None:
    healers = await settlement(realm, "Healers", population=10000)
    plain = await settlement(realm, "Plain", population=10000)
    cure = await knowledge(realm, "Cure", KnowledgeBranch.MEDICINE)
    await link(realm.session, healers.id, cure.id, BondKind.KNOWS)
    cult = await make(realm.session, "Pyre", EntityType.CULT, CultStats(followers=1000), world_id=realm.world.id, location_id=plain.id)
    ctx = context(realm.session)
    await apply_disaster(ctx, healers, Disaster.PLAGUE, 1.0)
    await apply_disaster(ctx, plain, Disaster.PLAGUE, 1.0)
    assert (stat(healers, "population") or 0) > (stat(plain, "population") or 0)
    assert stat(cult, "followers") == 1000 - 1000 * RULES.intervention_effects.plague_follower_loss // 100


async def test_mortals_can_perish(realm: Realm) -> None:
    town = await settlement(realm, "Flooded")
    victim = await mortal(realm, "Drowned", location_id=town.id)
    rules = tuned(intervention_effects={"flood_mortal_death_chance": 100})
    ctx = context(realm.session, rules)
    impact = await apply_disaster(ctx, town, Disaster.FLOOD, 1.0)
    assert victim.status is EntityStatus.DEAD
    assert impact.dead == [victim]
    event = await record_disaster_event(ctx, town, Disaster.FLOOD, 80, impact)
    assert victim.death_event_entity_id == event.id


async def test_region_disasters_need_terrain(realm: Realm) -> None:
    await store_map(
        realm.session,
        realm.world.id,
        [region_record(realm.region.id, neighbours=[], elevation=ElevationClass.MOUNTAINOUS), region_record(realm.far_region.id, neighbours=[], coastal=True)],
    )
    ctx = context(realm.session, tuned(disasters={"earthquake_chance": 100, "flood_chance": 100, "cap": 5}))
    await natural_disasters(ctx)
    events = await named(realm.session, EntityType.EVENT)
    kinds = {event.engine_kind for event in events}
    assert {EngineKind.EARTHQUAKE, EngineKind.FLOOD} <= kinds
    for event in events:
        assert await realm.session.get(EntityFlagRow, (event.id, EntityFlag.DISASTER)) is not None


async def test_city_plague_and_spread(realm: Realm) -> None:
    city = await settlement(realm, "Crowded", population=50000)
    partner = await settlement(realm, "Partner", population=2000, location_id=realm.far_region.id)
    await trade_route(realm, city, partner)
    ctx = context(
        realm.session,
        tuned(
            disasters={"city_plague_chance": 100, "plague_spread_chance": 100},
            epidemiology={"crowd_population": 1000, "route_spread_chance": 100, "route_volume_floor_pct": 100},
        ),
    )
    await set_stores(ctx, city.id, {Commodity.FOOD: 100})
    await natural_disasters(ctx)
    plagues = [event for event in await named(realm.session, EntityType.EVENT) if event.engine_kind is EngineKind.PLAGUE]
    assert len(plagues) == 1
    assert await bonded(realm.session, plagues[0].id, partner.id, BondKind.CAUSED)
    keys = await chronicle_keys(realm.session)
    assert "disasters.city_plague" in keys
    assert "disasters.plague_spread" in keys


async def test_manual_disaster_validates_target(realm: Realm) -> None:
    ctx = context(realm.session)
    event = await send_disaster(ctx, realm.region.id, Disaster.STORM, 50)
    assert event.engine_kind is EngineKind.STORM
    place = await make(realm.session, "Glade", EntityType.PLACE, PlaceStats(fertility=40), world_id=realm.world.id, location_id=realm.region.id)
    await send_disaster(ctx, place.id, Disaster.DROUGHT, 70)
    assert (stat(place, "fertility") or 0) < 40
    lore = await knowledge(realm, "Nothing", KnowledgeBranch.TRADE)
    with pytest.raises(ValidationFailedError):
        await send_disaster(ctx, lore.id, Disaster.FLOOD)
    events = list(await realm.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DISASTER)))
    assert len(events) == 2
