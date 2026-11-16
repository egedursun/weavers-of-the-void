from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.couplings import DeepSealRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.couplings import SealKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.couplings.rite_body import owned_rites
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.stats import stat_or


async def active_seal(session: AsyncSession, place_id: int) -> DeepSealRow | None:
    return await session.scalar(
        select(DeepSealRow).where(DeepSealRow.place_entity_id == place_id, DeepSealRow.broken_epoch.is_(None), DeepSealRow.strength > 0).limit(1)
    )


async def seal_deep(ctx: TickContext, place_id: int, kind: SealKind, sealer_id: int | None, strength: int | None = None) -> DeepSealRow:
    table = ctx.rules.deep_seals
    row = DeepSealRow(
        place_entity_id=place_id,
        kind=kind,
        strength=clamp_percent(strength if strength is not None else table.strength),
        decay=table.rite_decay if kind is SealKind.RITE else table.decay,
        sealer_node_id=sealer_id,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def knows_school(ctx: TickContext, holder_id: int, school: MagicSchool) -> bool:
    rites = await owned_rites(ctx, holder_id)
    if not rites:
        return False
    found = await ctx.session.scalar(
        select(RiteProfileRow.rite_entity_id).where(RiteProfileRow.rite_entity_id.in_(rites), RiteProfileRow.school == school).limit(1)
    )
    return found is not None


async def seal_after_breach(ctx: TickContext, resource: EntityRow, community: EntityRow) -> DeepSealRow | None:
    if held(resource.id, community.id) or await active_seal(ctx.session, resource.id) is not None:
        return None
    if await knows_school(ctx, community.id, MagicSchool.WARDING):
        kind = SealKind.RITE
    elif stat_or(community, "prosperity", 0) >= ctx.rules.deep_seals.structure_prosperity:
        kind = SealKind.STRUCTURE
    else:
        return None
    row = await seal_deep(ctx, resource.id, kind, community.id)
    await note(ctx, f"{community.name} sealed the deep beneath {resource.name}.", key="seal.made", ids=[resource.id, community.id])
    return row


async def danger_below(ctx: TickContext, region_id: int | None) -> int:
    if region_id is None:
        return 0
    statement = (
        select(EntityRow)
        .join(SpeciesRangeRow, SpeciesRangeRow.species_entity_id == EntityRow.id)
        .where(SpeciesRangeRow.region_entity_id == region_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.SPECIES)
    )
    return max((stat_or(species, "danger", 0) for species in await ctx.session.scalars(statement)), default=0)


async def test_seal(ctx: TickContext, row: DeepSealRow) -> None:
    table = ctx.rules.deep_seals
    place = await ctx.session.get(EntityRow, row.place_entity_id)
    if place is None or held(place.id) or "strength" in row.locked:
        return
    loss = row.decay
    if row.kind is SealKind.RITE and row.sealer_node_id is not None and not await knows_school(ctx, row.sealer_node_id, MagicSchool.WARDING):
        loss += table.lapsed_rite
    if await danger_below(ctx, place.location_id) >= table.beast_danger:
        loss += table.beast_test
    profile = await ctx.session.get(ResourceProfileRow, place.id)
    if profile is not None and profile.reserve * PERCENT < profile.initial_reserve * table.unseal_reserve_pct:
        row.strength = 0
        row.broken_epoch = ctx.epoch
        await note(ctx, f"The miners of {place.name} dug through its seal to reach the deep again.", key="seal.unsealed", ids=[place.id])
        return
    row.strength = clamp_percent(row.strength - loss)
    if row.strength == 0:
        row.broken_epoch = ctx.epoch
        await note(ctx, f"The seal beneath {place.name} gave way; the deep is open again.", key="seal.broken", ids=[place.id])


@reads("table.bonds", "table.deep_seals", "table.resource_profiles", "table.rite_profiles", "table.species_ranges")
@writes("table.deep_seals")
async def deep_seals(ctx: TickContext) -> None:
    for row in list(await ctx.session.scalars(select(DeepSealRow).where(DeepSealRow.broken_epoch.is_(None)).order_by(DeepSealRow.id))):
        await test_seal(ctx, row)
    await ctx.session.flush()
