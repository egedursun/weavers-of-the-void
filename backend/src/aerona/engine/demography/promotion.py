from collections import Counter

from sqlalchemy import func, select

from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.conditions import gain_condition
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import CohortKey, cohorts_of, row_for
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.phases.births import NOTABLE_ROLES, raise_notable
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, add_flag, living_entity, remove_flag
from aerona.engine.primitives.stats import stat


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


async def notable_moments(ctx: TickContext) -> list[tuple[EntityRow, SocialClass, str]]:
    table = ctx.rules.cohorts
    moments: list[tuple[EntityRow, SocialClass, str]] = []
    maimed: Counter[int] = Counter()
    for row in await ctx.session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.updated_epoch == ctx.epoch)):
        maimed[row.community_entity_id] += row.count
    for community_id, count in sorted(maimed.items()):
        community = await living_entity(ctx.session, community_id)
        if community is not None and count >= table.promotion_maimed_min:
            moments.append((community, SocialClass.WARRIOR, "maimed"))
    for community_id, count in sorted(famine_dead(ctx).items()):
        community = await living_entity(ctx.session, community_id)
        if community is not None and count >= table.promotion_famine_dead_min:
            moments.append((community, SocialClass.FARMER, "orphan"))
    atlas = await RegionAtlas.load(ctx.session)
    for outbreak in await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.started_epoch == ctx.epoch).order_by(OutbreakRow.id)):
        residents = [await living_entity(ctx.session, entity_id) for entity_id in atlas.communities_in(outbreak.region_entity_id)]
        living = [item for item in residents if item is not None and item.entity_type in {EntityType.SETTLEMENT, EntityType.PEOPLE}]
        if living:
            moments.append((max(living, key=lambda item: (stat(item, "population") or 0, -item.id)), SocialClass.FARMER, "first_sick"))
    return moments


async def promote(ctx: TickContext) -> int:
    table = ctx.rules.cohorts
    over = await named_count(ctx) > table.named_mortal_soft_limit_per_world
    chance = table.promotion_chance * (table.promotion_over_limit_pct / 100 if over else 1)
    raised = 0
    for community, social_class, reason in await notable_moments(ctx):
        if raised >= table.promotion_cap:
            break
        if not ctx.rng(f"promote.{community.id}.{reason}").chance(chance):
            continue
        roles = NOTABLE_ROLES[social_class]
        mortal = await raise_notable(ctx, community, social_class, roles[0])
        if reason == "first_sick":
            await gain_condition(ctx, mortal, ConditionKind.CHRONIC_ILLNESS, HarmCause.DISASTER)
        raised += 1
        ctx.count(f"promoted.{reason}")
    return raised


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
        if mortal.id in recent or mortal.id in flagged:
            continue
        if await active_bonds(ctx.session, [BondKind.RULES, BondKind.COMMANDS], sources=[mortal.id]):
            continue
        if await add_flag(ctx.session, mortal.id, EntityFlag.DORMANT, ctx.epoch):
            slept += 1
    return slept, woke


async def dormant_ids(ctx: TickContext) -> set[int]:
    return set(await ctx.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DORMANT)))
