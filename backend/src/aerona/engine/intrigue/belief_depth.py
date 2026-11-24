from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.intrigue import BELIEF_ATTRIBUTES
from aerona.catalog.life.made import LANDED
from aerona.constants.units import PERCENT
from aerona.db.tables.belief_depth import SourceTrustRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.tables.made import IntrusionRow, SurveillanceProfileRow
from aerona.db.tables.mind import DreamRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.sacred import DivinationRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.made import Attribution, IntrusionAim
from aerona.domain.enums.minds import MindOrigin
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.intrigue.sources import SourceTally, shown_facts
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat

HOSTILE = "hostile"
WRONG_PCT = 25


async def tell(ctx: TickContext, holder: int, subject: EntityRow, source: BeliefSource, *, confidence: int, tally: SourceTally) -> None:
    for attribute, truth in shown_facts(subject):
        if await believe(ctx, holder, subject.id, attribute, truth, source=source, confidence=confidence):
            tally.beliefs += 1


async def surveillance_reports(ctx: TickContext, tally: SourceTally) -> None:
    base = ctx.rules.belief_depth.surveillance_confidence
    for profile in list(await ctx.session.scalars(select(SurveillanceProfileRow).where(SurveillanceProfileRow.capacity > 0))):
        if held(profile.polity_entity_id):
            continue
        towns = await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == profile.polity_entity_id))
        for town_id in list(towns):
            town = await ctx.session.get(EntityRow, town_id)
            if town is not None and town.status is EntityStatus.CANON:
                await tell(ctx, profile.polity_entity_id, town, BeliefSource.SURVEILLANCE, confidence=base * profile.reach_pct // PERCENT, tally=tally)


async def intrusion_reports(ctx: TickContext, tally: SourceTally) -> None:
    confidence = ctx.rules.belief_depth.intrusion_confidence
    rows = await ctx.session.scalars(
        select(IntrusionRow).where(IntrusionRow.epoch == ctx.epoch, IntrusionRow.outcome.in_(sorted(LANDED)), IntrusionRow.aim == IntrusionAim.READ)
    )
    for row in list(rows):
        target = await ctx.session.get(EntityRow, row.target_node_id) if row.target_node_id is not None else None
        if row.actor_node_id is not None and target is not None and not held(row.actor_node_id):
            await tell(ctx, row.actor_node_id, target, BeliefSource.INTRUSION, confidence=confidence, tally=tally)


async def dream_reports(ctx: TickContext, tally: SourceTally) -> None:
    confidence = ctx.rules.belief_depth.dream_confidence
    for row in list(await ctx.session.scalars(select(DreamRow).where(DreamRow.epoch == ctx.epoch).order_by(DreamRow.id))):
        if held(row.dreamer_node_id):
            continue
        for subject_id in row.content or []:
            subject = await ctx.session.get(EntityRow, subject_id)
            if subject is not None and subject.id != row.dreamer_node_id:
                await tell(ctx, row.dreamer_node_id, subject, BeliefSource.DREAM, confidence=confidence * row.intensity // PERCENT, tally=tally)


async def omen_reports(ctx: TickContext, tally: SourceTally) -> None:
    confidence = ctx.rules.belief_depth.omen_confidence
    rows = await ctx.session.scalars(
        select(DivinationRow)
        .where(DivinationRow.epoch == ctx.epoch, DivinationRow.heeded.is_(True), DivinationRow.client_entity_id.is_not(None))
        .order_by(DivinationRow.id)
    )
    for row in list(rows):
        client = await ctx.session.get(EntityRow, row.client_entity_id) if row.client_entity_id is not None else None
        place = await ctx.session.get(EntityRow, client.location_id) if client is not None and client.location_id is not None else None
        if client is not None and place is not None and not held(client.id):
            await tell(ctx, client.id, place, BeliefSource.OMEN, confidence=confidence, tally=tally)


async def made_mind_reports(ctx: TickContext, tally: SourceTally) -> None:
    confidence = ctx.rules.belief_depth.made_mind_confidence
    minds = await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.origin != MindOrigin.BORN, MindProfileRow.made_by_node_id.is_not(None)))
    for mind in list(minds):
        being = await ctx.session.get(EntityRow, mind.node_id)
        place = await ctx.session.get(EntityRow, being.location_id) if being is not None and being.location_id is not None else None
        if place is not None and mind.made_by_node_id is not None and not held(mind.made_by_node_id):
            await tell(ctx, mind.made_by_node_id, place, BeliefSource.MADE_MIND_REPORT, confidence=confidence, tally=tally)


async def false_flags(ctx: TickContext, tally: SourceTally) -> None:
    rows = await ctx.session.scalars(select(IntrusionRow).where(IntrusionRow.epoch == ctx.epoch, IntrusionRow.attribution == Attribution.FALSE_FLAG))
    for row in list(rows):
        if row.target_node_id is None or row.blamed_node_id is None or row.blamed_node_id == row.actor_node_id:
            continue
        if await believe(ctx, row.target_node_id, row.blamed_node_id, HOSTILE, PERCENT, source=BeliefSource.DECEPTION, confidence=PERCENT, false=True):
            tally.beliefs += 1


async def trust_of(ctx: TickContext, holder: int, source: BeliefSource) -> SourceTrustRow:
    row = await ctx.session.get(SourceTrustRow, (holder, source))
    if row is None:
        row = SourceTrustRow(holder_node_id=holder, source=source, locked=[])
        ctx.session.add(row)
    return row


async def judge_sources(ctx: TickContext) -> int:
    step = ctx.rules.belief_depth.trust_step
    judged = 0
    fresh = await ctx.session.scalars(select(BeliefRow).where(BeliefRow.as_of_epoch == ctx.epoch - 1, BeliefRow.attribute.in_(list(BELIEF_ATTRIBUTES))))
    for belief in list(fresh):
        subject = await ctx.session.get(EntityRow, belief.subject_node_id)
        truth = stat(subject, belief.attribute) if subject is not None else None
        if truth is None or held(belief.holder_node_id):
            continue
        row = await trust_of(ctx, belief.holder_node_id, belief.source)
        wrong = abs(belief.value - truth) * PERCENT > WRONG_PCT * max(1, abs(truth))
        if wrong:
            row.wrong += 1
        else:
            row.right += 1
        if "trust" not in row.locked:
            row.trust = clamp_int(row.trust + (-step if wrong else step), 0, PERCENT)
        row.updated_epoch = ctx.epoch
        judged += 1
    return judged


async def share_beliefs(ctx: TickContext) -> int:
    table = ctx.rules.belief_depth
    groups: dict[tuple[int, int, str], list[int]] = defaultdict(list)
    rows = await ctx.session.execute(
        select(EntityRow.location_id, BeliefRow.subject_node_id, BeliefRow.attribute, BeliefRow.value)
        .join(EntityRow, EntityRow.id == BeliefRow.holder_node_id)
        .where(EntityRow.location_id.is_not(None), BeliefRow.false.is_(False))
    )
    for place, subject, attribute, value in rows:
        if place is not None:
            groups[(place, subject, attribute)].append(value)
    shared = 0
    for (place, subject, attribute), values in sorted(groups.items()):
        community = await ctx.session.get(EntityRow, place)
        if community is None or community.entity_type not in COMMUNITY_TYPES or len(values) < table.shared_at or held(community.id) or subject == community.id:
            continue
        mean = sum(values) // len(values)
        await believe(
            ctx, community.id, subject, attribute, mean, source=BeliefSource.RUMOUR, confidence=min(PERCENT, len(values) * PERCENT // (table.shared_at * 2))
        )
        if attribute == HOSTILE and mean > PERCENT // 2:
            await sway_opinion(ctx, community.id, subject)
        shared += 1
    return shared


async def sway_opinion(ctx: TickContext, community_id: int, subject_id: int) -> None:
    first, second = sorted((community_id, subject_id))
    row = await ctx.session.scalar(select(CommunityRelationRow).where(CommunityRelationRow.entity_a_id == first, CommunityRelationRow.entity_b_id == second))
    if row is not None:
        row.value = clamp_int(row.value - ctx.rules.belief_depth.public_opinion_pct, -PERCENT, PERCENT)


async def keep_belief_depth(ctx: TickContext, tally: SourceTally) -> None:
    await surveillance_reports(ctx, tally)
    await intrusion_reports(ctx, tally)
    await made_mind_reports(ctx, tally)
    await dream_reports(ctx, tally)
    await omen_reports(ctx, tally)
    await false_flags(ctx, tally)
    ctx.count("sources_judged", await judge_sources(ctx))
    ctx.count("beliefs_shared", await share_beliefs(ctx))
