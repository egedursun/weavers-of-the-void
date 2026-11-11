from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import MERCHANT_HOUSES
from aerona.constants.units import PERCENT
from aerona.db.tables.affairs import MandateRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.urban import MarketPlayRow, TradingPostRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.statecraft import MandateState
from aerona.domain.enums.urban import MarketPlay
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holdings
from aerona.engine.factions.book import monopolies_at
from aerona.engine.notes import note
from aerona.engine.polity.laws import LawBook
from aerona.engine.renown.currencies import realm_of_community
from aerona.rules.registry import Rules

PLAY_WORDS = {MarketPlay.CORNER: "cornered the market in", MarketPlay.DUMP: "flooded the market with"}


@dataclass
class PlayTally:
    played: int = 0
    ended: int = 0


def swing(rules: Rules, play: MarketPlay, strength: int) -> float:
    table = rules.manipulation
    share = strength / PERCENT
    return 1 + table.corner_pct / PERCENT * share if play is MarketPlay.CORNER else 1 - table.dump_pct / PERCENT * share


async def mandated(session: AsyncSession, realm_id: int, commodity: CommodityKind) -> bool:
    found = await session.scalar(
        select(MandateRow.id)
        .where(MandateRow.polity_entity_id == realm_id, MandateRow.commodity == commodity, MandateRow.state == MandateState.ACTIVE)
        .limit(1)
    )
    return found is not None


async def countered(session: AsyncSession, rules: Rules, laws: LawBook, market_id: int, commodity: CommodityKind) -> float:
    table = rules.manipulation
    kept = 1.0
    realm = await realm_of_community(session, market_id)
    if realm is not None and laws.in_force(realm, LawKind.FAIR_MARKET) is not None:
        kept *= 1 - table.law_counter_pct / PERCENT
    if realm is not None and await mandated(session, realm, commodity):
        kept *= 1 - table.law_counter_pct / PERCENT
    if commodity.value in await monopolies_at(session, market_id):
        kept *= 1 - table.guild_counter_pct / PERCENT
    return kept


async def plays_at(session: AsyncSession, rules: Rules, market_id: int, epoch: int) -> dict[CommodityKind, float]:
    found: dict[CommodityKind, float] = {}
    statement = select(MarketPlayRow).where(
        MarketPlayRow.settlement_entity_id == market_id, or_(MarketPlayRow.until_epoch.is_(None), MarketPlayRow.until_epoch >= epoch)
    )
    rows = list(await session.scalars(statement))
    if not rows:
        return found
    laws = await LawBook.load(session)
    for row in rows:
        kept = await countered(session, rules, laws, market_id, row.commodity)
        found[row.commodity] = found.get(row.commodity, 1.0) * (1 + (swing(rules, row.play, row.strength) - 1) * kept)
    return found


async def stock_of(ctx: TickContext, house: FactionProfileRow) -> tuple[dict[CommodityKind, int], int]:
    stock = dict(await holdings(ctx.session, house.home_entity_id)) if house.home_entity_id is not None else {}
    stored = sum(post.goods for post in await ctx.session.scalars(select(TradingPostRow).where(TradingPostRow.owner_entity_id == house.faction_entity_id)))
    return stock, stored


async def play_markets(ctx: TickContext, tally: PlayTally) -> None:
    table = ctx.rules.manipulation
    for row in list(await ctx.session.scalars(select(MarketPlayRow).where(MarketPlayRow.until_epoch < ctx.epoch))):
        if not held(row.holder_entity_id) and "until_epoch" not in row.locked:
            await ctx.session.delete(row)
            tally.ended += 1
    houses = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_(list(MERCHANT_HOUSES)), EntityRow.status == EntityStatus.CANON, FactionProfileRow.home_entity_id.is_not(None))
        .order_by(EntityRow.id)
    )
    for house, profile in houses.all():
        market = profile.home_entity_id
        if market is None or held(house.id, market) or not ctx.rng(f"market_play.{house.id}").chance(table.play_pct):
            continue
        stock, stored = await stock_of(ctx, profile)
        if not stock:
            continue
        commodity, amount = max(sorted(stock.items(), key=lambda item: item[0].value), key=lambda item: item[1])
        amount += stored
        play = MarketPlay.CORNER if amount >= table.corner_stock else MarketPlay.DUMP
        if await ctx.session.get(MarketPlayRow, (house.id, market, commodity, play)) is not None:
            continue
        strength = min(PERCENT, round(amount * PERCENT / max(1, table.corner_stock)))
        ctx.session.add(
            MarketPlayRow(
                holder_entity_id=house.id,
                settlement_entity_id=market,
                commodity=commodity,
                play=play,
                strength=strength,
                since_epoch=ctx.epoch,
                until_epoch=ctx.epoch + table.length,
                locked=[],
            )
        )
        tally.played += 1
        town = await ctx.session.get(EntityRow, market)
        if town is not None:
            await note(
                ctx, f"{house.name} {PLAY_WORDS[play]} {commodity.value.replace('_', ' ')} at {town.name}.", key="trade.market_play", ids=[house.id, town.id]
            )
    await ctx.session.flush()
