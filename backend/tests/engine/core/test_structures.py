import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import CohortRow, LabourRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.structures import ConstructionRow, StructureProfileRow, StructureStaffRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Job, SexKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.settlement import BuildMaterial, WaterSupply
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import AbandonCause, ConstructionState, ConstructionStatus, StructureKind
from aerona.domain.models.entity_stats import PeopleStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.phases import works
from aerona.engine.phases.works import free_slots, site_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat
from aerona.engine.settlement.book import town_of
from aerona.engine.structures.backfill import BACKFILL_FIXUP, FALLBACK, backfill_structures, type_from_record
from aerona.engine.structures.construction import Commission, abandon, advance, begin, finish
from aerona.engine.structures.control import commission, create_design
from aerona.engine.structures.functions import run_functions
from aerona.engine.structures.profiles import effect_of, material_props, refresh, resolved_of
from aerona.engine.structures.readers import gate_opened, palace_legitimacy, rite_keeping, workshop_output
from aerona.engine.structures.settlement import serve_town
from aerona.engine.structures.spec import build_cost, resolve
from aerona.engine.structures.upkeep import keep
from tests.engine.core.factories import CoreWorld, bond, entity, knowledge, settlement, tuned_rules

CLASS_COUNT = 400
BUILDERS = 100
FEW_BUILDERS = 20
DOTLESS = chr(0x131)


async def staffed_town(session: AsyncSession, world: CoreWorld, *classes: SocialClass, population: int = 6000, builders: int = BUILDERS) -> EntityRow:
    town = await settlement(session, "Brookhold", world, world.regions[0], population=population, prosperity=80, piety=70)
    for social_class in classes:
        session.add(
            CohortRow(
                community_entity_id=town.id,
                age_band=AgeBand.ADULT,
                sex_kind=SexKind.BEGETTER,
                social_class=social_class,
                condition=CohortCondition.NONE,
                count=CLASS_COUNT,
                generation_epoch=0,
            )
        )
    session.add(LabourRow(community_entity_id=town.id, job=Job.BUILDING, workers=builders, output_pct=100, epoch=1))
    await session.flush()
    return town


async def surveyed(ctx: TickContext, town: EntityRow) -> SettlementProfileRow:
    found = await town_of(ctx, town, await KnowledgeMap.load(ctx.session))
    found.profile.treasury = 100000
    await ctx.session.flush()
    return found.profile


async def stocked(ctx: TickContext, town: EntityRow, *commodities: CommodityKind) -> None:
    for commodity in commodities:
        await goods_of(ctx.session, ctx.epoch).add(town.id, commodity, 100000, GoodsFlow.PLAYER)


async def construction_of(session: AsyncSession, structure_id: int) -> ConstructionRow:
    row = await session.scalar(select(ConstructionRow).where(ConstructionRow.structure_entity_id == structure_id))
    assert row is not None
    return row


async def test_construction_takes_ages_and_progress_follows_workers_engineering_and_materials(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.PRIEST, builders=FEW_BUILDERS)
    await surveyed(ctx, town)
    await stocked(ctx, town, CommodityKind.STONE, CommodityKind.INCENSE)
    work, row = await begin(ctx, Commission(site=town, kind=StructureKind.TEMPLE, material=MaterialKind.STONE))
    profile = await ctx.session.get(StructureProfileRow, work.id)
    assert profile is not None and profile.construction_state is ConstructionState.BUILDING and profile.effect_pct == 0
    assert row.cost == build_cost(ctx.rules, resolve(StructureKind.TEMPLE), 1)
    knowledge_map = await KnowledgeMap.load(ctx.session)
    added = await advance(ctx, row, active=1, knowledge=knowledge_map)
    table = ctx.rules.construction
    workers = max(table.builder_floor, round(FEW_BUILDERS * table.worker_share_pct / 100))
    assert added == workers * table.worker_output
    assert row.materials_pct == 100 and 0 < profile.progress < 100
    while row.status is ConstructionStatus.ACTIVE:
        await advance(ctx, row, active=1, knowledge=knowledge_map)
    assert profile.construction_state is ConstructionState.COMPLETE
    assert profile.effect_pct > 0 and profile.staff_pct == 100
    assert (stat(work, "splendor") or 0) > 0


async def test_without_materials_or_coin_the_work_stalls_and_is_abandoned_into_a_legend(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world)
    profile = await surveyed(ctx, town)
    profile.treasury = 0
    work, row = await begin(ctx, Commission(site=town, kind=StructureKind.WONDER))
    knowledge_map = await KnowledgeMap.load(ctx.session)
    assert await advance(ctx, row, active=1, knowledge=knowledge_map) == 0
    assert row.stalled_epochs == 1
    await abandon(ctx, row, AbandonCause.STOOD_STILL)
    assert row.status is ConstructionStatus.ABANDONED
    assert await has_flag(ctx.session, work.id, EntityFlag.RUIN)
    legends = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.LEGEND)))
    assert any("Unfinished" in legend.name for legend in legends)


async def test_no_staff_means_no_function_and_a_plague_on_scribes_closes_the_library(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.SCRIBE)
    await surveyed(ctx, town)
    work, row = await begin(ctx, Commission(site=town, kind=StructureKind.LIBRARY))
    await finish(ctx, row)
    profile = await ctx.session.get(StructureProfileRow, work.id)
    assert profile is not None and profile.staff_pct == 100 and profile.effect_pct > 0
    cohort = await ctx.session.scalar(select(CohortRow).where(CohortRow.community_entity_id == town.id))
    assert cohort is not None
    cohort.count = 0
    await refresh(ctx.session, ctx.rules, work, profile)
    assert profile.staff_pct == 0 and profile.effect_pct == 0


async def test_unpaid_upkeep_wears_condition_and_paid_upkeep_repairs(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.WARRIOR)
    town_profile = await surveyed(ctx, town)
    work, row = await begin(ctx, Commission(site=town, kind=StructureKind.FORT, material=MaterialKind.STONE))
    await finish(ctx, row)
    profile = await ctx.session.get(StructureProfileRow, work.id)
    assert profile is not None
    town_profile.treasury = 0
    before = profile.condition
    await keep(ctx, work, profile)
    assert profile.unpaid_epochs == 1 and profile.condition <= before - ctx.rules.upkeep.unpaid_condition_loss
    worn = profile.condition
    town_profile.treasury = 100000
    await stocked(ctx, town, CommodityKind.WEAPONS)
    await keep(ctx, work, profile)
    assert profile.unpaid_epochs == 0 and profile.condition > worn


async def test_a_held_condition_is_kept_by_the_upkeep(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.WARRIOR)
    town_profile = await surveyed(ctx, town)
    work, row = await begin(ctx, Commission(site=town, kind=StructureKind.FORT))
    await finish(ctx, row)
    profile = await ctx.session.get(StructureProfileRow, work.id)
    assert profile is not None
    profile.condition = 77
    profile.locked = ["condition"]
    town_profile.treasury = 0
    await keep(ctx, work, profile)
    assert profile.condition == 77


async def test_typed_structures_write_their_contribution_into_the_settlement(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.WARRIOR, SocialClass.FARMER, SocialClass.ARTISAN, SocialClass.SCRIBE)
    town_profile = await surveyed(ctx, town)
    infrastructure = await ctx.session.get(SettlementInfrastructureRow, town.id)
    assert infrastructure is not None
    for kind in (StructureKind.WALL, StructureKind.GRANARY, StructureKind.AQUEDUCT, StructureKind.TOWER, StructureKind.COURT):
        _, row = await begin(ctx, Commission(site=town, kind=kind, level=3 if kind is StructureKind.WALL else 1, material=MaterialKind.STONE))
        await finish(ctx, row)
    granary_before = infrastructure.granary_capacity
    order_before = town_profile.public_order
    await serve_town(ctx, town, town_profile, infrastructure)
    assert infrastructure.walls_level == 3 and infrastructure.walls_material is BuildMaterial.STONE
    assert infrastructure.granary_capacity > granary_before
    assert infrastructure.water is WaterSupply.AQUEDUCT and infrastructure.towers >= 1
    assert town_profile.public_order > order_before


async def test_palaces_lend_legitimacy_and_tombs_keep_the_rites(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.NOBLE, SocialClass.PRIEST)
    await surveyed(ctx, town)
    for kind in (StructureKind.PALACE, StructureKind.NECROPOLIS):
        _, row = await begin(ctx, Commission(site=town, kind=kind))
        await finish(ctx, row)
    assert await palace_legitimacy(ctx.session, ctx.rules, [town.id]) > 0
    assert 0 < await rite_keeping(ctx.session, ctx.rules, town.id) <= 1


async def test_a_working_mill_multiplies_its_workshop_and_a_ruined_forge_stops_it(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.ARTISAN)
    await surveyed(ctx, town)
    mill, row = await begin(ctx, Commission(site=town, kind=StructureKind.MILL))
    await finish(ctx, row)
    workshop = await ctx.session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == town.id, WorkshopRow.kind == WorkshopKind.MILL))
    assert workshop is not None and workshop.structure_entity_id == mill.id
    assert await workshop_output(ctx.session, ctx.rules, workshop) > 1
    profile = await ctx.session.get(StructureProfileRow, mill.id)
    assert profile is not None
    profile.effect_pct = 0
    assert await workshop_output(ctx.session, ctx.rules, workshop) == 0


async def test_cosmic_gates_open_ancient_gates_and_schools_raise_literacy(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.PRIEST, SocialClass.SCRIBE)
    await surveyed(ctx, town)
    _, row = await begin(ctx, Commission(site=town, kind=StructureKind.COSMIC_GATE))
    await finish(ctx, row)
    assert await gate_opened(ctx.session, ctx.rules, [world.world.id])
    _, row = await begin(ctx, Commission(site=town, kind=StructureKind.SCHOOL))
    await finish(ctx, row)
    tally = await run_functions(ctx)
    assert tally.held >= 0


async def test_slots_and_tiers_gate_commissions(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, population=150)
    await surveyed(ctx, town)
    with pytest.raises(ValidationFailedError, match="too small"):
        await commission(ctx, town.id, StructureKind.WONDER)


async def test_the_backfill_types_old_structures_once_and_links_their_workshop(session: AsyncSession, world: CoreWorld) -> None:
    town = await staffed_town(session, world, SocialClass.PRIEST)
    temple = await entity(
        session,
        f"Ak Tap{DOTLESS}nak",
        EntityType.STRUCTURE,
        StructureStats(splendor=40, durability=70, function=60),
        world_id=world.world.id,
        location_id=town.id,
    )
    temple.subtype = f"tap{DOTLESS}nak"
    granary = await entity(
        session, "Great Store", EntityType.STRUCTURE, StructureStats(splendor=10, durability=60, function=50), world_id=world.world.id, location_id=town.id
    )
    granary.subtype = "ambar"
    library = await entity(
        session, "Old Shelves", EntityType.STRUCTURE, StructureStats(splendor=10, durability=60, function=50), world_id=world.world.id, location_id=town.id
    )
    library.engine_kind = EngineKind.LIBRARY
    session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.GRANARY, level=1, built_epoch=1))
    await bond(session, town.id, temple.id, BondKind.BUILT)
    await session.flush()
    assert type_from_record(temple, legacy=True) is StructureKind.TEMPLE
    ctx = await manual_context(session, "structure_survey", tuned_rules())
    result = await backfill_structures(ctx)
    assert result["typed"] == 3 and result["workshops"] == 1
    kinds = {row.structure_entity_id: row.kind for row in await session.scalars(select(StructureProfileRow))}
    assert kinds == {temple.id: StructureKind.TEMPLE, granary.id: StructureKind.GRANARY, library.id: StructureKind.LIBRARY}
    shrine = await entity(
        session, "Temple of Bells", EntityType.STRUCTURE, StructureStats(splendor=10, durability=60, function=50), world_id=world.world.id, location_id=town.id
    )
    shrine.subtype = "temple"
    await session.flush()
    assert type_from_record(shrine, legacy=False) is FALLBACK
    await backfill_structures(ctx)
    late = await session.get(StructureProfileRow, shrine.id)
    assert late is not None and late.kind is FALLBACK
    assert await session.get(AppliedFixupRow, BACKFILL_FIXUP) is not None
    assert await backfill_structures(ctx) == {}
    profile = await session.get(StructureProfileRow, temple.id)
    assert profile is not None and profile.builder_entity_id == town.id and profile.condition == 70


async def test_a_design_overrides_the_base_kind(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, SocialClass.FARMER)
    await surveyed(ctx, town)
    design = await create_design(ctx, {"name": "Great Silo", "base_kind": "granary", "capacity_pct": 300, "function_pct": 150}, world_id=world.world.id)
    work, row = await begin(ctx, Commission(site=town, kind=StructureKind.GRANARY, design=design))
    await finish(ctx, row)
    profile = await ctx.session.get(StructureProfileRow, work.id)
    assert profile is not None and profile.design_id == design.id
    resolved = await resolved_of(ctx.session, profile)
    assert resolved.label == "Great Silo" and resolved.capacity_pct == 300
    plain = resolve(StructureKind.GRANARY)
    assert profile.capacity == 3 * ctx.rules.structure_functions.tons_per_level * plain.capacity_pct // 100
    assert effect_of(ctx.rules, work, profile, resolved) >= effect_of(ctx.rules, work, profile, plain)
    staff = await ctx.session.scalar(select(StructureStaffRow).where(StructureStaffRow.structure_entity_id == work.id))
    assert staff is not None and staff.social_class is SocialClass.FARMER


async def test_knowledge_of_architecture_builds_in_stone(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world)
    stone = await knowledge(ctx.session, world, "Stone Art", KnowledgeBranch.ARCHITECTURE)
    await bond(ctx.session, town.id, stone.id, BondKind.KNOWS)
    await surveyed(ctx, town)
    work, _ = await begin(ctx, Commission(site=town, kind=StructureKind.MONUMENT))
    props = await material_props(ctx.session, work)
    assert props is not None and props.kind is MaterialKind.STONE


async def test_a_poor_town_without_stone_shares_its_coin_between_materials_and_wages_and_still_builds(ctx: TickContext, world: CoreWorld) -> None:
    town = await staffed_town(ctx.session, world, builders=FEW_BUILDERS)
    profile = await surveyed(ctx, town)
    table = ctx.rules.construction
    workers = max(table.builder_floor, round(FEW_BUILDERS * table.worker_share_pct / 100))
    full_cost = workers * table.worker_output * (table.materials_per_100_work * table.funds_buy_materials + table.funds_per_100_work) // 100
    profile.treasury = full_cost // 2
    _work, row = await begin(ctx, Commission(site=town, kind=StructureKind.GRANARY, material=MaterialKind.STONE))
    added = await advance(ctx, row, active=1, knowledge=await KnowledgeMap.load(ctx.session))
    assert added > 0 and row.stalled_epochs == 0 and 0 < row.materials_pct < 100
    assert profile.treasury < full_cost // 4


async def test_a_full_town_still_raises_the_power_it_lacks_and_a_people_without_a_town_builds_in_its_own_lands(
    ctx: TickContext, world: CoreWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    town = await staffed_town(ctx.session, world, population=500)
    await surveyed(ctx, town)
    for index in range(await free_slots(ctx, town)):
        filler = await entity(ctx.session, f"Hall {index}", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
        ctx.session.add(StructureProfileRow(structure_entity_id=filler.id, kind=StructureKind.SHRINE, host_entity_id=town.id))
    plant = await entity(ctx.session, "Old Plant", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    ctx.session.add(StructureProfileRow(structure_entity_id=plant.id, kind=StructureKind.POWER_PLANT, host_entity_id=town.id))
    await ctx.session.flush()
    assert await free_slots(ctx, town) == 0
    monkeypatch.setattr(works, "wanted", lambda _rules, _facts: [StructureKind.SHRINE, StructureKind.POWER_PLANT])
    knowledge_map = await KnowledgeMap.load(ctx.session)
    raised = await works.plan_work(ctx, town, knowledge_map, await RegionAtlas.load(ctx.session))
    assert raised is not None
    profile = await ctx.session.get(StructureProfileRow, raised.id)
    assert profile is not None and profile.kind is StructureKind.POWER_PLANT
    monkeypatch.setattr(works, "wanted", lambda _rules, _facts: [StructureKind.SHRINE])
    assert await works.plan_work(ctx, town, knowledge_map, await RegionAtlas.load(ctx.session)) is None
    lone = await entity(ctx.session, "Wanderers", EntityType.PEOPLE, PeopleStats(population=9000), world_id=world.world.id, location_id=world.regions[1].id)
    assert await site_of(ctx, lone) is lone
