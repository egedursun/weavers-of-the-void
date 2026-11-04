import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.region import PolityMapKnowledgeRow, RegionDangerRow, RegionMemoryRow
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, ScarKind, SoilKind, TemperatureBand, TerrainKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.region import DangerSource, RegionMemoryKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.environment.control import world_seam
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import environment, regions
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.engine.society.factories import make
from tests.services.player.factories import PlayerWorld, make_entity

LEVERS = (
    "region:danger_create",
    "region:danger_edit",
    "region:danger_release",
    "region:danger_delete",
    "region:sanctify",
    "region:memory_add",
    "region:memory_edit",
    "region:memory_delete",
    "region:knowledge_set",
    "region:knowledge_release",
    "region:river_redirect",
    "environment:biome",
)


def ground_for(region_id: int, world_id: int) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(
        entity_id=region_id,
        world_id=world_id,
        surveyed=True,
        biome_mix=[0, 0, 0, 0, 100, 0, 0, 0, 0, 0],
        dominant_terrain=TerrainKind.PLAIN,
        elevation_mean=20,
        roughness=20,
        latitude=30,
        moisture=50,
        base_forest=30,
        forest_cover=30,
        base_wetland=10,
        wetland=10,
        river_class=RiverClass.RIVER,
        coast_kind=CoastKind.NONE,
        soil=SoilKind.LOAM,
        soil_fertility=60,
        soil_base=60,
        temperature=50,
        temperature_band=TemperatureBand.TEMPERATE,
        rainfall=50,
        seasonality=30,
        disease_load=10,
        mineral_layers={},
        magic_density=20,
        passability={},
        defensibility=30,
        scars={},
    )


async def _undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    report = await UndoRun(session, epoch, changes, label_names(changes, await node_names(session, changes))).run()
    return report.conflicts


def test_every_region_lever_is_in_the_catalog() -> None:
    assert [lever for lever in LEVERS if lever not in ACTIONS_BY_ID] == []


async def test_a_danger_is_created_edited_held_released_deleted_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    session.add(ground_for(world.region.id, world.world.id))
    await session.flush()
    await regions.create_danger(scope, regions.CreateDanger(region_id=world.region.id, source=DangerSource.BANDITS, strength=40))
    row = await session.scalar(select(RegionDangerRow))
    assert row is not None and row.held and row.strength == 40
    await regions.edit_danger(scope, regions.EditDanger(danger_id=row.id, strength=70))
    assert row.strength == 70
    await regions.release_danger(scope, regions.DangerTarget(danger_id=row.id))
    assert not row.held
    with pytest.raises(ValidationFailedError):
        await regions.release_danger(scope, regions.DangerTarget(danger_id=row.id))
    await regions.delete_danger(scope, regions.DangerTarget(danger_id=row.id))
    assert await session.scalar(select(RegionDangerRow)) is None


async def test_create_danger_is_undoable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    session.add(ground_for(world.region.id, world.world.id))
    await session.flush()
    created = await regions.create_danger(scope, regions.CreateDanger(region_id=world.region.id, source=DangerSource.MONSTERS, strength=55))
    assert await _undo(session, created.ledger_entry_id, world.cosmos.epoch) == []
    assert await session.scalar(select(RegionDangerRow)) is None


async def test_sanctity_memory_and_maps_can_be_set_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    ground = ground_for(world.region.id, world.world.id)
    session.add(ground)
    await session.flush()
    await regions.sanctify(scope, regions.Sanctify(region_id=world.region.id, sacredness=77))
    assert ground.sacredness == 77 and "sacredness" in ground.locked
    await environment.unlock_region_environment(scope, environment.UnlockRegionEnvironment(region_id=world.region.id, field="sacredness"))
    assert "sacredness" not in ground.locked
    await regions.add_memory(scope, regions.AddMemory(region_id=world.region.id, kind=RegionMemoryKind.MIRACLE, magnitude=60, title="The Weeping Stone"))
    memory = await session.scalar(select(RegionMemoryRow))
    assert memory is not None and memory.held
    await regions.edit_memory(scope, regions.EditMemory(memory_id=memory.id, kind=RegionMemoryKind.MASSACRE, magnitude=90, hold=False))
    assert (memory.kind, memory.magnitude, memory.held) == (RegionMemoryKind.MASSACRE, 90, False)
    await regions.delete_memory(scope, regions.MemoryTarget(memory_id=memory.id))
    assert await session.scalar(select(RegionMemoryRow)) is None
    polity = await make(session, "Kingdom", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    await regions.set_knowledge(scope, regions.SetKnowledge(polity_id=polity.id, region_id=world.region.id, level=0))
    known = await session.get(PolityMapKnowledgeRow, (polity.id, world.region.id))
    assert known is not None and known.level == 0 and known.held
    await regions.release_knowledge(scope, regions.KnowledgeTarget(polity_id=polity.id, region_id=world.region.id))
    assert not known.held


async def test_every_land_value_can_be_held_and_seams_take_world_materials(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    ground = ground_for(world.region.id, world.world.id)
    session.add(ground)
    material = WorldMaterialRow(
        world_id=world.world.id,
        origin=MaterialOrigin.RESEARCH,
        base_kind=MaterialKind.IRON,
        name="Starsteel",
        family=MaterialFamily.METAL,
        hardness=90,
        toughness=80,
        weight=50,
        edge=90,
        conductivity=40,
        sanctity=20,
        corruption=0,
        rarity=90,
        base_value=90,
        decay=0,
        created_epoch=1,
    )
    session.add(material)
    await session.flush()
    for field, value in (("soil", "salt"), ("farmed", 7), ("erosion", 9), ("temperature_band", "cold"), ("derived_fertility", 44), ("cleared", 3)):
        await environment.set_region_environment(scope, environment.SetRegionEnvironment(region_id=world.region.id, field=field, value=value))
        assert field in ground.locked
    await environment.set_region_scar(scope, environment.SetScar(region_id=world.region.id, kind=ScarKind.CRATER, depth=40, lock=True))
    assert "scar.crater" in ground.locked
    await environment.set_region_mineral(scope, environment.SetMineral(region_id=world.region.id, world_material_id=material.id, richness=70, lock=True))
    assert ground.mineral_layers[world_seam(material.id)] == 70
    with pytest.raises(ValidationFailedError):
        await environment.set_region_mineral(scope, environment.SetMineral(region_id=world.region.id, richness=10))
    await environment.set_region_biome(scope, environment.SetBiome(region_id=world.region.id, biome=8, share=60))
    assert ground.biome_mix[8] == 60 and "biome_mix" in ground.locked


async def test_a_river_is_turned_only_into_a_neighbour(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await make_entity(session, "Far Vale", EntityType.REGION, world_id=world.world.id)
    session.add(ground_for(world.region.id, world.world.id))
    session.add(ground_for(other.id, world.world.id))
    await session.flush()
    with pytest.raises(ValidationFailedError):
        await regions.redirect_river(scope, regions.RedirectRiver(from_region_id=world.region.id, to_region_id=other.id))
