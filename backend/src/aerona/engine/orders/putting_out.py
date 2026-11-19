from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import func, select

from aerona.catalog.commodities import COMMODITIES
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.db.tables.economy import ProductionRunRow, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.orders import ChainHoldingRow, PuttingOutRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, TradeRouteStatus
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.lore.research_depth import add_progress
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record

PUT_OUT: MappingProxyType[CommodityKind, CommodityKind] = MappingProxyType(
    {
        CommodityKind.WOOL: CommodityKind.CLOTH,
        CommodityKind.FIBRE: CommodityKind.CLOTH,
        CommodityKind.TIMBER: CommodityKind.TOOLS,
        CommodityKind.ORE: CommodityKind.TOOLS,
    }
)
VILLAGES = (SizeTier.HAMLET, SizeTier.VILLAGE)


@dataclass
class PuttingOutTally:
    founded: int = 0
    worked: int = 0
    idle: int = 0
    bought: int = 0
    drawn: int = 0


async def merchant_houses(ctx: TickContext) -> list[EntityRow]:
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.FACTION,
            EntityRow.engine_kind == EngineKind.MERCHANT_GUILD,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id.is_not(None),
        )
        .order_by(EntityRow.id)
    )
    return list(found)


async def village_near(ctx: TickContext, home: EntityRow) -> EntityRow | None:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(
            EntityRow.world_id == home.world_id,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != home.id,
            SettlementProfileRow.size_tier.in_(list(VILLAGES)),
        )
        .order_by((EntityRow.location_id == home.location_id).desc(), EntityRow.id)
        .limit(1)
    )
    return found


async def put_out(ctx: TickContext, tally: PuttingOutTally) -> None:
    table = ctx.rules.putting_out
    working = set(await ctx.session.scalars(select(PuttingOutRow.merchant_entity_id).where(PuttingOutRow.active.is_(True))))
    for house in await merchant_houses(ctx):
        home = await ctx.session.get(EntityRow, house.location_id) if house.location_id is not None else None
        if home is None or house.id in working or held(house.id, home.id):
            continue
        if not ctx.rng(seed_of("putting_out", house.id, ctx.epoch)).chance(table.found_chance):
            continue
        raw = None
        for kind in PUT_OUT:
            if await holding(ctx.session, home.id, kind) > 0:
                raw = kind
                break
        village = await village_near(ctx, home)
        if raw is None or village is None or held(village.id):
            continue
        volume = max(1, round_half_up(table.volume * stat_or(village, "population", 0) / PER_MILLE))
        ctx.session.add(
            PuttingOutRow(
                merchant_entity_id=house.id, town_entity_id=village.id, raw=raw, product=PUT_OUT[raw], volume=volume, since_epoch=ctx.epoch, locked=[]
            )
        )
        tally.founded += 1
        await record(
            ctx,
            "putting_out.founded",
            roles={IncidentRole.OWNER: house.id, IncidentRole.PLACE: village.id},
            facts={"raw": raw, "product": PUT_OUT[raw], "volume": volume},
            place=village.id,
        )
    await ctx.session.flush()


async def work_put_out(ctx: TickContext, row: PuttingOutRow, tally: PuttingOutTally) -> None:
    table = ctx.rules.putting_out
    ledger = goods_of(ctx.session, ctx.epoch)
    house, village = await ctx.session.get(EntityRow, row.merchant_entity_id), await ctx.session.get(EntityRow, row.town_entity_id)
    home = await ctx.session.get(EntityRow, house.location_id) if house is not None and house.location_id is not None else None
    if house is None or village is None or home is None or village.status is not EntityStatus.CANON:
        row.active = False
        return
    handed = await ledger.take_units(home.id, row.raw, row.volume, GoodsFlow.INPUT)
    if handed <= 0:
        if "active" not in row.locked:
            row.active = False
        tally.idle += 1
        return
    made = await ledger.add(home.id, row.product, handed, GoodsFlow.PRODUCTION)
    worth = made * COMMODITIES[row.product].base_price
    await give_coin(ctx.session, ctx.rules, house, round_half_up(worth * table.merchant_margin / PERCENT))
    shift_stat(village, "prosperity", max(1, table.village_pay * made // max(1, row.volume) // 10), ctx.rules.society.default_stat)
    await add_progress(ctx, home.id, Technique.FACTORY_PRODUCTION, table.proto_progress)
    tally.worked += 1


async def buy_in(ctx: TickContext, tally: PuttingOutTally) -> None:
    table = ctx.rules.putting_out
    for house in await merchant_houses(ctx):
        if held(house.id) or not ctx.rng(seed_of("chain.buy", house.id, ctx.epoch)).chance(table.chain_chance):
            continue
        partner = await ctx.session.scalar(
            select(TradeRouteProfileRow.second_market_id)
            .where(TradeRouteProfileRow.first_market_id == house.location_id, TradeRouteProfileRow.status == TradeRouteStatus.OPEN)
            .order_by(TradeRouteProfileRow.route_entity_id)
            .limit(1)
        )
        if partner is None or held(partner):
            continue
        product = await ctx.session.scalar(
            select(ProductionRunRow.output)
            .where(ProductionRunRow.community_entity_id == partner, ProductionRunRow.epoch == ctx.epoch - 1)
            .group_by(ProductionRunRow.output)
            .order_by(func.sum(ProductionRunRow.quantity).desc())
            .limit(1)
        )
        if product is None or await ctx.session.get(ChainHoldingRow, (house.id, partner, product)) is not None:
            continue
        ctx.session.add(
            ChainHoldingRow(holder_entity_id=house.id, town_entity_id=partner, product=product, share_pct=table.chain_share, since_epoch=ctx.epoch, locked=[])
        )
        tally.bought += 1
        await record(
            ctx,
            "chains.bought",
            roles={IncidentRole.BUYER: house.id, IncidentRole.PLACE: partner},
            facts={"product": product, "share": table.chain_share},
            place=partner,
        )
    await ctx.session.flush()


async def draw_chain(ctx: TickContext, row: ChainHoldingRow, tally: PuttingOutTally) -> None:
    house = await ctx.session.get(EntityRow, row.holder_entity_id)
    if house is None or house.location_id is None or held(house.id, row.town_entity_id):
        return
    made = await ctx.session.scalar(
        select(func.sum(ProductionRunRow.quantity)).where(
            ProductionRunRow.community_entity_id == row.town_entity_id, ProductionRunRow.output == row.product, ProductionRunRow.epoch == ctx.epoch
        )
    )
    share = int(made or 0) * row.share_pct // PERCENT
    if share > 0:
        await goods_of(ctx.session, ctx.epoch).move(row.town_entity_id, house.location_id, row.product, share, flow=GoodsFlow.TRADE)
        tally.drawn += 1


async def keep_putting_out(ctx: TickContext, tally: PuttingOutTally) -> None:
    await put_out(ctx, tally)
    for row in list(await ctx.session.scalars(select(PuttingOutRow).where(PuttingOutRow.active.is_(True)).order_by(PuttingOutRow.id))):
        if not held(row.merchant_entity_id, row.town_entity_id):
            await work_put_out(ctx, row, tally)
    await buy_in(ctx, tally)
    for holding_row in list(await ctx.session.scalars(select(ChainHoldingRow).order_by(ChainHoldingRow.holder_entity_id, ChainHoldingRow.town_entity_id))):
        await draw_chain(ctx, holding_row, tally)
    await ctx.session.flush()
