from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.knowledge import ENGINE_UNDISCOVERABLE_BRANCHES, KNOWLEDGE_BRANCHES, branch_label
from aerona.catalog.techniques import BRANCH_GRAPH, Gate
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held as frozen
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.models.entity_stats import KnowledgeStats
from aerona.engine.context import TickContext
from aerona.engine.disease.load import DiseaseLoads, endemic_regions
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.research import gate_open, holder_levels, raise_holder, research_factor
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat, stat_or
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

SCRIBED_SOCIETIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
ORDERS = frozenset({EntityType.CULT, EntityType.FACTION})
PROSPERITY_KEY = "prosperity"
ORDINARY_WEIGHT = PERCENT


class DevelopmentKind(StrEnum):
    DEEPEN = "deepen"
    LEARN = "learn"
    NEW = "new"


@dataclass(frozen=True)
class Development:
    kind: DevelopmentKind
    knowledge: EntityRow | None = None


@dataclass(frozen=True)
class LevelChange:
    knowledge: EntityRow
    level: int
    step: int


def shift_level(rules: Rules, knowledge: EntityRow, step: int) -> int | None:
    before = knowledge_level(rules, knowledge)
    after = max(1, min(rules.knowledge.level_cap, before + step))
    if after == before:
        return None
    spread = stat_or(knowledge, "spread", 0)
    if step > 0:
        spread = clamp_int(spread + rules.knowledge.level_up_spread, 0, PERCENT)
    knowledge.stats = KnowledgeStats(level=after, spread=spread)
    return after


async def world_knowledge(session: AsyncSession, world_id: int) -> list[EntityRow]:
    return await canon(session, [EntityType.KNOWLEDGE], world_id)


async def same_branch(session: AsyncSession, rules: Rules, world_id: int, branch: KnowledgeBranch) -> list[EntityRow]:
    found = [item for item in await world_knowledge(session, world_id) if item.knowledge_branch is branch]
    return sorted(found, key=lambda item: (-knowledge_level(rules, item), item.id))


async def empty_branches(session: AsyncSession, world_id: int) -> list[KnowledgeBranch]:
    present = {item.knowledge_branch for item in await world_knowledge(session, world_id)}
    return [branch for branch in KnowledgeBranch if branch not in present]


async def known_records(session: AsyncSession, holder_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id == holder_id,
            BondRow.kind == BondKind.KNOWS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.KNOWLEDGE,
            EntityRow.status == EntityStatus.CANON,
        )
        .order_by(EntityRow.id)
    )
    return list((await session.scalars(statement)).unique())


async def development_for(session: AsyncSession, rules: Rules, holder: EntityRow, branch: KnowledgeBranch) -> Development:
    held = sorted((item for item in await known_records(session, holder.id) if item.knowledge_branch is branch), key=lambda item: -knowledge_level(rules, item))
    if held:
        return Development(DevelopmentKind.DEEPEN, held[0])
    present = await same_branch(session, rules, holder.world_id, branch)
    if len(present) >= rules.knowledge.branch_record_cap:
        return Development(DevelopmentKind.LEARN, present[0])
    return Development(DevelopmentKind.NEW)


def empty_branch_hint(rules: Rules, branches: list[KnowledgeBranch]) -> str:
    return ", ".join(branch_label(branch) for branch in branches[: rules.knowledge.hint_empty_branches])


async def scribe_share(session: AsyncSession, rules: Rules, community: EntityRow) -> float:
    if community.entity_type in SCRIBED_SOCIETIES:
        return (await class_shares(session, rules, community.id))[SocialClass.SCRIBE]
    if community.entity_type in ORDERS:
        return float(rules.knowledge.discovery_min_scribe_pct)
    return 0.0


@dataclass
class KnowledgeScene:
    communities: list[EntityRow]
    knowledge: dict[int, EntityRow]
    holders: dict[int, list[int]]
    held: dict[int, list[int]]
    lost: set[int]

    @classmethod
    async def load(cls, ctx: TickContext) -> "KnowledgeScene":
        communities = await canon(ctx.session, COMMUNITY_TYPES)
        knowledge = {item.id: item for item in await canon(ctx.session, [EntityType.KNOWLEDGE])}
        living = {item.id for item in await canon(ctx.session)}
        holders: dict[int, list[int]] = defaultdict(list)
        held: dict[int, list[int]] = defaultdict(list)
        statement = select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(list(knowledge))
        )
        for source, target in await ctx.session.execute(statement.order_by(BondRow.id)):
            if source in living:
                holders[target].append(source)
                held[source].append(target)
        return cls(communities, knowledge, holders, held, await flags_by_entity(ctx.session, EntityFlag.LOST))


async def progressed(ctx: TickContext, holder_id: int, branch: KnowledgeBranch, pressure: float, levels: dict[int, dict[KnowledgeBranch, int]]) -> bool:
    row = await ctx.session.get(HolderLevelRow, (holder_id, branch))
    if row is None or "progress" in row.locked:
        return False
    if "progress" not in row.locked:
        row.progress = clamp_int(row.progress + round_half_up(pressure * ctx.rules.research.progress_pct / PERCENT), 0, PERCENT)
    if row.progress < PERCENT or not gate_open(BRANCH_GRAPH.get(branch, Gate()), levels.get(holder_id, {})):
        return False
    row.progress = 0
    return True


async def deepen_round(ctx: TickContext, scene: KnowledgeScene) -> int:
    table = ctx.rules.knowledge
    deepened = 0
    loads = await DiseaseLoads.load(ctx.session)
    sick = await endemic_regions(ctx.session)
    levels = await holder_levels(ctx.session)
    for community in unheld(scene.communities):
        if deepened >= table.deepen_cap:
            break
        options = [
            scene.knowledge[item]
            for item in scene.held.get(community.id, [])
            if item not in scene.lost and not frozen(item) and knowledge_level(ctx.rules, scene.knowledge[item]) < table.level_cap
        ]
        if not options or stat_or(community, PROSPERITY_KEY, table.deepen_min_prosperity) < table.deepen_min_prosperity:
            continue
        rng = ctx.rng(f"deepen.{community.id}")
        chance = table.deepen_chance + await scribe_share(ctx.session, ctx.rules, community) / table.deepen_scribe_divisor
        healing = [item for item in options if item.knowledge_branch is KnowledgeBranch.MEDICINE]
        if healing and loads.atlas.top_region(community.id) in sick:
            chance *= ctx.rules.epidemiology.medicine_pressure_pct / PERCENT
            options = healing
        chosen = rng.pick(options)
        branch = chosen.knowledge_branch
        known = levels.get(community.id, {}).get(branch, knowledge_level(ctx.rules, chosen)) if branch is not None else 0
        if branch is not None:
            chance *= await research_factor(ctx, community, branch, known, levels)
        if branch is None or not await progressed(ctx, community.id, branch, chance, levels):
            continue
        reached = await raise_holder(ctx, community.id, branch, table.level_cap)
        level = shift_level(ctx.rules, chosen, 1) if reached is None or reached > knowledge_level(ctx.rules, chosen) else None
        if reached is None and level is None:
            continue
        deepened += 1
        shown = level if level is not None else reached
        frontier = " and pushed the frontier" if level is not None else ""
        await note(
            ctx,
            f"The masters of {community.name} deepened their knowledge of {chosen.name}{frontier}; they now stand at level {shown}.",
            key="knowledge.deepened",
            ids=[community.id, chosen.id],
            kind=ChronicleKind.KNOWLEDGE,
        )
    return deepened


@dataclass(frozen=True)
class BranchOption:
    branch: KnowledgeBranch
    base: EntityRow | None
    weight: float


def branch_options(ctx: TickContext, scene: KnowledgeScene, discoverer: EntityRow, empty: list[KnowledgeBranch]) -> list[BranchOption]:
    known = {scene.knowledge[item].knowledge_branch: scene.knowledge[item] for item in scene.held.get(discoverer.id, [])}
    levels = {branch: knowledge_level(ctx.rules, record) for branch, record in known.items() if branch is not None}
    options: list[BranchOption] = []
    for branch in empty:
        gate = BRANCH_GRAPH.get(branch, Gate())
        needed = [item for item, _ in (*gate.all_of, *gate.any_of)]
        if not gate_open(gate, levels):
            continue
        base = next((known[item] for item in needed if item in known), None)
        weight = ctx.rules.knowledge.rare_branch_weight_pct if needed else ORDINARY_WEIGHT
        options.append(BranchOption(branch, base, weight))
    return options


async def discover_branch(ctx: TickContext, discoverer: EntityRow, option: BranchOption) -> EntityRow:
    table = ctx.rules.knowledge
    label = branch_label(option.branch)
    name = await Namer(ctx.session, ctx.rules).from_speaker(
        discoverer.id, seed_of("knowledge", option.branch.value, ctx.epoch, discoverer.id), NameKind.GENERAL
    )
    how = f"building on {option.base.name}" if option.base is not None else "unaided"
    knowledge = await create_record(
        ctx,
        RecordSpec(
            name=name or f"{discoverer.name} {label}",
            entity_type=EntityType.KNOWLEDGE,
            body=f"The scribes of {discoverer.name} reached, {how}, a branch nobody in their world had known. {KNOWLEDGE_BRANCHES[option.branch].effect}",
            stats=KnowledgeStats(level=1, spread=table.discovery_spread),
            power=table.discovery_power,
            world_id=discoverer.world_id,
            subtype=label.lower(),
            knowledge_branch=option.branch,
        ),
    )
    await teach(ctx, discoverer.id, knowledge, "discovered")
    if option.base is not None:
        await BondRepository(ctx.session).connect(BondDraft(knowledge.id, option.base.id, BondKind.DESCENDS_FROM, ctx.epoch, "built upon"))
    return knowledge


async def discovery_round(ctx: TickContext, scene: KnowledgeScene) -> int:
    table = ctx.rules.knowledge
    found = 0
    for world in await WorldRepository(ctx.session).reachable_worlds():
        if found >= table.discovery_cap:
            break
        rng = ctx.rng(f"discovery.{world.id}")
        if not rng.chance(table.discovery_chance):
            continue
        empty = [branch for branch in await empty_branches(ctx.session, world.id) if branch not in ENGINE_UNDISCOVERABLE_BRANCHES]
        if not empty:
            continue
        shares = {community.id: await scribe_share(ctx.session, ctx.rules, community) for community in scene.communities if community.world_id == world.id}
        able = sorted(
            (item for item in scene.communities if shares.get(item.id, 0.0) >= table.discovery_min_scribe_pct), key=lambda item: (-shares[item.id], item.id)
        )
        candidates = [item for item in able if not frozen(item.id)][: table.discovery_candidates]
        if not candidates:
            continue
        discoverer = rng.pick(candidates)
        options = branch_options(ctx, scene, discoverer, empty)
        if not options:
            continue
        option = rng.weighted_by(options, lambda item: item.weight)
        knowledge = await discover_branch(ctx, discoverer, option)
        scene.knowledge[knowledge.id] = knowledge
        scene.held[discoverer.id].append(knowledge.id)
        found += 1
        ids = [discoverer.id, knowledge.id, *([option.base.id] if option.base is not None else [])]
        await note(
            ctx,
            f"{discoverer.name} reached a knowledge never known in its world: {branch_label(option.branch)} ({knowledge.name}).",
            key="knowledge.discovered",
            ids=ids,
            kind=ChronicleKind.KNOWLEDGE,
        )
    return found


async def decline_round(ctx: TickContext, scene: KnowledgeScene) -> int:
    table = ctx.rules.knowledge
    entities = {item.id: item for item in scene.communities}
    declined = 0
    for knowledge_id, holder_ids in sorted(scene.holders.items()):
        if declined >= table.decline_cap:
            break
        knowledge = scene.knowledge.get(knowledge_id)
        if knowledge is None or frozen(knowledge.id) or knowledge_level(ctx.rules, knowledge) <= 1:
            continue
        holders = [entities[item] for item in holder_ids if item in entities and stat(entities[item], PROSPERITY_KEY) is not None]
        if not holders or any(stat_or(item, PROSPERITY_KEY, 0) >= table.decline_prosperity for item in holders):
            continue
        if not ctx.rng(f"decline.{knowledge_id}").chance(table.decline_chance):
            continue
        level = shift_level(ctx.rules, knowledge, -1)
        if level is None:
            continue
        declined += 1
        await note(
            ctx,
            f"Ruin and famine scattered the masters of {knowledge.name}; its finer arts were forgotten and it fell to level {level}.",
            key="knowledge.declined",
            ids=[knowledge.id, *(item.id for item in holders)],
            kind=ChronicleKind.KNOWLEDGE,
        )
    return declined


@reads(
    "knowledge.spread",
    "people.prosperity",
    "settlement.prosperity",
    "table.bodies",
    "table.bonds",
    "table.community_societies",
    "table.endemic_diseases",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.holder_techniques",
    "table.institutions",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.offices",
    "table.outbreaks",
    "table.people_culture",
    "table.polity_eras",
    "table.polity_members",
    "table.region_environment",
    "table.skills",
    "table.war_sides",
    "table.world_maps",
)
@writes(
    "knowledge.spread",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
)
async def knowledge_levels(ctx: TickContext) -> None:
    scene = await KnowledgeScene.load(ctx)
    ctx.count("deepened", await deepen_round(ctx, scene))
    ctx.count("discovered", await discovery_round(ctx, scene))
    ctx.count("declined", await decline_round(ctx, scene))


async def set_knowledge_level(session: AsyncSession, rules: Rules, knowledge_id: int, step: int) -> LevelChange:
    knowledge = await session.get(EntityRow, knowledge_id)
    if knowledge is None or knowledge.entity_type is not EntityType.KNOWLEDGE or knowledge.status is not EntityStatus.CANON:
        raise ValidationFailedError("Choose a living knowledge.")
    direction = 1 if step >= 0 else -1
    level = shift_level(rules, knowledge, direction)
    if level is None:
        bound = f"already at its highest level ({rules.knowledge.level_cap})" if direction > 0 else "already at its most basic level"
        raise ValidationFailedError(f"{knowledge.name} is {bound}.")
    ctx = await manual_context(session, "knowledge_level", rules, key=str(knowledge_id))
    verb = "deepened" if direction > 0 else "blunted"
    await note(
        ctx,
        f"The Creator {verb} the knowledge of {knowledge.name}; it now stands at level {level}.",
        key=f"knowledge.creator_{verb}",
        ids=[knowledge.id],
        kind=ChronicleKind.CREATOR_HAND,
    )
    await session.flush()
    return LevelChange(knowledge, level, direction)


async def run_knowledge_levels(session: AsyncSession, rules: Rules) -> None:
    await knowledge_levels(await manual_context(session, "knowledge_levels", rules))


PHASES = (Phase("knowledge_levels", knowledge_levels),)
