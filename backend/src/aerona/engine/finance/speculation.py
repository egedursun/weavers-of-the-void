from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.finance import FOOD_HOARDS
from aerona.constants.units import PERCENT
from aerona.db.record_context import Term
from aerona.db.tables.economy import MarketPriceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.finance import SpeculationRow
from aerona.db.tables.mind import FacetRow, PressureRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.finance import SpeculationStatus
from aerona.domain.enums.mind import ActKind, Facet, PressureKind
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.industry.owners import credit_owner, purse_value
from aerona.engine.intrigue.beliefs import believed_prices
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record

MERCHANT_GUILDS = (FactionKind.MERCHANT_GUILD, FactionKind.WANDERING_MARKET)


@dataclass
class SpeculationTally:
    opened: int = 0
    sold: int = 0
    busts: int = 0
    famine_hoards: int = 0


async def prices(ctx: TickContext, market_id: int, epoch: int) -> dict[CommodityKind, int]:
    rows = await ctx.session.scalars(select(MarketPriceRow).where(MarketPriceRow.market_entity_id == market_id, MarketPriceRow.epoch == epoch))
    return {row.commodity: row.price for row in rows}


async def hunger_at(ctx: TickContext, market_id: int) -> int:
    row = await ctx.session.get(PressureRow, (market_id, PressureKind.HUNGER))
    return row.value if row is not None else 0


async def speculators(ctx: TickContext, book: EconomyBook) -> list[tuple[int, EntityRow]]:
    markets = {community.id: community for community in book.communities if book.workshop(community.id, WorkshopKind.MARKET) is not None}
    found: list[tuple[int, EntityRow]] = []
    greedy = select(FacetRow.node_id).where(FacetRow.facet == Facet.GREED, FacetRow.value >= ctx.rules.speculation.greed_at)
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.mortal_role == MortalRole.MERCHANT,
        EntityRow.id.in_(greedy),
    )
    for mortal in await ctx.session.scalars(statement.order_by(EntityRow.id)):
        home = book.community_of(mortal.id)
        if home is not None and home.id in markets:
            found.append((mortal.id, home))
    guilds = select(FactionProfileRow).where(FactionProfileRow.kind.in_(list(MERCHANT_GUILDS))).order_by(FactionProfileRow.faction_entity_id)
    for guild in await ctx.session.scalars(guilds):
        if guild.home_entity_id in markets:
            found.append((guild.faction_entity_id, markets[guild.home_entity_id]))
    return [(merchant, market) for merchant, market in found if not held(merchant) and not held(market.id)]


def best_rise(ctx: TickContext, now: dict[CommodityKind, int], before: dict[CommodityKind, int]) -> CommodityKind | None:
    table = ctx.rules.speculation
    rising = [
        (now[kind] * PERCENT / before[kind], kind) for kind in now if before.get(kind) and now[kind] * PERCENT >= before[kind] * (PERCENT + table.rise_pct)
    ]
    return max(rising, key=lambda item: (item[0], item[1].value))[1] if rising else None


async def open_hoard(ctx: TickContext, merchant: int, market: EntityRow, commodity: CommodityKind, price: int, *, famine: bool) -> SpeculationRow | None:
    table = ctx.rules.speculation
    stock = await holding(ctx.session, market.id, commodity)
    units = round_half_up(stock * table.hoard_share_pct / PERCENT)
    cost = round_half_up(price * units / PERCENT)
    if units <= 0 or cost <= 0 or await purse_value(ctx, merchant) < cost:
        return None
    taken = sum(lot.quantity for lot in await goods_of(ctx.session, ctx.epoch).take(market.id, commodity, units, GoodsFlow.TRADE))
    if taken <= 0:
        return None
    await credit_owner(ctx, merchant, -round_half_up(price * taken / PERCENT))
    row = SpeculationRow(
        merchant_node_id=merchant,
        market_node_id=market.id,
        commodity=commodity,
        units=taken,
        price=price,
        status=SpeculationStatus.HOARDING,
        opened_epoch=ctx.epoch,
        gain=0,
        locked=[],
    )
    ctx.session.add(row)
    town = await ctx.session.get(SettlementProfileRow, market.id)
    spike = table.unrest_per_hoard if famine else table.unrest_per_hoard * table.spike_unrest_pct / PERCENT
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest + spike, 0, PERCENT)
    if famine:
        await judged(ctx, merchant, market.id, ActKind.HOARDING_IN_FAMINE)
    return row


async def open_hoards(ctx: TickContext, book: EconomyBook, tally: SpeculationTally) -> None:
    table = ctx.rules.speculation
    for merchant, market in await speculators(ctx, book):
        rng = ctx.rng(f"speculate.{merchant}.{ctx.epoch}")
        if not rng.chance(table.chance_pct):
            continue
        now, before = await prices(ctx, market.id, ctx.epoch), await prices(ctx, market.id, ctx.epoch - 1)
        seen = await believed_prices(ctx, merchant, market.id, now)
        famine = await hunger_at(ctx, market.id) >= table.famine_hunger
        commodity = next((kind for kind in FOOD_HOARDS if kind in now), None) if famine else best_rise(ctx, seen, before)
        if commodity is None or commodity not in now:
            continue
        if await open_hoard(ctx, merchant, market, commodity, now[commodity], famine=famine) is not None:
            tally.opened += 1
            tally.famine_hoards += int(famine)


async def ruin(ctx: TickContext, merchant_id: int) -> None:
    profile = await ctx.session.get(MortalProfileRow, merchant_id)
    if profile is not None and "standing" not in (profile.locked or []):
        profile.wealth = 0
    guild = await ctx.session.get(FactionProfileRow, merchant_id)
    if guild is not None:
        guild.treasury //= 2


async def settle_hoards(ctx: TickContext, book: EconomyBook, tally: SpeculationTally) -> None:
    table = ctx.rules.speculation
    statement = select(SpeculationRow).where(SpeculationRow.status == SpeculationStatus.HOARDING).order_by(SpeculationRow.id)
    for row in await ctx.session.scalars(statement):
        if "status" in (row.locked or []) or held(row.merchant_node_id) or held(row.market_node_id):
            continue
        price = (await prices(ctx, row.market_node_id, ctx.epoch)).get(row.commodity)
        if price is None:
            continue
        boom = price * PERCENT >= row.price * (PERCENT + table.sell_rise_pct)
        bust = price * PERCENT <= row.price * (PERCENT - table.bust_fall_pct)
        if not (boom or bust or ctx.epoch - row.opened_epoch >= table.hold_epochs):
            continue
        await goods_of(ctx.session, ctx.epoch).add(row.market_node_id, row.commodity, row.units, GoodsFlow.TRADE)
        value = round_half_up(price * row.units / PERCENT)
        row.gain = value - round_half_up(row.price * row.units / PERCENT)
        await credit_owner(ctx, row.merchant_node_id, value)
        row.status, row.settled_epoch = (SpeculationStatus.BUST if bust else SpeculationStatus.SOLD), ctx.epoch
        if bust:
            tally.busts += 1
            await ruin(ctx, row.merchant_node_id)
            await record(
                ctx,
                "speculation.bust",
                roles={IncidentRole.VICTIM: row.merchant_node_id, IncidentRole.PLACE: row.market_node_id},
                facts={"good": row.commodity, "units": row.units, "bought_at": row.price, "sold_at": price, "loss": -row.gain},
                terms=(Term("speculation.bought_at", row.price), Term("speculation.sold_at", price), Term("speculation.units", row.units, ModifierOp.MULTIPLY)),
                place=row.market_node_id,
            )
        else:
            tally.sold += 1


async def tend_speculation(ctx: TickContext, book: EconomyBook, tally: SpeculationTally) -> None:
    await settle_hoards(ctx, book, tally)
    await open_hoards(ctx, book, tally)
