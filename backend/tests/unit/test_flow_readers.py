import inspect

from aerona.engine.pipeline import POST_TRANSITION_ORDER, PRE_TRANSITION_ORDER, TICK_ORDER, TRANSITION_ORDER

FLOWS = ".stats.flows"
ADDS_ITS_OWN_STAGE_TO_THE_TICK_SUMMARY = frozenset({"epoch_statistics"})


def test_a_step_that_reads_the_epochs_flows_runs_in_the_tick_that_records_them() -> None:
    tick = {phase.name for phase in TICK_ORDER}
    later = [
        phase.name
        for phase in (*PRE_TRANSITION_ORDER, *TRANSITION_ORDER, *POST_TRANSITION_ORDER)
        if phase.name not in tick
        and phase.name not in ADDS_ITS_OWN_STAGE_TO_THE_TICK_SUMMARY
        and FLOWS in inspect.getsource(inspect.getmodule(phase.run) or phase.run)
    ]
    assert later == [], "the transition starts with fresh statistics, so these steps would never see a death, a loss or a move"
