import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import AeronaError, NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.domain.enums.epoch import EpochPhase
from aerona.engine import records, snapshot, transition
from aerona.engine.context import Publisher, TickContext, TickEnvironment, phase_window
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.notes import FoldResult, fold_tick_lines, last_chronicle_id
from aerona.engine.phase import Phase
from aerona.engine.phases import (
    afterlife,
    belief_memory,
    births,
    body,
    casualties,
    civilization,
    climate,
    commerce,
    cosmic_economy,
    cosmos_upkeep,
    creator_mood,
    creatures,
    culture_exchange,
    curses,
    dark_ages,
    demography,
    dialects,
    diplomacy,
    disasters,
    doom,
    ecology,
    environment,
    epidemics,
    espionage,
    exploration,
    factions,
    faith,
    geography,
    goals,
    god_death,
    god_power,
    grudges,
    heroes,
    heroism,
    horror,
    institutions,
    interconnect,
    knowledge_levels,
    language_contact,
    language_death,
    life_cycles,
    life_seed,
    living_stats,
    lore,
    magic,
    market,
    mechanics_assignment,
    migration,
    mind,
    monsters,
    mortals,
    native_faith,
    pantheon,
    population,
    prisoners,
    production,
    prosperity,
    realms,
    refugees,
    religion_spread,
    remembrance,
    reputation,
    resources,
    ruins,
    settlement_life,
    settlements,
    sky,
    society,
    society_economy,
    sons,
    spirits,
    trade,
    travel,
    tribute,
    vendettas,
    warfare,
    wonders,
    works,
    world_balance,
    writing,
)
from aerona.engine.primitives.manual import silent
from aerona.engine.snapshot import store_tick_flows
from aerona.engine.stats import TickStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules

Finalizer = Callable[[AsyncSession], Awaitable[None]]
LOGGER = logging.getLogger(__name__)
FAILED_COUNTER = "failed"
DISABLED_COUNTER = "disabled"

EXPORTED_PHASES: tuple[Phase, ...] = (
    records.PHASES
    + transition.PHASES
    + snapshot.PHASES
    + interconnect.PHASES
    + interconnect.THREAD_PHASES
    + afterlife.PHASES
    + belief_memory.PHASES
    + births.PHASES
    + body.PHASES
    + mind.PHASES
    + casualties.PHASES
    + ecology.PHASES
    + environment.PHASES
    + geography.PHASES
    + life_cycles.PHASES
    + institutions.PHASES
    + remembrance.PHASES
    + world_balance.PHASES
    + civilization.PHASES
    + commerce.PHASES
    + production.PHASES
    + climate.PHASES
    + cosmic_economy.PHASES
    + cosmos_upkeep.PHASES
    + creator_mood.PHASES
    + creatures.PHASES
    + culture_exchange.PHASES
    + curses.PHASES
    + dark_ages.PHASES
    + dialects.PHASES
    + diplomacy.PHASES
    + disasters.PHASES
    + doom.PHASES
    + espionage.PHASES
    + exploration.PHASES
    + factions.PHASES
    + goals.PHASES
    + god_death.PHASES
    + god_power.PHASES
    + grudges.PHASES
    + heroes.PHASES
    + heroism.PHASES
    + knowledge_levels.PHASES
    + language_contact.PHASES
    + horror.PHASES
    + language_death.PHASES
    + life_seed.PHASES
    + living_stats.PHASES
    + magic.PHASES
    + market.PHASES
    + mechanics_assignment.PHASES
    + migration.PHASES
    + monsters.PHASES
    + mortals.PHASES
    + native_faith.PHASES
    + pantheon.PHASES
    + population.PHASES
    + prisoners.PHASES
    + prosperity.PHASES
    + refugees.PHASES
    + religion_spread.PHASES
    + reputation.PHASES
    + resources.PHASES
    + ruins.PHASES
    + settlements.PHASES
    + sky.PHASES
    + society.PHASES
    + society_economy.PHASES
    + sons.PHASES
    + spirits.PHASES
    + trade.PHASES
    + travel.PHASES
    + tribute.PHASES
    + warfare.PHASES
    + wonders.PHASES
    + works.PHASES
    + writing.PHASES
    + epidemics.PHASES
    + lore.PHASES
    + faith.PHASES
    + vendettas.PHASES
    + realms.PHASES
    + settlement_life.PHASES
    + demography.PHASES
)
PHASE_REGISTRY: dict[str, Phase] = {phase.name: phase for phase in EXPORTED_PHASES}


def stage(*names: str) -> tuple[Phase, ...]:
    return tuple(PHASE_REGISTRY[name] for name in names)


CLEANUP_STAGE = stage(
    "dead_bonds_opening",
    "modifier_upkeep",
    "world_maps",
    "environment_survey",
    "mind_survey",
    "body_survey",
    "economy_survey",
    "expire_truces",
    "language_and_faith",
)
GRUDGE_STAGE = stage("divine_grudges")
SUB_ENGINE_STAGE = stage(
    "labour_allocation",
    "harvest",
    "diplomacy",
    "war_upkeep",
    "tribute",
    "treaty_cycles",
    "campaigns",
    "vendetta_cycles",
    "prisoners",
    "war_casualties",
    "travel",
    "exploration",
    "geography",
    "resource_mechanics",
    "mechanics_assignment",
    "cosmic_economy",
    "market",
    "horror",
    "creatures",
    "ecology",
    "pantheon",
    "native_faith",
    "death_engine",
    "civilization",
    "world_balance",
    "polity_cycles",
    "sky",
    "beyond",
    "soul_cycles",
)
RAID_STAGE = stage("monster_raids", "sworn_hunts", "glory_hunts")
ECONOMY_STAGE = stage(
    "trade_income",
    "curse_decay",
    "world_materials",
    "species_yields",
    "deposit_finding",
    "resource_economy",
    "prosperity_reversion",
    "barter_and_rivalry",
    "curse_lifting",
    "cursed_items",
    "magic_storms",
    "resource_regeneration",
)
SOCIETY_STAGE = stage(
    "schisms",
    "faith_cycles",
    "creature_migration",
    "hero_births",
    "knowledge_diffusion",
    "cultural_exchange",
    "natural_disasters",
    "famine_migration",
    "refugees",
    "disaster_casualties",
    "epidemics",
    "uprisings",
    "spirits_rest",
    "hauntings",
    "settlement_laws",
    "currency",
    "wizards",
    "rite_cycles",
    "creature_rebellion",
    "godlessness",
    "speciation",
    "couple_births",
    "house_cycles",
    "love_and_rivalry",
    "dialect_divergence",
    "language_death",
    "language_contact",
    "language_cycles",
    "price_of_magic",
    "architecture",
)
SOCIETY_ENGINE_STAGE = stage(
    "society_economy",
    "refining",
    "markets",
    "trade_flow",
    "banking",
    "society_mobility",
    "settlement_life",
    "heroes",
    "spontaneous_births",
    "factions",
    "ideology_cycles",
    "engine_works",
    "splendor_growth",
    "religion_spread",
    "life_seed",
    "writing_systems",
    "knowledge_levels",
    "research_cycles",
    "calendars",
    "living_stats",
    "belief_and_memory",
    "legend_cycles",
    "prophecy_cycles",
    "espionage",
    "wonders",
    "dark_ages",
    "ruins",
    "settlement_cycles",
    "land_use",
    "material_decay",
    "institution_cycles",
    "culture_cycles",
    "tradition_cycles",
    "people_cycles",
    "remembrance",
    "item_cycles",
    "artwork_cycles",
)
AGING_STAGE = stage("body_healing", "mortal_wounds", "body_conditions", "body_society", "mortal_aging", "dead_bonds_closing")
MIND_STAGE = stage("mind_values", "mind_skills", "mind_memories", "mind_needs", "famine_aid", "mind_opinion", "incident_threads")

TICK_ORDER: tuple[Phase, ...] = (
    CLEANUP_STAGE + GRUDGE_STAGE + SUB_ENGINE_STAGE + RAID_STAGE + ECONOMY_STAGE + SOCIETY_STAGE + SOCIETY_ENGINE_STAGE + AGING_STAGE + MIND_STAGE
)

PRE_TRANSITION_ORDER = stage("local_gods")
GROWTH_STAGE = stage(
    "law_fertility", "population_baseline", "climate_transition", "environment_derive", "ley_lines", "population_growth", "cohort_upkeep", "epoch_stars"
)
GODS_STAGE = stage("sons_renewal", "gods_fate", "works_remember_gods", "domain_rivalry", "rebel_theft")
CLOSING_STAGE = stage("doom_clock", "creator_essence", "epoch_statistics", "advance_epoch")

TRANSITION_ORDER: tuple[Phase, ...] = GROWTH_STAGE + GODS_STAGE + CLOSING_STAGE
POST_TRANSITION_ORDER: tuple[Phase, ...] = stage("creator_mood", "god_power", "reputation", "goals")

TOLERANT_TRANSITION_STEPS: frozenset[str] = frozenset(phase.name for phase in PRE_TRANSITION_ORDER + POST_TRANSITION_ORDER)


ESSENTIAL_PHASES: frozenset[str] = frozenset({"advance_epoch"})


def disabled_by_rules(rules: Rules) -> frozenset[str]:
    switches = rules.engine_phases
    return frozenset(name for name in PHASE_REGISTRY if name not in ESSENTIAL_PHASES and getattr(switches, name) == 0)


def enabled_phases(phases: Sequence[Phase], rules: Rules) -> tuple[Phase, ...]:
    disabled = disabled_by_rules(rules)
    return tuple(phase for phase in phases if phase.name not in disabled)


def after_transition(environment: TickEnvironment) -> TickEnvironment:
    return replace(environment, epoch=environment.epoch + 1, window=phase_window(environment.rules, EpochPhase.NOT_STARTED))


class EnginePhaseError(AeronaError):
    def __init__(self, phase: str, error: BaseException) -> None:
        super().__init__(f"The engine stopped in the {phase} step: {error}")
        self.phase = phase


@dataclass(frozen=True)
class TickResult:
    stats: TickStats
    fold: FoldResult
    since_chronicle_id: int


@dataclass(frozen=True)
class EpochRun:
    epoch: int
    tick: TickResult
    transition: TickStats


def all_phases() -> tuple[Phase, ...]:
    return TICK_ORDER + PRE_TRANSITION_ORDER + TRANSITION_ORDER + POST_TRANSITION_ORDER


def find_phase(name: str) -> Phase:
    found = next((phase for phase in all_phases() if phase.name == name), None)
    if found is None:
        raise NotFoundError(f"No engine step is called {name}.")
    return found


async def run_phase(environment: TickEnvironment, database: Database, phase: Phase) -> None:
    started = time.perf_counter()
    try:
        async with database.write() as session:
            await run_guarded(phase, TickContext(environment, session, phase.name))
    except AeronaError:
        raise
    except Exception as error:
        raise EnginePhaseError(phase.name, error) from error
    elapsed = time.perf_counter() - started
    environment.stats.phase_seconds[phase.name] = environment.stats.phase_seconds.get(phase.name, 0.0) + elapsed
    environment.publish(EventKind.ENGINE_PHASE, {"epoch": environment.epoch, "phase": phase.name, "seconds": elapsed})
    await asyncio.sleep(0)


async def run_phases(
    environment: TickEnvironment,
    database: Database,
    phases: Sequence[Phase],
    disabled: frozenset[str] = frozenset(),
    tolerant: frozenset[str] = frozenset(),
) -> TickStats:
    skipped = disabled | disabled_by_rules(environment.rules)
    for phase in phases:
        if phase.name in skipped:
            environment.stats.count(f"{phase.name}.{DISABLED_COUNTER}")
            continue
        try:
            await run_phase(environment, database, phase)
        except EnginePhaseError as error:
            if phase.name not in tolerant:
                raise
            LOGGER.exception("Engine step %s failed and was skipped", phase.name)
            environment.stats.count(f"{phase.name}.{FAILED_COUNTER}")
            environment.publish(EventKind.ENGINE_PHASE, {"epoch": environment.epoch, "phase": phase.name, "error": error.message})
    return environment.stats


async def run_tick(
    environment: TickEnvironment,
    database: Database,
    *,
    phases: Sequence[Phase] = TICK_ORDER,
    disabled: frozenset[str] = frozenset(),
    finalize: Finalizer | None = None,
) -> TickResult:
    async with database.read() as session:
        since = await last_chronicle_id(session)
    await run_phases(environment, database, phases, disabled)
    async with database.write() as session:
        fold = await fold_tick_lines(session, environment.rules, environment.epoch, since)
        await store_tick_flows(session, environment.epoch, environment.stats.flows)
        if finalize is not None:
            await finalize(session)
    return TickResult(stats=environment.stats, fold=fold, since_chronicle_id=since)


async def run_epoch_transition(
    environment: TickEnvironment,
    database: Database,
    *,
    phases: Sequence[Phase] = TRANSITION_ORDER,
    pre_phases: Sequence[Phase] = PRE_TRANSITION_ORDER,
    post_phases: Sequence[Phase] = POST_TRANSITION_ORDER,
    disabled: frozenset[str] = frozenset(),
    tolerant: frozenset[str] = TOLERANT_TRANSITION_STEPS,
) -> TickStats:
    await run_phases(environment, database, pre_phases, disabled, tolerant)
    await run_phases(environment, database, phases, disabled, tolerant)
    return await run_phases(after_transition(environment), database, post_phases, disabled, tolerant)


async def run_named_phase(environment: TickEnvironment, database: Database, name: str) -> TickStats:
    await run_phase(environment, database, find_phase(name))
    return environment.stats


async def current_environment(
    database: Database, publish: Publisher = silent, rules: Rules | None = None, *, phase: EpochPhase | None = None
) -> TickEnvironment:
    async with database.read() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        resolved = rules or rules_from_snapshot(cosmos.rules_snapshot)
        return TickEnvironment(
            rules=resolved,
            epoch=cosmos.epoch,
            world_seed=cosmos.rng_seed,
            lore_language=cosmos.lore_language,
            publish=publish,
            stats=TickStats(),
            window=phase_window(resolved, phase) if phase is not None else None,
        )


async def simulate(database: Database, epochs: int, *, rules: Rules | None = None, publish: Publisher = silent) -> list[EpochRun]:
    runs: list[EpochRun] = []
    for _ in range(epochs):
        tick_environment = await current_environment(database, publish, rules, phase=EpochPhase.ENGINE)
        tick = await run_tick(tick_environment, database)
        transition_environment = await current_environment(database, publish, rules, phase=EpochPhase.TRANSITION)
        transition_stats = await run_epoch_transition(transition_environment, database)
        runs.append(EpochRun(epoch=tick_environment.epoch, tick=tick, transition=transition_stats))
    return runs


def describe_order() -> list[dict[str, Any]]:
    stages = (("tick", TICK_ORDER), ("before_transition", PRE_TRANSITION_ORDER), ("transition", TRANSITION_ORDER), ("after_transition", POST_TRANSITION_ORDER))
    return [{"stage": label, "phase": phase.name} for label, phases in stages for phase in phases]
