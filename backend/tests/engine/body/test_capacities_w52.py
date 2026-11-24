from aerona.catalog.anatomy import anatomy_of
from aerona.catalog.conditions import CAPACITIES
from aerona.domain.enums.body import BodyPart, BodyPlan, Capacity, InjuryKind
from aerona.engine.body.capacities import BearerStats, BodyState, capacities
from aerona.engine.body.functions import Wound
from aerona.rules.registry import Rules

RULES = Rules()
STATS = BearerStats(50, 50, 50, 50, 50)


def test_ten_capacities_and_the_new_two_follow_breath_legs_and_senses() -> None:
    assert len(Capacity) == len(CAPACITIES) == 12
    body = anatomy_of(BodyPlan.HUMANOID)
    whole = capacities(RULES, STATS, BodyState(body, (), {}, 0))
    blind = (Wound(BodyPart.LEFT_EYE.value, InjuryKind.GOUGED, 5, 100), Wound(BodyPart.RIGHT_EYE.value, InjuryKind.GOUGED, 5, 100))
    breathless = (Wound(BodyPart.LUNGS.value, InjuryKind.CRUSH, 4, 80),)
    assert capacities(RULES, STATS, BodyState(body, blind, {}, 0))[Capacity.PERCEPTION] < whole[Capacity.PERCEPTION]
    assert capacities(RULES, STATS, BodyState(body, breathless, {}, 0))[Capacity.ENDURANCE] < whole[Capacity.ENDURANCE]
    assert whole[Capacity.ENDURANCE] > 0 and whole[Capacity.PERCEPTION] > 0
