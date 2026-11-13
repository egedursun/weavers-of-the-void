import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.equipment import ROLE_ARMS
from aerona.catalog.vehicles import FRAMES
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.body import BodyRow
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.economy import CommunityStockRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import ArmyUnitEquipmentRow, EquipmentModelRow, EquipmentStoreRow, UnitDesignEquipmentRow, UnitDesignTechniqueRow
from aerona.db.tables.integrity import StructureSectionRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, UnitDesignRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.vehicles import DesignMountRow, DesignTechniqueRow, VehicleGroupSectionRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.equipment import ArmamentSlot, EquipmentFamily
from aerona.domain.enums.integrity import Criticality, HarmForce, SectionHazard, SectionState
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.structure import SectionRole, StructureSection
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.models.entity_stats import ArmyStats, CosmicBeingStats, PeopleStats, PolityStats
from aerona.engine.body.decline import onset_chance
from aerona.engine.collective.designs import MOUNT_ARCS, draw_design
from aerona.engine.collective.embodied import TABLE_KINDS, align_made, settle
from aerona.engine.cosmos.being_wounds import WoundTally, effective_might, regrow, strike, wound_being
from aerona.engine.cuisine.dishes import dish_traits, run_kitchens
from aerona.engine.equipment.models import draw_model
from aerona.engine.military.unit_types import draw_type, run_unit_types
from aerona.engine.military.units import designs_of, equip_bare_stacks
from aerona.engine.mortal.attraction import drawn, pull
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.made_names import MADE_TABLES, made_name
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.renames import rename_everywhere
from aerona.engine.primitives.stats import stat
from aerona.engine.structures.integrity import overall, strike_rows
from aerona.engine.vehicles.fleet import borne_baggage
from aerona.engine.vehicles.groups import add_vehicles, read
from aerona.engine.vehicles.production import buildable, vehicle_works
from aerona.engine.vehicles.sections import strike_group
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

PERCENT = 100


def section(name: StructureSection, *, role: SectionRole, share: int, flammability: int, neighbours: list[str], critical: bool = False) -> StructureSectionRow:
    return StructureSectionRow(
        structure_entity_id=0,
        section=name,
        role=role,
        criticality=Criticality.CRITICAL if critical else Criticality.MINOR,
        share=share,
        exposure=50,
        hazard=SectionHazard.NONE,
        neighbours=neighbours,
        condition=PERCENT,
        state=SectionState.SOUND,
        material=None,
        flammability=flammability,
        locked=[],
    )


async def kit_of(session: AsyncSession, design_id: int) -> dict[ArmamentSlot, EquipmentFamily]:
    rows = await session.execute(
        select(EquipmentModelRow.slot, EquipmentModelRow.family)
        .join(UnitDesignEquipmentRow, UnitDesignEquipmentRow.model_id == EquipmentModelRow.id)
        .where(UnitDesignEquipmentRow.design_id == design_id)
    )
    return {slot: family for slot, family in rows}


async def people(session: AsyncSession, world: CoreWorld, name: str = "Ardan") -> EntityRow:
    return await entity(session, name, EntityType.PEOPLE, PeopleStats(population=4000), world_id=world.world.id)


async def test_fire_spreads_by_what_a_section_is_built_of_and_a_fallen_foundation_brings_down_the_rest(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "integrity", rules=tuned_rules(integrity={"fire_spread_pct": 100}))
    timber = section(StructureSection.ROOF, role=SectionRole.SHELTER, share=30, flammability=90, neighbours=["main_hall"])
    hall = section(StructureSection.MAIN_HALL, role=SectionRole.SHELTER, share=40, flammability=90, neighbours=["roof", "vault"])
    stone = section(StructureSection.VAULT, role=SectionRole.STORAGE, share=30, flammability=5, neighbours=["main_hall"])
    strike = strike_rows(ctx, [timber, hall, stone], 70, HarmForce.FIRE)
    assert strike.fire_spread > 0
    assert stone.condition > hall.condition
    footing = section(StructureSection.FOUNDATION, role=SectionRole.SUPPORT, share=50, flammability=5, neighbours=[], critical=True)
    upper = section(StructureSection.UPPER_FLOORS, role=SectionRole.SHELTER, share=50, flammability=5, neighbours=[])
    footing.condition = 1
    fallen = strike_rows(ctx, [footing, upper], 40, HarmForce.QUAKE)
    assert fallen.collapsed and upper.state is SectionState.DESTROYED


async def test_a_vehicle_group_takes_hits_on_its_sections_and_reads_its_strength(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "vehicles")
    folk = await people(session, world)
    design = await draw_design(ctx, folk, VehicleFrame.WAGON)
    group = await add_vehicles(session, folk.id, design, 6, epoch=0, crewed=6, region_id=None)
    assert group is not None
    before = await read(session, group)
    assert before is not None and before.cargo > 0
    await strike_group(ctx, group, 30, "test")
    hits = list(await session.scalars(select(VehicleGroupSectionRow).where(VehicleGroupSectionRow.group_id == group.id)))
    assert hits and sum(row.damaged + row.disabled + row.destroyed for row in hits) > 0


async def test_a_vehicle_type_is_built_only_by_makers_who_know_its_technique(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "vehicles")
    folk = await people(session, world)
    galley = await draw_design(ctx, folk, VehicleFrame.GALLEY)
    needed = list(await session.scalars(select(DesignTechniqueRow.technique).where(DesignTechniqueRow.design_id == galley.id)))
    assert needed == [Technique.SAILING]
    assert not await buildable(ctx, folk, galley)
    session.add(HolderTechniqueRow(holder_entity_id=folk.id, technique=Technique.SAILING, since_epoch=0))
    await session.flush()
    assert await buildable(ctx, folk, galley)


async def test_a_kind_of_soldier_is_mustered_only_when_its_makers_know_its_technique(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "unit_types")
    folk = await people(session, world)
    pikes = await draw_type(ctx, folk, UnitKind.PIKE_INFANTRY, await KnowledgeMap.load(session))
    assert await session.get(UnitDesignTechniqueRow, (pikes.id, Technique.PHALANX_DRILL)) is not None
    assert pikes.id not in {row.id for row in await designs_of(session, folk)}
    session.add(HolderTechniqueRow(holder_entity_id=folk.id, technique=Technique.PHALANX_DRILL, since_epoch=0))
    await session.flush()
    assert pikes.id in {row.id for row in await designs_of(session, folk)}


async def test_made_names_never_repeat_within_a_world(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "names")
    folk = await people(session, world)
    first = await made_name(session, ctx.rules, folk, "Boat", "boat", 3)
    session.add(DesignRow(owner_entity_id=folk.id, kind=FRAMES[VehicleFrame.BOAT].kind, frame=VehicleFrame.BOAT, name=first, world_id=folk.world_id, locked=[]))
    await session.flush()
    second = await made_name(session, ctx.rules, folk, "Boat", "boat", 3)
    assert second != first


async def test_an_army_of_a_town_is_armed_from_its_realm_stores(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "armament")
    town = await settlement(session, "Hollin", world, world.regions[0])
    realm = await entity(session, "Crown of Hollin", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    spear = await draw_model(ctx, realm, EquipmentFamily.SPEAR, world_id=world.world.id)
    session.add(EquipmentStoreRow(holder_node_id=realm.id, model_id=spear.id, count=500, locked=[]))
    host = await entity(session, "Hollin Host", EntityType.ARMY, ArmyStats(size=100), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ArmyRow(entity_id=host.id, owner_entity_id=town.id, raised_epoch=0))
    session.add(ArmyUnitRow(army_entity_id=host.id, kind=UnitKind.LINE_INFANTRY, count=100))
    await session.flush()
    assert await equip_bare_stacks(ctx) > 0
    carried = list(await session.scalars(select(ArmyUnitEquipmentRow)))
    store = await session.get(EquipmentStoreRow, (realm.id, spear.id))
    assert carried and carried[0].model_id == spear.id and store is not None and store.count < 500


def test_a_dish_nourishes_keeps_and_honours_by_how_it_is_made() -> None:
    staple = dish_traits(CookingMethod.BAKED, DishCourse.STAPLE, [CommodityKind.GRAIN])
    feast = dish_traits(CookingMethod.DRIED, DishCourse.FESTIVE, [CommodityKind.MEAT, CommodityKind.HERBS])
    assert staple["nourishment"] > feast["nourishment"] - 10
    assert feast["keeps"] > staple["keeps"] and feast["prestige"] > staple["prestige"] and feast["delight"] > staple["delight"]


def test_attraction_gates_courtship_by_whom_a_mortal_is_drawn_to() -> None:
    drawn_one = MortalProfileRow(entity_id=1, drawn_to=["female", "other"], attraction=60)
    none = MortalProfileRow(entity_id=2, drawn_to=[], attraction=60)
    cold = MortalProfileRow(entity_id=3, drawn_to=["male"], attraction=0)
    assert drawn(drawn_one, "female") and not drawn(drawn_one, "male")
    assert not drawn(none, "female") and not drawn(cold, "male")
    assert pull(drawn_one, "other") == 0.6 and pull(cold, "male") == 0.0


async def test_a_struck_cosmic_being_loses_might_through_its_body(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "cosmic_wounds")
    being = await entity(session, "The Long Watcher", EntityType.COSMIC_BEING, CosmicBeingStats(size=80), world_id=world.world.id)
    whole = await effective_might(session, being, 60)
    outcome = await wound_being(ctx, being, 2000, HarmCause.GOD, "struck down")
    assert outcome is not None
    body = await session.get(BodyRow, being.id)
    assert body is not None
    assert await effective_might(session, being, 60) < whole


async def test_the_creator_strikes_a_vast_being_and_its_body_grows_and_its_might_falls(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "cosmic_wounds")
    being = await entity(session, "The Far Shape", EntityType.COSMIC_BEING, CosmicBeingStats(size=80), world_id=world.world.id)
    assert await session.get(BodyRow, being.id) is None
    whole = await effective_might(session, being, 60)
    await strike(ctx, being.id, 10, "struck by the Creator")
    assert await session.get(BodyRow, being.id) is not None
    assert await effective_might(session, being, 60) < whole
    town = await settlement(session, "Hollin", world, world.regions[0])
    with pytest.raises(ValidationFailedError):
        await strike(ctx, town.id, 1, "struck by the Creator")


async def test_blows_on_a_vast_being_add_up_and_its_wounds_heal_over_the_epochs(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "cosmic_wounds")
    being = await entity(session, "The Slow Tide", EntityType.COSMIC_BEING, CosmicBeingStats(size=80), world_id=world.world.id)
    await strike(ctx, being.id, 1, "struck by the Creator")
    first = stat(being, "hp")
    await strike(ctx, being.id, 1, "struck by the Creator")
    second = stat(being, "hp")
    body = await session.get(BodyRow, being.id)
    assert body is not None and first is not None and second is not None
    assert second < first < body.hp_max
    await regrow(ctx, being, WoundTally())
    healed = stat(being, "hp")
    assert healed is not None and healed > second


async def test_an_old_mind_may_decline_unless_learning_holds_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "decline")
    town = await settlement(session, "Hollin", world, world.regions[0])
    plain = await mortal(session, "Ira", world, town.id, age=80)
    learned = await mortal(session, "Oss", world, town.id, age=80)
    session.add(MortalProfileRow(entity_id=learned.id, education=PERCENT))
    await session.flush()
    assert await onset_chance(ctx, learned) < await onset_chance(ctx, plain)


async def test_harm_spread_across_sections_still_costs_the_whole_what_it_names(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "integrity")
    gate = section(StructureSection.GATE, role=SectionRole.ENTRY, share=10, flammability=5, neighbours=[])
    gate.condition = 20
    wall = section(StructureSection.OUTER_WALL, role=SectionRole.DEFENCE, share=60, flammability=5, neighbours=[])
    hall = section(StructureSection.MAIN_HALL, role=SectionRole.SHELTER, share=30, flammability=5, neighbours=[])
    rows = [gate, wall, hall]
    before = overall(rows)
    strike_rows(ctx, rows, 30, HarmForce.SIEGE)
    assert gate.condition == 0
    assert abs(before - 30 - overall(rows)) <= 1
    roof = section(StructureSection.ROOF, role=SectionRole.SHELTER, share=50, flammability=5, neighbours=[])
    strike_rows(ctx, [roof], 25, HarmForce.SIEGE, even=True)
    assert roof.condition == 75


async def test_a_kind_of_soldier_carries_the_weapons_of_its_role(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "unit_types")
    folk = await people(session, world)
    knowledge = await KnowledgeMap.load(session)
    slingers = await draw_type(ctx, folk, UnitKind.SLINGERS, knowledge)
    pikes = await draw_type(ctx, folk, UnitKind.PIKE_INFANTRY, knowledge)

    sling_kit = await kit_of(session, slingers.id)
    pike_kit = await kit_of(session, pikes.id)
    assert sling_kit[ArmamentSlot.MISSILE_WEAPON] in ROLE_ARMS[UnitKind.SLINGERS][ArmamentSlot.MISSILE_WEAPON]
    assert pike_kit[ArmamentSlot.HAND_WEAPON] in ROLE_ARMS[UnitKind.PIKE_INFANTRY][ArmamentSlot.HAND_WEAPON]
    assert slingers.doctrine is not None and pikes.doctrine is not None


async def test_an_army_of_a_town_fights_as_its_realms_kind_of_soldier(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "unit_types")
    town = await settlement(session, "Hollin", world, world.regions[0])
    realm = await entity(session, "Crown of Hollin", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    host = await entity(session, "Hollin Host", EntityType.ARMY, ArmyStats(size=200), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ArmyRow(entity_id=host.id, owner_entity_id=town.id, raised_epoch=0))
    stack = ArmyUnitRow(army_entity_id=host.id, kind=UnitKind.LINE_INFANTRY, count=200)
    session.add(stack)
    await session.flush()
    await run_unit_types(ctx)
    drawn = await session.scalar(select(UnitDesignRow).where(UnitDesignRow.owner_entity_id == realm.id, UnitDesignRow.base_kind == UnitKind.LINE_INFANTRY))
    assert drawn is not None
    assert stack.design_id == drawn.id


async def test_a_market_town_builds_carts_and_its_army_takes_them_to_bear_its_baggage(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "vehicle_works")
    town = await settlement(session, "Hollin", world, world.regions[0], wealth=100)
    session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.MARKET, level=5, built_epoch=0))
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.TIMBER, quantity=500))
    host = await entity(session, "Hollin Host", EntityType.ARMY, ArmyStats(size=500), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ArmyRow(entity_id=host.id, owner_entity_id=town.id, raised_epoch=0))
    session.add(ArmyProfileRow(army_entity_id=host.id, baggage=10, supply_line=[], locked=[]))
    await session.flush()
    await vehicle_works(ctx)
    assert await borne_baggage(session, ctx.rules, host.id) > 0


async def test_every_people_with_stores_comes_to_cook_a_cuisine_of_its_own(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "kitchens")
    folk = await people(session, world)
    town = await settlement(session, "Hollin", world, world.regions[0])
    await bond(session, town.id, folk.id, BondKind.DESCENDS_FROM)
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, quantity=500))
    await session.flush()
    await run_kitchens(ctx)
    courses = set(await session.scalars(select(DishRow.course).where(DishRow.origin_node_id == folk.id)))
    assert len(courses) >= ctx.rules.cuisine.starting_dishes


async def test_a_vehicle_type_carries_only_armed_mounts_seated_and_aimed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "vehicles")
    folk = await people(session, world)
    carrack = await draw_design(ctx, folk, VehicleFrame.CARRACK)
    mounts = list(await session.scalars(select(DesignMountRow).where(DesignMountRow.design_id == carrack.id)))
    assert all(row.model_id is not None and row.section is not None for row in mounts)
    assert all(row.arc is MOUNT_ARCS[row.mount] for row in mounts)


async def test_every_made_type_is_a_record_of_its_world_like_any_other(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "vehicles")
    folk = await people(session, world)
    wagon = await draw_design(ctx, folk, VehicleFrame.WAGON)
    record = await session.get(EntityRow, wagon.entity_id)
    assert record is not None and record.entity_type is EntityType.VEHICLE_TYPE and record.name == wagon.name and record.world_id == world.world.id
    await rename_everywhere(session, record.id, "The Long Hauler")
    assert wagon.name == "The Long Hauler"
    wagon.obsolete = True
    await settle(session, wagon)
    assert record.status is EntityStatus.DEAD
    bare = DesignRow(
        owner_entity_id=folk.id, kind=FRAMES[VehicleFrame.CART].kind, frame=VehicleFrame.CART, name="Bare cart", world_id=world.world.id, locked=[]
    )
    session.add(bare)
    await session.flush()
    assert await align_made(session) >= 1
    assert bare.entity_id is not None


def test_every_made_table_names_its_entity() -> None:
    assert set(TABLE_KINDS) == set(MADE_TABLES)
    assert all("entity_id" in table.__table__.c for table in MADE_TABLES)
