from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import PlaceKind, SecretKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record


async def places_by_region(session: AsyncSession, kind: PlaceKind) -> Counter[int]:
    atlas = await RegionAtlas.load(session)
    found: Counter[int] = Counter()
    for place_id in await session.scalars(select(PlaceProfileRow.entity_id).where(PlaceProfileRow.kind == kind).order_by(PlaceProfileRow.entity_id)):
        region = atlas.top_region(place_id)
        if region is not None:
            found[region] += 1
    return found


async def ways_by_region(session: AsyncSession) -> Counter[int]:
    atlas = await RegionAtlas.load(session)
    found: Counter[int] = Counter()
    revealed = select(PlaceSecretRow.place_entity_id).where(PlaceSecretRow.kind == SecretKind.HIDDEN_ROUTE, PlaceSecretRow.revealed_epoch.is_not(None))
    for place_id in await session.scalars(revealed.order_by(PlaceSecretRow.id)):
        region = atlas.top_region(place_id)
        if region is not None:
            found[region] += 1
    return found


async def collapse_sinkhole(ctx: TickContext, place: EntityRow) -> int:
    if held(place.id) or not ctx.rng(f"sinkhole.{place.id}.{ctx.epoch}").chance(ctx.rules.places.sinkhole_collapse_pct):
        return 0
    harm = ctx.rules.places.sinkhole_collapse_harm
    built = (
        select(StructureProfileRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(EntityRow.location_id == place.id, EntityRow.status == EntityStatus.CANON)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    harmed = 0
    for row in await ctx.session.scalars(built):
        if held(row.structure_entity_id) or "condition" in (row.locked or []):
            continue
        row.condition = clamp_int(row.condition - harm, 0, PERCENT)
        harmed += 1
    await record(ctx, "place.collapsed", roles={IncidentRole.PLACE: place.id}, facts={"buildings": harmed, "harm": harm}, place=place.id)
    return harmed


async def bathe(ctx: TickContext, place: EntityRow) -> int:
    heal = ctx.rules.places.hot_spring_heal
    bathers = select(EntityRow.id).where(
        await present_in(ctx.session, place), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    eased = 0
    for wound in await ctx.session.scalars(
        select(InjuryRow).where(InjuryRow.bearer_node_id.in_(bathers), InjuryRow.healed_epoch.is_(None)).order_by(InjuryRow.id)
    ):
        if held(wound.bearer_node_id) or wound.severity <= 1:
            continue
        wound.severity = max(1, wound.severity - heal)
        eased += 1
    return eased


async def trap_beasts(ctx: TickContext, place: EntityRow, region_id: int | None) -> int:
    if region_id is None or held(region_id):
        return 0
    trapped = 0
    for row in await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.abundance > 0).order_by(SpeciesRangeRow.species_entity_id)
    ):
        if held(row.species_entity_id) or "abundance" in (row.locked or []):
            continue
        row.abundance = max(0, row.abundance - ctx.rules.places.tar_pit_trap)
        trapped += 1
    return trapped
