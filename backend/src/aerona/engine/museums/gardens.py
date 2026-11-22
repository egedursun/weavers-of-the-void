from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.museums import PLANTING_SPECIES_CLASSS
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import GameReserveRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import SpeciesClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import domains_of, faithful_communities, living_gods
from aerona.engine.divine.standing import standing_row
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or

LAID_OUT = {
    StructureKind.PARK: GardenKind.PARK,
    StructureKind.BOTANICAL_GARDEN: GardenKind.PHYSIC,
    StructureKind.CEMETERY: GardenKind.CEMETERY,
    StructureKind.MONASTERY: GardenKind.MONASTERY,
}
GROWING = frozenset({Domain.PLANTS, Domain.LIFE, Domain.HARVEST, Domain.HUNT})
PLANTED = {GardenKind.HUNTING_PARK: (SpeciesClass.ANIMAL,)}


@dataclass
class GardenTally:
    founded: int = 0
    tended: int = 0
    neglected: int = 0
    loved: int = 0


async def known_gardens(ctx: TickContext) -> set[tuple[int, GardenKind]]:
    return {(row.settlement_entity_id, row.kind) for row in await ctx.session.scalars(select(GardenRow))}


async def lay_out(ctx: TickContext, town_id: int, kind: GardenKind, structure_id: int | None, atlas: RegionAtlas) -> GardenRow:
    table = ctx.rules.gardens
    row = GardenRow(
        settlement_entity_id=town_id,
        structure_entity_id=structure_id,
        kind=kind,
        species=await planting(ctx, atlas, town_id, kind),
        upkeep=table.upkeep,
        condition=table.condition,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def planting(ctx: TickContext, atlas: RegionAtlas, town_id: int, kind: GardenKind) -> list[int]:
    region = atlas.top_region(town_id)
    if region is None:
        return []
    classes = PLANTED.get(kind, PLANTING_SPECIES_CLASSS)
    found = await ctx.session.scalars(
        select(SpeciesRangeRow.species_entity_id)
        .join(SpeciesProfileRow, SpeciesProfileRow.species_entity_id == SpeciesRangeRow.species_entity_id)
        .where(SpeciesRangeRow.region_entity_id == region, SpeciesRangeRow.abundance > 0, SpeciesProfileRow.species_class.in_(list(classes)))
        .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.species_entity_id)
        .limit(ctx.rules.gardens.planted)
    )
    return [int(item) for item in found]


async def towns_in(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> list[EntityRow]:
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [town for town in towns if atlas.top_region(town.id) == region_id]


async def found_gardens(ctx: TickContext, atlas: RegionAtlas, tally: GardenTally) -> None:
    known = await known_gardens(ctx)
    wanted: list[tuple[int, GardenKind, int | None]] = []
    for structure_id, host_id, hall in await ctx.session.execute(
        select(StructureProfileRow.structure_entity_id, StructureProfileRow.host_entity_id, StructureProfileRow.kind).where(
            StructureProfileRow.kind.in_(list(LAID_OUT)), StructureProfileRow.host_entity_id.is_not(None)
        )
    ):
        if host_id is not None:
            wanted.append((host_id, LAID_OUT[hall], structure_id))
    groves = await ctx.session.execute(
        select(EntityRow.location_id).join(PlaceProfileRow, PlaceProfileRow.entity_id == EntityRow.id).where(PlaceProfileRow.kind == PlaceKind.GROVE)
    )
    for (place_region,) in groves.all():
        for town in await towns_in(ctx, atlas, place_region) if place_region is not None else []:
            wanted.append((town.id, GardenKind.SACRED_GROVE, None))
    for reserve_region in sorted(set(await ctx.session.scalars(select(GameReserveRow.region_entity_id)))):
        near = await towns_in(ctx, atlas, reserve_region)
        if near:
            seat = max(near, key=lambda town: (stat_or(town, "population", 0), -town.id))
            wanted.append((seat.id, GardenKind.HUNTING_PARK, None))
    for town in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if stat_or(town, "prosperity", 0) >= ctx.rules.gardens.pleasure_from:
            wanted.append((town.id, GardenKind.PLEASURE, None))
    for town_id, garden_kind, hall_id in wanted:
        if (town_id, garden_kind) in known or held(town_id):
            continue
        await lay_out(ctx, town_id, garden_kind, hall_id, atlas)
        known.add((town_id, garden_kind))
        tally.founded += 1


async def tend(ctx: TickContext, garden: GardenRow, tally: GardenTally) -> None:
    table = ctx.rules.gardens
    town = await ctx.session.get(EntityRow, garden.settlement_entity_id)
    if town is None or town.status is not EntityStatus.CANON:
        return
    paid = await take_coin(ctx.session, ctx.rules, town, garden.upkeep)
    if "condition" not in garden.locked:
        garden.condition = clamp_int(garden.condition + (table.tended if paid else -table.neglect), 0, PERCENT)
    garden.unpaid_epochs = 0 if paid else garden.unpaid_epochs + 1
    tally.tended += int(paid)
    tally.neglected += int(not paid)


async def love_groves(ctx: TickContext, tally: GardenTally) -> None:
    groves = list(await ctx.session.scalars(select(GardenRow).where(GardenRow.kind == GardenKind.SACRED_GROVE, GardenRow.condition > 0)))
    if not groves:
        return
    towns = {garden.settlement_entity_id for garden in groves}
    for god in await living_gods(ctx.session):
        if not set(domains_of(god)) & GROWING or held(god.id):
            continue
        faithful = {community.id for community in await faithful_communities(ctx.session, god.id)}
        for town_id in sorted(towns & faithful):
            if held(town_id):
                continue
            row = await standing_row(ctx, town_id, god.id)
            if "love" not in row.locked:
                row.love = clamp_int(row.love + ctx.rules.gardens.grove_standing, 0, PERCENT)
                tally.loved += 1


async def keep_gardens(ctx: TickContext, tally: GardenTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await found_gardens(ctx, atlas, tally)
    for garden in list(await ctx.session.scalars(select(GardenRow).order_by(GardenRow.id))):
        if held(garden.settlement_entity_id):
            continue
        await tend(ctx, garden, tally)
    await love_groves(ctx, tally)
    await ctx.session.flush()
