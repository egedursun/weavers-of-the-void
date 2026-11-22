from sqlalchemy import func, select

from aerona.catalog.life.made import MAKERS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import FabricationRow, MarketScarcityRow, PatternRightRow, ReplicatorLineRow, ReplicatorPresenceRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.made import ReplicatorStage
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import Commodity
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.stats import shift_stat

LIVE = (ReplicatorStage.WORKING, ReplicatorStage.SPREADING, ReplicatorStage.RUNAWAY)


async def maker_mass(ctx: TickContext, region: int | None) -> int:
    if region is None:
        return 0
    lines = select(ReplicatorLineRow.id).where(ReplicatorLineRow.output.in_(MAKERS), ReplicatorLineRow.stage.in_(LIVE))
    statement = select(func.coalesce(func.sum(ReplicatorPresenceRow.mass), 0)).where(
        ReplicatorPresenceRow.line_id.in_(lines), ReplicatorPresenceRow.place_node_id == region
    )
    return int(await ctx.session.scalar(statement) or 0)


async def scarcity_of(ctx: TickContext, town_id: int, commodity: Commodity) -> MarketScarcityRow:
    row = await ctx.session.get(MarketScarcityRow, (town_id, commodity))
    if row is None:
        row = MarketScarcityRow(settlement_entity_id=town_id, commodity=commodity, scarcity=PERCENT, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def pay_patterns(ctx: TickContext, fabrication: FabricationRow) -> None:
    table = ctx.rules.abundance
    for pattern in await ctx.session.scalars(select(PatternRightRow).where(PatternRightRow.open.is_(False), PatternRightRow.holder_node_id.is_not(None))):
        holder = await ctx.session.get(EntityRow, pattern.holder_node_id)
        if holder is None or held(holder.id):
            continue
        fee = round_half_up(pattern.licence_fee * fabrication.share_pct * table.pattern_fee_share / PERCENT / PERCENT)
        if fee:
            await shift_points(ctx.session, holder, fee)


async def fabricate(ctx: TickContext, atlas: RegionAtlas, town: EntityRow) -> None:
    table = ctx.rules.abundance
    row = await ctx.session.get(FabricationRow, town.id)
    mass = await maker_mass(ctx, atlas.top_region(town.id))
    if row is None and not mass:
        return
    if row is None:
        row = FabricationRow(settlement_entity_id=town.id, share_pct=0, dividend_pct=0, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "share_pct" not in row.locked:
        row.share_pct = clamp_percent(max(row.share_pct - 1, mass // 10))
    row.updated_epoch = ctx.epoch
    if not row.share_pct:
        return
    society = await ctx.session.get(CommunitySocietyRow, town.id)
    floor = table.floor_pct
    for commodity in Commodity:
        scarcity = await scarcity_of(ctx, town.id, commodity)
        if "scarcity" not in scarcity.locked:
            scarcity.scarcity = clamp_percent(max(floor, scarcity.scarcity - round_half_up(table.scarcity_drop * row.share_pct / PERCENT)))
        scarcity.updated_epoch = ctx.epoch
        if society is not None:
            column = f"price_{commodity.value}"
            setattr(society, column, max(1, round_half_up(society.price(commodity) * scarcity.scarcity / PERCENT)))
    if society is not None:
        moved = min(society.share_worker, society.share_worker * row.share_pct * table.labour_shift / PERCENT / PERCENT)
        society.share_worker -= moved
        society.share_unemployed += moved
        level = str(await law_param(ctx.session, town.id, LawKind.PROVISION_LAW, "level") or "market")
        if level in {"universal", "communal"}:
            society.satisfaction_unemployed = clamp_percent(society.satisfaction_unemployed + table.provision_satisfaction)
    if row.dividend_pct:
        shift_stat(town, "prosperity", round_half_up(table.dividend_prosperity * row.dividend_pct / PERCENT), 0, high=PERCENT)
    await pay_patterns(ctx, row)


@reads(
    "table.community_societies",
    "table.entities",
    "table.fabrication",
    "table.fabrications",
    "table.law_profiles",
    "table.nodes",
    "table.pattern_rights",
    "table.replicator_lines",
    "table.replicator_presence",
    "table.replicator_presences",
)
@writes("table.community_societies", "table.entities", "table.fabrications", "table.market_scarcities", "table.mortal_profiles")
async def keep_abundance(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    towns = await ctx.session.scalars(
        select(EntityRow)
        .join(CommunitySocietyRow, CommunitySocietyRow.entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        await fabricate(ctx, atlas, town)
    await ctx.session.flush()
