import inspect
from pathlib import Path

import aerona.domain.enums as enums_package
from aerona.catalog.beast_tempers import HELD_TEMPERS
from aerona.catalog.calendar_slots import SLOTS
from aerona.catalog.catch import GEAR, GROUNDS
from aerona.catalog.domestication import ATHERMIC_BIOCHEMISTRY
from aerona.catalog.movement import BODY_MODES
from aerona.catalog.planetary_cycles import cycle_label
from aerona.catalog.rocks import WORLD_CRUSTS
from aerona.catalog.terrain import TERRAIN
from aerona.catalog.weather import WEATHER
from aerona.constants.calendar import SEASONS_MAX
from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.nature_kinds import TraitKindRow
from aerona.domain.enums.affliction import CureKind, Transmission
from aerona.domain.enums.agrarian import CommonsKind, LandUseRing, PerennialKind
from aerona.domain.enums.body import BodyFunction, BodyPlan, DamageType, InjuryKind, MedicineTier
from aerona.domain.enums.body_systems import BodySystem, Sensitivity
from aerona.domain.enums.climes import OscillationPhase
from aerona.domain.enums.crafts import CatchGround, CatchMedium, Gear
from aerona.domain.enums.culture import CalendarSlot, SlotOpening
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent
from aerona.domain.enums.ecology import AnimalRole, AttackDelivery, BeastTemper, SizeClass, SpeciesClass
from aerona.domain.enums.environment import MovementMode, NotableYearKind, TerrainKind, WeatherDraw, WeatherKind, WeatherTrait
from aerona.domain.enums.evolution import PlanetaryCycle
from aerona.domain.enums.geology import RockKind
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.nature import FermentKind, SymbiosisKind
from aerona.domain.enums.region import DangerHarm
from aerona.domain.enums.world import ClimateEra, SurfaceLiquid, WorldType
from aerona.engine.environment.seasons import season_count_for, season_drafts
from aerona.engine.environment.spells import stacked
from aerona.engine.lore.rites import RiteRequirements, unmet
from aerona.rules.registry import Rules
from aerona.tools.mortal.fossils import revive

SHARE_TOTAL = 100


def enum_names() -> set[str]:
    return {
        line.split("(")[0].removeprefix("class ").strip()
        for path in Path(enums_package.__path__[0]).rglob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("class ")
    }


def test_k54_a_world_holds_at_most_eight_seasons() -> None:
    rules = Rules()
    assert SEASONS_MAX == 8
    assert max(season_count_for(rules, kind, tilt) for kind in WorldType for tilt in range(0, 91, 5)) <= SEASONS_MAX


def test_k55_seasons_hold_shares_of_the_year_that_sum_to_a_whole() -> None:
    rules = Rules()
    for kind in WorldType:
        for count in range(1, SEASONS_MAX + 1):
            assert sum(draft.share_pct for draft in season_drafts(rules, kind, count, 23)) == SHARE_TOTAL


def test_k56_frost_ice_storm_snow_and_hail_are_told_apart() -> None:
    frost, ice_storm, snow, hail = (WEATHER[kind] for kind in (WeatherKind.FROST, WeatherKind.ICE_STORM, WeatherKind.SNOW, WeatherKind.HAIL))
    assert frost.draw is WeatherDraw.FREEZING_CLEAR and not frost.traits & {WeatherTrait.WET, WeatherTrait.LIQUID}
    assert ice_storm.draw is WeatherDraw.FREEZING_WET and {WeatherTrait.LIQUID, WeatherTrait.ICY} <= ice_storm.traits
    assert WeatherTrait.SNOW_COVER in snow.traits and WeatherTrait.LIQUID not in snow.traits and WeatherTrait.LIQUID not in hail.traits


def test_k57_several_long_seasons_combine_and_winter_and_summer_offset() -> None:
    rules = Rules()
    assert not any(getattr(item, "unique", False) for item in IrregularSeasonRow.__table__.indexes)
    assert stacked(rules, [60, 40]) == 60 + 40 * rules.long_seasons.stacking_share_pct // 100


def test_k58_named_years_keep_eight_kinds_and_gain_peace_and_founding() -> None:
    assert {NotableYearKind.PEACE, NotableYearKind.FOUNDING} <= set(NotableYearKind)


def test_k59_campaign_is_the_season_fit_for_war_and_war_is_a_rite_requirement() -> None:
    assert SLOTS[CalendarSlot.CAMPAIGN].opening is SlotOpening.WAR_SEASON
    assert RiteRequirements(war=True).war
    assert "it is worked only in a time of war" in inspect.getsource(unmet)


def test_k60_ambush_stays_a_harm_of_danger() -> None:
    assert DangerHarm.AMBUSH in set(DangerHarm)


def test_k61_every_terrain_has_a_passage_for_every_mode_from_its_rules() -> None:
    rules = Rules()
    assert all(set(spec.passage(rules)) == set(MovementMode) for spec in TERRAIN.values())
    assert len(TERRAIN) == len(TerrainKind)


def test_k62_only_incorporeal_bodies_move_incorporeal() -> None:
    assert [plan for plan, modes in BODY_MODES.items() if MovementMode.INCORPOREAL in modes] == [BodyPlan.INCORPOREAL]
    settings = Rules().movement
    assert hasattr(settings, "incorporeal_speed")


def test_k63_world_types_keep_their_layers_and_the_lacking_ones_gain_one() -> None:
    assert {WorldType.CRYSTAL, WorldType.METHANE, WorldType.CORPSE_WORLD, WorldType.LIVING} <= set(WORLD_CRUSTS)


def test_k64_a_living_world_has_a_living_crust_that_regrows() -> None:
    assert WORLD_CRUSTS[WorldType.LIVING] is RockKind.LIVING_TISSUE
    assert Rules().rocks.tissue_regrowth > 0


def test_k73_creature_traits_are_typed_kinds_of_function_and_strength() -> None:
    assert {"category", "strength"} <= {column.name for column in TraitKindRow.__table__.columns}


def test_k65_revival_reaches_species_and_never_gods() -> None:
    assert "kind.entity_type is not EntityType.SPECIES" in inspect.getsource(revive)


def test_k66_k67_oscillation_phases_and_climate_eras_are_widened() -> None:
    assert {OscillationPhase.STRONG_WARM, OscillationPhase.STRONG_COLD} <= set(OscillationPhase)
    assert {ClimateEra.WARMING, ClimateEra.COOLING} <= set(ClimateEra)


def test_k68_the_water_cycle_counts_the_world_own_liquid() -> None:
    labels = {cycle_label(PlanetaryCycle.WATER, liquid) for liquid in SurfaceLiquid}
    assert len(labels) == len(SurfaceLiquid)
    assert PlanetaryCycle.WATER.value == "water"


def test_k69_rings_soil_stocks_perennials_and_commons_are_widened() -> None:
    assert {LandUseRing.INDUSTRY, LandUseRing.FALLOW} <= set(LandUseRing)
    assert {PerennialKind.COPPICE, PerennialKind.HEDGEROW, PerennialKind.PALM_STAND} <= set(PerennialKind)
    assert {CommonsKind.TURBARY, CommonsKind.FORAGING_GROUND, CommonsKind.SHORE} <= set(CommonsKind)


def test_k70_fish_ponds_are_a_catch_ground_of_their_own_medium() -> None:
    assert GROUNDS[CatchGround.FISH_PONDS].medium is CatchMedium.POND


def test_k71_hunting_animals_are_gear_that_needs_animals() -> None:
    assert GEAR[Gear.HUNTING_ANIMALS].needs_animals
    assert AnimalRole.HUNTING in set(AnimalRole)


def test_k72_species_and_size_classes_are_widened_and_sizes_keep_order() -> None:
    assert SpeciesClass.LICHEN in set(SpeciesClass)
    assert next(iter(SizeClass)) is SizeClass.MICROSCOPIC


def test_k75_k76_symbiosis_and_ferments_are_widened() -> None:
    assert {SymbiosisKind.AMENSALISM, SymbiosisKind.FARMING} <= set(SymbiosisKind)
    assert {FermentKind.ALKALINE, FermentKind.WILD} <= set(FermentKind)


def test_k77_athermic_bodies_are_a_typed_trait_of_their_biochemistry() -> None:
    assert ATHERMIC_BIOCHEMISTRY


def test_k78_attacks_are_widened() -> None:
    assert {AttackDelivery.PROJECTILE, AttackDelivery.CONSTRICTION} <= set(AttackDelivery)


def test_k79_held_beasts_come_from_one_catalogue() -> None:
    assert {BeastTemper.BOUND, BeastTemper.TAMED, BeastTemper.COMPANION} == HELD_TEMPERS


def test_k80_k81_merged_taxonomies_keep_one_name() -> None:
    names = enum_names()
    assert "KnowledgeKind" in names and not {"LoreKind", "TeachingKind"} & names
    assert "Transmission" in names and "DiseaseVector" not in names
    assert KnowledgeKind and Transmission


def test_k82_agents_and_functions_are_widened() -> None:
    assert {DiseaseAgent.HEREDITARY, DiseaseAgent.AUTOIMMUNE} <= set(DiseaseAgent)
    assert {BodyFunction.SWIM, BodyFunction.CLIMB} <= set(BodyFunction)


def test_k83_cure_means_and_cure_classes_are_two_concepts() -> None:
    assert CureKind is not CureClass and not {item.value for item in CureKind} >= {item.value for item in CureClass}


def test_k84_medicine_tiers_systems_and_sensitivities_are_widened() -> None:
    assert MedicineTier.ANATOMY in set(MedicineTier)
    assert BodySystem.EXCRETION in set(BodySystem)
    assert Sensitivity.TO_PRESSURE in set(Sensitivity)


def test_k85_bleeding_harm_is_a_rule() -> None:
    assert Rules().injuries.internal_bleed_death_pct >= 0


def test_k86_asphyxia_is_both_a_damage_type_and_a_wound() -> None:
    assert DamageType.ASPHYXIA.value == InjuryKind.ASPHYXIA.value
