from dataclasses import dataclass

from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from aerona.constants.units import PERCENT
from aerona.db.read_memo import register_index
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.intrigue import BeliefSource
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

LOCK = "value"
PRICE = "price."
DEFENCE = "defense"
DARING_MIN = 0.5
DARING_MAX = 1.5


BELIEF_INDEX = "aerona.belief_index"


def foreign_beliefs(sync: Session, index: dict[int, dict[tuple[int, str], BeliefRow]]) -> bool:
    for item in sync.new:
        if isinstance(item, BeliefRow) and index.get(item.holder_node_id, {}).get((item.subject_node_id, item.attribute)) is not item:
            return True
    return any(isinstance(item, BeliefRow) for item in sync.deleted)


async def beliefs_of(session: AsyncSession, holder_id: int) -> dict[tuple[int, str], BeliefRow]:
    sync = session.sync_session
    index: dict[int, dict[tuple[int, str], BeliefRow]] = sync.info.setdefault(BELIEF_INDEX, {})
    if foreign_beliefs(sync, index):
        await session.flush()
        index = sync.info.setdefault(BELIEF_INDEX, {})
    known = index.get(holder_id)
    if known is None:
        known = {}
        for row in await session.scalars(select(BeliefRow).where(BeliefRow.holder_node_id == holder_id).order_by(BeliefRow.id)):
            known.setdefault((row.subject_node_id, row.attribute), row)
        index[holder_id] = known
    return known


def follow_beliefs(sync: Session, *_: object) -> None:
    index: dict[int, dict[tuple[int, str], BeliefRow]] | None = sync.info.get(BELIEF_INDEX)
    if index is None:
        return
    for item in sync.new:
        if isinstance(item, BeliefRow) and item.holder_node_id in index:
            index[item.holder_node_id].setdefault((item.subject_node_id, item.attribute), item)
    for item in [*sync.deleted, *sync.dirty]:
        if isinstance(item, BeliefRow):
            index.pop(item.holder_node_id, None)


def drop_beliefs(sync: Session, *_: object) -> None:
    sync.info.pop(BELIEF_INDEX, None)


def drop_beliefs_on_write(state: ORMExecuteState) -> None:
    if not state.is_select and getattr(getattr(state.statement, "table", None), "name", BeliefRow.__tablename__) == BeliefRow.__tablename__:
        drop_beliefs(state.session)


event.listen(Session, "after_flush", follow_beliefs)
event.listen(Session, "after_soft_rollback", drop_beliefs)
event.listen(Session, "do_orm_execute", drop_beliefs_on_write)
register_index(BELIEF_INDEX)


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
    known = await beliefs_of(ctx.session, holder_id)
    row = known.get((subject_id, attribute))
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
        known[(subject_id, attribute)] = row
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
        row = (await beliefs_of(self.session, self.holder_id)).get((subject_id, attribute))
        if row is None or row.confidence <= 0:
            return round_half_up(truth * self.rules.belief_state.prior_pct / PERCENT)
        return row.value


async def literacy_for(ctx: TickContext, holder_id: int, seen: dict[int, int]) -> int:
    if holder_id not in seen:
        holder = await ctx.session.get(EntityRow, holder_id)
        folk = await people_of(ctx.session, holder) if holder is not None else None
        culture = await ctx.session.get(PeopleCultureRow, folk.id) if folk is not None else None
        seen[holder_id] = culture.literacy if culture is not None else 0
    return seen[holder_id]


async def fade_beliefs(ctx: TickContext) -> int:
    faded = 0
    table = ctx.rules.belief_state
    literacy: dict[int, int] = {}
    for row in list(await ctx.session.scalars(select(BeliefRow).where(BeliefRow.as_of_epoch < ctx.epoch))):
        if LOCK in (row.locked or []) or held(row.holder_node_id):
            continue
        letters = await literacy_for(ctx, row.holder_node_id, literacy)
        decay = table.decay * (1 - letters / PERCENT * table.records_pct / PERCENT)
        if letters >= table.records_at and row.source is not BeliefSource.RECORDS:
            row.source = BeliefSource.RECORDS
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
