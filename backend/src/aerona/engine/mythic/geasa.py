from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.mythic import GEAS_ACTS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.dominion import DominionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mythic import GeasRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mythic import GeasLayer, GeasMode, GeasState
from aerona.engine.body.afflictions import afflict
from aerona.engine.context import TickContext
from aerona.engine.divine.standing import standing_row
from aerona.engine.gods.queries import community_of
from aerona.engine.mythic.geas_acts import break_geas
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record


@dataclass
class GeasTally:
    laid: int = 0
    kept: int = 0
    broken: int = 0


async def lay_geas(ctx: TickContext, bearer: EntityRow, *, layer_node_id: int | None, layer: GeasLayer, mode: GeasMode, act: ActKind) -> GeasRow:
    row = GeasRow(
        bearer_entity_id=bearer.id,
        layer_node_id=layer_node_id,
        layer=layer,
        mode=mode,
        act=act,
        state=GeasState.KEPT,
        favour=0,
        laid_epoch=ctx.epoch,
        last_kept_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def seer_near(ctx: TickContext, place_id: int | None) -> EntityRow | None:
    if place_id is None:
        return None
    found: EntityRow | None = await ctx.session.scalar(
        select(EntityRow)
        .where(await present_among(ctx.session, [place_id]), EntityRow.mortal_role == MortalRole.SEER, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def birth_geas(ctx: TickContext, child: EntityRow, patron_id: int | None) -> GeasRow | None:
    if patron_id is None or held(child.id):
        return None
    rng = ctx.rng(f"geas.birth.{child.id}")
    if not rng.chance(ctx.rules.geasa.birth_pct):
        return None
    mode = GeasMode.DUTY if rng.chance(PERCENT // 4) else GeasMode.TABOO
    seer = await seer_near(ctx, child.location_id)
    layer = GeasLayer.SEER if seer is not None else GeasLayer.GOD
    return await lay_geas(ctx, child, layer_node_id=patron_id, layer=layer, mode=mode, act=rng.pick(list(GEAS_ACTS[mode])))


async def doom(ctx: TickContext, row: GeasRow, bearer: EntityRow, why: str) -> None:
    if "state" in row.locked:
        return
    break_geas(row, ctx.epoch)
    await afflict(ctx, bearer, PackageKind.GEAS_DOOM, Transmission.CURSE, source_node_id=row.layer_node_id)
    await record(ctx, "mythic.geas_broken", roles={IncidentRole.SUBJECT: bearer.id}, facts={"why": why}, kind=ChronicleKind.WORLD)


async def doom_broken(ctx: TickContext, tally: GeasTally) -> None:
    recent = select(GeasRow).where(GeasRow.state == GeasState.BROKEN, GeasRow.broken_epoch >= ctx.epoch - 1)
    for row in list(await ctx.session.scalars(recent)):
        bearer = await ctx.session.get(EntityRow, row.bearer_entity_id)
        if bearer is None or held(bearer.id):
            continue
        doomed = await ctx.session.scalar(
            select(AfflictionRow.id).where(
                AfflictionRow.bearer_node_id == bearer.id, AfflictionRow.package == PackageKind.GEAS_DOOM, AfflictionRow.cured_epoch.is_(None)
            )
        )
        if doomed is None and await afflict(ctx, bearer, PackageKind.GEAS_DOOM, Transmission.CURSE, source_node_id=row.layer_node_id) is not None:
            await record(ctx, "mythic.geas_broken", roles={IncidentRole.SUBJECT: bearer.id}, facts={"act": spoken(row.act)}, kind=ChronicleKind.WORLD)
            tally.broken += 1


async def favour(ctx: TickContext, atlas: RegionAtlas, row: GeasRow, bearer: EntityRow) -> None:
    table = ctx.rules.geasa
    if row.layer_node_id is None:
        return
    if "favour" not in row.locked:
        row.favour = clamp_int(row.favour + table.favour, 0, PERCENT)
    community = await community_of(ctx.session, bearer)
    if community is not None and not held(community.id, row.layer_node_id):
        standing = await standing_row(ctx, community.id, row.layer_node_id)
        if "awe" not in standing.locked:
            standing.awe = clamp_int(standing.awe + table.favour, 0, PERCENT)
    region = atlas.top_region(bearer.id)
    claim = await ctx.session.get(DominionRow, (row.layer_node_id, region)) if region is not None else None
    if claim is not None and "strength" not in claim.locked:
        claim.strength = clamp_int(claim.strength + table.favour_dominion, 0, PERCENT)


async def tend_geasa(ctx: TickContext, tally: GeasTally) -> None:
    table = ctx.rules.geasa
    await doom_broken(ctx, tally)
    atlas = await RegionAtlas.load(ctx.session)
    for row in list(await ctx.session.scalars(select(GeasRow).where(GeasRow.state == GeasState.KEPT).order_by(GeasRow.id))):
        bearer = await ctx.session.get(EntityRow, row.bearer_entity_id)
        if bearer is None or bearer.status is not EntityStatus.CANON or bearer.entity_type is not EntityType.MORTAL or held(bearer.id):
            continue
        if row.mode is GeasMode.DUTY and ctx.epoch - row.last_kept_epoch > table.duty_epochs:
            await doom(ctx, row, bearer, f"it left undone {spoken(row.act)}")
            tally.broken += 1
            continue
        await favour(ctx, atlas, row, bearer)
        tally.kept += 1
    await ctx.session.flush()


async def spring_trap(ctx: TickContext, target: EntityRow, stream: str) -> GeasRow | None:
    row = await ctx.session.scalar(select(GeasRow).where(GeasRow.bearer_entity_id == target.id, GeasRow.state == GeasState.KEPT).order_by(GeasRow.id).limit(1))
    if row is None or held(target.id) or not ctx.rng(stream).chance(ctx.rules.geasa.trap_pct):
        return None
    await doom(ctx, row, target, "a rival forced the moment on it")
    return row
