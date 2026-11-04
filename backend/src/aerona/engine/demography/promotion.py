from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.body import BodyFunction, HarmCause, InjuryKind, MaimedKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.book import anatomy_for, ensure_body
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import CohortKey, cohorts_of, row_for
from aerona.engine.disease.harm import lasting_illness
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.interconnect.guards import blocked
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.memories import remember
from aerona.engine.phases.births import NOTABLE_ROLES, raise_notable
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, add_flag, living_entity, remove_flag
from aerona.engine.primitives.stats import stat

DORMANT_KEY = "dormant"
MAIMED_KEY = "maimed"
F = BodyFunction
IK = InjuryKind
M = MaimedKind
MAIMED_WOUNDS: dict[MaimedKind, tuple[BodyFunction, InjuryKind]] = {
    M.ONE_ARMED: (F.GRASP, IK.SEVERED),
    M.ONE_LEGGED: (F.LOCOMOTION, IK.SEVERED),
    M.ONE_EYED: (F.SIGHT, IK.GOUGED),
    M.BLIND: (F.SIGHT, IK.GOUGED),
    M.DEAF: (F.HEARING, IK.DESTROYED),
    M.MUTE: (F.SPEECH, IK.DESTROYED),
    M.LAME: (F.LOCOMOTION, IK.CRUSH),
    M.SCARRED: (F.PRESENCE, IK.BURN),
    M.BROKEN_MINDED: (F.COGNITION, IK.CRUSH),
}
BOTH_SIDES = frozenset({M.BLIND, M.DEAF})


async def named_count(ctx: TickContext) -> int:
    found = await ctx.session.scalar(
        select(func.count()).select_from(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    )
    return int(found or 0)


def famine_dead(ctx: TickContext) -> Counter[int]:
    dead: Counter[int] = Counter()
    for (_phase, key, node, category), delta in ctx.environment.stats.flows.items():
        if key == "population" and category == FlowCategory.FAMINE.value and delta < 0:
            dead[node] -= delta
    return dead


@dataclass(frozen=True)
class Moment:
    community: EntityRow
    social_class: SocialClass
    reason: str
    maimed: MaimedKind | None = None
    outbreak: OutbreakRow | None = None


async def notable_moments(ctx: TickContext) -> list[Moment]:
    table = ctx.rules.cohorts
    moments: list[Moment] = []
    maimed: Counter[int] = Counter()
    kinds: dict[int, Counter[MaimedKind]] = {}
    for row in await ctx.session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.updated_epoch == ctx.epoch)):
        maimed[row.community_entity_id] += row.count
        kinds.setdefault(row.community_entity_id, Counter())[row.kind] += row.count
    for community_id, count in sorted(maimed.items()):
        community = await living_entity(ctx.session, community_id)
        if community is not None and count >= table.promotion_maimed_min:
            common = max(sorted(kinds[community_id].items(), key=lambda item: item[0].value), key=lambda item: item[1])[0]
            moments.append(Moment(community, SocialClass.WARRIOR, "maimed", maimed=common))
    for community_id, count in sorted(famine_dead(ctx).items()):
        community = await living_entity(ctx.session, community_id)
        if community is not None and count >= table.promotion_famine_dead_min:
            moments.append(Moment(community, SocialClass.FARMER, "orphan"))
    atlas = await RegionAtlas.load(ctx.session)
    for outbreak in await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.started_epoch == ctx.epoch).order_by(OutbreakRow.id)):
        residents = [await living_entity(ctx.session, entity_id) for entity_id in atlas.communities_in(outbreak.region_entity_id)]
        living = [item for item in residents if item is not None and item.entity_type in {EntityType.SETTLEMENT, EntityType.PEOPLE}]
        if living:
            moments.append(Moment(max(living, key=lambda item: (stat(item, "population") or 0, -item.id)), SocialClass.FARMER, "first_sick", outbreak=outbreak))
    return moments


async def matching_wound(ctx: TickContext, mortal: EntityRow, kind: MaimedKind) -> int:
    function, injury = MAIMED_WOUNDS[kind]
    body = await ensure_body(ctx.session, ctx.rules, mortal, ctx.epoch)
    parts = anatomy_for(body).with_function(function)
    if not parts:
        return 0
    chosen = parts if kind in BOTH_SIDES else parts[:1]
    severity = ctx.rules.cohorts.promotion_injury_severity
    for part in chosen:
        harm = Harm(
            ctx.rules.intervention_effects.disaster_injury_hp, HarmCause.BATTLE, "died of an old war wound", part=part.key, kind=injury, severity=severity
        )
        await apply_hits(ctx, mortal, harm, lethal=False)
    return len(chosen)


async def orphan_memory(ctx: TickContext, mortal: EntityRow, community: EntityRow) -> None:
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=mortal.id,
        subject_id=community.id,
        kind=MemoryKind.LAMENTED,
        magnitude=-ctx.rules.cohorts.promotion_orphan_intensity,
        epoch=ctx.epoch,
        note=f"orphaned by the famine that emptied {community.name}",
        forced=True,
    )


async def first_sickness(ctx: TickContext, mortal: EntityRow, outbreak: OutbreakRow | None) -> None:
    profile = await ctx.session.get(DiseaseProfileRow, outbreak.disease_entity_id) if outbreak is not None else None
    await lasting_illness(ctx, mortal, profile)


async def promote(ctx: TickContext) -> int:
    table = ctx.rules.cohorts
    over = await named_count(ctx) > table.named_mortal_soft_limit_per_world
    chance = table.promotion_chance * (table.promotion_over_limit_pct / 100 if over else 1)
    raised = 0
    for moment in await notable_moments(ctx):
        if raised >= table.promotion_cap:
            break
        if not ctx.rng(f"promote.{moment.community.id}.{moment.reason}").chance(chance):
            continue
        roles = NOTABLE_ROLES[moment.social_class]
        mortal = await raise_notable(ctx, moment.community, moment.social_class, roles[0])
        if moment.reason == "first_sick":
            await first_sickness(ctx, mortal, moment.outbreak)
        elif moment.reason == "maimed" and moment.maimed is not None:
            await matching_wound(ctx, mortal, moment.maimed)
        elif moment.reason == "orphan":
            await orphan_memory(ctx, mortal, moment.community)
        raised += 1
        ctx.count(f"promoted.{moment.reason}")
    return raised


async def sync_maimed(ctx: TickContext, community: EntityRow) -> int:
    rows = await cohorts_of(ctx.session, community.id)
    if not rows or blocked(community.id, MAIMED_KEY):
        return 0
    civilians = sum(
        max(0, row.count - row.veterans)
        for row in await ctx.session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.community_entity_id == community.id))
    )
    held = sum(row.count for key, row in rows.items() if key[3] is CohortCondition.MAIMED)
    gap = civilians - held
    if gap == 0:
        return 0
    source = CohortCondition.NONE if gap > 0 else CohortCondition.MAIMED
    keys: list[CohortKey] = sorted(
        (key for key in rows if key[0] is not AgeBand.CHILD and key[3] is source and rows[key].count > 0),
        key=lambda key: (key[0] is not AgeBand.ADULT, key[1] is not Sex.MALE, -rows[key].count, tuple(part.value for part in key)),
    )
    moved = 0
    for key in keys:
        part = min(rows[key].count, abs(gap) - moved)
        if part <= 0:
            break
        rows[key].count -= part
        target = (key[0], key[1], key[2], CohortCondition.MAIMED if gap > 0 else CohortCondition.NONE)
        row_for(ctx.session, rows, community.id, target, ctx.epoch).count += part
        moved += part
    return moved


async def sync_veterans(ctx: TickContext, community: EntityRow) -> int:
    veterans = sum(row.veterans for row in await ctx.session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.community_entity_id == community.id)))
    rows = await cohorts_of(ctx.session, community.id)
    if not rows:
        return 0
    held = sum(row.count for key, row in rows.items() if key[3] is CohortCondition.VETERAN)
    gap = veterans - held
    if gap == 0:
        return 0
    keys: list[CohortKey] = sorted(
        (key for key in rows if key[0] is AgeBand.ADULT and key[1] is Sex.MALE and key[3] is (CohortCondition.NONE if gap > 0 else CohortCondition.VETERAN)),
        key=lambda key: -rows[key].count,
    )
    moved = 0
    for key in keys:
        part = min(rows[key].count, abs(gap) - moved)
        if part <= 0:
            break
        rows[key].count -= part
        target = (key[0], key[1], key[2], CohortCondition.VETERAN if gap > 0 else CohortCondition.NONE)
        row_for(ctx.session, rows, community.id, target, ctx.epoch).count += part
        moved += part
    return moved


async def doze(ctx: TickContext) -> tuple[int, int]:
    table = ctx.rules.cohorts
    since = ctx.epoch - table.dormant_after_epochs
    recent = set(
        await ctx.session.scalars(
            select(IncidentParticipantRow.node_id).join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id).where(IncidentRow.epoch >= since)
        )
    )
    woken_now = set(
        await ctx.session.scalars(
            select(IncidentParticipantRow.node_id)
            .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
            .where(IncidentRow.epoch >= ctx.epoch - 1)
        )
    )
    slept = woke = 0
    flagged = await dormant_ids(ctx)
    for mortal_id in sorted(flagged & woken_now):
        if blocked(mortal_id, DORMANT_KEY):
            continue
        if await remove_flag(ctx.session, mortal_id, EntityFlag.DORMANT):
            woke += 1
    candidates = await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.birth_epoch <= since,
            func.coalesce(EntityRow.importance, 0) < table.dormant_importance,
        )
    )
    for mortal in candidates:
        if mortal.id in recent or mortal.id in flagged or blocked(mortal.id, DORMANT_KEY):
            continue
        if await active_bonds(ctx.session, [BondKind.RULES, BondKind.COMMANDS], sources=[mortal.id]):
            continue
        if await add_flag(ctx.session, mortal.id, EntityFlag.DORMANT, ctx.epoch):
            slept += 1
    return slept, woke


async def dormant_ids(ctx: TickContext) -> set[int]:
    return set(await ctx.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DORMANT)))
