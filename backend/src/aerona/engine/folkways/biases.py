from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memo_of, memoized, table_names
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import BiasWeightRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.mind import FACET_MAX, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folkways import BiasedDecision, DecisionBias
from aerona.domain.enums.mind import Facet, SkillKind, ValueAxis
from aerona.engine.body.variants import ORDINARY, bias_target, folk_biology
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import living_gods
from aerona.engine.mind.book import load_holder, values_for
from aerona.engine.mind.drives import rulers_of
from aerona.engine.mind.split import culture_mean, facets_of, has_facets
from aerona.engine.primitives.numbers import clamp_int, round_half_up

MIDDLE = 50
WEIGHTS_MEMO = "bias_weights"
WEIGHT_TABLES = table_names((BiasWeightRow,))

SOURCES: Mapping[DecisionBias, tuple[tuple[Facet, int], ...]] = {
    DecisionBias.OVERCONFIDENCE: ((Facet.VANITY, 1), (Facet.AMBITION, 1), (Facet.MODESTY, -1)),
    DecisionBias.SUNK_COST: ((Facet.PERSEVERANCE, 1), (Facet.ABSTRACTION, -1)),
    DecisionBias.LOSS_AVERSION: ((Facet.ANXIETY, 1), (Facet.CAUTION, 1), (Facet.EXCITEMENT_SEEKING, -1)),
    DecisionBias.CONFIRMATION: ((Facet.CURIOSITY, -1), (Facet.TOLERANCE_OF_DIFFERENCE, -1)),
    DecisionBias.RECENCY: ((Facet.ACTIVITY_LEVEL, 1), (Facet.DISCIPLINE, -1)),
    DecisionBias.GROUPTHINK: ((Facet.COOPERATION, 1), (Facet.POLITENESS, 1), (Facet.ASSERTIVENESS, -1)),
    DecisionBias.HOSTILE_ATTRIBUTION: ((Facet.ANGER, 1), (Facet.TRUST, -1)),
    DecisionBias.OPTIMISM: ((Facet.CHEERFULNESS, 1), (Facet.DEPRESSION, -1)),
    DecisionBias.STATUS_QUO: ((Facet.ORDERLINESS, 1), (Facet.IMAGINATION, -1)),
    DecisionBias.AVAILABILITY: ((Facet.VULNERABILITY, 1), (Facet.THOROUGHNESS, -1)),
    DecisionBias.ANCHORING: ((Facet.SELF_CONSCIOUSNESS, 1), (Facet.ABSTRACTION, -1)),
    DecisionBias.IN_GROUP_FAVOUR: ((Facet.GREGARIOUSNESS, 1), (Facet.TOLERANCE_OF_DIFFERENCE, -1), (Facet.ALTRUISM, -1)),
    DecisionBias.AUTHORITY_DEFERENCE: ((Facet.SENSE_OF_DUTY, 1), (Facet.ASSERTIVENESS, -1)),
    DecisionBias.SCARCITY_PANIC: ((Facet.GREED, 1), (Facet.ANXIETY, 1), (Facet.EMOTIONAL_STABILITY, -1)),
    DecisionBias.FATALISM: ((Facet.DEPRESSION, 1), (Facet.ACTIVITY_LEVEL, -1)),
    DecisionBias.RISK_SEEKING: ((Facet.EXCITEMENT_SEEKING, 1), (Facet.CAUTION, -1)),
    DecisionBias.PLANNING_FALLACY: ((Facet.IMAGINATION, 1), (Facet.THOROUGHNESS, -1)),
    DecisionBias.HALO: ((Facet.FRIENDLINESS, 1), (Facet.GRATITUDE, 1), (Facet.THOROUGHNESS, -1)),
    DecisionBias.PROJECTION: ((Facet.SELF_CONSCIOUSNESS, 1), (Facet.IMAGINATION, -1), (Facet.FRIENDLINESS, 1)),
    DecisionBias.LITERALISM: (),
    DecisionBias.COLONY_RISK_AVERSION: (),
}

PUSHES: Mapping[BiasedDecision, Mapping[DecisionBias, int]] = total(
    BiasedDecision,
    {
        BiasedDecision.RAID: {
            DecisionBias.OVERCONFIDENCE: 1,
            DecisionBias.RISK_SEEKING: 1,
            DecisionBias.LOSS_AVERSION: -1,
            DecisionBias.OPTIMISM: 1,
            DecisionBias.HOSTILE_ATTRIBUTION: 1,
            DecisionBias.COLONY_RISK_AVERSION: -1,
        },
        BiasedDecision.PEACE: {
            DecisionBias.SUNK_COST: -1,
            DecisionBias.OVERCONFIDENCE: -1,
            DecisionBias.LOSS_AVERSION: 1,
            DecisionBias.FATALISM: 1,
            DecisionBias.OPTIMISM: -1,
            DecisionBias.ANCHORING: -1,
            DecisionBias.GROUPTHINK: -1,
            DecisionBias.LITERALISM: -1,
            DecisionBias.COLONY_RISK_AVERSION: 1,
        },
        BiasedDecision.SURRENDER: {
            DecisionBias.SUNK_COST: -1,
            DecisionBias.FATALISM: 1,
            DecisionBias.SCARCITY_PANIC: 1,
            DecisionBias.PLANNING_FALLACY: -1,
            DecisionBias.AUTHORITY_DEFERENCE: -1,
            DecisionBias.LITERALISM: -1,
        },
        BiasedDecision.SCHEME: {
            DecisionBias.HOSTILE_ATTRIBUTION: 1,
            DecisionBias.RECENCY: 1,
            DecisionBias.PROJECTION: 1,
            DecisionBias.HALO: -1,
        },
        BiasedDecision.BELIEF: {
            DecisionBias.AVAILABILITY: 1,
            DecisionBias.AUTHORITY_DEFERENCE: 1,
            DecisionBias.GROUPTHINK: 1,
            DecisionBias.RECENCY: 1,
            DecisionBias.CONFIRMATION: -1,
        },
        BiasedDecision.CONVERSION: {
            DecisionBias.LITERALISM: -1,
            DecisionBias.STATUS_QUO: -1,
            DecisionBias.IN_GROUP_FAVOUR: -1,
            DecisionBias.CONFIRMATION: -1,
            DecisionBias.AUTHORITY_DEFERENCE: 1,
            DecisionBias.HALO: 1,
        },
        BiasedDecision.MIGRATION: {
            DecisionBias.COLONY_RISK_AVERSION: -1,
            DecisionBias.STATUS_QUO: -1,
            DecisionBias.LOSS_AVERSION: -1,
            DecisionBias.SCARCITY_PANIC: 1,
            DecisionBias.OPTIMISM: 1,
            DecisionBias.RISK_SEEKING: 1,
        },
        BiasedDecision.GOD_GOAL: {
            DecisionBias.OVERCONFIDENCE: 1,
            DecisionBias.PLANNING_FALLACY: 1,
            DecisionBias.SUNK_COST: 1,
            DecisionBias.ANCHORING: 1,
            DecisionBias.IN_GROUP_FAVOUR: 1,
        },
        BiasedDecision.WAR: {
            DecisionBias.OVERCONFIDENCE: 1,
            DecisionBias.HOSTILE_ATTRIBUTION: 1,
            DecisionBias.OPTIMISM: 1,
            DecisionBias.IN_GROUP_FAVOUR: 1,
            DecisionBias.GROUPTHINK: 1,
            DecisionBias.LOSS_AVERSION: -1,
            DecisionBias.STATUS_QUO: -1,
        },
        BiasedDecision.RETREAT: {
            DecisionBias.SUNK_COST: -1,
            DecisionBias.OVERCONFIDENCE: -1,
            DecisionBias.LOSS_AVERSION: 1,
            DecisionBias.SCARCITY_PANIC: 1,
            DecisionBias.FATALISM: 1,
            DecisionBias.RISK_SEEKING: -1,
        },
        BiasedDecision.TRADE: {
            DecisionBias.STATUS_QUO: -1,
            DecisionBias.IN_GROUP_FAVOUR: -1,
            DecisionBias.HOSTILE_ATTRIBUTION: -1,
            DecisionBias.OPTIMISM: 1,
            DecisionBias.ANCHORING: -1,
            DecisionBias.AVAILABILITY: 1,
        },
        BiasedDecision.ALLIANCE: {
            DecisionBias.HALO: 1,
            DecisionBias.PROJECTION: 1,
            DecisionBias.IN_GROUP_FAVOUR: -1,
            DecisionBias.HOSTILE_ATTRIBUTION: -1,
            DecisionBias.RECENCY: 1,
        },
        BiasedDecision.SUCCESSION: {
            DecisionBias.STATUS_QUO: 1,
            DecisionBias.AUTHORITY_DEFERENCE: 1,
            DecisionBias.HALO: 1,
            DecisionBias.IN_GROUP_FAVOUR: 1,
            DecisionBias.ANCHORING: 1,
        },
        BiasedDecision.LAW: {
            DecisionBias.STATUS_QUO: -1,
            DecisionBias.CONFIRMATION: 1,
            DecisionBias.GROUPTHINK: 1,
            DecisionBias.AUTHORITY_DEFERENCE: 1,
            DecisionBias.LITERALISM: -1,
        },
        BiasedDecision.RESEARCH: {
            DecisionBias.PLANNING_FALLACY: 1,
            DecisionBias.OPTIMISM: 1,
            DecisionBias.SUNK_COST: 1,
            DecisionBias.STATUS_QUO: -1,
            DecisionBias.AVAILABILITY: 1,
        },
    },
)

COUNTERS = (SkillKind.STRATEGY, SkillKind.TACTICS)
DECIDING = frozenset({BondKind.RULES, BondKind.COMMANDS})


@dataclass
class BiasTally:
    derived: int = 0


def derived_weight(facets: Mapping[Facet, int], bias: DecisionBias, stress: int, stress_pct: int) -> int:
    parts = SOURCES[bias]
    lean = sum(facets.get(facet, 0) * sign for facet, sign in parts) / len(parts) if parts else 0.0
    return clamp_int(round_half_up(MIDDLE + lean * MIDDLE / FACET_MAX + stress * stress_pct / PERCENT), 0, PERCENT)


async def weights_of(ctx: TickContext, node_id: int) -> dict[DecisionBias, BiasWeightRow]:
    memo = memo_of(ctx.session, WEIGHTS_MEMO, WEIGHT_TABLES, live=True)
    found: dict[DecisionBias, BiasWeightRow] | None = memo.get(node_id) if memo is not None else None
    if found is None:
        found = {row.bias: row for row in await ctx.session.scalars(select(BiasWeightRow).where(BiasWeightRow.holder_node_id == node_id))}
        if memo is not None:
            memo[node_id] = found
    return dict(found)


@memoized(SkillRow)
async def counter_level(session: AsyncSession, node_id: int) -> int:
    levels = await session.scalars(select(SkillRow.level).where(SkillRow.holder_node_id == node_id, SkillRow.skill.in_(COUNTERS)))
    return max(levels, default=0)


async def derive(ctx: TickContext, node_id: int, tally: BiasTally) -> dict[DecisionBias, BiasWeightRow]:
    table = ctx.rules.biases
    found = await weights_of(ctx, node_id)
    facets = await facets_of(ctx.session, node_id)
    if not facets:
        holder = await load_holder(ctx.session, node_id)
        facets = await culture_mean(ctx.session, ctx.rules, holder) if holder is not None and has_facets(holder) else {}
    if not facets:
        return found
    profile = await ctx.session.get(MortalProfileRow, node_id)
    stress = profile.stress if profile is not None else 0
    entity = await ctx.session.get(EntityRow, node_id)
    nature = await folk_biology(ctx.session, entity) if entity is not None else ORDINARY
    for bias in DecisionBias:
        weight = bias_target(nature, bias, derived_weight(facets, bias, stress, table.stress_pct), ctx.rules.biology_variants.bias_pct)
        row = found.get(bias)
        if row is None:
            row = BiasWeightRow(holder_node_id=node_id, bias=bias, weight=weight, last_shift=0, locked=[])
            ctx.session.add(row)
            found[bias] = row
            tally.derived += 1
        elif "weight" not in (row.locked or []):
            row.weight = clamp_int(round_half_up(row.weight + (weight - row.weight) * table.drift_pct / PERCENT), 0, PERCENT)
    return found


@memoized(NetworkNodeRow, SpyNetworkRow)
async def informed_node(session: AsyncSession, node_id: int) -> bool:
    linked = await session.scalar(select(NetworkNodeRow.id).where(NetworkNodeRow.member_node_id == node_id).limit(1))
    spies = await session.scalar(select(SpyNetworkRow.id).where(SpyNetworkRow.owner_entity_id == node_id).limit(1))
    return linked is not None or spies is not None


@memoized(RelationshipRow)
async def isolated_node(session: AsyncSession, node_id: int) -> bool:
    close = select(RelationshipRow.id).where(RelationshipRow.holder_node_id == node_id, RelationshipRow.friendship > 0).limit(1)
    return await session.scalar(close) is None


async def damping(ctx: TickContext, node_id: int) -> float:
    table = ctx.rules.biases
    learned = max(0, (await values_for(ctx.session, node_id)).get(ValueAxis.KNOWLEDGE, 0))
    damp = 1 - await counter_level(ctx.session, node_id) * table.skill_damp_pct / PERCENT - learned * table.knowledge_damp_pct / PERCENT / PERCENT
    if await informed_node(ctx.session, node_id):
        damp -= table.informed_damp_pct / PERCENT
    if await isolated_node(ctx.session, node_id):
        damp += table.isolation_pct / PERCENT
    return max(0.0, damp)


async def lean(ctx: TickContext, node_id: int | None, decision: BiasedDecision) -> float:
    if node_id is None:
        return 1.0
    rows = await weights_of(ctx, node_id)
    if not rows:
        return 1.0
    table = ctx.rules.biases
    damp = await damping(ctx, node_id)
    summed = 0.0
    strongest: tuple[float, BiasWeightRow] | None = None
    for bias, sign in PUSHES[decision].items():
        row = rows.get(bias)
        if row is None:
            continue
        push = (row.weight - MIDDLE) / MIDDLE * sign * table.push_pct * damp
        summed += push
        if strongest is None or abs(push) > abs(strongest[0]):
            strongest = (push, row)
    if strongest is not None and round_half_up(strongest[0]) != 0:
        row = strongest[1]
        row.last_decision, row.last_shift, row.last_epoch = decision, round_half_up(strongest[0]), ctx.epoch
    return max(0.0, 1 + summed / PERCENT)


@memoized(OfficeRow, PolityMemberRow)
async def council_members(session: AsyncSession, community_id: int, ruler_id: int) -> tuple[int, ...]:
    realm = community_id if await session.scalar(select(OfficeRow.id).where(OfficeRow.polity_entity_id == community_id).limit(1)) else None
    realm = realm or await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    if realm is None:
        return ()
    holders = await session.scalars(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm, OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id)
    )
    return tuple(sorted({int(holder) for holder in holders if holder is not None and holder != ruler_id}))


async def lean_community(ctx: TickContext, community_id: int, decision: BiasedDecision) -> float:
    rulers = await rulers_of(ctx.session, community_id)
    if not rulers:
        return 1.0
    first = await lean(ctx, rulers[0].id, decision)
    council = [await lean(ctx, member, decision) for member in await council_members(ctx.session, community_id, rulers[0].id)]
    if not council:
        return first
    share = ctx.rules.biases.council_pct / PERCENT
    combined = first * (1 - share) + sum(council) / len(council) * share
    return 1 + (combined - 1) * (1 - ctx.rules.biases.dissent_damp_pct / PERCENT)


async def deciders(ctx: TickContext) -> list[int]:
    found = set(await ctx.session.scalars(select(BondRow.source_node_id).where(BondRow.kind.in_(list(DECIDING)), BondRow.state == BondState.ACTIVE)))
    found |= set(await ctx.session.scalars(select(BiasWeightRow.holder_node_id)))
    mortals = select(EntityRow.id).where(EntityRow.id.in_(list(found)), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    living = set(await ctx.session.scalars(mortals)) | {god.id for god in await living_gods(ctx.session)}
    return sorted(node for node in living if not held(node))


async def keep_biases(ctx: TickContext, tally: BiasTally) -> None:
    for node_id in await deciders(ctx):
        await derive(ctx, node_id, tally)
    await ctx.session.flush()
