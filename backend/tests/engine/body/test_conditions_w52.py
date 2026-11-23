from aerona.catalog.anatomy import anatomy_of
from aerona.catalog.conditions import AGE_CONDITIONS, CONDITIONS
from aerona.domain.enums.body import BodyPlan, Capacity, ConditionKind
from aerona.engine.body.capacities import BearerStats, BodyState, capacities
from aerona.rules.registry import Rules

RULES = Rules()
STATS = BearerStats(50, 50, 50, 50, 50)


def capacity_with(kind: ConditionKind | None) -> dict[Capacity, int]:
    held = ((kind, float(RULES.capacities.condition_full_severity)),) if kind is not None else ()
    return capacities(RULES, STATS, BodyState(anatomy_of(BodyPlan.HUMANOID), (), {}, 0, conditions=held))


def test_twenty_one_conditions_and_the_new_three_weigh_on_their_capacities() -> None:
    assert len(ConditionKind) == len(CONDITIONS) == 21
    whole = capacity_with(None)
    assert capacity_with(ConditionKind.PARALYSIS)[Capacity.MOBILITY] < whole[Capacity.MOBILITY] * 0.2
    assert capacity_with(ConditionKind.INFERTILITY)[Capacity.FERTILITY] == 0
    pained = capacity_with(ConditionKind.CHRONIC_PAIN)
    assert pained[Capacity.CRAFT] < whole[Capacity.CRAFT] and pained[Capacity.FERTILITY] == whole[Capacity.FERTILITY]
    assert ConditionKind.INFERTILITY in AGE_CONDITIONS
