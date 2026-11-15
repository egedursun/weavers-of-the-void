from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.arcana import WarpingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.entity import EntityType
from aerona.engine.body.afflictions import afflict, enter_stage
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon


@dataclass
class WarpTally:
    exposed: int = 0
    staged: int = 0
    faded: int = 0


def stage_for(ctx: TickContext, value: int) -> int:
    table = ctx.rules.warping
    return sum(1 for mark in (table.touched_at, table.marked_at, table.unmoored_at) if value >= mark)


def floor_of(ctx: TickContext, row: WarpingRow) -> int:
    table = ctx.rules.warping
    marks = (table.touched_at, table.marked_at, table.unmoored_at)
    return marks[table.permanent_stage - 1] if row.stage >= table.permanent_stage else 0


def fade(ctx: TickContext, row: WarpingRow) -> bool:
    if row.updated_epoch >= ctx.epoch or "value" in row.locked:
        return False
    lowered = max(floor_of(ctx, row), row.value - ctx.rules.warping.fade)
    if lowered >= row.value:
        return False
    row.value = lowered
    return True


async def warp_row(ctx: TickContext, node_id: int) -> WarpingRow:
    row = await ctx.session.get(WarpingRow, node_id)
    if row is None:
        row = WarpingRow(node_id=node_id, value=0, stage=0, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def expose(ctx: TickContext, node_id: int, amount: int) -> int:
    if amount <= 0 or held(node_id):
        return 0
    row = await warp_row(ctx, node_id)
    if "value" in row.locked:
        return 0
    row.value = clamp_int((row.value or 0) + amount, 0, PERCENT)
    row.updated_epoch = ctx.epoch
    return amount


async def settle_stage(ctx: TickContext, bearer: EntityRow, row: WarpingRow) -> bool:
    wanted = stage_for(ctx, row.value)
    if "stage" in row.locked:
        wanted = row.stage
    if wanted == row.stage and wanted == 0:
        return False
    found = await ctx.session.scalar(
        select(AfflictionRow).where(
            AfflictionRow.bearer_node_id == bearer.id, AfflictionRow.package == PackageKind.WARPING, AfflictionRow.cured_epoch.is_(None)
        )
    )
    if wanted and found is None:
        found = await afflict(ctx, bearer, PackageKind.WARPING, Transmission.EXPERIENCE)
    changed = row.stage != wanted
    row.stage = wanted
    if found is not None and wanted and found.stage != wanted:
        await enter_stage(ctx, bearer, found, wanted)
        changed = True
    return changed


async def ley_dwellers(ctx: TickContext) -> list[EntityRow]:
    lines = await ctx.session.execute(select(LeyLineRow.region_a_id, LeyLineRow.region_b_id).where(LeyLineRow.severed.is_(False)))
    regions = {region for pair in lines for region in pair if region is not None}
    if not regions:
        return []
    atlas = await RegionAtlas.load(ctx.session)
    found = [mortal for mortal in await canon(ctx.session, [EntityType.MORTAL]) if atlas.top_region(mortal.id) in regions]
    return found[: ctx.rules.warping.bearers_max]


async def warp_world(ctx: TickContext, tally: WarpTally) -> None:
    for mortal in await ley_dwellers(ctx):
        tally.exposed += int(await expose(ctx, mortal.id, ctx.rules.warping.ley) > 0)
    for row in list(await ctx.session.scalars(select(WarpingRow).where(WarpingRow.value > 0).order_by(WarpingRow.node_id))):
        bearer = await ctx.session.get(EntityRow, row.node_id)
        if bearer is None or held(bearer.id):
            continue
        tally.faded += int(fade(ctx, row))
        tally.staged += int(await settle_stage(ctx, bearer, row))
    await ctx.session.flush()
