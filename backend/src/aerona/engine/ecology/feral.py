from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import STAGE_ORDER, DomesticationStage
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int


@dataclass
class FeralTally:
    released: int = 0
    reverted: int = 0
    wild: int = 0


async def release_herd(ctx: TickContext, herd: HerdRow, atlas: RegionAtlas | None = None) -> SpeciesRangeRow | None:
    atlas = atlas or await RegionAtlas.load(ctx.session)
    region_id = atlas.top_region(herd.community_entity_id)
    species = await ctx.session.get(EntityRow, herd.species_entity_id)
    profile = await ctx.session.get(SpeciesProfileRow, herd.species_entity_id)
    await ctx.session.delete(herd)
    if region_id is None or species is None:
        return None
    row = await ctx.session.get(SpeciesRangeRow, (species.id, region_id))
    if row is None:
        row = SpeciesRangeRow(species_entity_id=species.id, region_entity_id=region_id, abundance=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "abundance" not in row.locked:
        row.abundance = clamp_int((row.abundance or 0) + ctx.rules.feral.release_abundance, 0, PERCENT)
    row.updated_epoch = ctx.epoch
    if profile is not None and profile.stage is not DomesticationStage.WILD and "feral_epoch" not in profile.locked:
        profile.feral_epoch = ctx.epoch
    region = await ctx.session.get(EntityRow, region_id)
    if region is not None:
        await note(ctx, f"The herds of {species.name} went loose in {region.name}.", key="ecology.herd_feral", ids=[species.id, region.id])
    await ctx.session.flush()
    return row


async def abandoned_herds(ctx: TickContext) -> list[HerdRow]:
    statement = (
        select(HerdRow)
        .join(EntityRow, EntityRow.id == HerdRow.community_entity_id)
        .where(EntityRow.status != EntityStatus.CANON)
        .order_by(HerdRow.community_entity_id, HerdRow.species_entity_id)
    )
    return [herd for herd in await ctx.session.scalars(statement) if not held(herd.community_entity_id, herd.species_entity_id)]


async def kept_anywhere(ctx: TickContext, species_id: int) -> bool:
    return bool(await ctx.session.scalar(select(func.count()).select_from(HerdRow).where(HerdRow.species_entity_id == species_id)))


async def run_wild(ctx: TickContext, tally: FeralTally) -> None:
    table = ctx.rules.feral
    atlas = await RegionAtlas.load(ctx.session)
    for herd in await abandoned_herds(ctx):
        if await release_herd(ctx, herd, atlas) is not None:
            tally.released += 1
    for profile in list(await ctx.session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.feral_epoch.is_not(None)))):
        if profile.feral_epoch is None or held(profile.species_entity_id) or await kept_anywhere(ctx, profile.species_entity_id):
            continue
        species = await ctx.session.get(EntityRow, profile.species_entity_id)
        if species is None:
            continue
        if profile.stage is not DomesticationStage.WILD:
            if ctx.epoch - profile.stage_epoch >= table.revert_epochs and "stage" not in profile.locked:
                profile.stage = STAGE_ORDER[STAGE_ORDER.index(profile.stage) - 1]
                profile.stage_epoch = ctx.epoch
                tally.reverted += 1
            continue
        if ctx.epoch - profile.feral_epoch >= table.breed_after and "feral_epoch" not in profile.locked:
            profile.feral_epoch = None
            tally.wild += 1
            await note(ctx, f"{species.name}, once kept, is a wild breed of its own now.", key="ecology.feral_breed", ids=[species.id])
    await ctx.session.flush()
