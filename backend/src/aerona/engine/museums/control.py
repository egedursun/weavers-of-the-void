from collections.abc import Mapping
from typing import Any

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gardens import GARDEN_FIELDS, GardenRow
from aerona.db.tables.museums import HOARD_FIELDS, PIECE_FIELDS, MuseumCollectionRow, MuseumPieceRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.museum import HoardKind, PieceKind
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import allowed
from aerona.engine.museums.gardens import GardenTally, keep_gardens, lay_out
from aerona.engine.museums.hoards import HoardTally, hoard_of, keep_hoards, restitute
from aerona.engine.primitives.distance import RegionAtlas


async def require_keeper(ctx: TickContext, keeper_id: int) -> EntityRow:
    keeper = await ctx.session.get(EntityRow, keeper_id)
    if keeper is None:
        raise NotFoundError("No such keeper.")
    return keeper


async def require_hoard(ctx: TickContext, hoard_id: int) -> MuseumCollectionRow:
    hoard = await ctx.session.get(MuseumCollectionRow, hoard_id)
    if hoard is None:
        raise NotFoundError("No such collection.")
    return hoard


async def require_piece(ctx: TickContext, piece_id: int) -> MuseumPieceRow:
    piece = await ctx.session.get(MuseumPieceRow, piece_id)
    if piece is None:
        raise NotFoundError("No such piece.")
    return piece


async def found_hoard(ctx: TickContext, keeper_id: int, kind: HoardKind) -> MuseumCollectionRow:
    keeper = await require_keeper(ctx, keeper_id)
    return await hoard_of(ctx, keeper.id, kind)


async def edit_hoard(ctx: TickContext, hoard_id: int, values: Mapping[str, Any], release: list[str]) -> MuseumCollectionRow:
    hoard = await require_hoard(ctx, hoard_id)
    allowed(values, HOARD_FIELDS, "collection")
    apply(hoard, values, release)
    await ctx.session.flush()
    return hoard


async def remove_hoard(ctx: TickContext, hoard_id: int) -> None:
    await ctx.session.delete(await require_hoard(ctx, hoard_id))
    await ctx.session.flush()


async def add_piece(ctx: TickContext, hoard_id: int, kind: PieceKind, item_id: int) -> MuseumPieceRow:
    hoard = await require_hoard(ctx, hoard_id)
    item = await ctx.session.get(EntityRow, item_id)
    if item is None:
        raise NotFoundError("No such thing to place in the collection.")
    piece = MuseumPieceRow(collection_id=hoard.id, kind=kind, item_entity_id=item.id, acquired_epoch=ctx.epoch, locked=[])
    ctx.session.add(piece)
    await ctx.session.flush()
    return piece


async def edit_piece(ctx: TickContext, piece_id: int, values: Mapping[str, Any], release: list[str]) -> MuseumPieceRow:
    piece = await require_piece(ctx, piece_id)
    allowed(values, PIECE_FIELDS, "piece")
    apply(piece, values, release)
    await ctx.session.flush()
    return piece


async def remove_piece(ctx: TickContext, piece_id: int) -> None:
    await ctx.session.delete(await require_piece(ctx, piece_id))
    await ctx.session.flush()


async def return_piece(ctx: TickContext, piece_id: int) -> MuseumCollectionRow:
    piece = await require_piece(ctx, piece_id)
    home = await restitute(ctx, piece)
    if home is None:
        raise ValidationFailedError("That piece was not taken from anyone.")
    return home


async def run_hoards(ctx: TickContext) -> HoardTally:
    tally = HoardTally()
    await keep_hoards(ctx, tally)
    return tally


async def require_town(ctx: TickContext, town_id: int) -> EntityRow:
    town = await ctx.session.get(EntityRow, town_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        raise NotFoundError("No such town.")
    return town


async def require_garden(ctx: TickContext, garden_id: int) -> GardenRow:
    garden = await ctx.session.get(GardenRow, garden_id)
    if garden is None:
        raise NotFoundError("No such garden.")
    return garden


async def found_garden(ctx: TickContext, town_id: int, kind: GardenKind) -> GardenRow:
    town = await require_town(ctx, town_id)
    return await lay_out(ctx, town.id, kind, None, await RegionAtlas.load(ctx.session))


async def edit_garden(ctx: TickContext, garden_id: int, values: Mapping[str, Any], release: list[str]) -> GardenRow:
    garden = await require_garden(ctx, garden_id)
    allowed(values, GARDEN_FIELDS, "garden")
    apply(garden, values, release)
    await ctx.session.flush()
    return garden


async def remove_garden(ctx: TickContext, garden_id: int) -> None:
    await ctx.session.delete(await require_garden(ctx, garden_id))
    await ctx.session.flush()


async def plant(ctx: TickContext, garden_id: int, species_id: int, present: bool) -> GardenRow:
    garden = await require_garden(ctx, garden_id)
    species = await ctx.session.get(EntityRow, species_id)
    if species is None or species.entity_type is not EntityType.SPECIES:
        raise NotFoundError("No such kind of life.")
    kept = [item for item in garden.species if item != species.id]
    garden.species = [*kept, species.id] if present else kept
    await ctx.session.flush()
    return garden


async def run_gardens(ctx: TickContext) -> GardenTally:
    tally = GardenTally()
    await keep_gardens(ctx, tally)
    return tally
