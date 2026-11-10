from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.relations import APPEALS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.relations import GroupRankRow, PassionRow, PersuasionRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Facet, SkillKind, ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.relations import AppealKind, PassionKind, PersuasionAim
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import evidence_trust
from aerona.engine.mind.aspirations import rules_over
from aerona.engine.mind.book import is_locked, mind_of, skill_level, stored_values, values_for, write_values
from aerona.engine.mind.split import facets_of
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int

FACET_SPAN = 50
VALUE_SPAN = 100
HALF = PERCENT // 2
WARM = (PassionKind.LOVE, PassionKind.LOYALTY)
COUNCIL_VOICES = 3
COURT_FLOOR = 10**6
EVIDENCE_TRUST_DIVISOR = 4


@dataclass(frozen=True)
class Argument:
    score: int
    success: bool
    record_id: int | None


async def voice_of(session: AsyncSession, node_id: int) -> int:
    entity = await session.get(EntityRow, node_id)
    if entity is None or entity.entity_type is EntityType.MORTAL:
        return node_id
    profile = await session.get(FactionProfileRow, node_id)
    return profile.leader_entity_id if profile is not None and profile.leader_entity_id is not None else node_id


def facet_lean(facets: dict[Facet, int], appeal: AppealKind) -> float:
    return sum(facets.get(facet, 0) * weight for facet, weight in APPEALS[appeal].facets.items()) / FACET_SPAN


async def appeal_fit(session: AsyncSession, speaker: int, target: int, appeal: AppealKind, *, axis: ValueAxis | None, toward: int | None) -> float:
    facets = await facets_of(session, target)
    fit = facet_lean(facets, appeal)
    speaking = await session.get(MortalProfileRow, speaker)
    if appeal is AppealKind.BELIEF and axis is not None:
        held = (await values_for(session, target)).get(axis, 0)
        fit += held * (1 if (toward or 0) >= 0 else -1) / VALUE_SPAN * HALF
    elif appeal is AppealKind.AUTHORITY:
        fit += await rules_over(session, speaker) / 2 + (speaking.renown if speaking is not None else 0) / 4
    elif appeal is AppealKind.EVIDENCE:
        fit += await skill_level(session, speaker, SkillKind.LORE) / 2 + await evidence_trust(session, target) / EVIDENCE_TRUST_DIVISOR
    elif appeal is AppealKind.FEAR:
        fit += (speaking.infamy if speaking is not None else 0) / 2
    elif appeal is AppealKind.SELF_INTEREST:
        fit += (speaking.wealth if speaking is not None else 0) / 4
    return fit


async def stubbornness(session: AsyncSession, target: int) -> float:
    facets = await facets_of(session, target)
    profile = await session.get(MortalProfileRow, target)
    return (facets.get(Facet.ASSERTIVENESS, 0) + FACET_SPAN) / 2 + (profile.conviction if profile is not None else HALF) / 2


async def passion_pull(session: AsyncSession, target: int, speaker: int) -> int:
    rows = await session.scalars(select(PassionRow).where(PassionRow.holder_node_id == target, PassionRow.object_node_id == speaker))
    return sum(row.strength if row.kind in WARM else -row.strength for row in rows)


async def sway_belief(ctx: TickContext, target: int, axis: ValueAxis, toward: int) -> None:
    entity = await ctx.session.get(EntityRow, target)
    if entity is None or entity.entity_type is not EntityType.MORTAL or is_locked(await mind_of(ctx.session, target), "values"):
        return
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, target)
    step = ctx.rules.persuasion.belief_shift * (1 if toward >= 0 else -1)
    values[axis] = clamp_int(values.get(axis, 0) + step, -VALUE_SPAN, VALUE_SPAN)
    await write_values(ctx.session, ValueHolder.PERSONAL, target, values)


async def persuade(
    ctx: TickContext,
    speaker_id: int,
    target_id: int,
    appeal: AppealKind,
    aim: PersuasionAim,
    *,
    axis: ValueAxis | None = None,
    toward: int | None = None,
    subject_id: int | None = None,
) -> Argument:
    table = ctx.rules.persuasion
    session = ctx.session
    speaker = await voice_of(session, speaker_id)
    listener = await voice_of(session, target_id)
    oratory = await skill_level(session, speaker, SkillKind.ORATORY)
    fit = await appeal_fit(session, speaker, listener, appeal, axis=axis, toward=toward)
    stubborn = await stubbornness(session, listener)
    pull = await passion_pull(session, listener, speaker)
    jitter = ctx.rng(seed_of("persuade", speaker, listener, ctx.epoch, aim.value)).integer(-table.jitter, table.jitter) if table.jitter else 0
    score = round(
        HALF
        + oratory * table.oratory_pct / PERCENT
        + fit * table.fit_pct / PERCENT
        - stubborn * table.stubborn_pct / PERCENT
        + pull * table.passion_pct / PERCENT
        + jitter
    )
    success = score >= table.threshold
    if success and aim is PersuasionAim.BELIEF and axis is not None:
        await sway_belief(ctx, listener, axis, toward or 0)
    if success:
        await think(session, ctx.rules, listener, ThoughtKind.WAS_PERSUADED, ctx.epoch, subject_id=speaker)
    if write_blocked(listener, "persuasions"):
        return Argument(score, success, None)
    row = PersuasionRow(
        speaker_node_id=speaker_id,
        target_node_id=target_id,
        appeal=appeal,
        aim=aim,
        axis=axis,
        subject_node_id=subject_id,
        score=score,
        success=success,
        epoch=ctx.epoch,
    )
    session.add(row)
    await session.flush()
    return Argument(score, success, row.id)


def lift(rules_pct: int, argument: Argument) -> float:
    return 1 + rules_pct / PERCENT * (argument.score - PERCENT // 2) / PERCENT


async def office_holder(session: AsyncSession, polity_id: int, *kinds: OfficeKind) -> int | None:
    found = await session.scalar(
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind.in_(list(kinds)), OfficeRow.holder_entity_id.is_not(None))
        .order_by(OfficeRow.id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def council_lift(ctx: TickContext, speaker_id: int, polity_id: int) -> float:
    standing = (
        select(GroupRankRow.rank).where(GroupRankRow.group_node_id == polity_id, GroupRankRow.member_node_id == OfficeRow.holder_entity_id).scalar_subquery()
    )
    query = (
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.holder_entity_id.is_not(None), OfficeRow.holder_entity_id != speaker_id)
        .order_by(func.coalesce(standing, COURT_FLOOR), OfficeRow.id)
        .limit(COUNCIL_VOICES)
    )
    councillors = [holder for holder in await ctx.session.scalars(query) if holder is not None]
    if not councillors:
        return 1.0
    lifts = [
        lift(ctx.rules.persuasion.council_pct, await persuade(ctx, speaker_id, holder, AppealKind.AUTHORITY, PersuasionAim.VOTE, subject_id=polity_id))
        for holder in councillors
    ]
    return sum(lifts) / len(lifts)


async def counsel_lift(ctx: TickContext, polity_id: int, ruler_id: int | None, subject_id: int) -> float:
    adviser = await office_holder(ctx.session, polity_id, OfficeKind.CHANCELLOR, OfficeKind.TREASURER)
    if adviser is None or ruler_id is None or adviser == ruler_id:
        return 1.0
    argument = await persuade(ctx, adviser, ruler_id, AppealKind.SELF_INTEREST, PersuasionAim.DECISION, subject_id=subject_id)
    return lift(ctx.rules.persuasion.counsel_pct, argument)


async def envoy_sways(ctx: TickContext, proposer_id: int, others: list[int], treaty_id: int) -> bool:
    envoy = await office_holder(ctx.session, proposer_id, OfficeKind.AMBASSADOR, OfficeKind.CHANCELLOR, OfficeKind.RULER)
    if envoy is None:
        return False
    for other in others:
        listener = await office_holder(ctx.session, other, OfficeKind.RULER) or other
        argument = await persuade(ctx, envoy, listener, AppealKind.SELF_INTEREST, PersuasionAim.TREATY, subject_id=treaty_id)
        if not argument.success:
            return False
    return ctx.rng(seed_of("envoy", treaty_id, ctx.epoch)).chance(ctx.rules.persuasion.envoy_pct)
