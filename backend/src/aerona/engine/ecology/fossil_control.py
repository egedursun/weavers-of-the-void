from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fossils import FOSSIL_FIELDS, FossilBedRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.fossil import FossilSource
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.ecology.fossils import FossilTally, finder_in, is_frozen, keep_fossils, reveal
from aerona.engine.gatherings.control import allowed


async def require_region(ctx: TickContext, region_id: int) -> EntityRow:
    region = await ctx.session.get(EntityRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        raise NotFoundError("No such land.")
    return region


async def require_bed(ctx: TickContext, bed_id: int) -> FossilBedRow:
    bed = await ctx.session.get(FossilBedRow, bed_id)
    if bed is None:
        raise NotFoundError("No such fossil bed.")
    return bed


async def place_bed(ctx: TickContext, region_id: int, source: FossilSource, richness: int) -> FossilBedRow:
    region = await require_region(ctx, region_id)
    bed = FossilBedRow(
        region_entity_id=region.id,
        world_id=region.world_id,
        source=source,
        richness=max(1, min(100, richness)),
        frozen=await is_frozen(ctx, region.id, region.world_id),
        laid_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(bed)
    await ctx.session.flush()
    return bed


async def edit_bed(ctx: TickContext, bed_id: int, values: Mapping[str, Any], release: list[str]) -> FossilBedRow:
    bed = await require_bed(ctx, bed_id)
    allowed(values, FOSSIL_FIELDS, "fossil bed")
    apply(bed, values, release)
    await ctx.session.flush()
    return bed


async def remove_bed(ctx: TickContext, bed_id: int) -> None:
    await ctx.session.delete(await require_bed(ctx, bed_id))
    await ctx.session.flush()


async def reveal_bed(ctx: TickContext, bed_id: int) -> FossilBedRow:
    bed = await require_bed(ctx, bed_id)
    if bed.found_epoch is not None:
        raise ValidationFailedError("That bed has already been found.")
    await reveal(ctx, bed, await finder_in(ctx, bed.region_entity_id), FossilTally())
    return bed


async def first_hidden(ctx: TickContext, region_id: int) -> FossilBedRow | None:
    return await ctx.session.scalar(
        select(FossilBedRow).where(FossilBedRow.region_entity_id == region_id, FossilBedRow.found_epoch.is_(None)).order_by(FossilBedRow.id).limit(1)
    )


async def run_fossils(ctx: TickContext) -> FossilTally:
    tally = FossilTally()
    await keep_fossils(ctx, tally)
    return tally
