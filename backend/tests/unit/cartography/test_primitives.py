import numpy as np

from aerona.cartography.biomes import Biome, classify_biomes
from aerona.cartography.noise import ValueNoise
from aerona.cartography.palette import darken, palette_for
from aerona.cartography.terrain import TerrainOverrides, default_terrain, terrain_settings
from aerona.cartography.world_types import WORLD_TYPE_PROFILES
from aerona.core.keyed_random import fnv1a32
from aerona.domain.enums.world import WorldType
from tests.unit.cartography.helpers import RULES


def test_value_noise_matches_reference_vectors() -> None:
    noise = ValueNoise(fnv1a32("Aerona:h"))
    assert noise.fractal(np.array([0.5]), np.array([0.5]))[0] == 0.2811705769571603
    assert noise.fractal(np.array([10.3]), np.array([-4.7]), 3)[0] == 0.4057523126927773
    assert noise.fractal(np.array([-123.456]), np.array([789.01]))[0] == 0.49524498099103353


def test_biome_classifier_follows_thresholds() -> None:
    elevation = np.array([-0.1, -0.9, 0.01, 0.2, 0.2, 0.2, 0.4, 0.4, 0.7, 0.9])
    moisture = np.array([0.5, 0.5, 0.5, 0.3, 0.5, 0.7, 0.3, 0.6, 0.5, 0.5])
    water = np.array([True, True] + [False] * 8)
    assert classify_biomes(elevation, moisture, water, RULES).tolist() == [int(biome) for biome in Biome]


def test_every_world_type_has_a_profile_and_a_palette() -> None:
    for world_type in WorldType:
        profile = WORLD_TYPE_PROFILES[world_type]
        assert len(profile.biomes) == len(Biome)
        assert len(set(profile.biomes)) == len(Biome)
        palette = palette_for(world_type)
        assert palette == palette_for(world_type)
        assert len(palette.biome_colours) == len(palette.terrain_colours) == len(Biome)
        assert all(colour.startswith("#") and len(colour) == 7 for colour in [*palette.biome_colours, *palette.terrain_colours, palette.background])


def test_darken_moves_toward_black() -> None:
    assert darken("#ffffff", 0.5) == "#808080"
    assert darken("#123456", 0) == "#123456"
    assert darken("#123456", 1) == "#000000"


def test_terrain_defaults_come_from_the_rules_and_overrides_win() -> None:
    defaults = default_terrain(WorldType.SAND, RULES)
    assert defaults.sea_pct == RULES.world_terrain.sand_sea_pct
    settings = terrain_settings(WorldType.SAND, TerrainOverrides(sea_pct=70), RULES)
    assert settings.sea_fraction == 0.7
    assert settings.moisture_offset == RULES.world_terrain.sand_moisture_pct / 100
