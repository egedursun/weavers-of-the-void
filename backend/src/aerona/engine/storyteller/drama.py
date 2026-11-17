from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.ages import ArcBeatRow, ArcFigureRow, ArcRow, SetupRow
from aerona.db.tables.culture import ProphecyConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.mind import DreamRow
from aerona.db.tables.sacred import DivinationRow, ForesightRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import ArcOutcome, ArcRole, ArcTemplate, PayoffKind, SetupKind
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.collective import StoryletId
from aerona.domain.enums.culture import ProphecyState
from aerona.domain.enums.mind import DreamReading
from aerona.domain.enums.sacred import ForesightStatus
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int

CONFRONTING = frozenset({ArcTemplate.REVENGE, ArcTemplate.RIVALRY})
OPPOSED = (ArcRole.FOE, ArcRole.RIVAL)
T = ArcTemplate
ADVANCED_BY: dict[StoryletId, frozenset[ArcTemplate]] = {
    StoryletId.LOST_HEIR: frozenset({T.EXILE_AND_RETURN, T.RAGS_TO_RICHES, T.COMING_OF_AGE}),
    StoryletId.HOARDED_STORE: frozenset({T.CORRUPTION, T.REDEMPTION}),
    StoryletId.BEAST_DEMAND: frozenset({T.QUEST, T.REVENGE, T.APOTHEOSIS}),
    StoryletId.FORBIDDEN_TEXT: frozenset({T.CORRUPTION, T.MENTOR_AND_HEIR, T.APOTHEOSIS}),
    StoryletId.DEFILED_SITE: frozenset({T.REDEMPTION, T.TRAGEDY, T.CORRUPTION}),
    StoryletId.WEDDING_CHALLENGE: frozenset({T.FORBIDDEN_LOVE, T.RIVALRY, T.FOUNDING}),
    StoryletId.DYING_RULER: frozenset({T.RISE_AND_FALL, T.TRAGEDY, T.FALL_OF_A_HOUSE, T.MENTOR_AND_HEIR}),
    StoryletId.INSULTED_ENVOY: frozenset({T.RIVALRY, T.REVENGE, T.EXILE_AND_RETURN}),
}


@dataclass
class DramaTally:
    pressed: int = 0
    countered: int = 0
    setups: int = 0
    fulfilled: int = 0
    subverted: int = 0
    lapsed: int = 0


async def press_stalled(ctx: TickContext, tally: DramaTally) -> None:
    table = ctx.rules.arcs
    awaited = set(await ctx.session.scalars(select(SetupRow.subject_node_id).where(SetupRow.payoff == PayoffKind.OPEN, SetupRow.subject_node_id.is_not(None))))
    for arc in await ctx.session.scalars(select(ArcRow).where(ArcRow.outcome == ArcOutcome.OPEN).order_by(ArcRow.id)):
        if held(arc.subject_node_id) or "drama" in arc.locked:
            continue
        stalled = ctx.epoch - arc.last_beat_epoch >= table.stall_epochs
        gain = (table.drama_step if stalled else 0) + (table.setup_pull if arc.subject_node_id in awaited else 0)
        if not gain:
            continue
        arc.drama = clamp_int(arc.drama + gain, 0, PERCENT)
        tally.pressed += 1


async def counter(ctx: TickContext, moved: list[ArcRow], tally: DramaTally) -> None:
    table = ctx.rules.arcs
    for arc in moved:
        figures = list(await ctx.session.scalars(select(ArcFigureRow.node_id).where(ArcFigureRow.arc_id == arc.id)))
        if not figures:
            continue
        for other in await ctx.session.scalars(select(ArcRow).where(ArcRow.subject_node_id.in_(figures), ArcRow.outcome == ArcOutcome.OPEN)):
            if held(other.subject_node_id) or "drama" in other.locked:
                continue
            other.drama = clamp_int(other.drama + table.counterpoint, 0, PERCENT)
            tally.countered += 1
        if "drama" not in arc.locked:
            arc.drama = 0


async def world_drama(ctx: TickContext, world_id: int, storylet: StoryletId) -> int:
    subjects = select(EntityRow.id).where(EntityRow.world_id == world_id)
    found = await ctx.session.scalar(
        select(func.max(ArcRow.drama)).where(
            ArcRow.subject_node_id.in_(subjects), ArcRow.outcome == ArcOutcome.OPEN, ArcRow.template.in_(sorted(ADVANCED_BY[storylet]))
        )
    )
    return int(found or 0)


def pressed(ctx: TickContext, chance: float, drama: int) -> float:
    return chance * (1 + drama * ctx.rules.arcs.drama_boost / PERCENT / PERCENT)


async def pressing_foe(ctx: TickContext, node_id: int) -> tuple[int, int] | None:
    rows = await ctx.session.execute(
        select(ArcRow.drama, ArcFigureRow.node_id)
        .join(ArcFigureRow, ArcFigureRow.arc_id == ArcRow.id)
        .where(
            ArcRow.subject_node_id == node_id,
            ArcRow.outcome == ArcOutcome.OPEN,
            ArcRow.template.in_(list(CONFRONTING)),
            ArcFigureRow.role.in_(list(OPPOSED)),
        )
        .order_by(ArcRow.drama.desc(), ArcRow.id)
        .limit(1)
    )
    found = rows.first()
    return (int(found[0]), int(found[1])) if found is not None else None


async def logged(ctx: TickContext, kind: SetupKind, source_id: int) -> bool:
    found = await ctx.session.scalar(select(SetupRow.id).where(SetupRow.kind == kind, SetupRow.source_id == source_id).limit(1))
    return found is not None


async def log_setup(ctx: TickContext, kind: SetupKind, source_id: int, subject_id: int | None, tally: DramaTally) -> None:
    if (subject_id is not None and held(subject_id)) or await logged(ctx, kind, source_id):
        return
    ctx.session.add(SetupRow(kind=kind, source_id=source_id, subject_node_id=subject_id, opened_epoch=ctx.epoch, locked=[]))
    tally.setups += 1


async def log_setups(ctx: TickContext, tally: DramaTally) -> None:
    since = ctx.epoch - 1
    for sight in await ctx.session.scalars(select(ForesightRow).where(ForesightRow.made_epoch >= since)):
        await log_setup(ctx, SetupKind.FORESIGHT, sight.id, sight.subject_node_id, tally)
    for prophecy in await ctx.session.scalars(select(ProphecyConditionRow).where(ProphecyConditionRow.state == ProphecyState.PENDING)):
        target = prophecy.args.get("subject") or prophecy.args.get("target")
        about = target if isinstance(target, int) else prophecy.prophecy_entity_id
        await log_setup(ctx, SetupKind.PROPHECY, prophecy.prophecy_entity_id, about, tally)
    for dream in await ctx.session.scalars(select(DreamRow).where(DreamRow.epoch >= since, DreamRow.reading != DreamReading.UNREAD)):
        await log_setup(ctx, SetupKind.DREAM, dream.id, dream.dreamer_node_id, tally)
    for reading in await ctx.session.scalars(select(DivinationRow).where(DivinationRow.epoch >= since)):
        await log_setup(ctx, SetupKind.OMEN, reading.id, reading.client_entity_id, tally)
    for thread in await ctx.session.scalars(select(ThreadRow).where(ThreadRow.epoch >= since, ThreadRow.status == ThreadStatus.OPEN)):
        subject = await ctx.session.scalar(
            select(ThreadLinkRow.entity_id).where(ThreadLinkRow.thread_id == thread.id).order_by(ThreadLinkRow.entity_id).limit(1)
        )
        await log_setup(ctx, SetupKind.INCIDENT_ARC, thread.id, subject, tally)
    await ctx.session.flush()


Resolution = tuple[PayoffKind, str] | None


async def foresight_paid(ctx: TickContext, setup: SetupRow) -> Resolution:
    source_id = setup.source_id
    foresight = await ctx.session.get(ForesightRow, source_id)
    if foresight is None or foresight.status is ForesightStatus.PENDING:
        return None
    if foresight.status is ForesightStatus.FULFILLED:
        return PayoffKind.FULFILLED, "what was foreseen came to pass"
    return PayoffKind.SUBVERTED, "what was foreseen did not come"


async def prophecy_paid(ctx: TickContext, setup: SetupRow) -> Resolution:
    source_id = setup.source_id
    prophecy = await ctx.session.get(ProphecyConditionRow, source_id)
    if prophecy is None or prophecy.state is ProphecyState.PENDING:
        return None
    if prophecy.state is ProphecyState.FULFILLED:
        return PayoffKind.FULFILLED, "the prophecy was fulfilled"
    return PayoffKind.SUBVERTED, "the prophecy came to nothing"


async def thread_paid(ctx: TickContext, setup: SetupRow) -> Resolution:
    source_id = setup.source_id
    thread = await ctx.session.get(ThreadRow, source_id)
    if thread is None or thread.status is not ThreadStatus.CLOSED:
        return None
    return PayoffKind.FULFILLED, thread.closing_text or "the story was closed"


async def dream_paid(ctx: TickContext, setup: SetupRow) -> Resolution:
    source_id = setup.source_id
    dream = await ctx.session.get(DreamRow, source_id)
    if dream is None or dream.reading_true is None:
        return None
    if dream.reading_true:
        return PayoffKind.FULFILLED, "the dream was read truly"
    return PayoffKind.SUBVERTED, "the dream was read falsely"


async def omen_paid(ctx: TickContext, setup: SetupRow) -> Resolution:
    source_id = setup.source_id
    reading = await ctx.session.get(DivinationRow, source_id)
    if reading is None or reading.epoch >= ctx.epoch:
        return None
    if reading.verdict is reading.true_verdict:
        return PayoffKind.FULFILLED, "the omen read true"
    return PayoffKind.SUBVERTED, "the omen read false"


async def portent_paid(ctx: TickContext, setup: SetupRow) -> Resolution:
    if setup.subject_node_id is None:
        return None
    subject = await ctx.session.get(EntityRow, setup.subject_node_id)
    if subject is not None and subject.end_epoch is not None and subject.end_epoch > setup.opened_epoch:
        return PayoffKind.FULFILLED, f"what was foretold came upon {subject.name} at the end"
    beat = await ctx.session.scalar(
        select(ArcBeatRow.text)
        .join(ArcRow, ArcRow.id == ArcBeatRow.arc_id)
        .where(ArcRow.subject_node_id == setup.subject_node_id, ArcBeatRow.epoch > setup.opened_epoch)
        .order_by(ArcBeatRow.id)
        .limit(1)
    )
    if beat is None:
        return None
    return PayoffKind.FULFILLED, beat


PAYERS = {
    SetupKind.FORESIGHT: foresight_paid,
    SetupKind.PROPHECY: prophecy_paid,
    SetupKind.INCIDENT_ARC: thread_paid,
    SetupKind.DREAM: dream_paid,
    SetupKind.OMEN: omen_paid,
    SetupKind.PORTENT: portent_paid,
}


async def resolution_of(ctx: TickContext, row: SetupRow) -> Resolution:
    found = await PAYERS[row.kind](ctx, row)
    if found is not None:
        return found
    if ctx.epoch - row.opened_epoch >= ctx.rules.arcs.lapse_epochs:
        return PayoffKind.LAPSED, "it was never paid"
    return None


async def pay_setups(ctx: TickContext, tally: DramaTally) -> None:
    for row in list(await ctx.session.scalars(select(SetupRow).where(SetupRow.payoff == PayoffKind.OPEN).order_by(SetupRow.id))):
        if "payoff" in row.locked or (row.subject_node_id is not None and held(row.subject_node_id)):
            continue
        found = await resolution_of(ctx, row)
        if found is None:
            continue
        row.payoff, row.payoff_text = found
        row.paid_epoch = ctx.epoch
        setattr(tally, found[0].value, getattr(tally, found[0].value) + 1)
        if found[0] is not PayoffKind.LAPSED:
            told = f"What was set up in epoch {row.opened_epoch} ({spoken(row.kind)}) was paid off: {found[1]}."
            await note(ctx, told, key="arcs.payoff", ids=[row.subject_node_id] if row.subject_node_id is not None else [])


async def keep_drama(ctx: TickContext, moved: list[ArcRow], tally: DramaTally) -> None:
    await press_stalled(ctx, tally)
    await counter(ctx, moved, tally)
    await log_setups(ctx, tally)
    await pay_setups(ctx, tally)
    await ctx.session.flush()
