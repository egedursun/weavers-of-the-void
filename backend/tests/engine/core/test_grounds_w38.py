from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityFlagRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.fossil import FossilSource
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.lifecycle_end import LifecycleKind, LifecycleState
from aerona.domain.enums.museum import HoardKind, PieceKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import ArtworkStats, DiseaseStats, ItemStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.fossils import FossilTally, keep_fossils
from aerona.engine.museums.gardens import GardenTally, keep_gardens
from aerona.engine.museums.hoards import HoardTally, keep_hoards, loot, restitute
from aerona.engine.museums.reading import collection_factor, gardens_kept, grandeur, physic_share, refuges
from aerona.engine.primitives.manual import manual_context
from aerona.engine.renown.currencies import amends
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "fossils", rules=tuned_rules(**rules))


async def test_a_kind_that_died_out_leaves_a_bed_that_is_found_yields_luxuries_and_frees_what_it_kept_in_ice(session: AsyncSession, world: CoreWorld) -> None:
    land = world.regions[0]
    town = await settlement(session, "Bonebrook", world, land)
    session.add(SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=land.id, abundance=0, fit=100, since_epoch=0, locked=[]))
    session.add(EntityFlagRow(entity_id=world.species.id, flag=EntityFlag.EXTINCT, epoch=1))
    world.species.status = EntityStatus.DEAD
    world.species.end_epoch = 1
    sickness = await entity(session, "Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(LifecycleStateRow(holder_entity_id=sickness.id, kind=LifecycleKind.DISEASE, state=LifecycleState.ERADICATED, locked=[]))
    await session.flush()
    tally = FossilTally()
    await keep_fossils(await at(session, 2, fossils={"find_pct": 0}), tally)
    bed = await session.scalar(select(FossilBedRow).where(FossilBedRow.source_entity_id == world.species.id))
    assert bed is not None and tally.laid >= 1 and bed.source is FossilSource.EXTINCT_SPECIES and bed.region_entity_id == land.id
    assert bed.found_epoch is None
    bed.frozen, bed.disease_entity_id = True, sickness.id
    await session.flush()
    await keep_fossils(await at(session, 3, fossils={"find_pct": 100}), tally)
    assert bed.found_epoch == 3 and bed.finder_entity_id == town.id and tally.rereleased == 1
    luxuries = await session.scalar(
        select(CommunityStockRow.quantity).where(CommunityStockRow.community_entity_id == town.id, CommunityStockRow.commodity == CommodityKind.LUXURIES)
    )
    assert luxuries is not None and luxuries > 0
    assert await session.scalar(select(OutbreakRow.id).where(OutbreakRow.disease_entity_id == sickness.id)) is not None


async def test_a_museum_gathers_works_gives_grandeur_and_research_and_its_pieces_are_looted_and_given_back(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Archford", world, world.regions[0])
    rival = await settlement(session, "Spoilmere", world, world.regions[1])
    hall = await entity(session, "The Long Hall", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=hall.id, kind=StructureKind.MUSEUM, host_entity_id=town.id, locked=[]))
    work = await entity(session, "The Grey Shore", EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id, location_id=town.id)
    await session.flush()
    ctx = await at(session, 2)
    tally = HoardTally()
    await keep_hoards(ctx, tally)
    hoard = await session.scalar(select(MuseumCollectionRow).where(MuseumCollectionRow.keeper_entity_id == town.id))
    assert hoard is not None and hoard.kind is HoardKind.MUSEUM and tally.founded >= 1
    pieces = list(await session.scalars(select(MuseumPieceRow).where(MuseumPieceRow.collection_id == hoard.id)))
    assert any(piece.item_entity_id == work.id and piece.kind is PieceKind.ART for piece in pieces)
    assert hoard.prestige == len(pieces) * ctx.rules.museums.prestige_per_piece
    assert await grandeur(session, ctx.rules, [town.id]) == hoard.prestige
    assert await collection_factor(session, ctx.rules, town.id, natural=False) > 1
    moved = await loot(ctx, town.id, rival.id)
    taken = await session.get(MuseumPieceRow, pieces[0].id)
    assert moved == len(pieces) and taken is not None and taken.looted_from_entity_id == town.id
    home = await restitute(ctx, taken)
    assert home is not None and home.keeper_entity_id == town.id and taken.returned_by_entity_id == rival.id
    assert await amends(ctx, rival.id, []) >= 1


async def test_a_park_is_laid_out_falls_into_ruin_unpaid_and_gardens_feed_needs_heal_and_shelter_kinds(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenward", world, world.regions[0])
    park = await entity(session, "The Common", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=park.id, kind=StructureKind.PARK, host_entity_id=town.id, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    tally = GardenTally()
    await keep_gardens(ctx, tally)
    garden = await session.scalar(select(GardenRow).where(GardenRow.settlement_entity_id == town.id, GardenRow.kind == GardenKind.PARK))
    assert garden is not None and tally.founded >= 1
    assert tally.neglected >= 1 and garden.condition == ctx.rules.gardens.condition - ctx.rules.gardens.neglect
    garden.condition = ctx.rules.gardens.condition
    garden.kind = GardenKind.PHYSIC
    garden.species = [world.species.id]
    await session.flush()
    assert await gardens_kept(session, ctx.rules, [town.id]) == 1
    assert await physic_share(session, ctx.rules, town.id) > 0
    assert (world.species.id, world.regions[0].id) in await refuges(session, {town.id: world.regions[0].id})


async def test_a_temple_keeps_the_relics_held_in_its_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Shrineholm", world, world.regions[0])
    temple = await entity(session, "The High House", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=temple.id, kind=StructureKind.TEMPLE, host_entity_id=town.id, locked=[]))
    relic = await entity(session, "The First Lamp", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    session.add(ItemProfileRow(item_entity_id=relic.id, item_class=ItemClass.HOLY_RELIC, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    await keep_hoards(ctx, HoardTally())
    hoard = await session.scalar(select(MuseumCollectionRow).where(MuseumCollectionRow.keeper_entity_id == town.id))
    assert hoard is not None and hoard.kind is HoardKind.TEMPLE_TREASURY and hoard.prestige > 0
    piece = await session.scalar(select(MuseumPieceRow).where(MuseumPieceRow.item_entity_id == relic.id))
    assert piece is not None and piece.kind is PieceKind.RELIC
