from types import SimpleNamespace
from typing import cast

from aerona.cartography.biomes import Biome
from aerona.catalog.anatomy import ANATOMIES
from aerona.catalog.beast_tempers import TEMPERAMENTS
from aerona.catalog.disease_agents import AGENTS, CURES
from aerona.catalog.evolution import TROPHIC_ORDER, trophic_level
from aerona.catalog.harm_kinds import DAMAGE
from aerona.catalog.movement import BODY_MODES
from aerona.catalog.planetary_cycles import CYCLES, SCALES
from aerona.catalog.seals import SEALS
from aerona.catalog.spread_paths import SPREAD_PATHS
from aerona.catalog.transmission import ROUTES
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.agrarian import CommonsRule, LandUseRing, PerennialKind
from aerona.domain.enums.body import BodyPart, BodyPlan, DamageType
from aerona.domain.enums.climes import CirculationBand
from aerona.domain.enums.couplings import SealKind
from aerona.domain.enums.crafts import CatchGround
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent
from aerona.domain.enums.ecology import Aversion, AwakeningTrigger, Diet, SizeClass, Sociality, Temperament
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import CoastKind, MovementMode, RiverClass, TemperatureBand, TerrainKind
from aerona.domain.enums.evolution import PlanetaryCycle, TrophicLevel
from aerona.domain.enums.geology import RockKind, UndergroundStratum
from aerona.domain.enums.nature import Thermoregulation
from aerona.domain.enums.water import CoastForm, SedimentCarrier, SedimentKind
from aerona.domain.enums.world import WorldType
from aerona.engine.agrarian.lands import kind_of, wear_share
from aerona.engine.agrarian.rings import worked_ring
from aerona.engine.climes.winds import local_band
from aerona.engine.context import TickContext
from aerona.engine.couplings.deep import SealLinks, missing_link
from aerona.engine.crafts.grounds import land_ground
from aerona.engine.ecology.anatomy import WARDS
from aerona.engine.ecology.beast_acts import TRIGGERS
from aerona.engine.environment.geology import Layer, strata_for
from aerona.engine.nature.seasons import activity
from aerona.engine.water.ice import carried_by, coast_form, sediment_kind
from aerona.rules.registry import Rules

RULES = Rules()


def land(**values: object) -> RegionEnvironmentRow:
    base: dict[str, object] = {
        "dominant_terrain": TerrainKind.PLAIN,
        "coast_kind": CoastKind.NONE,
        "river_class": RiverClass.NONE,
        "temperature": 50,
        "temperature_band": TemperatureBand.TEMPERATE,
        "wetland": 0,
        "mined": 0,
        "roughness": 0,
        "forest_cover": 0,
        "farmed": 0,
        "soil_fertility": 50,
        "latitude": 0,
        "biome_mix": [],
    }
    base.update(values)
    return RegionEnvironmentRow(**base)


def test_ice_grinds_rock_flour_into_rivers_and_mines_carry_their_waste() -> None:
    assert sediment_kind(land(), land(river_class=RiverClass.RIVER), SedimentCarrier.ICE) is SedimentKind.GLACIAL_FLOUR
    assert (
        carried_by(RULES.water_and_ice, land(mined=RULES.sediment.tailings_mined), RULES.environment.frozen_below, RULES.sediment.tailings_mined)[0]
        is SedimentCarrier.WORKS
    )


def test_a_reef_island_rings_a_lagoon_as_an_atoll() -> None:
    assert coast_form(land(dominant_terrain=TerrainKind.ISLAND, coast_kind=CoastKind.REEF)) is CoastForm.ATOLL


def test_perennials_follow_the_warmth_and_use_of_their_land() -> None:
    assert kind_of({CommodityKind.FRUIT}, land(temperature_band=TemperatureBand.HOT), 50) is PerennialKind.PALM_STAND
    assert kind_of({CommodityKind.TIMBER}, land(forest_cover=10), 50) is PerennialKind.COPPICE
    assert kind_of(set(), land(farmed=70), 50) is PerennialKind.HEDGEROW


def test_a_common_taken_in_turns_wears_less_than_one_open_to_all() -> None:
    ctx = cast(TickContext, SimpleNamespace(rules=RULES))
    assert wear_share(ctx, CommonsRule.ROTATIONAL) < wear_share(ctx, CommonsRule.OPEN)


def test_mines_take_land_for_works_and_worn_grain_land_rests_fallow() -> None:
    ctx = cast(TickContext, SimpleNamespace(rules=RULES))
    assert worked_ring(ctx, land(mined=5), LandUseRing.GRAIN) is LandUseRing.INDUSTRY
    assert worked_ring(ctx, land(soil_fertility=10), LandUseRing.GRAIN) is LandUseRing.FALLOW


def test_nesting_birds_give_eggs_and_insects_give_their_nests() -> None:
    assert land_ground(SpeciesProfileRow(body_plan=BodyPlan.INSECTOID, sociality=Sociality.HIVE), fowling=False, large=False) is CatchGround.INSECT_GATHERING
    assert land_ground(SpeciesProfileRow(body_plan=BodyPlan.AVIAN, sociality=Sociality.COLONY), fowling=True, large=False) is CatchGround.EGG_GATHERING


def test_slopes_take_slope_winds_and_warm_coasts_take_the_monsoon() -> None:
    highland = [0] * len(Biome)
    highland[list(Biome).index(Biome.MOUNTAINS)] = 100
    assert local_band(RULES, CirculationBand.WESTERLY, land(biome_mix=highland)) is CirculationBand.MOUNTAIN_WIND
    assert local_band(RULES, CirculationBand.TRADE, land(coast_kind=CoastKind.BEACH, latitude=20)) is CirculationBand.MONSOON


def test_inner_heat_cools_and_ice_lowers_the_seas() -> None:
    assert CYCLES[PlanetaryCycle.HEAT].cools and CYCLES[PlanetaryCycle.ICE].inverse
    assert set(SCALES) == set(PlanetaryCycle)


def test_cold_ground_lies_frozen_and_moving_plates_lie_over_faults() -> None:
    physics = WorldPhysicsRow(tectonics=90, volcanism=0, hydrosphere=0)
    found = {
        under.stratum for under in strata_for(RULES, [Layer(RockKind.GRANITE, 25)], physics, WorldType.ORDINARY, underworld=False, rough=True, frozen=True)
    }
    assert {UndergroundStratum.PERMAFROST_LAYER, UndergroundStratum.FAULT_ZONE} <= found


def test_a_made_seal_names_the_mind_that_keeps_it() -> None:
    assert SEALS[SealKind.MADE].link is not None
    assert missing_link(SealKind.MADE, SealLinks()) == "made mind"
    assert missing_link(SealKind.MADE, SealLinks(mind_id=1)) is None


def test_parasites_stand_on_their_own_level_and_fixers_feed_the_soil() -> None:
    assert trophic_level(Diet.PARASITE, SizeClass.TINY) is TrophicLevel.PARASITE
    assert TrophicLevel.PARASITE not in TROPHIC_ORDER


def test_sickness_of_the_line_never_spreads_and_herds_carry_sickness() -> None:
    assert not AGENTS[DiseaseAgent.HEREDITARY].spreads and not AGENTS[DiseaseAgent.AUTOIMMUNE].spreads
    assert SPREAD_PATHS[SpreadPath.LIVESTOCK].chance is not None and SPREAD_PATHS[SpreadPath.WATER_SUPPLY].chance is not None
    assert ROUTES[Transmission.SOIL].disease and CURES[CureClass.IMMUNISATION].level is not None


def test_six_limbed_bodies_climb_and_rooted_bodies_hold_by_their_roots() -> None:
    assert MovementMode.CLIMBING in BODY_MODES[BodyPlan.HEXAPOD]
    assert BodyPart.ROOTS in {part.key for part in ANATOMIES[BodyPlan.ROOTED].parts}
    assert DAMAGE[DamageType.PRESSURE].breathing


def test_proud_beasts_are_honoured_and_new_wards_and_wakings_are_read() -> None:
    assert TEMPERAMENTS[Temperament.PROUD].honoured and TEMPERAMENTS[Temperament.PLAYFUL].befriends
    assert Aversion.TRUE_NAME in WARDS and AwakeningTrigger.KIN_HARMED in TRIGGERS


def test_a_warm_core_spends_less_in_the_cold_than_it_would_idle() -> None:
    assert activity(RULES, Thermoregulation.MESOTHERM, TemperatureBand.COLD) == RULES.dormancy.mesotherm_food_pct / 100
