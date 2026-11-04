import importlib
import pkgutil
from dataclasses import fields, replace
from types import ModuleType

import pytest

import aerona.engine
from aerona.db.session import Database
from aerona.engine.phase import Phase
from aerona.engine.pipeline import (
    ESSENTIAL_PHASES,
    POST_TRANSITION_ORDER,
    PRE_TRANSITION_ORDER,
    TICK_ORDER,
    TOLERANT_TRANSITION_STEPS,
    TRANSITION_ORDER,
    all_phases,
    current_environment,
    disabled_by_rules,
    run_tick,
)
from aerona.engine.startup import STARTUP_STEPS, prepare_engine
from aerona.rules.registry import Rules
from aerona.rules.registry.engine_phases import EnginePhasesRules
from tests.engine.core.factories import seed_core_world

TICK_CONSTRAINTS = (
    ("dead_bonds_opening", "expire_truces"),
    ("expire_truces", "language_and_faith"),
    ("language_and_faith", "divine_grudges"),
    ("divine_grudges", "diplomacy"),
    ("diplomacy", "war_upkeep"),
    ("war_upkeep", "tribute"),
    ("tribute", "campaigns"),
    ("campaigns", "prisoners"),
    ("prisoners", "travel"),
    ("travel", "exploration"),
    ("exploration", "resource_mechanics"),
    ("resource_mechanics", "cosmic_economy"),
    ("cosmic_economy", "horror"),
    ("horror", "creatures"),
    ("creatures", "pantheon"),
    ("pantheon", "death_engine"),
    ("death_engine", "civilization"),
    ("civilization", "sky"),
    ("sky", "beyond"),
    ("beyond", "monster_raids"),
    ("monster_raids", "sworn_hunts"),
    ("glory_hunts", "trade_income"),
    ("trade_income", "curse_decay"),
    ("prosperity_reversion", "barter_and_rivalry"),
    ("resource_regeneration", "schisms"),
    ("schisms", "creature_migration"),
    ("creature_migration", "hero_births"),
    ("hero_births", "knowledge_diffusion"),
    ("knowledge_diffusion", "cultural_exchange"),
    ("cultural_exchange", "natural_disasters"),
    ("famine_migration", "refugees"),
    ("refugees", "uprisings"),
    ("uprisings", "spirits_rest"),
    ("settlement_laws", "currency"),
    ("currency", "wizards"),
    ("wizards", "creature_rebellion"),
    ("creature_rebellion", "godlessness"),
    ("godlessness", "speciation"),
    ("speciation", "couple_births"),
    ("couple_births", "love_and_rivalry"),
    ("love_and_rivalry", "dialect_divergence"),
    ("dialect_divergence", "language_death"),
    ("architecture", "society_economy"),
    ("society_economy", "heroes"),
    ("heroes", "spontaneous_births"),
    ("spontaneous_births", "factions"),
    ("factions", "engine_works"),
    ("engine_works", "religion_spread"),
    ("religion_spread", "life_seed"),
    ("life_seed", "writing_systems"),
    ("writing_systems", "belief_and_memory"),
    ("belief_and_memory", "espionage"),
    ("espionage", "wonders"),
    ("wonders", "dark_ages"),
    ("dark_ages", "ruins"),
    ("ruins", "mortal_wounds"),
    ("mortal_wounds", "mortal_aging"),
    ("mortal_aging", "dead_bonds_closing"),
)
TRANSITION_CONSTRAINTS = (
    ("law_fertility", "population_baseline"),
    ("population_baseline", "climate_transition"),
    ("climate_transition", "population_growth"),
    ("population_growth", "epoch_stars"),
    ("epoch_stars", "sons_renewal"),
    ("sons_renewal", "gods_fate"),
    ("gods_fate", "works_remember_gods"),
    ("works_remember_gods", "domain_rivalry"),
    ("domain_rivalry", "rebel_theft"),
    ("rebel_theft", "doom_clock"),
    ("doom_clock", "creator_essence"),
    ("creator_essence", "epoch_statistics"),
    ("epoch_statistics", "advance_epoch"),
)
POST_ORDER = ("creator_mood", "god_power", "reputation", "goals")


def engine_modules() -> list[ModuleType]:
    found = [aerona.engine]
    for info in pkgutil.walk_packages(aerona.engine.__path__, prefix="aerona.engine."):
        found.append(importlib.import_module(info.name))
    return found


def exported_phases() -> dict[int, Phase]:
    collected: dict[int, Phase] = {}
    for module in engine_modules():
        for value in vars(module).values():
            if isinstance(value, tuple) and value and all(isinstance(item, Phase) for item in value):
                collected.update({id(item): item for item in value})
    return collected


def test_every_exported_phase_is_wired_exactly_once() -> None:
    wired = all_phases()
    wired_ids = [id(phase) for phase in wired]
    assert len(wired_ids) == len(set(wired_ids))
    assert len({phase.name for phase in wired}) == len(wired)
    exported = exported_phases()
    missing = sorted(phase.name for key, phase in exported.items() if key not in set(wired_ids))
    assert missing == []
    assert set(wired_ids) <= set(exported)


@pytest.mark.parametrize(("order", "constraints"), [(TICK_ORDER, TICK_CONSTRAINTS), (TRANSITION_ORDER, TRANSITION_CONSTRAINTS)])
def test_order_constraints_hold(order: tuple[Phase, ...], constraints: tuple[tuple[str, str], ...]) -> None:
    position = {phase.name: index for index, phase in enumerate(order)}
    broken = [(first, second) for first, second in constraints if position[first] >= position[second]]
    assert broken == []


def test_post_transition_steps_follow_the_spec_and_are_tolerant() -> None:
    assert tuple(phase.name for phase in POST_TRANSITION_ORDER) == POST_ORDER
    assert tuple(phase.name for phase in PRE_TRANSITION_ORDER) == ("local_gods",)
    assert set(POST_ORDER) <= TOLERANT_TRANSITION_STEPS
    assert "local_gods" in TOLERANT_TRANSITION_STEPS


def test_every_phase_has_a_rules_switch() -> None:
    switches = {definition.name for definition in fields(EnginePhasesRules)}
    assert switches == {phase.name for phase in all_phases()} - ESSENTIAL_PHASES
    assert disabled_by_rules(Rules()) == frozenset()


async def test_a_disabled_phase_is_skipped(database: Database) -> None:
    async with database.write() as session:
        await seed_core_world(session)
    rules = Rules()
    rules = replace(rules, engine_phases=replace(rules.engine_phases, language_and_faith=0, divine_grudges=0))
    environment = await current_environment(database, rules=rules)
    result = await run_tick(
        environment, database, phases=TICK_ORDER[: TICK_ORDER.index(next(phase for phase in TICK_ORDER if phase.name == "divine_grudges")) + 1]
    )
    assert "language_and_faith" not in result.stats.phase_seconds
    assert result.stats.counters["language_and_faith.disabled"] == 1
    assert "dead_bonds_opening" in result.stats.phase_seconds


async def test_engine_startup_runs_every_step_once_a_cosmos_exists(database: Database) -> None:
    assert not (await prepare_engine(database)).ran
    async with database.write() as session:
        await seed_core_world(session)
    report = await prepare_engine(database)
    assert report.ran
    assert set(report.changes) == {name for name, _ in STARTUP_STEPS}
