from dataclasses import replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.movement import MOVEMENT
from aerona.catalog.wind_belts import CURRENTS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.environment import CoastKind, MovementMedium, MovementMode, RiverClass, TerrainKind
from aerona.domain.enums.world import WorldType
from aerona.engine.environment.profile import Ground, Surroundings, Works, passability_of
from aerona.engine.phases.environment import refresh_climate
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed

RULES = Rules()
SUBMERGED = MovementMode.SUBMERGED.value
INCORPOREAL = MovementMode.INCORPOREAL.value


BASE = Ground(roughness=20, forest=20, wetland=20, river=RiverClass.NONE, temperature=60, coast=CoastKind.BEACH, terrain=TerrainKind.COAST)


def ground(terrain: TerrainKind = TerrainKind.COAST, **values: Any) -> Ground:
    return replace(BASE, terrain=terrain, **values)


def test_every_mode_has_a_medium_and_a_passage_value() -> None:
    assert set(MOVEMENT) == set(MovementMode)
    assert {MovementMedium.UNDER_WATER, MovementMedium.THROUGH_MATTER} <= {spec.medium for spec in MOVEMENT.values()}
    assert set(passability_of(RULES, ground())) == {mode.value for mode in MovementMode}


def test_beneath_the_water_passage_needs_water_and_falls_under_ice() -> None:
    open_sea = passability_of(RULES, ground())[SUBMERGED]
    assert open_sea > 0
    assert passability_of(RULES, ground(TerrainKind.DESERT, coast=CoastKind.NONE, roughness=60))[SUBMERGED] == 0
    assert passability_of(RULES, ground(temperature=0))[SUBMERGED] < open_sea


def test_a_current_adds_or_takes_passage_beneath_the_water() -> None:
    still = passability_of(RULES, ground(current=OceanCurrent.NONE))[SUBMERGED]
    for current in (OceanCurrent.WARM, OceanCurrent.TIDAL):
        drift = CURRENTS[current].sailing_pct(RULES) * RULES.passability.submerged_current_pct / 100
        assert passability_of(RULES, ground(current=current))[SUBMERGED] == max(0, min(100, round(still + drift)))
    assert passability_of(RULES, ground(current=OceanCurrent.TIDAL))[SUBMERGED] < still < passability_of(RULES, ground(current=OceanCurrent.WARM))[SUBMERGED]
    assert passability_of(RULES, ground(TerrainKind.DESERT, coast=CoastKind.NONE, current=OceanCurrent.WARM))[SUBMERGED] == 0


def test_passage_through_matter_ignores_the_land_and_is_cut_by_wards_and_holy_ground() -> None:
    plain = passability_of(RULES, ground(TerrainKind.PLAIN))[INCORPOREAL]
    assert passability_of(RULES, ground(TerrainKind.PLAIN, roughness=90, forest=90, wetland=90, river=RiverClass.GREAT_RIVER))[INCORPOREAL] == plain
    assert passability_of(RULES, ground(TerrainKind.PLAIN, works=Works(wards=4)))[INCORPOREAL] < plain
    assert passability_of(RULES, ground(TerrainKind.PLAIN, sacred=100))[INCORPOREAL] < plain


async def test_a_region_carries_its_current_into_its_passage(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    env = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert env is not None
    env.dominant_terrain, env.coast_kind, env.temperature = TerrainKind.COAST, CoastKind.BEACH, 60
    env.locked = ["dominant_terrain", "temperature", "rainfall"]
    around = Surroundings(world_type=WorldType.ORDINARY, era=None, coastal=True, highland=False)
    env.current = OceanCurrent.NONE
    refresh_climate(RULES, env, around, 0)
    still = env.passability[SUBMERGED]
    env.current = OceanCurrent.TIDAL
    refresh_climate(RULES, env, around, 0)
    assert env.passability[SUBMERGED] < still
