from aerona.catalog.dangers import HAZARDS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.environment import CoastKind, RiverClass, ScarKind, TerrainKind, WeatherEffect
from aerona.domain.enums.region import TerrainHazard
from aerona.engine.environment.hazards import chance_of, exposed, strength_of, threshold_of
from aerona.rules.registry import Rules

RULES = Rules()
H = TerrainHazard


def ground(terrain: TerrainKind, **values: object) -> RegionEnvironmentRow:
    base: dict[str, object] = {
        "dominant_terrain": terrain,
        "wetland": 0,
        "cleared": 0,
        "rainfall": 50,
        "forest_cover": 50,
        "river_class": RiverClass.NONE,
        "coast_kind": CoastKind.NONE,
        "scars": {},
    }
    base.update(values)
    return RegionEnvironmentRow(**base)


def is_exposed(hazard: TerrainHazard, land: RegionEnvironmentRow) -> bool:
    return exposed(RULES, hazard, HAZARDS[hazard], land)


def test_a_mudslide_needs_rough_wet_ground_with_a_loose_slope() -> None:
    assert is_exposed(H.MUDSLIDE, ground(TerrainKind.HILLS, wetland=30, cleared=20))
    assert is_exposed(H.MUDSLIDE, ground(TerrainKind.HILLS, wetland=30, scars={ScarKind.ERODED.value: 40}))
    assert not is_exposed(H.MUDSLIDE, ground(TerrainKind.HILLS, wetland=30))
    assert not is_exposed(H.MUDSLIDE, ground(TerrainKind.PLAIN, wetland=30, cleared=20))


def test_flash_floods_strike_arid_ground_and_thin_ice_cold_waters() -> None:
    assert is_exposed(H.FLASH_FLOOD, ground(TerrainKind.DESERT, rainfall=10))
    assert not is_exposed(H.FLASH_FLOOD, ground(TerrainKind.FOREST, rainfall=10))
    assert is_exposed(H.THIN_ICE, ground(TerrainKind.TUNDRA, river_class=RiverClass.RIVER))
    assert not is_exposed(H.THIN_ICE, ground(TerrainKind.TUNDRA))
    assert not is_exposed(H.THIN_ICE, ground(TerrainKind.PLAIN, river_class=RiverClass.RIVER))


def test_a_hazard_strikes_only_past_its_threshold_and_works_cut_its_chance() -> None:
    for hazard in (H.MUDSLIDE, H.FLASH_FLOOD, H.THIN_ICE):
        spec = HAZARDS[hazard]
        need = threshold_of(RULES, hazard)
        assert strength_of(RULES, hazard, spec, {spec.effect: need - 1}) == 0
        assert strength_of(RULES, hazard, spec, {spec.effect: need}) == need
        assert chance_of(RULES, hazard, 100) <= chance_of(RULES, hazard, 0)
    assert HAZARDS[H.FLASH_FLOOD].effect is WeatherEffect.FLOOD
