from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agrarian import GameReserveRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.protected_nature import ConservationMovementRow, ProtectedAreaRow, SpeciesProtectionRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.faction import FactionKind, MovementCause
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.protected_nature import ProtectedUse, ProtectionBasis, ProtectionMeasure
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.agrarian.book import reserve_factor
from aerona.engine.context import TickContext
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import add_flag, remove_flag
from aerona.engine.primitives.stats import stat
from aerona.engine.protected_nature.areas import lift, protect_area, protect_rights, tend_areas
from aerona.engine.protected_nature.book import NatureTally, hunting_marks, spared_species
from aerona.engine.protected_nature.movement import loss_of_wild, protect_for_movement, tend_movements
from aerona.engine.protected_nature.species import protect_species, tend_species
from tests.engine.core.factories import CoreWorld, entity, settlement, surveyed, tuned_rules


async def land_of(session: AsyncSession, world: CoreWorld) -> RegionEnvironmentRow:
    await surveyed(session, world)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    return land


async def test_a_hunting_ban_by_land_or_by_kind_cuts_the_hunt(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    tally = NatureTally()
    area = await protect_area(ctx, world.regions[0], ProtectionBasis.LAW, [ProtectedUse.HUNTING], tally)
    area.strength = 100
    marks = await hunting_marks(session, ctx.rules)
    assert reserve_factor(ctx.rules, marks, world.species.id, world.regions[0].id) < 1
    await protect_species(ctx, world.species, ProtectionBasis.FAITH, [ProtectionMeasure.HUNTING_BAN], tally)
    assert (await spared_species(session, ctx.rules))[world.species.id] == ctx.rules.protected_nature.use_cut_per_strength_pct / 100


async def test_a_protected_land_regrows_and_its_wildlife_recovers_while_its_towns_suffer(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    land = await land_of(session, world)
    land.base_forest, land.forest_cover, land.farmed = 80, 20, 30
    town = await settlement(session, "Woodedge", world, world.regions[0], population=3000)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=0, locked=[]))
    session.add(SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=world.regions[0].id, abundance=40, locked=[]))
    await session.flush()
    area = await protect_area(ctx, world.regions[0], ProtectionBasis.LAW, [ProtectedUse.LOGGING, ProtectedUse.FARMING, ProtectedUse.HUNTING], NatureTally())
    area.strength = 100
    wealth = stat(town, "prosperity") or 0
    await tend_areas(ctx, NatureTally())
    wild = await session.get(SpeciesRangeRow, (world.species.id, world.regions[0].id))
    profile = await session.get(SettlementProfileRow, town.id)
    assert land.forest_cover > 20 and land.farmed < 30 and wild is not None and wild.abundance > 40
    assert profile is not None and profile.unrest > 0 and (stat(town, "prosperity") or 0) < wealth


async def test_want_around_a_weak_protection_draws_poachers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "poached", tuned_rules(protected_nature={"poaching_per_price_pct": 100, "poached_at": 5}))
    land = await land_of(session, world)
    land.harvest_pct = 20
    await settlement(session, "Hungerton", world, world.regions[0], population=2000, prosperity=5)
    area = await protect_area(ctx, world.regions[0], ProtectionBasis.CUSTOM, [ProtectedUse.HUNTING], NatureTally())
    area.strength = 10
    tally = NatureTally()
    await tend_areas(ctx, tally)
    assert area.poaching >= 5 and tally.poached == 1
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "nature.poached")) is not None


async def test_a_protected_kind_is_bred_brought_back_and_recovers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "brought", tuned_rules(protected_nature={"reintroduction_success_pct": 100}))
    living = SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=world.regions[0].id, abundance=30, fit=60, locked=[])
    left = SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=world.regions[1].id, abundance=0, fit=60, locked=[])
    session.add_all([living, left])
    await add_flag(session, world.species.id, EntityFlag.ENDANGERED, 0)
    await session.flush()
    measures = [ProtectionMeasure.BREEDING_PROGRAMME, ProtectionMeasure.REINTRODUCTION]
    row = await protect_species(ctx, world.species, ProtectionBasis.LAW, measures, NatureTally())
    assert row.endangered_at_start
    tally = NatureTally()
    await tend_species(ctx, tally)
    assert living.abundance > 30 and left.abundance > 0 and tally.reintroduced == 1
    await remove_flag(session, world.species.id, EntityFlag.ENDANGERED)
    await tend_species(ctx, tally)
    assert row.recovered_epoch == ctx.epoch and tally.recovered == 1


async def test_lost_wild_land_raises_a_movement_that_protects_land_when_it_rises(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    land = await land_of(session, world)
    land.base_forest, land.forest_cover = 90, 10
    town = await settlement(session, "Stumpholm", world, world.regions[0], population=3000)
    assert await loss_of_wild(ctx, town) > 0
    movement = await entity(session, "The Green Movement", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=movement.id, kind=FactionKind.MOVEMENT, home_entity_id=town.id, influence_over={}, locked=[]))
    realm = await entity(session, "The Green Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    rule = next(iter(DecisionRule))
    session.add(PolityProfileRow(polity_entity_id=realm.id, government=next(iter(GovernmentKind)), decision_rule=rule, core_entity_id=town.id))
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    row = MovementProfileRow(faction_entity_id=movement.id, cause=MovementCause.CONSERVATION, polity_entity_id=realm.id, support=40, locked=[])
    session.add(row)
    await session.flush()
    tally = NatureTally()
    await tend_movements(ctx, tally)
    aims = await session.get(ConservationMovementRow, movement.id)
    assert aims is not None and tally.movements == 1 and aims.cohort_support
    found = (await RealmBook.load(session)).realms[realm.id]
    session.add(SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=world.regions[0].id, abundance=10, fit=60, locked=[]))
    await add_flag(session, world.species.id, EntityFlag.ENDANGERED, 0)
    await session.flush()
    await protect_for_movement(ctx, found, row)
    area = await session.scalar(select(ProtectedAreaRow).where(ProtectedAreaRow.region_entity_id == world.regions[0].id))
    assert area is not None and area.protector_node_id == realm.id and ProtectedUse.LOGGING.value in area.banned_uses
    guarded = await session.scalar(select(SpeciesProtectionRow).where(SpeciesProtectionRow.species_entity_id == world.species.id))
    assert guarded is not None and guarded.holder_node_id == realm.id and guarded.endangered_at_start


async def test_game_reserves_become_lands_protected_against_hunting(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    session.add(GameReserveRow(region_entity_id=world.regions[2].id, strictness=70, locked=[]))
    await session.flush()
    await protect_rights(ctx, NatureTally())
    area = await session.scalar(select(ProtectedAreaRow).where(ProtectedAreaRow.region_entity_id == world.regions[2].id))
    assert area is not None and area.basis is ProtectionBasis.LAW and area.banned_uses == [ProtectedUse.HUNTING.value] and area.strength == 70
    assert await session.scalar(select(EntityRow.id).where(EntityRow.id == world.regions[2].id)) is not None


async def test_a_reserve_set_aside_in_a_later_epoch_is_protected_and_a_lifted_protection_stays_lifted(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    session.add(GameReserveRow(region_entity_id=world.regions[2].id, strictness=70, locked=[]))
    await session.flush()
    tally = NatureTally()
    await protect_rights(ctx, tally)
    first = await session.scalar(select(ProtectedAreaRow).where(ProtectedAreaRow.region_entity_id == world.regions[2].id))
    assert first is not None
    await lift(ctx, first, tally)
    session.add(GameReserveRow(region_entity_id=world.regions[1].id, strictness=40, locked=[]))
    await session.flush()
    await protect_rights(ctx, tally)
    later = await session.scalar(select(ProtectedAreaRow).where(ProtectedAreaRow.region_entity_id == world.regions[1].id))
    assert later is not None and later.strength == 40
    again = list(await session.scalars(select(ProtectedAreaRow).where(ProtectedAreaRow.region_entity_id == world.regions[2].id)))
    assert len(again) == 1 and again[0].lifted_epoch is not None
