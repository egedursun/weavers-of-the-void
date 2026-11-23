from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.region import RegionDangerRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, ScarKind, TerrainKind
from aerona.domain.enums.region import DangerHarm, DangerSource
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.environment.dangers import currents, exposure, landslide, reaches, toxic_ground
from aerona.engine.environment.perils import harm_works
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, seed_core_world, surveyed

RULES = Rules()
D = DangerSource


def ground(terrain: TerrainKind = TerrainKind.PLAIN, **values: object) -> RegionEnvironmentRow:
    base: dict[str, object] = {
        "dominant_terrain": terrain,
        "roughness": 30,
        "rainfall": 50,
        "temperature": 50,
        "wetland": 0,
        "river_class": RiverClass.NONE,
        "coast_kind": CoastKind.NONE,
        "scars": {},
        "locked": [],
    }
    base.update(values)
    base.setdefault("current", OceanCurrent.NONE)
    return RegionEnvironmentRow(**base)


def test_each_new_danger_rises_from_its_own_ground() -> None:
    assert landslide(RULES, ground()) == 0.0
    steep = landslide(RULES, ground(TerrainKind.MOUNTAINS, roughness=80, rainfall=80))
    assert steep > 0 and landslide(RULES, ground(TerrainKind.MOUNTAINS, roughness=80, rainfall=80, scars={ScarKind.ERODED.value: 60})) > steep
    assert exposure(RULES, ground()) == 0.0 and exposure(RULES, ground(temperature=2)) > 0 and exposure(RULES, ground(temperature=98)) > 0
    assert currents(RULES, ground()) == 0.0 and currents(RULES, ground(river_class=RiverClass.GREAT_RIVER)) > currents(
        RULES, ground(river_class=RiverClass.STREAM)
    )
    assert toxic_ground(RULES, ground()) == 0 and toxic_ground(RULES, ground(TerrainKind.VOLCANIC)) > 0
    assert toxic_ground(RULES, ground(scars={ScarKind.POISONED.value: 60})) > 0


def test_each_new_danger_harms_its_own_targets() -> None:
    assert DangerHarm.VESSELS in reaches(RULES, D.CURRENTS) and DangerHarm.CROPS not in reaches(RULES, D.CURRENTS)
    assert {DangerHarm.CROPS, DangerHarm.STRUCTURES} <= set(reaches(RULES, D.LANDSLIDE))
    assert DangerHarm.STRUCTURES not in reaches(RULES, D.EXPOSURE)
    assert DangerHarm.CROPS in reaches(RULES, D.TOXIC_GROUND)


async def test_dangers_cut_the_harvest_and_wear_the_works_of_their_land(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", RULES)
    region = world.regions[0].id
    hall = await entity(session, "Old Hall", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=region)
    session.add(StructureProfileRow(structure_entity_id=hall.id, kind=StructureKind.TEMPLE, condition=100))
    danger = RegionDangerRow(world_id=world.world.id, region_entity_id=region, source=D.LANDSLIDE, strength=90)
    session.add(danger)
    land = await session.get(RegionEnvironmentRow, region)
    assert land is not None
    land.harvest_pct = 100
    await session.flush()
    tally = await harm_works(ctx, {region: [danger]}, {region: land})
    profile = await session.get(StructureProfileRow, hall.id)
    assert tally.fields == 1 and land.harvest_pct < 100
    assert tally.buildings == 1 and profile is not None and profile.condition < 100
    assert "danger.harmed" in set(await session.scalars(select(IncidentRow.kind)))
