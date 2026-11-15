import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import AeronaError, NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database, Steps
from aerona.domain.enums.epoch import EpochPhase
from aerona.engine import records, snapshot, transition
from aerona.engine.context import Publisher, TickContext, TickEnvironment, phase_window
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.notes import FoldResult, fold_tick_lines, last_chronicle_id
from aerona.engine.phase import Phase
from aerona.engine.phases import (
    affairs,
    afterlife,
    ages,
    agrarian,
    arcana,
    arts,
    belief_memory,
    belonging,
    biology_variants,
    births,
    body,
    casualties,
    civilization,
    climate,
    climes,
    collective,
    commerce,
    communication,
    cosmic_economy,
    cosmography,
    cosmos_upkeep,
    crafts,
    creator_mood,
    creatures,
    culture_exchange,
    curses,
    customs,
    cycles,
    dark_ages,
    demography,
    dialects,
    diplomacy,
    disasters,
    divine,
    dominion,
    doom,
    ecology,
    environment,
    epidemics,
    eras,
    espionage,
    estates,
    evolution,
    exploration,
    factions,
    faith,
    finance,
    folkways,
    fossils,
    gatherings,
    genetics,
    geography,
    goals,
    god_death,
    god_power,
    grudges,
    happenings,
    heroes,
    heroism,
    honours,
    horror,
    households,
    industry,
    institutions,
    interconnect,
    intrigue,
    justice,
    knowledge_levels,
    language_contact,
    language_death,
    law_depth,
    life_cycles,
    life_seed,
    lifecycle_ends,
    living_stats,
    lore,
    made_kinds,
    magic,
    market,
    means,
    mechanics_assignment,
    migration,
    mind,
    monsters,
    mortal_life,
    mortals,
    museums,
    mythic,
    native_faith,
    nature,
    operations,
    orders,
    pantheon,
    places,
    population,
    prehistory,
    prisoners,
    production,
    prosperity,
    realms,
    refugees,
    regimes,
    regions,
    relations,
    religion_spread,
    remembrance,
    renown,
    reputation,
    resources,
    ruins,
    rumours,
    sacred,
    seafaring,
    settlement_life,
    settlements,
    sky,
    society,
    society_economy,
    sons,
    spirits,
    statecraft,
    structures,
    titles,
    tongues,
    trade,
    transformations,
    travel,
    tribute,
    urban_depth,
    vendettas,
    warfare,
    wilds,
    wonders,
    works,
    world_balance,
    world_views,
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
OVER_BUDGET_PHASE = "tick_over_budget"

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
    + relations.PHASES
    + renown.PHASES
    + industry.PHASES
    + genetics.PHASES
    + gatherings.PHASES
    + dominion.PHASES
    + arcana.PHASES
    + mythic.PHASES
    + tongues.PHASES
    + households.PHASES
    + intrigue.PHASES
    + communication.PHASES
    + titles.PHASES
    + justice.PHASES
    + statecraft.PHASES
    + affairs.PHASES
    + estates.PHASES
    + finance.PHASES
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
    + cosmography.PHASES
    + cosmos_upkeep.PHASES
    + creator_mood.PHASES
    + creatures.PHASES
    + culture_exchange.PHASES
    + curses.PHASES
    + dark_ages.PHASES
    + dialects.PHASES
    + diplomacy.PHASES
    + disasters.PHASES
    + divine.PHASES
    + doom.PHASES
    + espionage.PHASES
    + evolution.PHASES
    + urban_depth.PHASES
    + law_depth.PHASES
    + collective.PHASES
    + cycles.PHASES
    + regimes.PHASES
    + agrarian.PHASES
    + operations.PHASES
    + sacred.PHASES
    + arts.PHASES
    + means.PHASES
    + orders.PHASES
    + honours.PHASES
    + world_views.PHASES
    + biology_variants.PHASES
    + lifecycle_ends.PHASES
    + fossils.PHASES
    + prehistory.PHASES
    + transformations.PHASES
    + museums.PHASES
    + ages.PHASES
    + folkways.PHASES
    + belonging.PHASES
    + eras.PHASES
    + nature.PHASES
    + climes.PHASES
    + crafts.PHASES
    + customs.PHASES
    + made_kinds.PHASES
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
    + places.PHASES
    + magic.PHASES
    + market.PHASES
    + mechanics_assignment.PHASES
    + migration.PHASES
    + monsters.PHASES
    + mortals.PHASES
    + mortal_life.PHASES
    + native_faith.PHASES
    + pantheon.PHASES
    + population.PHASES
    + prisoners.PHASES
    + prosperity.PHASES
    + refugees.PHASES
    + religion_spread.PHASES
    + reputation.PHASES
    + rumours.PHASES
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
    + seafaring.PHASES
    + wonders.PHASES
    + works.PHASES
    + writing.PHASES
    + epidemics.PHASES
    + wilds.PHASES
    + lore.PHASES
    + faith.PHASES
    + vendettas.PHASES
    + realms.PHASES
    + settlement_life.PHASES
    + structures.PHASES
    + demography.PHASES
    + happenings.PHASES
    + regions.PHASES
)
PHASE_REGISTRY: dict[str, Phase] = {phase.name: phase for phase in EXPORTED_PHASES}


def stage(*names: str) -> tuple[Phase, ...]:
    return tuple(PHASE_REGISTRY[name] for name in names)


CLEANUP_STAGE = stage(
    "dead_bonds_opening",
    "modifier_upkeep",
    "world_maps",
    "scale_ladder",
    "stellar_systems",
    "formation_history",
    "cosmic_influence",
    "climes",
    "environment_survey",
    "environment_modifiers",
    "region_survey",
    "mind_survey",
    "biases",
    "body_survey",
    "mortal_survey",
    "genetics_survey",
    "household_survey",
    "intrigue_survey",
    "economy_survey",
    "structure_survey",
    "expire_truces",
    "language_and_faith",
    "creator_taboos",
)
GRUDGE_STAGE = stage("divine_grudges")
SUB_ENGINE_STAGE = stage(
    "labour_allocation",
    "harvest",
    "long_seasons",
    "nutrition",
    "foresight",
    "diplomacy",
    "correspondence",
    "war_upkeep",
    "tribute",
    "treaty_cycles",
    "admiralty",
    "equipment_forging",
    "unit_types",
    "vehicle_works",
    "constructs",
    "order_of_battle",
    "campaigns",
    "vendetta_cycles",
    "prisoners",
    "war_casualties",
    "veterans",
    "crossings",
    "travel",
    "cosmic_trade",
    "seafaring",
    "exploration",
    "geography",
    "place_profiles",
    "site_rooms",
    "expeditions",
    "excavations",
    "place_secrets",
    "magic_sites",
    "thrones",
    "resource_mechanics",
    "mechanics_assignment",
    "natural_laws",
    "cosmic_economy",
    "market",
    "galaxy_cycles",
    "star_lives",
    "world_physics",
    "planetary_climate",
    "world_cycles",
    "cosmic_features",
    "impacts",
    "terraforming",
    "surveys",
    "dimension_cycles",
    "rift_cycles",
    "cosmic_beings",
    "phenomena",
    "regional_leak",
    "celestial_omens",
    "horror",
    "outer_hunger",
    "creatures",
    "ecology",
    "husbandry",
    "trait_evolution",
    "niches",
    "trophic_flow",
    "keystones",
    "feral_reversion",
    "lineages",
    "biome_succession",
    "flora_cycles",
    "living_nature",
    "beast_cycles",
    "pet_cycles",
    "necromancy_cycles",
    "pantheon",
    "native_faith",
    "god_relations",
    "council_rulings",
    "avatars",
    "death_engine",
    "civilization",
    "world_balance",
    "tech_eras",
    "polity_cycles",
    "regimes",
    "patronage",
    "legislature",
    "titles",
    "statecraft",
    "affairs",
    "sky",
    "beyond",
    "soul_cycles",
)
RAID_STAGE = stage("monster_raids", "sworn_hunts", "glory_hunts", "monster_contracts")
ECONOMY_STAGE = stage(
    "trade_income",
    "curse_decay",
    "world_materials",
    "species_yields",
    "deposit_finding",
    "industry_methods",
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
    "folk_spirits",
    "mysteries",
    "rites_of_passage",
    "creature_migration",
    "hero_births",
    "knowledge_diffusion",
    "cultural_exchange",
    "natural_disasters",
    "danger_harm",
    "terrain_hazards",
    "famine_migration",
    "refugees",
    "disaster_casualties",
    "epidemics",
    "pathogen_evolution",
    "carriers",
    "spillover",
    "plague_responses",
    "vaccination",
    "cure_research",
    "uprisings",
    "spirits_rest",
    "hauntings",
    "sacred_pilgrims",
    "settlement_laws",
    "remade_lives",
    "currency",
    "wizards",
    "rite_cycles",
    "creature_rebellion",
    "godlessness",
    "speciation",
    "couple_births",
    "birth_signs",
    "house_cycles",
    "bloodlines",
    "love_and_rivalry",
    "intrigue",
    "dialect_divergence",
    "language_death",
    "language_contact",
    "language_cycles",
    "divine_tongues",
    "grammar",
    "sound_changes",
    "semantic_drift",
    "pidgins",
    "language_policy",
    "price_of_magic",
    "architecture",
    "art_market",
    "art_movements",
    "pastimes",
)
SOCIETY_ENGINE_STAGE = stage(
    "people_customs",
    "written_media",
    "vaults",
    "water_lifting",
    "pilots",
    "containers",
    "biology_variants",
    "lifecycle_ends",
    "world_ends",
    "fossils",
    "dreamt_pasts",
    "transformations",
    "collections",
    "gardens",
    "world_views",
    "society_economy",
    "putting_out",
    "refining",
    "market_manipulation",
    "markets",
    "trade_policy",
    "convoys",
    "transport_fleets",
    "trade_flow",
    "tourism",
    "speculation",
    "industry_aftermath",
    "site_profits",
    "staples",
    "economic_indicators",
    "credit_ratings",
    "banking",
    "money_changing",
    "society_mobility",
    "labour_regimes",
    "economic_orders",
    "structure_upkeep",
    "district_coverage",
    "desirability",
    "housing_evolution",
    "turf",
    "crime_orgs",
    "trading_posts",
    "magical_orders",
    "spatial_economy",
    "settlement_life",
    "resilience",
    "structural_demography",
    "asabiyya",
    "satire",
    "crowds",
    "mobs",
    "popular_movements",
    "demography_depth",
    "role_norms",
    "sanctuary",
    "legal_systems",
    "trials",
    "appeals",
    "registries",
    "jurisdictions",
    "pardons",
    "outlawry",
    "prisons",
    "public_opinion",
    "households",
    "saving",
    "heroes",
    "spontaneous_births",
    "factions",
    "estates",
    "ideology_cycles",
    "engine_works",
    "splendor_growth",
    "structure_functions",
    "religion_spread",
    "divine_standing",
    "dominion",
    "worship_views",
    "divine_creatures",
    "cosmic_offices",
    "servitors",
    "divine_spies",
    "geasa",
    "mantling",
    "spell_grammar",
    "vis",
    "longevity",
    "warping",
    "life_seed",
    "writing_systems",
    "script_evolution",
    "decipherment",
    "knowledge_levels",
    "research_cycles",
    "learning_institutions",
    "calendars",
    "dating_systems",
    "heraldry",
    "designs",
    "living_stats",
    "belief_and_memory",
    "legend_cycles",
    "heroquests",
    "prophecy_cycles",
    "espionage",
    "spy_cells",
    "mole_hunts",
    "wonders",
    "megastructures",
    "kin_politics",
    "long_plans",
    "eco_transformations",
    "dark_ages",
    "ruins",
    "settlement_cycles",
    "nomadism",
    "land_use",
    "agrarian_cycles",
    "geomorphology",
    "material_decay",
    "institution_cycles",
    "culture_cycles",
    "tradition_cycles",
    "people_cycles",
    "kitchens",
    "legacy_traits",
    "remembrance",
    "historiography",
    "founding_myths",
    "commemorations",
    "lost_lands",
    "generations",
    "event_phases",
    "item_cycles",
    "artwork_cycles",
    "rumour_cycles",
    "ages",
    "arcs",
)
AGING_STAGE = stage(
    "body_healing",
    "mortal_wounds",
    "body_afflictions",
    "body_conditions",
    "cognitive_decline",
    "being_wounds",
    "body_society",
    "mortal_life_course",
    "mortal_aging",
    "attraction",
    "reproduction_systems",
    "dead_bonds_closing",
)
MIND_STAGE = stage(
    "mind_values",
    "mind_skills",
    "mind_split",
    "mind_ideas",
    "mind_memories",
    "mind_needs",
    "mind_thoughts",
    "mind_grief",
    "mind_dreams",
    "mind_preferences",
    "mind_ethics",
    "mind_aspirations",
    "social_norms",
    "social_learning",
    "relations_social",
    "purity",
    "mishaps",
    "witchcraft",
    "customs",
    "belonging",
    "town_life",
    "civics",
    "trades",
    "learning_aids",
    "sympathies",
    "gatherings",
    "reciprocity",
    "relations_circles",
    "relations_passions",
    "relations_pecking",
    "relations_contests",
    "renown_hearsay",
    "renown_claims",
    "ruler_currencies",
    "lore_market",
    "mortal_kin",
    "kinship_systems",
    "mortal_standing",
    "mortal_minds",
    "famine_aid",
    "mind_opinion",
    "ethnic_relations",
    "battlefields",
    "event_collections",
    "challenge_response",
    "storyteller",
    "storylets",
    "incident_threads",
)

TICK_ORDER: tuple[Phase, ...] = (
    CLEANUP_STAGE + GRUDGE_STAGE + SUB_ENGINE_STAGE + RAID_STAGE + ECONOMY_STAGE + SOCIETY_STAGE + SOCIETY_ENGINE_STAGE + AGING_STAGE + MIND_STAGE
)

PRE_TRANSITION_ORDER = stage("local_gods")
GROWTH_STAGE = stage(
    "law_fertility",
    "population_baseline",
    "climate_transition",
    "world_lives",
    "regional_climate",
    "environment_derive",
    "ley_lines",
    "population_growth",
    "cohort_upkeep",
    "epoch_stars",
)
GODS_STAGE = stage(
    "sons_renewal",
    "domain_economy",
    "divine_wounds",
    "gods_fate",
    "works_remember_gods",
    "domain_rivalry",
    "god_images",
    "rebel_theft",
    "god_goals",
    "creator_attention",
)
CLOSING_STAGE = stage("doom_clock", "creator_essence", "epoch_statistics", "advance_epoch")

TRANSITION_ORDER: tuple[Phase, ...] = GROWTH_STAGE + GODS_STAGE + CLOSING_STAGE
POST_TRANSITION_ORDER: tuple[Phase, ...] = stage("creator_mood", "god_power", "reputation", "goals")

TOLERANT_TRANSITION_STEPS: frozenset[str] = frozenset(phase.name for phase in PRE_TRANSITION_ORDER + POST_TRANSITION_ORDER)


ESSENTIAL_PHASES: frozenset[str] = frozenset({"advance_epoch"})


def disabled_by_rules(rules: Rules) -> frozenset[str]:
    switches = rules.engine_phases
    return frozenset(name for name in PHASE_REGISTRY if name not in ESSENTIAL_PHASES and getattr(switches, name) == 0)


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


async def run_phase(environment: TickEnvironment, database: Database, phase: Phase, steps: Steps | None = None) -> None:
    started = time.perf_counter()
    thought = time.process_time()
    try:
        async with database.write() if steps is None else steps.step() as session:
            await run_guarded(phase, TickContext(environment, session, phase.name))
    except AeronaError:
        raise
    except Exception as error:
        raise EnginePhaseError(phase.name, error) from error
    elapsed = time.perf_counter() - started
    environment.stats.phase_seconds[phase.name] = environment.stats.phase_seconds.get(phase.name, 0.0) + elapsed
    environment.stats.phase_cpu[phase.name] = environment.stats.phase_cpu.get(phase.name, 0.0) + time.process_time() - thought
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
    async with database.steps() as steps:
        for phase in phases:
            if phase.name in skipped:
                environment.stats.count(f"{phase.name}.{DISABLED_COUNTER}")
                continue
            try:
                await run_phase(environment, database, phase, steps)
            except EnginePhaseError as error:
                if phase.name not in tolerant:
                    raise
                LOGGER.exception("Engine step %s failed and was skipped", phase.name)
                environment.stats.count(f"{phase.name}.{FAILED_COUNTER}")
                environment.publish(EventKind.ENGINE_PHASE, {"epoch": environment.epoch, "phase": phase.name, "error": error.message})
    return environment.stats


def warn_over_budget(environment: TickEnvironment) -> float | None:
    target = environment.rules.engine_budget.tick_target_seconds
    seconds = environment.stats.over_budget(target)
    if seconds is not None:
        LOGGER.warning("Engine tick of epoch %s took %.1f s, over its %s s target", environment.epoch, seconds, target)
        environment.publish(EventKind.ENGINE_PHASE, {"epoch": environment.epoch, "phase": OVER_BUDGET_PHASE, "seconds": seconds, "target": target})
    return seconds


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
    warn_over_budget(environment)
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
