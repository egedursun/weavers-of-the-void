from aerona.agents.context.chronicle_facts import verdict_ref
from aerona.agents.context.powers import effect_text, unlock_levels, unlocked
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.son import PowerEffect
from aerona.rules.registry import Rules

RULES = Rules()


def power(slot: int, **values: object) -> SonPowerRow:
    return SonPowerRow(son_id=1, slot=slot, name="Gift", description="A gift.", effect=next(iter(PowerEffect)), **values)


def test_each_power_slot_opens_at_its_own_level() -> None:
    first, second, third = unlock_levels(RULES)
    son = SonRow(level=first)
    assert unlocked(RULES, son, power(0))
    assert unlocked(RULES, son, power(1)) is (first >= second)
    son.level = third
    assert unlocked(RULES, son, power(2)) and unlocked(RULES, son, power(9))


def test_a_power_names_the_type_or_stat_it_was_given() -> None:
    plain = effect_text(RULES, power(0))
    typed = effect_text(RULES, power(0, param_entity_type=EntityType.SETTLEMENT))
    assert typed == f"{plain} (chosen type: {ENTITY_TYPES[EntityType.SETTLEMENT].label})"
    assert verdict_ref(7) == "verdict-7"
