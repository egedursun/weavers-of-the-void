import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import delete, select, update

from aerona.agents.chronicle import ChroniclePhase, write_line
from aerona.agents.context.mortal import mortal_context
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.speech import tics
from aerona.agents.context.tired_images import tired_images
from aerona.agents.metrics import metrics_turn
from aerona.agents.roles import AgentRole, turn_label
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import extract_word
from aerona.agents.turns.ports import SpeechOnlyToolkit, ToolCatalogue, TurnToolkit
from aerona.agents.turns.session import TurnOutcome, TurnPlan, run_turn
from aerona.agents.turns.state import begin_turn, finish_turn, long_job_notes, turn_row
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.agents import CHOSEN_TAG, MORTAL_WORD_CHRONICLE_CHARS
from aerona.constants.llm import HAIKU_MODEL_ID
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow, EntityTagRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.mind import NeedRow, PressureRow, TraitRow
from aerona.domain.enums.agent import AgentKind, MessageIntent
from aerona.domain.enums.body import Consciousness
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import TraitEffect, TraitKind
from aerona.domain.enums.node import ActorKind
from aerona.engine.body.book import bedridden
from aerona.engine.gods.mortal_opportunities import mortal_opportunities
from aerona.engine.mind.book import scaled_by, trait_effect
from aerona.engine.phases.civilization import late_debts
from aerona.engine.primitives.manual import manual_context
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.mortal import MortalTurnSystemContext, MortalTurnUserContext
from aerona.prompts.contexts.opportunities import MortalOpportunitiesContext
from aerona.prompts.contexts.son_turn import DoneAction, TurnContinuationContext, TurnInterruption
from aerona.rules.registry import Rules

AGENT_TYPES = (EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.BEAST)
SELECTION_STREAM = "agents.mortal_selection"
CREATURES = frozenset({EntityType.BEAST})
CROWD_FLOOR = 10


@dataclass(frozen=True)
class Candidate:
    entity: EntityRow
    forced: bool
    chosen: bool
    dreaming: bool
    pressure: int = 0
    temperament: int = 0


@dataclass(frozen=True)
class MortalTurnResult:
    entity_id: int
    name: str
    word: str
    creations: list[int] = field(default_factory=list)
    status: str = ""


def intelligence(entity: EntityRow) -> int:
    return int(getattr(entity.stats, "intelligence", 0) or 0)


def crowd(entity: EntityRow, rules: Rules) -> int:
    stats = entity.stats
    return int(getattr(stats, "population", None) or getattr(stats, "followers", None) or rules.mortal_tools.agent_default_crowd)


async def candidates(session_scope: Scope) -> list[Candidate]:
    rules = session_scope.rules
    epoch = session_scope.epoch
    rows = await session_scope.session.scalars(
        select(EntityRow)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.last_acted_epoch < epoch, EntityRow.entity_type.in_(AGENT_TYPES))
        .order_by(EntityRow.id)
    )
    listed = list(rows)
    minds = {
        beast_id: value
        for beast_id, value in await session_scope.session.execute(
            select(BeastProfileRow.beast_entity_id, BeastProfileRow.intelligence).where(BeastProfileRow.beast_entity_id.in_([row.id for row in listed]))
        )
    }
    senseless = set(
        await session_scope.session.scalars(
            select(BodyRow.node_id).where(BodyRow.node_id.in_([row.id for row in listed]), BodyRow.consciousness == Consciousness.UNCONSCIOUS)
        )
    )
    eligible = [
        row
        for row in listed
        if (row.entity_type not in CREATURES or minds.get(row.id, intelligence(row)) >= rules.mortal_agents.creature_min_intelligence)
        and not bedridden(rules, row)
        and row.id not in senseless
    ]
    ids = [row.id for row in eligible]
    tags: dict[int, set[str]] = defaultdict(set)
    for entity_id, tag in await session_scope.session.execute(select(EntityTagRow.entity_id, EntityTagRow.tag).where(EntityTagRow.entity_id.in_(ids))):
        tags[entity_id].add(tag)
    forced = set(
        await session_scope.session.scalars(
            select(EntityFlagRow.entity_id).where(EntityFlagRow.entity_id.in_(ids), EntityFlagRow.flag == EntityFlag.AGENT_SELECTED)
        )
    )
    dreamers = set(
        await session_scope.session.scalars(
            select(MessageRow.recipient_node_id).where(
                MessageRow.recipient_node_id.in_(ids), MessageRow.intent == MessageIntent.DREAM, MessageRow.is_read.is_(False)
            )
        )
    )
    pressure: dict[int, int] = defaultdict(int)
    for entity_id, value in await session_scope.session.execute(select(PressureRow.entity_id, PressureRow.value).where(PressureRow.entity_id.in_(ids))):
        pressure[entity_id] = max(pressure[entity_id], value)
    for node_id, value in await session_scope.session.execute(select(NeedRow.node_id, NeedRow.value).where(NeedRow.node_id.in_(ids))):
        pressure[node_id] = max(pressure[node_id], PERCENT - value)
    held: dict[int, list[TraitKind]] = defaultdict(list)
    for node_id, trait in await session_scope.session.execute(select(TraitRow.node_id, TraitRow.trait).where(TraitRow.node_id.in_(ids))):
        held[node_id].append(trait)
    return [
        Candidate(
            row,
            row.id in forced,
            CHOSEN_TAG in tags[row.id],
            row.id in dreamers,
            pressure[row.id],
            trait_effect(held[row.id], TraitEffect.AGENT_WEIGHT, rules.traits.effect_scale_pct),
        )
        for row in eligible
    ]


def score(rules: Rules, candidate: Candidate, epoch: int, rng: SeededRandom) -> float:
    tools = rules.mortal_tools
    entity = candidate.entity
    value: float = entity.power_level * tools.agent_power_weight
    value += math.log10(max(CROWD_FLOOR, crowd(entity, rules))) * tools.agent_population_weight
    value += tools.agent_chosen_bonus if candidate.chosen else 0
    value += min(tools.agent_wait_cap, (epoch - entity.last_acted_epoch) * tools.agent_wait_weight)
    value += rng.die(tools.agent_random_die)
    value += tools.agent_dream_bonus if candidate.dreaming else 0
    value += candidate.pressure * rules.needs.agent_pressure_weight / PERCENT
    return value * scaled_by(candidate.temperament)


def pick(rules: Rules, group: Sequence[Candidate], count: int, epoch: int, rng: SeededRandom) -> list[Candidate]:
    if count <= 0:
        return [candidate for candidate in group if candidate.forced]
    forced = [candidate for candidate in group if candidate.forced]
    scored = sorted((candidate for candidate in group if not candidate.forced), key=lambda candidate: -score(rules, candidate, epoch, rng))
    ordered = forced + scored
    cap = max(1, math.ceil(count / max(1, rules.mortal_tools.agent_type_share_divisor)))
    chosen: list[Candidate] = []
    per_type: Counter[EntityType] = Counter()
    for candidate in ordered:
        if len(chosen) >= count:
            break
        if per_type[candidate.entity.entity_type] < cap or candidate.forced:
            chosen.append(candidate)
            per_type[candidate.entity.entity_type] += 1
    for candidate in ordered:
        if len(chosen) >= count:
            break
        if candidate not in chosen:
            chosen.append(candidate)
    return chosen


def world_shares(groups: dict[int, int], manual: dict[int, int | None], total: int, exponent_pct: int = PERCENT) -> dict[int, int]:
    shares = {world_id: min(manual[world_id] or 0, size) for world_id, size in groups.items() if manual.get(world_id) is not None}
    automatic = [world_id for world_id, size in groups.items() if manual.get(world_id) is None and size > 0]
    if not automatic or total <= 0:
        return shares
    weights = {world_id: groups[world_id] ** (exponent_pct / PERCENT) for world_id in automatic}
    weight_sum = sum(weights.values())
    exact = {world_id: total * weights[world_id] / weight_sum for world_id in automatic}
    floor = 1 if total >= len(automatic) else 0
    for world_id in automatic:
        shares[world_id] = min(groups[world_id], max(floor, math.floor(exact[world_id])))
    remaining = total - sum(shares[world_id] for world_id in automatic)
    for world_id in sorted(automatic, key=lambda item: -(exact[item] - math.floor(exact[item]))):
        if remaining <= 0:
            break
        if shares[world_id] < groups[world_id]:
            shares[world_id] += 1
            remaining -= 1
    return shares


async def choose_mortal_agents(scope: Scope, count: int) -> list[EntityRow]:
    rules = scope.rules
    rng = SeededRandom.for_epoch(scope.cosmos.rng_seed, scope.epoch, SELECTION_STREAM)
    pool = await candidates(scope)
    worlds = scope.living_worlds
    if len(worlds) < 2:
        return [candidate.entity for candidate in pick(rules, pool, count, scope.epoch, rng)]
    first = worlds[0].id
    known = {world.id for world in worlds}
    grouped: dict[int, list[Candidate]] = defaultdict(list)
    for candidate in pool:
        grouped[candidate.entity.world_id if candidate.entity.world_id in known else first].append(candidate)
    shares = world_shares(
        {world.id: len(grouped[world.id]) for world in worlds},
        {world.id: world.mortal_agents for world in worlds},
        count,
        rules.world_balance.agent_share_exponent_pct,
    )
    chosen = [candidate for world in worlds for candidate in pick(rules, grouped[world.id], shares.get(world.id, 0), scope.epoch, rng)]
    chosen.extend(candidate for candidate in pool if candidate.forced and candidate not in chosen)
    return [candidate.entity for candidate in chosen]


@dataclass(frozen=True)
class StartedMortalTurn:
    entity_id: int
    name: str
    epoch: int
    resumed: bool
    action_points: int
    messages: list[int]


async def start_mortal_turn(runtime: AgentRuntime, entity_id: int) -> StartedMortalTurn:
    async with runtime.database.write() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        if entity.status is not EntityStatus.CANON or entity.last_acted_epoch >= scope.epoch:
            raise ValidationFailedError(f"{entity.name} cannot act this epoch.")
        ctx = await manual_context(session, "late_debts", rules)
        await late_debts(ctx)
        start = await begin_turn(session, entity.id, AgentKind.MORTAL, scope.epoch, rules.mortal_agents.action_points)
        messages = list(
            await session.scalars(
                select(MessageRow.id).where(MessageRow.recipient_node_id == entity.id, MessageRow.intent == MessageIntent.DREAM, MessageRow.is_read.is_(False))
            )
        )
        return StartedMortalTurn(entity.id, entity.name, scope.epoch, start.resumed, start.action_points, messages)


async def captor_name(scope: Scope, entity: EntityRow) -> str | None:
    holders = await BondRepository(scope.session).incoming(entity.id, BondKind.HOLDS_CAPTIVE)
    captor = await scope.session.get(EntityRow, holders[0].source_node_id) if holders else None
    return captor.name if captor is not None else None


async def mortal_prompts(runtime: AgentRuntime, started: StartedMortalTurn, catalogue: ToolCatalogue, continuation: str = "") -> tuple[str, str]:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        entity = await session.get(EntityRow, started.entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        row = await turn_row(session, entity.id)
        points = row.action_points_left if row is not None and row.action_points_left is not None else started.action_points
        sanity = entity.sanity
        system = MortalTurnSystemContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            name=entity.name,
            world_name=scope.world_name(entity.world_id) or scope.cosmos.name,
            type_label=ENTITY_TYPES[entity.entity_type].label.lower(),
            subtype=entity.subtype,
            action_points=points,
            sanity=sanity,
            clouded=sanity is not None and sanity < rules.cosmic_horror.clouding_threshold,
            paid_tools=catalogue.paid,
            free_tools=catalogue.free,
            captor=await captor_name(scope, entity),
            tics=await tics(session, rules, None),
            tired_images=await tired_images(scope, entity.world_id),
        )
        seen = await EntityRepository(session).has_flag(entity.id, EntityFlag.SAW_THE_CREATOR)
        texts = list(await session.scalars(select(MessageRow.text).where(MessageRow.id.in_(started.messages)).order_by(MessageRow.id)))
        lines = await mortal_opportunities(session, rules, entity)
        opportunities = (
            render(PromptId.MORTAL_OPPORTUNITIES, MortalOpportunitiesContext(rules=rules, lines=lines, available_tools=catalogue.names or None))
            if lines
            else ""
        )
        user = MortalTurnUserContext(
            age=scope.epoch,
            creator_name=scope.creator.name,
            manifestations=texts if seen else [],
            dreams=[] if seen else texts,
            context=render(PromptId.MORTAL_CONTEXT, await mortal_context(scope, entity)),
            opportunities=opportunities,
            resumed=started.resumed,
            continuation=continuation,
            actions_left=points,
        )
        return render(PromptId.MORTAL_TURN_SYSTEM, system), render(PromptId.MORTAL_TURN_USER, user)


async def finish_mortal_turn(runtime: AgentRuntime, started: StartedMortalTurn, outcome: TurnOutcome, creations: list[int]) -> MortalTurnResult:
    word = extract_word(outcome.text)
    async with runtime.database.write() as session:
        rules = await runtime.rules(session)
        entity = await session.get(EntityRow, started.entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        entity.last_acted_epoch = started.epoch
        await finish_turn(session, entity.id)
        if started.messages:
            await session.execute(update(MessageRow).where(MessageRow.id.in_(started.messages)).values(is_read=True))
        await session.execute(delete(EntityFlagRow).where(EntityFlagRow.entity_id == entity.id, EntityFlagRow.flag == EntityFlag.AGENT_SELECTED))
        if word:
            text = f'{entity.name}: "{word[:MORTAL_WORD_CHRONICLE_CHARS]}"'
            await write_line(
                session, rules, started.epoch, ChronicleKind.SPEECH, text, key="mortal.word", phase=ChroniclePhase.MORTALS, entity_ids=[entity.id, *creations]
            )
    return MortalTurnResult(started.entity_id, started.name, word, creations, outcome.status.value)


async def run_mortal_turn(runtime: AgentRuntime, entity_id: int, order: tuple[int, int] | None = None) -> MortalTurnResult:
    runtime.require_llm("mortal turn")
    started = await start_mortal_turn(runtime, entity_id)
    toolkit: TurnToolkit = SpeechOnlyToolkit()
    if runtime.toolkits is not None:
        toolkit = await runtime.toolkits.mortal_toolkit(entity_id, started.epoch, started.action_points)
    catalogue = toolkit.catalogue
    system, prompt = await mortal_prompts(runtime, started, catalogue)
    rules = await runtime.current_rules()
    position = {"order": order[0], "total": order[1]} if order is not None else {}
    payload = {"entity_id": entity_id, "name": started.name, "resumed": started.resumed, "model": HAIKU_MODEL_ID, **position}
    runtime.publish(EventKind.MORTAL_TURN_STARTED, payload)

    async def follow_up(reason: TurnInterruption, detail: str | None, done: list[DoneAction]) -> str | None:
        async with runtime.database.read() as session:
            jobs = await long_job_notes(session, entity_id, rules.model.continuation_action_summary_chars)
        note = render(PromptId.MORTAL_TURN_CONTINUATION, TurnContinuationContext(reason=reason, error_detail=detail, done=done, long_jobs=jobs))
        return (await mortal_prompts(runtime, started, catalogue, note))[1]

    plan = TurnPlan(
        label=turn_label(AgentRole.MORTAL_TURN, started.name),
        actor=started.name,
        actor_kind=ActorKind.MORTAL,
        actor_id=entity_id,
        system_prompt=system,
        prompt=prompt,
        max_turns=rules.mortal_agents.max_turns,
        timeout=rules.model.agent_timeout,
        continuation=follow_up,
        is_complete=lambda text: bool(extract_word(text)),
    )
    with metrics_turn(started.epoch, started.action_points):
        outcome = await run_turn(runtime.model, plan, toolkit, rules.model, runtime.publish)
    result = await finish_mortal_turn(runtime, started, outcome, list(toolkit.created_entity_ids))
    runtime.publish(
        EventKind.MORTAL_TURN_FINISHED,
        {"entity_id": entity_id, "name": result.name, "word": result.word, "creations": result.creations, "status": result.status, "model": HAIKU_MODEL_ID},
    )
    return result
