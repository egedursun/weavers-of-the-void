from aerona.catalog.anatomy import ANATOMIES, anatomy_of
from aerona.catalog.body_plans import PLAN_TEXT, PLANS
from aerona.catalog.body_words import BODY_WORDS
from aerona.catalog.movement import BODY_MODES
from aerona.catalog.peoples import KIN
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.domain.enums.body import BodyFunction, BodyPart, BodyPlan, DamageType, InjuryKind
from aerona.engine.body.functions import Wound, function_levels
from aerona.engine.body.hits import shielded
from aerona.engine.military.clash import born_riders
from aerona.rules.registry import Rules
from tests.engine.society.factories import tuned

RULES = Rules()
BACKBONED = (BodyPlan.HUMANOID, BodyPlan.QUADRUPED, BodyPlan.AVIAN, BodyPlan.SERPENTINE, BodyPlan.AQUATIC, BodyPlan.CENTAUROID)


def test_sixteen_plans_each_with_an_anatomy_and_every_table_that_reads_a_plan() -> None:
    assert len(BodyPlan) == 18 and len(BodyPart) == 55
    for plan in BodyPlan:
        assert plan in ANATOMIES and plan in KIN and plan in BODY_MODES and plan in PLAN_TEXT and plan in PLANS and plan in BODY_WORDS


def test_backboned_plans_carry_a_spine_and_shelled_ones_a_carapace() -> None:
    assert all(ANATOMIES[plan].part(BodyPart.SPINE) is not None for plan in BACKBONED)
    assert ANATOMIES[BodyPlan.INSECTOID].part(BodyPart.CARAPACE) is not None
    many = ANATOMIES[BodyPlan.TENTACLED]
    assert many.part(BodyPart.BEAK) is not None and many.part(BodyPart.TENTACLES) is not None
    assert ANATOMIES[BodyPlan.RADIAL].part(BodyPart.HEAD) is None
    assert ANATOMIES[BodyPlan.COLONIAL].colonial and not any(part.vital for part in ANATOMIES[BodyPlan.COLONIAL].parts)


def test_soft_arms_are_lost_a_share_at_a_time_and_a_spine_wound_takes_movement() -> None:
    many = anatomy_of(BodyPlan.TENTACLED)
    torn = (Wound(BodyPart.TENTACLES.value, InjuryKind.SEVERED, 2, 100),)
    levels = function_levels(RULES.capacities, many, torn, {}, RULES.injury.venom_paralysis_at, share=RULES.body.tentacle_share)
    assert 0.5 < levels[BodyFunction.GRASP] < 1.0
    whole = function_levels(RULES.capacities, anatomy_of(BodyPlan.HUMANOID), (Wound(BodyPart.SPINE.value, InjuryKind.CRUSH, 4, 80),), {}, 5)
    assert whole[BodyFunction.LOCOMOTION] <= 0.2 + 1e-9


def test_a_carapace_takes_the_blow_before_the_body() -> None:
    shell = anatomy_of(BodyPlan.INSECTOID)
    thorax = shell.part(BodyPart.TORSO)
    assert thorax is not None
    certain = tuned(body={"carapace_guard_pct": 100})
    rng = SeededRandom(RandomKey(1, 0, "shell"))
    assert shielded(certain, shell, thorax, DamageType.BLUNT, rng).key is BodyPart.CARAPACE
    assert shielded(certain, shell, thorax, DamageType.PSYCHIC, rng).key is BodyPart.TORSO
    never = tuned(body={"carapace_guard_pct": 0})
    assert shielded(never, shell, thorax, DamageType.BLUNT, rng).key is BodyPart.TORSO


def test_upright_four_legged_peoples_fight_as_riders_and_centred_ones_have_no_flank() -> None:
    assert born_riders(RULES, PeopleBiologyRow(body_plan=BodyPlan.CENTAUROID)) > 1.0
    assert born_riders(RULES, PeopleBiologyRow(body_plan=BodyPlan.HUMANOID)) == 1.0
    assert born_riders(RULES, None) == 1.0
    assert KIN[BodyPlan.RADIAL].frontless and not KIN[BodyPlan.HUMANOID].frontless
