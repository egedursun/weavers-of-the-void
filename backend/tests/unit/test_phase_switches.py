import dataclasses

from aerona.engine import pipeline
from aerona.engine.pipeline import ESSENTIAL_PHASES, PHASE_REGISTRY
from aerona.rules.registry.engine_phases import EnginePhasesRules


def test_every_engine_step_has_a_rule_that_turns_it_on_or_off() -> None:
    switches = {field.name for field in dataclasses.fields(EnginePhasesRules)}
    assert sorted(name for name in PHASE_REGISTRY if name not in ESSENTIAL_PHASES and name not in switches) == []


def test_every_engine_step_runs_in_a_tick_or_an_epoch_transition() -> None:
    orders = (pipeline.TICK_ORDER, pipeline.PRE_TRANSITION_ORDER, pipeline.TRANSITION_ORDER, pipeline.POST_TRANSITION_ORDER)
    scheduled = {phase.name for order in orders for phase in order}
    assert sorted(set(PHASE_REGISTRY) - scheduled) == []
