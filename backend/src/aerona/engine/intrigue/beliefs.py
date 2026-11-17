from dataclasses import dataclass

from sqlalchemy import event, func, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session
from sqlalchemy.orm.attributes import set_committed_value

from aerona.constants.units import PERCENT
from aerona.db.attr_history import changed
from aerona.db.profile_guard import profile_key
from aerona.db.read_memo import register_index, touched_rows
from aerona.db.tables.belief_depth import SourceTrustRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.write_guard import held, write_blocked
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
TRUST_BASE = 60


BELIEF_INDEX = "aerona.belief_index"
BELIEF_INDEX_WHOLE = "aerona.belief_index.whole"
BELIEF_PENDING = "aerona.belief_index.pending"
TRUST_ABSENT = "source_trust_absent"
BELIEF_KEYS = ("holder_node_id", "subject_node_id", "attribute")
KEEP_BELIEFS = "aerona.keep_belief_index"
FADED = ("confidence", "source")
FADE_CHUNK = 500


def note_pending(sync: Session, instance: object) -> None:
    if isinstance(instance, BeliefRow):
        sync.info.setdefault(BELIEF_PENDING, []).append(instance)
    if isinstance(instance, SourceTrustRow):
        sync.info.get(TRUST_ABSENT, set()).discard((instance.holder_node_id, instance.source))


async def trust_of(session: AsyncSession, holder_id: int, source: BeliefSource) -> SourceTrustRow | None:
    absent: set[tuple[int, BeliefSource]] = session.sync_session.info.setdefault(TRUST_ABSENT, set())
    if (holder_id, source) in absent:
        return None
    row = await session.get(SourceTrustRow, (holder_id, source))
    if row is None:
        absent.add((holder_id, source))
    return row


def foreign_beliefs(sync: Session, index: dict[int, dict[tuple[int, str], BeliefRow]]) -> bool:
    pending: list[BeliefRow] = sync.info.pop(BELIEF_PENDING, [])
    for item in pending:
        if index.get(item.holder_node_id, {}).get((item.subject_node_id, item.attribute)) is not item:
            return True
    return any(isinstance(item, BeliefRow) for item in sync.deleted)


async def beliefs_of(session: AsyncSession, holder_id: int) -> dict[tuple[int, str], BeliefRow]:
    sync = session.sync_session
    index: dict[int, dict[tuple[int, str], BeliefRow]] = sync.info.setdefault(BELIEF_INDEX, {})
    if foreign_beliefs(sync, index):
        await session.flush()
        index = sync.info.setdefault(BELIEF_INDEX, {})
    known = index.get(holder_id)
    if known is not None:
        return known
    if not sync.info.get(BELIEF_INDEX_WHOLE):
        for row in await session.scalars(select(BeliefRow).order_by(BeliefRow.id)):
            index.setdefault(row.holder_node_id, {}).setdefault((row.subject_node_id, row.attribute), row)
        sync.info[BELIEF_INDEX_WHOLE] = True
    return index.setdefault(holder_id, {})


def rekeyed(item: BeliefRow) -> bool:
    state = inspect(item)
    return any(key in state.committed_state and changed(state, key) for key in BELIEF_KEYS)


def follow_beliefs(sync: Session, *_: object) -> None:
    index: dict[int, dict[tuple[int, str], BeliefRow]] | None = sync.info.get(BELIEF_INDEX)
    if index is None:
        return
    whole = bool(sync.info.get(BELIEF_INDEX_WHOLE))
    new, dirty, deleted = touched_rows(sync, BeliefRow)
    for item in new:
        if whole or item.holder_node_id in index:
            index.setdefault(item.holder_node_id, {}).setdefault((item.subject_node_id, item.attribute), item)
    for item in deleted:
        known = index.get(item.holder_node_id, {})
        if known.get((item.subject_node_id, item.attribute)) is item:
            del known[(item.subject_node_id, item.attribute)]
    if any(rekeyed(item) for item in dirty):
        sync.info.pop(BELIEF_INDEX, None)
        sync.info.pop(BELIEF_INDEX_WHOLE, None)


def drop_beliefs(sync: Session, *_: object) -> None:
    sync.info.pop(TRUST_ABSENT, None)
    sync.info.pop(BELIEF_INDEX, None)
    sync.info.pop(BELIEF_INDEX_WHOLE, None)
    sync.info.pop(BELIEF_PENDING, None)


def drop_beliefs_on_write(state: ORMExecuteState) -> None:
    if state.is_select or state.execution_options.get(KEEP_BELIEFS):
        return
    if getattr(getattr(state.statement, "table", None), "name", BeliefRow.__tablename__) == BeliefRow.__tablename__:
        drop_beliefs(state.session)


event.listen(Session, "after_flush", follow_beliefs)
event.listen(Session, "transient_to_pending", note_pending)
event.listen(Session, "after_soft_rollback", drop_beliefs)
event.listen(Session, "do_orm_execute", drop_beliefs_on_write)
register_index(BELIEF_INDEX)
register_index(BELIEF_PENDING)


async def believe(
    ctx: TickContext, holder_id: int, subject_id: int, attribute: str, truth: int, *, source: BeliefSource, confidence: int, false: bool = False
) -> BeliefRow | None:
    if held(holder_id):
        return None
    trusted = await trust_of(ctx.session, holder_id, source)
    if trusted is not None:
        if trusted.trust < ctx.rules.belief_depth.trust_floor and not false:
            return None
        confidence = clamp_int(confidence * (PERCENT + trusted.trust - TRUST_BASE) // PERCENT, 0, PERCENT)
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


def guarded_fade(holder_id: int, subject_id: int, locked: list[str] | None) -> bool:
    return bool(locked) or any(write_blocked(owner, profile_key(BeliefRow.__tablename__, column)) for owner in (holder_id, subject_id) for column in FADED)


def fade_row(row: BeliefRow, letters: int, decay: float, records_at: int) -> None:
    if letters >= records_at and row.source is not BeliefSource.RECORDS:
        row.source = BeliefSource.RECORDS
    row.confidence = clamp_int(row.confidence - decay, 0, PERCENT)


async def fade_beliefs(ctx: TickContext) -> int:
    faded = 0
    table = ctx.rules.belief_state
    literacy: dict[int, int] = {}
    sync = ctx.session.sync_session
    found = await ctx.session.execute(
        select(BeliefRow.id, BeliefRow.holder_node_id, BeliefRow.subject_node_id, BeliefRow.confidence, BeliefRow.source, BeliefRow.locked).where(
            BeliefRow.as_of_epoch < ctx.epoch
        )
    )
    mapped: dict[int, tuple[int, float]] = {}
    updates: list[dict[str, object]] = []
    for belief_id, holder_id, subject_id, confidence, source, locked in list(found):
        if LOCK in (locked or []) or held(holder_id):
            continue
        letters = await literacy_for(ctx, holder_id, literacy)
        decay = table.decay * (1 - letters / PERCENT * table.records_pct / PERCENT)
        faded += 1
        after = clamp_int(confidence - decay, 0, PERCENT)
        if after <= 0 or guarded_fade(holder_id, subject_id, locked):
            mapped[belief_id] = (letters, decay)
            continue
        recorded = BeliefSource.RECORDS if letters >= table.records_at else source
        if after == confidence and recorded is source:
            continue
        updates.append({"id": belief_id, "confidence": after, "source": recorded})
    if updates:
        await ctx.session.execute(update(BeliefRow).execution_options(**{KEEP_BELIEFS: True}), updates)
        for change in updates:
            row = sync.identity_map.get(sync.identity_key(BeliefRow, change["id"]))
            if row is not None:
                set_committed_value(row, "confidence", change["confidence"])
                set_committed_value(row, "source", change["source"])
    ids = list(mapped)
    for start in range(0, len(ids), FADE_CHUNK):
        for row in list(await ctx.session.scalars(select(BeliefRow).where(BeliefRow.id.in_(ids[start : start + FADE_CHUNK])).order_by(BeliefRow.id))):
            letters, decay = mapped[row.id]
            fade_row(row, letters, decay, table.records_at)
            if row.confidence <= 0:
                await ctx.session.delete(row)
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


async def evidence_trusts(session: AsyncSession, holder_ids: list[int]) -> dict[int, float]:
    found: dict[int, float] = {}
    wanted = sorted(set(holder_ids))
    for start in range(0, len(wanted), FADE_CHUNK):
        rows = await session.execute(
            select(BeliefRow.holder_node_id, func.avg(BeliefRow.confidence))
            .where(BeliefRow.holder_node_id.in_(wanted[start : start + FADE_CHUNK]), BeliefRow.false.is_(False))
            .group_by(BeliefRow.holder_node_id)
        )
        found.update({holder: float(mean or 0) for holder, mean in rows})
    return found


def price_key(commodity: str) -> str:
    return f"{PRICE}{commodity}"


async def believed_prices(ctx: TickContext, holder_id: int, market_id: int, truth: dict[CommodityKind, int]) -> dict[CommodityKind, int]:
    confidence = ctx.rules.belief_state.observe_confidence
    seen: dict[CommodityKind, int] = {}
    for commodity, price in truth.items():
        row = await believe(ctx, holder_id, market_id, price_key(commodity.value), price, source=BeliefSource.OBSERVATION, confidence=confidence)
        seen[commodity] = row.value if row is not None else price
    return seen
