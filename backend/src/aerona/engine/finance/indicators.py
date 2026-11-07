from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.economy import LoanRow, MarketPriceRow, ProductionRunRow, TradeFlowRow
from aerona.db.tables.finance import EconomicIndicatorRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.finance.credit import owed
from aerona.engine.industry.methods import local_price
from aerona.engine.industry.owners import coin
from aerona.engine.primitives.numbers import clamp_int, round_half_up

PERCENT_FIGURES = frozenset({"unemployment", "market_access"})
COUNT_FIGURES = frozenset({"output", "price_index", "debt_ratio", "black_market"})


@dataclass
class IndicatorTally:
    recorded: int = 0


@dataclass
class Figures:
    output: int
    price_index: int
    trade_balance: int
    treasury: int
    debt_ratio: int
    unemployment: int
    market_access: int
    black_market: int
    living: dict[str, int]


async def output_of(ctx: TickContext, book: EconomyBook, members: set[int]) -> int:
    runs = await ctx.session.scalars(select(ProductionRunRow).where(ProductionRunRow.epoch == ctx.epoch, ProductionRunRow.community_entity_id.in_(members)))
    return round_half_up(coin(ctx, sum(run.quantity * local_price(book, run.community_entity_id, run.output) for run in runs)))


async def price_index_of(ctx: TickContext, members: set[int]) -> int:
    rows = list(await ctx.session.scalars(select(MarketPriceRow).where(MarketPriceRow.epoch == ctx.epoch, MarketPriceRow.market_entity_id.in_(members))))
    base = sum(COMMODITIES[row.commodity].base_price for row in rows)
    return round_half_up(sum(row.price for row in rows) * PERCENT / base) if base else PERCENT


async def balance_of(ctx: TickContext, members: set[int]) -> int:
    balance = 0
    for flow in await ctx.session.scalars(select(TradeFlowRow).where(TradeFlowRow.epoch == ctx.epoch)):
        out, into = flow.from_entity_id in members, flow.to_entity_id in members
        if out != into:
            balance += flow.value if out else -flow.value
    return balance


async def unemployment_of(ctx: TickContext, members: set[int]) -> int:
    rows = list(await ctx.session.scalars(select(LabourRow).where(LabourRow.community_entity_id.in_(members))))
    total = sum(row.workers for row in rows)
    idle = sum(row.workers for row in rows if row.job is Job.IDLE)
    return round_half_up(idle * PERCENT / total) if total else 0


async def living_of(ctx: TickContext, members: set[int]) -> dict[str, int]:
    rows = list(await ctx.session.scalars(select(CommunitySocietyRow).where(CommunitySocietyRow.entity_id.in_(members))))
    if not rows:
        return {}
    return {social_class.value: round_half_up(sum(row.satisfaction(social_class) for row in rows) / len(rows)) for social_class in SocialClass}


async def figures(ctx: TickContext, book: EconomyBook, members: set[int], *, treasury: int, debt: int) -> Figures:
    industry = [row for row in book.industry.values() if row.community_node_id in members]
    return Figures(
        output=await output_of(ctx, book, members),
        price_index=await price_index_of(ctx, members),
        trade_balance=await balance_of(ctx, members),
        treasury=treasury,
        debt_ratio=round_half_up(debt * PERCENT / max(1, treasury)),
        unemployment=await unemployment_of(ctx, members),
        market_access=round_half_up(sum(row.market_access for row in industry) / len(industry)) if industry else PERCENT,
        black_market=sum(row.black_market for row in industry),
        living=await living_of(ctx, members),
    )


def bounded(key: str, value: object) -> object:
    if key in PERCENT_FIGURES and isinstance(value, int):
        return clamp_int(value, 0, PERCENT)
    if key in COUNT_FIGURES and isinstance(value, int):
        return max(0, value)
    return value


async def store(ctx: TickContext, subject_id: int, found: Figures) -> EconomicIndicatorRow | None:
    if held(subject_id):
        return None
    row = await ctx.session.scalar(
        select(EconomicIndicatorRow).where(EconomicIndicatorRow.subject_node_id == subject_id, EconomicIndicatorRow.epoch == ctx.epoch)
    )
    if row is None:
        row = EconomicIndicatorRow(subject_node_id=subject_id, epoch=ctx.epoch, living={}, locked=[])
        ctx.session.add(row)
    for key, value in found.__dict__.items():
        if key not in (row.locked or []):
            setattr(row, key, bounded(key, value))
    return row


async def open_debt(ctx: TickContext, borrowers: set[int]) -> int:
    loans = await ctx.session.scalars(select(LoanRow).where(LoanRow.status == LoanStatus.OPEN, LoanRow.borrower_entity_id.in_(borrowers)))
    return sum(owed(loan) for loan in loans)


async def record_indicators(ctx: TickContext, book: EconomyBook, tally: IndicatorTally) -> None:
    members: dict[int, set[int]] = defaultdict(set)
    for row in await ctx.session.scalars(select(PolityMemberRow)):
        members[row.polity_entity_id].add(row.member_entity_id)
    for profile in await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id)):
        group = members.get(profile.polity_entity_id, set())
        debt = profile.debt + await open_debt(ctx, {profile.polity_entity_id, *group})
        if await store(ctx, profile.polity_entity_id, await figures(ctx, book, group, treasury=max(0, profile.treasury), debt=debt)) is not None:
            tally.recorded += 1
    for world in await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id)):
        group = {community.id for community in book.communities if community.world_id == world.id}
        if not group:
            continue
        treasuries = await ctx.session.scalars(select(SettlementProfileRow.treasury).where(SettlementProfileRow.settlement_entity_id.in_(group)))
        treasury = sum(max(0, value) for value in treasuries)
        if await store(ctx, world.id, await figures(ctx, book, group, treasury=treasury, debt=await open_debt(ctx, group))) is not None:
            tally.recorded += 1
