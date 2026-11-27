from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structures import KNOWLEDGE_KEEPERS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, ENDED_STATUSES, SOCIETY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarEnding
from aerona.engine.context import TickContext
from aerona.engine.endowments.trust import endowed
from aerona.engine.faith.zealotry import monastery_keeps
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.society_economy import society_of
from aerona.engine.phases.society_support.knowledge import KnowledgeHoldings, teach
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import at_cap, clamp_int
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

FORGOTTEN_REASON = "forgotten"


@dataclass(frozen=True)
class DarkAgeStatus:
    entity_id: int
    devastated: bool
    protected: bool
    forget_chance: int


@dataclass(frozen=True)
class EpochScars:
    violent_places: set[int]
    conquered: set[int]
    fallen_places: set[int]
    fallen_rulers: set[int]


async def load_scars(session: AsyncSession, rules: Rules, epoch: int) -> EpochScars:
    violent: set[int] = set()
    events = await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.birth_epoch == epoch))
    for event in events:
        if event.location_id is not None and stat_or(event, "severity", 0) >= rules.knowledge.dark_age_min_severity:
            violent.add(event.location_id)
    conquered = set(
        await session.scalars(
            select(WarRow.loser_entity_id).where(WarRow.ended_epoch == epoch, WarRow.ending == WarEnding.CONQUEST, WarRow.loser_entity_id.is_not(None))
        )
    )
    fallen = list(
        await session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status.in_(ENDED_STATUSES), EntityRow.end_epoch == epoch)
        )
    )
    places = {settlement.location_id for settlement in fallen if settlement.location_id is not None}
    rulers: set[int] = set()
    if fallen:
        statement = select(BondRow.source_node_id).where(BondRow.kind == BondKind.RULES, BondRow.target_node_id.in_([item.id for item in fallen]))
        rulers = set(await session.scalars(statement))
    return EpochScars(violent, {item for item in conquered if item is not None}, places, rulers)


def is_devastated(rules: Rules, community: EntityRow, scars: EpochScars) -> bool:
    if stat_or(community, "prosperity", rules.society.default_stat) < rules.knowledge.dark_age_prosperity:
        return True
    places = {community.id, community.location_id}
    if places & scars.violent_places or community.id in scars.conquered or community.id in scars.fallen_rulers:
        return True
    return community.location_id is not None and community.location_id in scars.fallen_places


async def keepers_by_place(session: AsyncSession, rules: Rules) -> set[int]:
    keeping = select(StructureProfileRow.structure_entity_id).where(
        StructureProfileRow.kind.in_(list(KNOWLEDGE_KEEPERS)), StructureProfileRow.effect_pct >= rules.structure_functions.archive_preserve_pct
    )
    statement = select(EntityRow.location_id).where(
        EntityRow.status == EntityStatus.CANON,
        EntityRow.location_id.is_not(None),
        EntityRow.id.in_(keeping) | (EntityRow.entity_type == EntityType.ARTWORK),
    )
    return {place for place in await session.scalars(statement) if place is not None}


async def is_protected(session: AsyncSession, rules: Rules, community: EntityRow, keepers: set[int]) -> bool:
    society = await society_of(session, rules, community.id)
    if society.shares[SocialClass.SCRIBE] >= rules.knowledge.dark_age_scribe_pct:
        return True
    return community.id in keepers or (community.location_id is not None and community.location_id in keepers)


async def forget_knowledge(ctx: TickContext, community: EntityRow, knowledge: EntityRow, holdings: KnowledgeHoldings) -> None:
    bonds = BondRepository(ctx.session)
    for bond in await bonds.outgoing(community.id, BondKind.KNOWS):
        if bond.target_node_id == knowledge.id:
            await bonds.deactivate(bond, ctx.epoch, FORGOTTEN_REASON)
    holdings.forget(community.id, knowledge.id)
    await record(
        ctx,
        "dark_ages.forgotten",
        roles={IncidentRole.ACTOR: community.id, IncidentRole.SUBJECT: knowledge.id},
        facts={"scribes": (await society_of(ctx.session, ctx.rules, community.id)).shares[SocialClass.SCRIBE]},
        steps=(StepDraft(StepAction.LOSE, actor=community.id, target=knowledge.id, outcome=StepOutcome.FAILURE),),
    )


async def _forgetting(ctx: TickContext, holdings: KnowledgeHoldings) -> int:
    settings = ctx.rules.knowledge
    scars = await load_scars(ctx.session, ctx.rules, ctx.epoch)
    keepers = await keepers_by_place(ctx.session, ctx.rules)
    rng = ctx.rng("forgetting")
    forgotten = 0
    for community in ctx.rng("forgetting.order").shuffled(unheld(await canon(ctx.session, COMMUNITY_TYPES))):
        if at_cap(forgotten, settings.dark_age_forget_cap):
            break
        known = holdings.known_by(community.id)
        if not known or not is_devastated(ctx.rules, community, scars):
            continue
        protected = await is_protected(ctx.session, ctx.rules, community, keepers)
        kept = 1 - ctx.rules.doctrine.monastic_protection_pct / PERCENT if await monastery_keeps(ctx, community.id) else 1.0
        kept *= 1 - ctx.rules.endowments.dark_age_keep_pct / PERCENT if await endowed(ctx.session, community.id) else 1.0
        if not rng.chance((settings.dark_age_forget_protected_chance if protected else settings.dark_age_forget_chance) * kept):
            continue
        await forget_knowledge(ctx, community, rng.pick(known), holdings)
        forgotten += 1
    return forgotten


async def _lost_marking(ctx: TickContext, holdings: KnowledgeHoldings, lost: set[int]) -> int:
    statement = select(BondRow.target_node_id).where(BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.PAST)
    remembered = set(await ctx.session.scalars(statement))
    repository = EntityRepository(ctx.session)
    marked = 0
    for knowledge in holdings.knowledge.values():
        if knowledge.id in lost or holdings.knowers(knowledge.id) or knowledge.id not in remembered:
            continue
        await repository.add_flag(knowledge.id, EntityFlag.LOST, ctx.epoch)
        lost.add(knowledge.id)
        marked += 1
        await record(ctx, "dark_ages.lost", roles={IncidentRole.SUBJECT: knowledge.id})
    return marked


def spread_target(rules: Rules, knowers: int, lost: bool) -> int:
    settings = rules.knowledge
    return 0 if lost else min(PERCENT, settings.spread_base + knowers * settings.spread_per_knower)


def drift_spread(rules: Rules, knowledge: EntityRow, knowers: int, lost: bool) -> int:
    settings = rules.knowledge
    current = stat(knowledge, "spread")
    start = settings.spread_default if current is None else current
    target = spread_target(rules, knowers, lost)
    step = max(-settings.spread_step, min(settings.spread_step, target - start))
    updated = clamp_int(start + step, 0, PERCENT)
    set_stats(knowledge, spread=updated)
    return updated


async def _canon_knowers(ctx: TickContext, holdings: KnowledgeHoldings) -> Mapping[int, int]:
    living = set(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)))
    return {knowledge_id: len(holdings.knowers(knowledge_id) & living) for knowledge_id in holdings.knowledge}


def ruin_near(community: EntityRow, ruins: Sequence[EntityRow], atlas: RegionAtlas) -> EntityRow | None:
    places = {place for place in (community.location_id, atlas.top_region(community.id)) if place is not None}
    return next((ruin for ruin in ruins if ruin.location_id is not None and ruin.location_id in places), None)


async def _rediscovery(ctx: TickContext, holdings: KnowledgeHoldings, lost: set[int]) -> int:
    settings = ctx.rules.knowledge
    lost_items = [holdings.knowledge[item] for item in sorted(lost) if item in holdings.knowledge]
    if not lost_items:
        return 0
    ruin_ids = await flags_by_entity(ctx.session, EntityFlag.RUIN)
    ruins = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(list(ruin_ids))).order_by(EntityRow.id)))
    atlas = await RegionAtlas.load(ctx.session)
    rng = ctx.rng("rediscovery")
    found = 0
    for community in ctx.rng("rediscovery.order").shuffled(await canon(ctx.session, SOCIETY_TYPES)):
        if at_cap(found, settings.relic_rediscovery_cap):
            break
        society = await society_of(ctx.session, ctx.rules, community.id)
        if society.shares[SocialClass.SCRIBE] < settings.relic_min_scribe_pct:
            continue
        ruin = ruin_near(community, ruins, atlas)
        candidates = [item for item in lost_items if item.world_id == community.world_id and item.id in lost and not held(item.id)]
        if ruin is None or held(community.id) or not candidates or not rng.chance(settings.relic_decipher_chance):
            continue
        knowledge = rng.pick(candidates)
        await teach(ctx, community.id, knowledge, "rediscovered from the ruins", holdings)
        await EntityRepository(ctx.session).remove_flag(knowledge.id, EntityFlag.LOST)
        lost.discard(knowledge.id)
        found += 1
        await record(
            ctx,
            "dark_ages.rediscovered",
            roles={IncidentRole.ACTOR: community.id, IncidentRole.SUBJECT: knowledge.id, IncidentRole.PLACE: ruin.id},
            facts={"scribes": society.shares[SocialClass.SCRIBE], "chance": settings.relic_decipher_chance},
            place=ruin.id,
        )
    return found


@reads(
    "event.severity",
    "knowledge.spread",
    "people.prosperity",
    "settlement.prosperity",
    "table.bonds",
    "table.community_societies",
    "table.creator",
    "table.cult_holdings",
    "table.deep_passages",
    "table.dimensions",
    "table.endowments",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.sons",
    "table.stars",
    "table.wars",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "knowledge.spread",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.node_births",
)
async def dark_ages(ctx: TickContext) -> None:
    holdings = await KnowledgeHoldings.load(ctx.session)
    ctx.count("forgotten", await _forgetting(ctx, holdings))
    lost = await flags_by_entity(ctx.session, EntityFlag.LOST)
    ctx.count("lost", await _lost_marking(ctx, holdings, lost))
    knowers = await _canon_knowers(ctx, holdings)
    for knowledge in holdings.knowledge.values():
        drift_spread(ctx.rules, knowledge, knowers.get(knowledge.id, 0), knowledge.id in lost)
    ctx.count("rediscovered", await _rediscovery(ctx, holdings, lost))


async def dark_age_status(session: AsyncSession, rules: Rules, epoch: int, community_id: int) -> DarkAgeStatus:
    community = await session.get(EntityRow, community_id)
    if community is None or community.entity_type not in COMMUNITY_TYPES:
        raise NotFoundError("No such community.")
    devastated = is_devastated(rules, community, await load_scars(session, rules, epoch))
    protected = await is_protected(session, rules, community, await keepers_by_place(session, rules))
    chance = rules.knowledge.dark_age_forget_protected_chance if protected else rules.knowledge.dark_age_forget_chance
    return DarkAgeStatus(community.id, devastated, protected, chance if devastated else 0)


PHASES = (Phase("dark_ages", dark_ages),)
