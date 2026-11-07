from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.intrigue import BeliefSource
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

LOCK = "value"
PRICE = "price."
DEFENCE = "defense"
DARING_MIN = 0.5
DARING_MAX = 1.5


async def believe(
    ctx: TickContext, holder_id: int, subject_id: int, attribute: str, truth: int, *, source: BeliefSource, confidence: int, false: bool = False
) -> BeliefRow | None:
    if held(holder_id):
        return None
    table = ctx.rules.belief_state
    spread = round_half_up(table.error_pct * (PERCENT - confidence) / PERCENT)
    value = (
        truth
        if false or spread <= 0
        else round_half_up(truth * (PERCENT + ctx.rng(f"belief.{holder_id}.{subject_id}.{attribute}.{ctx.epoch}").integer(-spread, spread)) / PERCENT)
    )
    row = await ctx.session.scalar(
        select(BeliefRow).where(BeliefRow.holder_node_id == holder_id, BeliefRow.subject_node_id == subject_id, BeliefRow.attribute == attribute).limit(1)
    )
    if row is None:
        row = BeliefRow(
            holder_node_id=holder_id,
            subject_node_id=subject_id,
            attribute=attribute,
            value=value,
            confidence=confidence,
            as_of_epoch=ctx.epoch,
            source=source,
            false=false,
            locked=[],
        )
        ctx.session.add(row)
        return row
    if LOCK in (row.locked or []) or (row.confidence > confidence and row.as_of_epoch == ctx.epoch):
        return row
    row.value, row.confidence, row.as_of_epoch, row.source, row.false = value, confidence, ctx.epoch, source, false
    return row


@dataclass(frozen=True)
class BeliefView:
    session: AsyncSession
    rules: Rules
    holder_id: int

    async def of(self, subject_id: int, attribute: str, truth: int) -> int:
        row = await self.session.scalar(
            select(BeliefRow)
            .where(BeliefRow.holder_node_id == self.holder_id, BeliefRow.subject_node_id == subject_id, BeliefRow.attribute == attribute)
            .limit(1)
        )
        if row is None or row.confidence <= 0:
            return round_half_up(truth * self.rules.belief_state.prior_pct / PERCENT)
        return row.value


async def fade_beliefs(ctx: TickContext) -> int:
    faded = 0
    decay = ctx.rules.belief_state.decay
    for row in list(await ctx.session.scalars(select(BeliefRow).where(BeliefRow.as_of_epoch < ctx.epoch))):
        if LOCK in (row.locked or []) or held(row.holder_node_id):
            continue
        row.confidence = clamp_int(row.confidence - decay, 0, PERCENT)
        if row.confidence <= 0:
            await ctx.session.delete(row)
        faded += 1
    return faded


async def daring(ctx: TickContext, actor_id: int, rival_id: int) -> float:
    rival = await ctx.session.get(EntityRow, rival_id)
    actor = await ctx.session.get(EntityRow, actor_id)
    if rival is None or actor is None:
        return 1.0
    believed = await BeliefView(ctx.session, ctx.rules, actor_id).of(rival_id, DEFENCE, stat(rival, DEFENCE) or 0)
    own = stat(actor, DEFENCE) or 0
    return min(DARING_MAX, max(DARING_MIN, (own + 1) / (believed + 1)))


async def evidence_trust(session: AsyncSession, holder_id: int) -> float:
    found = await session.scalar(select(func.avg(BeliefRow.confidence)).where(BeliefRow.holder_node_id == holder_id, BeliefRow.false.is_(False)))
    return float(found or 0)


def price_key(commodity: str) -> str:
    return f"{PRICE}{commodity}"


async def believed_prices(ctx: TickContext, holder_id: int, market_id: int, truth: dict[CommodityKind, int]) -> dict[CommodityKind, int]:
    confidence = ctx.rules.belief_state.observe_confidence
    seen: dict[CommodityKind, int] = {}
    for commodity, price in truth.items():
        row = await believe(ctx, holder_id, market_id, price_key(commodity.value), price, source=BeliefSource.OBSERVATION, confidence=confidence)
        seen[commodity] = row.value if row is not None else price
    return seen
