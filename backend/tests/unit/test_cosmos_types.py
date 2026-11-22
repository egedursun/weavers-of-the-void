from collections import Counter

from aerona.cartography.terrain import default_terrain
from aerona.cartography.world_types import WORLD_TYPE_PROFILES
from aerona.catalog.climate import WORLD_CLIMATE_MULTIPLIERS
from aerona.catalog.goods_tables import WORLD_MINERALS
from aerona.catalog.goods_traits import materials_with
from aerona.catalog.life.environment import WORLD_SOIL, WORLD_TEMPERATURE, WORLD_TERRAIN
from aerona.catalog.stars import STAR_TYPE_LABELS, STAR_TYPES
from aerona.catalog.worlds import WORLD_TYPES
from aerona.core.random import SeededRandom
from aerona.db.tables.celestial import StarRow
from aerona.domain.enums.environment import RiverClass, TerrainKind
from aerona.domain.enums.goods_traits import MaterialTrait
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.world import DARK_STAR_TYPES, EXTINGUISHED_STAR_TYPES, Atmosphere, ClimateEra, Gravity, StarType, WorldType
from aerona.engine.cosmos.star_types import STAR_TYPE_MECHANICS, brightness_band, fitted_brightness, kindled_brightness, star_capacity_pct, star_heat
from aerona.engine.cosmos.world_types import death_crossing_reaches, disaster_pct, mechanics_of, ore_yield_pct
from aerona.engine.environment.battleground import ENDLESS_DAY_WORLDS
from aerona.engine.environment.profile import Geography, Surroundings, mineral_layers, temperature_of
from aerona.engine.environment.seasons import NO_SEASON_WORLDS, TWO_SEASON_WORLDS
from aerona.engine.phases.geography import NATURES_BY_SUBTYPE, WORLD_NATURES
from aerona.prompts.schemas.descriptions import star_type_catalogue, world_type_catalogue
from aerona.rules.registry import Rules

RULES = Rules()
GEOGRAPHY = Geography(
    biome_mix=[0] * 10, elevation_mean=20, roughness=20, latitude=30, moisture=50, base_forest=20, base_wetland=10, river_class=RiverClass.NONE
)
NEW_WORLDS = frozenset(
    {
        WorldType.SUPER_EARTH,
        WorldType.ICE_GIANT,
        WorldType.HOT_GIANT,
        WorldType.IRON,
        WorldType.CARBON,
        WorldType.GREENHOUSE,
        WorldType.DWARF_PLANET,
        WorldType.CHTHONIAN,
        WorldType.HYCEAN,
        WorldType.JUNGLE,
        WorldType.FORGE,
        WorldType.FUNGAL,
        WorldType.SHATTERED,
        WorldType.HOLLOW,
        WorldType.ICE_SHELL,
        WorldType.METHANE,
    }
)


def star(star_type: StarType, brightness: int) -> StarRow:
    return StarRow(star_type=star_type, brightness=brightness, x=0.0, y=0.0, created_epoch=1)


def test_every_star_type_has_a_catalogue_and_mechanics_row() -> None:
    assert set(STAR_TYPES) == set(StarType) == set(STAR_TYPE_MECHANICS) == set(STAR_TYPE_LABELS)
    assert [label for label, count in Counter(STAR_TYPE_LABELS.values()).items() if count > 1] == []
    for star_type in StarType:
        low, high = brightness_band(RULES, star_type)
        assert 0 <= low <= high <= 100
        assert STAR_TYPES[star_type].description


def test_the_real_stellar_classes_and_remnants_exist() -> None:
    spectral = {StarType.BLUE_STAR, StarType.BLUE_WHITE_STAR, StarType.WHITE_STAR, StarType.YELLOW_WHITE_STAR}
    dwarfs = {StarType.YELLOW_DWARF, StarType.ORANGE_DWARF, StarType.RED_DWARF, StarType.BROWN_DWARF, StarType.WHITE_DWARF}
    giants = {StarType.YELLOW_GIANT, StarType.RED_GIANT, StarType.BLUE_GIANT, StarType.RED_SUPERGIANT, StarType.BLUE_SUPERGIANT, StarType.HYPERGIANT}
    remnants = {StarType.NEUTRON_STAR, StarType.PULSAR, StarType.MAGNETAR, StarType.BLACK_HOLE}
    assert spectral | dwarfs | giants | remnants <= set(StarType)
    assert StarType.BLACK_HOLE in DARK_STAR_TYPES and StarType.BLACK_HOLE in EXTINGUISHED_STAR_TYPES


def test_supernova_remnants_follow_the_mass_of_the_star() -> None:
    assert STAR_TYPES[StarType.BLUE_SUPERGIANT].remnant is StarType.BLACK_HOLE
    assert STAR_TYPES[StarType.RED_SUPERGIANT].remnant is StarType.NEUTRON_STAR
    assert STAR_TYPES[StarType.RED_GIANT].remnant is StarType.WHITE_DWARF
    assert STAR_TYPES[StarType.YELLOW_DWARF].remnant is StarType.STAR_REMNANT
    for star_type in StarType:
        if STAR_TYPE_MECHANICS[star_type].collapse_weight(RULES) > 0:
            assert STAR_TYPES[star_type].remnant is not star_type


def test_brightness_lands_inside_the_band_of_the_type() -> None:
    assert kindled_brightness(RULES, StarType.BLACK_HOLE, 100) == 0
    low, high = brightness_band(RULES, StarType.BROWN_DWARF)
    assert kindled_brightness(RULES, StarType.BROWN_DWARF, 0) == low and kindled_brightness(RULES, StarType.BROWN_DWARF, 100) == high
    assert kindled_brightness(RULES, StarType.BLUE_STAR, 50) > kindled_brightness(RULES, StarType.RED_DWARF, 50)
    assert fitted_brightness(RULES, StarType.WHITE_DWARF, 0) == brightness_band(RULES, StarType.WHITE_DWARF)[0]


def test_hot_stars_warm_and_dim_stars_cool_their_worlds() -> None:
    assert star_heat(RULES, None) == 0
    assert star_heat(RULES, star(StarType.BLUE_STAR, 92)) > star_heat(RULES, star(StarType.YELLOW_DWARF, 70)) > star_heat(RULES, star(StarType.RED_DWARF, 28))
    low, high = brightness_band(RULES, StarType.YELLOW_DWARF)
    assert star_heat(RULES, star(StarType.YELLOW_DWARF, high)) > star_heat(RULES, star(StarType.YELLOW_DWARF, low))
    assert star_capacity_pct(RULES, star(StarType.ORANGE_DWARF, 50)) > star_capacity_pct(RULES, star(StarType.BLACK_HOLE, 0))
    assert star_capacity_pct(RULES, None) == 100
    lit = Surroundings(world_type=WorldType.ORDINARY, era=None, coastal=False, highland=False, star_heat=star_heat(RULES, star(StarType.BLUE_STAR, 92)))
    plain = Surroundings(world_type=WorldType.ORDINARY, era=None, coastal=False, highland=False)
    assert temperature_of(RULES, GEOGRAPHY, lit) > temperature_of(RULES, GEOGRAPHY, plain)


def test_every_world_type_has_a_row_in_every_per_type_table() -> None:
    assert set(WORLD_TYPES) == set(WorldType) == set(WORLD_TYPE_PROFILES) == set(WORLD_TEMPERATURE)
    for world_type in WorldType:
        default_terrain(world_type, RULES)
        WORLD_TEMPERATURE[world_type](RULES)
        assert len(WORLD_TYPE_PROFILES[world_type].biomes) == 10
    for world_type in NEW_WORLDS:
        assert world_type in WORLD_NATURES
        assert world_type is WorldType.FORGE or mechanics_of(world_type).capacity_pct is not None
        assert any(key[0] is world_type for key in WORLD_CLIMATE_MULTIPLIERS)


def test_moon_archetypes_are_world_types() -> None:
    assert {WorldType.ICE_SHELL, WorldType.METHANE, WorldType.LAVA, WorldType.DWARF_PLANET} <= set(WorldType)


def test_new_world_types_carry_their_physics() -> None:
    assert mechanics_of(WorldType.SUPER_EARTH).forced_gravity is Gravity.HIGH
    assert mechanics_of(WorldType.DWARF_PLANET).forced_gravity is Gravity.LOW
    assert mechanics_of(WorldType.GREENHOUSE).forced_atmosphere is Atmosphere.TOXIC
    assert mechanics_of(WorldType.CHTHONIAN).forced_atmosphere is Atmosphere.NONE
    assert mechanics_of(WorldType.HYCEAN).forced_atmosphere is Atmosphere.DENSE
    assert {WorldType.HOLLOW, WorldType.HOT_GIANT, WorldType.CHTHONIAN, WorldType.GREENHOUSE} <= NO_SEASON_WORLDS
    assert WorldType.DWARF_PLANET in TWO_SEASON_WORLDS
    assert {WorldType.HOLLOW, WorldType.HOT_GIANT, WorldType.CHTHONIAN} <= ENDLESS_DAY_WORLDS
    assert WORLD_TERRAIN[WorldType.JUNGLE] is TerrainKind.JUNGLE
    assert WorldType.JUNGLE in WORLD_SOIL


def test_ore_yield_and_disasters_follow_the_world_type() -> None:
    assert ore_yield_pct(RULES, WorldType.IRON) > ore_yield_pct(RULES, WorldType.FORGE) > ore_yield_pct(RULES, WorldType.ORDINARY) == 100
    assert disaster_pct(RULES, WorldType.GODS_PALACE, Disaster.EARTHQUAKE) == 0
    assert disaster_pct(RULES, WorldType.GENERATION_SHIP, Disaster.EARTHQUAKE) == 0
    assert disaster_pct(RULES, WorldType.CHTHONIAN, Disaster.EARTHQUAKE) > 100
    assert disaster_pct(RULES, WorldType.LAVA, Disaster.EARTHQUAKE) > 100
    assert disaster_pct(RULES, WorldType.DWARF_PLANET, Disaster.STORM) == 0
    assert disaster_pct(RULES, WorldType.ORDINARY, Disaster.FLOOD) == 100


def test_signature_minerals_appear_in_their_worlds() -> None:
    for world_type, minerals in WORLD_MINERALS.items():
        assert set(minerals) <= frozenset(materials_with(MaterialTrait.MINERAL))
        layers = mineral_layers(RULES, SeededRandom.for_epoch(1, 1, world_type.value), GEOGRAPHY, world_type, TerrainKind.PLAIN)
        assert all(material.value in layers for material in minerals), world_type


def test_place_natures_have_unique_subtypes() -> None:
    subtypes = [nature.subtype for group in WORLD_NATURES.values() for nature in group]
    assert len(subtypes) == len(set(subtypes))
    assert all(subtype in NATURES_BY_SUBTYPE for subtype in subtypes)


def test_corpse_world_carries_the_river_of_the_dead() -> None:
    assert death_crossing_reaches(WorldType.DEAD) and death_crossing_reaches(WorldType.CORPSE_WORLD)
    assert not death_crossing_reaches(WorldType.ORDINARY)


def test_prompts_list_every_star_and_world_type_with_its_nature() -> None:
    stars, worlds = star_type_catalogue(), world_type_catalogue()
    assert all(f"{star_type.value} (" in stars for star_type in StarType)
    assert all(f"{world_type.value} (" in worlds for world_type in WorldType)
    assert STAR_TYPES[StarType.MAGNETAR].description in stars


def test_climate_eras_reference_known_eras() -> None:
    assert {era for _, era in WORLD_CLIMATE_MULTIPLIERS} <= set(ClimateEra)
