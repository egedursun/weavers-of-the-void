from aerona.catalog.methods import METHODS, PROCESS_LABELS, PROCESS_METHODS, PROCESS_OUTPUT, STEP_PROCESS, method_labour, method_output
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.rules.registry import Rules
from tests.engine.society.factories import tuned

NEW = (ProcessKind.SMITHING, ProcessKind.CARPENTRY, ProcessKind.FIRING, ProcessKind.DYEING, ProcessKind.COPYING, ProcessKind.EVAPORATING)


def test_twenty_six_processes_each_with_its_methods_by_era() -> None:
    assert len(ProcessKind) == 26 and len(MethodKind) == len(METHODS)
    for process in NEW:
        methods = PROCESS_METHODS[process]
        assert len(methods) >= 3 and process in PROCESS_LABELS and process in PROCESS_OUTPUT
        assert any(spec.technique is not None for spec in methods)
    assert METHODS[MethodKind.COPYING_PRESS].technique is Technique.PRINTING_PRESS
    assert PROCESS_OUTPUT[ProcessKind.COPYING] is CommodityKind.BOOKS and STEP_PROCESS["copy_books"] is ProcessKind.COPYING


def test_a_methods_output_and_hands_come_from_its_rules() -> None:
    spec = METHODS[MethodKind.TRIP_HAMMER]
    rules = Rules()
    assert method_output(rules, spec) == spec.output_pct and method_labour(rules, spec) == spec.labour_pct
    faster = tuned(rules, production={"trip_hammer_output": 300})
    assert method_output(faster, spec) == 300
