from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.materials import MATERIALS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.culture import ArtworkProfileRow, BookContentRow, HolderTechniqueRow, ItemProfileRow
from aerona.db.tables.economy import CommunityStockRow, NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.means import ContainerStockRow, NavigationKitRow, SecurityRow, WaterLiftRow, WritingCustomRow, WrittenWorkRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.culture import ArtMode, ItemClass, Technique
from aerona.domain.enums.economy import CommodityKind, MaterialSlot
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.integrity import HarmForce
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.means import ContainerKind, LockKind, NavigationAid, WaterLift, WritingMedium
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.models.entity_stats import ArtworkStats, ItemStats, KnowledgeStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import from_spec
from aerona.engine.means.building import can_repair, weathering
from aerona.engine.means.containers import ContainerTally, keep_containers, packed_capacity, sealed_share
from aerona.engine.means.media import MediaTally, burn_works, keep_media, legible
from aerona.engine.means.navigation import NavigationTally, accuracy_of, instrument_navigation, keep_navigation
from aerona.engine.means.security import SecurityTally, attempt_theft, keep_security
from aerona.engine.means.strength import siege_guard
from aerona.engine.means.water import WaterTally, build_lifts, flooded_yield, irrigation_lift, lifted_water
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, entity, knowledge, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "means", rules=tuned_rules(**rules))


async def homeland(session: AsyncSession, people_id: int, town_id: int) -> None:
    await BondRepository(session).connect(BondDraft(people_id, town_id, BondKind.LIVES_IN, 1, "homeland", role=BondRole.HOMELAND))


async def ground(session: AsyncSession, region: EntityRow, *, rainfall: int = 60, moisture: int = 50) -> RegionEnvironmentRow:
    if await session.get(RegionEnvironmentRow, region.id) is None:
        await environment_survey(await manual_context(session, "survey", rules=tuned_rules()))
    row = await session.get(RegionEnvironmentRow, region.id)
    assert row is not None
    row.rainfall, row.moisture = rainfall, moisture
    await session.flush()
    return row


async def knows(session: AsyncSession, world: CoreWorld, holder: int, branch: KnowledgeBranch, depth: int) -> None:
    lore = await knowledge(session, world, f"Lore of {branch.value} {holder}", branch)
    lore.stats = KnowledgeStats(level=depth, spread=30)
    await bond(session, holder, lore.id, BondKind.KNOWS)
    await session.flush()


async def book_in(session: AsyncSession, world: CoreWorld, town: EntityRow, name: str) -> EntityRow:
    book = await entity(session, name, EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    lore = await entity(session, f"Lore of {name}", EntityType.KNOWLEDGE, KnowledgeStats(level=2, spread=10), world_id=world.world.id)
    session.add(BookContentRow(book_entity_id=book.id, knowledge_entity_id=lore.id, fidelity=80))
    await session.flush()
    return book


async def test_a_people_writes_on_its_medium_and_works_rot_burn_and_bake_by_it(session: AsyncSession, world: CoreWorld) -> None:
    await ground(session, world.regions[0], moisture=100)
    town = await settlement(session, "Reedmere", world, world.regions[0])
    await homeland(session, world.people.id, town.id)
    await knows(session, world, world.people.id, KnowledgeBranch.WRITING, 2)
    session.add(HolderTechniqueRow(holder_entity_id=world.people.id, technique=Technique.PAPER))
    papyrus = await book_in(session, world, town, "The Reed Book")
    clay = await book_in(session, world, town, "The Clay Book")
    await session.flush()
    tally = MediaTally()
    await keep_media(await at(session, 2), tally)
    custom = await session.get(WritingCustomRow, world.people.id)
    assert custom is not None and custom.medium is WritingMedium.PAPER and tally.customs >= 1 and tally.works == 2
    reed = await session.get(WrittenWorkRow, papyrus.id)
    baked = await session.get(WrittenWorkRow, clay.id)
    assert reed is not None and baked is not None
    reed.medium, reed.condition, baked.medium, baked.condition = WritingMedium.PAPYRUS, 80, WritingMedium.CLAY_TABLET, 80
    await session.flush()
    ctx = await at(session, 3)
    await keep_media(ctx, MediaTally())
    assert reed.condition < 80 and baked.condition >= 79
    await burn_works(ctx, town)
    assert baked.condition > 80 and reed.condition < 40
    assert await legible(ctx, papyrus.id) < await legible(ctx, clay.id)


async def test_metalworking_towns_lock_their_stores_and_locks_thwart_thieves_unless_their_craft_undoes_them(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ironhold", world, world.regions[0])
    await knows(session, world, town.id, KnowledgeBranch.METALLURGY, 4)
    await knows(session, world, town.id, KnowledgeBranch.WRITING, 1)
    store = await entity(session, "Ironhold Treasury", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(
        StructureProfileRow(
            structure_entity_id=store.id, kind=StructureKind.BANK, host_entity_id=town.id, construction_state=ConstructionState.COMPLETE, locked=[]
        )
    )
    smith = await mortal(session, "Brann", world, town.id)
    session.add(SkillRow(holder_node_id=smith.id, skill=SkillKind.SMITHING, level=8, peak=8, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    tally = SecurityTally()
    await keep_security(await at(session, 2), tally)
    vault = await session.get(SecurityRow, store.id)
    assert vault is not None and vault.lock is LockKind.TUMBLER and vault.sealed and tally.secured == 1 and tally.improved == 1
    relic = await entity(session, "The Iron Crown", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    thief = await mortal(session, "Vesk", world, town.id)
    vault.lock_quality, vault.guards = 100, 10
    await session.flush()
    first = await attempt_theft(await at(session, 3, security={"lock_pct": 100, "seal_pct": 0}), thief, town, relic)
    assert first.thwarted and vault.thwarted == 1
    session.add(SkillRow(holder_node_id=thief.id, skill=SkillKind.INTRIGUE, level=10, peak=10, last_used_epoch=1, source=SkillSource.PRACTICE))
    vault.guards = 0
    await session.flush()
    second = await attempt_theft(await at(session, 4, security={"lock_pct": 100, "thief_pct": 10, "seal_pct": 0}), thief, town, relic)
    assert not second.thwarted


async def test_dry_towns_lift_water_that_feeds_their_fields_drains_their_mines_and_cleans_them(session: AsyncSession, world: CoreWorld) -> None:
    dry = await ground(session, world.regions[0], rainfall=10)
    town = await settlement(session, "Dustford", world, world.regions[0])
    session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.IRRIGATION))
    await session.flush()
    ctx = await at(session, 2, water_lifting={"build_chance": 100})
    tally = WaterTally()
    await build_lifts(ctx, tally)
    lift = await session.get(WaterLiftRow, (town.id, WaterLift.SHADUF))
    assert lift is not None and tally.built == 1
    assert await irrigation_lift(ctx, dry) > 1.0
    assert await lifted_water(ctx, town.id) == ctx.rules.water_lifting.sanitation_gain
    assert await flooded_yield(ctx, town.id, 90, 100) < 100
    session.add(WaterLiftRow(settlement_entity_id=town.id, device=WaterLift.SCREW, count=1, locked=[]))
    await session.flush()
    assert await flooded_yield(ctx, town.id, 90, 100) == 100


async def test_ports_take_up_instruments_whose_accuracy_spares_sea_roads_and_a_compass_needs_a_magnetic_world(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Saltwick", world, world.regions[0])
    session.add_all(
        [
            HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.SAILING),
            HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.NAVIGATION_STARS),
        ]
    )
    session.add(NavigationKitRow(holder_entity_id=town.id, aid=NavigationAid.LOG_LINE, quality=100, locked=[]))
    session.add(NavigationKitRow(holder_entity_id=town.id, aid=NavigationAid.COMPASS, quality=100, locked=[]))
    world.world.magnetism = 0
    await session.flush()
    ctx = await at(session, 2)
    weak = await accuracy_of(ctx, town.id)
    world.world.magnetism = 90
    await session.flush()
    strong = await accuracy_of(ctx, town.id)
    assert strong > weak > 0
    assert await instrument_navigation(ctx, (town.id, town.id), 1) < 1.0
    tally = NavigationTally()
    await keep_navigation(ctx, tally)
    assert tally.equipped == 0


async def test_a_structure_weathers_burns_and_turns_sieges_by_its_material_and_cannot_be_repaired_once_its_technique_is_lost(
    session: AsyncSession, world: CoreWorld
) -> None:
    await ground(session, world.regions[0], moisture=100)
    town = await settlement(session, "Brickton", world, world.regions[0])
    harbour = await entity(session, "Brickton Quay", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=world.regions[0].id)
    profile = StructureProfileRow(
        structure_entity_id=harbour.id, kind=StructureKind.HARBOUR, host_entity_id=town.id, construction_state=ConstructionState.COMPLETE, locked=[]
    )
    session.add(profile)
    session.add(NodeMaterialRow(node_id=harbour.id, slot=MaterialSlot.BODY, material=MaterialKind.MUD_BRICK))
    await session.flush()
    ctx = await at(session, 2)
    mud = await weathering(ctx, harbour, profile)
    body = await session.get(NodeMaterialRow, (harbour.id, MaterialSlot.BODY))
    assert body is not None
    body.material = MaterialKind.HYDRAULIC_CONCRETE
    await session.flush()
    concrete = await weathering(ctx, harbour, profile)
    assert mud > concrete >= 1.0
    assert not await can_repair(ctx, harbour, profile)
    session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.AQUEDUCT))
    await session.flush()
    assert await can_repair(ctx, harbour, profile)
    stone = siege_guard(ctx.rules, from_spec(MATERIALS[MaterialKind.DRESSED_STONE]), HarmForce.SIEGE)
    thatch = siege_guard(ctx.rules, from_spec(MATERIALS[MaterialKind.THATCH]), HarmForce.SIEGE)
    assert stone < thatch <= 1.0 and siege_guard(ctx.rules, None, HarmForce.FIRE) == 1.0


async def test_skilled_makers_fill_a_town_with_containers_that_carry_its_roads_and_keep_its_stores(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Jarford", world, world.regions[0])
    potter = await mortal(session, "Ula", world, town.id)
    session.add(SkillRow(holder_node_id=potter.id, skill=SkillKind.POTTERY, level=6, peak=6, last_used_epoch=1, source=SkillSource.PRACTICE))
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.ORE, quantity=100, quality=50))
    await session.flush()
    ctx = await at(session, 2)
    tally = ContainerTally()
    await keep_containers(ctx, tally)
    jars = await session.get(ContainerStockRow, (town.id, ContainerKind.JAR))
    amphorae = await session.get(ContainerStockRow, (town.id, ContainerKind.AMPHORA))
    assert jars is not None and amphorae is not None and tally.made > 0 and jars.count + amphorae.count == tally.made
    assert await sealed_share(ctx, town.id, 10) < 1.0
    empty = await settlement(session, "Bareport", world, world.regions[1])
    await session.flush()
    full = 10_000
    assert await packed_capacity(ctx, (empty.id, empty.id), full) < full


async def test_a_store_is_guarded_before_its_town_works_metal_and_locked_once_it_does(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Woodhold", world, world.regions[0])
    store = await entity(session, "Woodhold Granary", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(
        StructureProfileRow(
            structure_entity_id=store.id, kind=StructureKind.GRANARY, host_entity_id=town.id, construction_state=ConstructionState.COMPLETE, locked=[]
        )
    )
    await session.flush()
    ctx = await at(session, 2)
    tally = SecurityTally()
    await keep_security(ctx, tally)
    vault = await session.get(SecurityRow, store.id)
    assert vault is not None and vault.lock is None and vault.guards == ctx.rules.security.seed_guards and tally.secured == 1
    await knows(session, world, town.id, KnowledgeBranch.METALLURGY, 4)
    await keep_security(await at(session, 3), tally)
    assert vault.lock is not None and vault.lock_quality > 0 and tally.locked == 1


async def test_epic_poems_plays_and_book_items_are_written_on_their_maker_s_medium(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Scrollford", world, world.regions[0])
    await homeland(session, world.people.id, town.id)
    poet = await mortal(session, "Ilvi", world, town.id)
    poem = await entity(session, "The Long Road Song", EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id, location_id=town.id)
    song = await entity(session, "A Short Air", EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id, location_id=town.id)
    tome = await entity(session, "A Bound Book", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    session.add_all(
        [
            ArtworkProfileRow(artwork_entity_id=poem.id, medium=ArtMode.VERBAL, author_entity_id=poet.id),
            ArtworkProfileRow(artwork_entity_id=song.id, medium=ArtMode.MUSICAL, author_entity_id=poet.id),
            ItemProfileRow(item_entity_id=tome.id, item_class=ItemClass.BOOK, locked=[]),
        ]
    )
    await session.flush()
    tally = MediaTally()
    await keep_media(await at(session, 2), tally)
    assert await session.get(WrittenWorkRow, poem.id) is not None and await session.get(WrittenWorkRow, tome.id) is not None
    assert await session.get(WrittenWorkRow, song.id) is None and tally.works == 2
