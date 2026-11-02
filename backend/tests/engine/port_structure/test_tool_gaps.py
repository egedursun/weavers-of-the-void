from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.bond import BondKind
from aerona.engine.gods.rewards import RewardDraft, adjust_reward, creation_gains, creation_value, fade_pct, record_reward
from aerona.rules.registry import Rules
from aerona.tools.framework.inputs import clean_choice, synonyms_of
from aerona.tools.framework.schema import nearest_choices
from aerona.tools.son.creation_effects import bounded_percent
from aerona.tools.son.creation_rules import roots, similarity
from tests.engine.core.factories import CoreWorld

BOND_CHOICES = [kind.value for kind in BondKind]


def test_event_effects_are_bounded_by_severity_and_power() -> None:
    rules = Rules()
    assert bounded_percent(rules, -95, severity=30, power=2) == -20
    assert bounded_percent(rules, 40, severity=15, power=9) == 15
    assert bounded_percent(rules, -5, severity=80, power=9) == -5


def test_bond_synonyms_and_nearest_choices() -> None:
    synonyms = synonyms_of(BondKind)
    assert clean_choice("made by", BOND_CHOICES, synonyms) == BondKind.PRODUCED.value
    assert clean_choice("Worshipper", BOND_CHOICES, synonyms) == BondKind.WORSHIPS.value
    assert clean_choice("nonsense", BOND_CHOICES, synonyms) == "nonsense"
    assert nearest_choices(BOND_CHOICES, "worshps", 3)[0] == BondKind.WORSHIPS.value


def test_repeated_creations_fade_and_similarity_counts_roots() -> None:
    rules = Rules()
    assert fade_pct(rules, 0) == 100
    assert fade_pct(rules, 1) == 65
    assert fade_pct(rules, 9) == rules.son_tools.same_type_fade_floor_pct
    value = creation_value(rules, 10, 3)
    full = creation_gains(rules, value, 3, 100)
    faded = creation_gains(rules, value, 3, 50)
    assert full[0] > faded[0] > 0
    assert full[1] >= faded[1]
    first = roots("The Crimson Blade of Dawn", 5)
    second = roots("Crimson Blade of Dusk", 5)
    assert similarity(first, second) >= rules.son_tools.repeat_similarity_pct
    assert similarity(first, roots("Quiet River", 5)) == 0


async def test_reward_take_back_is_reversible(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    son = world.son
    son.xp, son.fame = 100, 50
    record_reward(session, RewardDraft(entity_id=world.people.id, son_id=son.id, epoch=1, xp=40, renown=20, essence=0, cost=10))
    await session.flush()
    change = await adjust_reward(session, rules, world.people.id, 50, reason="struck")
    assert change is not None
    assert (son.xp, son.fame) == (80, 40)
    assert await adjust_reward(session, rules, world.people.id, 20, raise_only=True) is None
    await adjust_reward(session, rules, world.people.id, 0)
    assert (son.xp, son.fame) == (100, 50)
