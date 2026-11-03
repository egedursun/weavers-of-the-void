from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum


class FlowCategory(StrEnum):
    BIRTH = "birth"
    GROWTH = "growth"
    DEATH = "death"
    CASUALTY = "casualty"
    DISASTER = "disaster"
    FAMINE = "famine"
    PLAGUE = "plague"
    MIGRATION = "migration"
    LEVY = "levy"
    JOURNEY = "journey"
    CAPTIVE = "captive"
    CONVERSION = "conversion"
    MERGE = "merge"
    CREATION = "creation"
    DIVINE = "divine"
    PLAYER = "player"
    UNSPECIFIED = "unspecified"


TRANSFERS = frozenset({FlowCategory.MIGRATION, FlowCategory.LEVY, FlowCategory.JOURNEY, FlowCategory.CAPTIVE, FlowCategory.MERGE})
SOURCES = frozenset({FlowCategory.BIRTH, FlowCategory.GROWTH, FlowCategory.CREATION, FlowCategory.CONVERSION})
SINKS = frozenset({FlowCategory.DEATH, FlowCategory.CASUALTY, FlowCategory.DISASTER, FlowCategory.FAMINE, FlowCategory.PLAGUE})

FLOW_CATEGORY: ContextVar[FlowCategory | None] = ContextVar("flow_category", default=None)


@contextmanager
def flowing(category: FlowCategory) -> Iterator[None]:
    token = FLOW_CATEGORY.set(category)
    try:
        yield
    finally:
        FLOW_CATEGORY.reset(token)


def current_category(phase: str) -> FlowCategory:
    explicit = FLOW_CATEGORY.get()
    if explicit is not None:
        return explicit
    return PHASE_FLOWS.get(phase, FlowCategory.UNSPECIFIED)


C = FlowCategory
PHASE_FLOWS: dict[str, FlowCategory] = {
    "diplomacy": C.LEVY,
    "war_upkeep": C.LEVY,
    "campaigns": C.CASUALTY,
    "war_casualties": C.CASUALTY,
    "travel": C.JOURNEY,
    "exploration": C.MIGRATION,
    "famine_migration": C.MIGRATION,
    "refugees": C.MIGRATION,
    "settlement_cycles": C.MIGRATION,
    "institution_cycles": C.MERGE,
    "schisms": C.MERGE,
    "resource_mechanics": C.DEATH,
    "price_of_magic": C.DEATH,
    "horror": C.DEATH,
    "beyond": C.DEATH,
    "curse_decay": C.DEATH,
    "monster_raids": C.CASUALTY,
    "natural_disasters": C.DISASTER,
    "disaster_casualties": C.DISASTER,
    "spontaneous_births": C.BIRTH,
    "couple_births": C.BIRTH,
    "hero_births": C.BIRTH,
    "population_growth": C.GROWTH,
    "population_baseline": C.GROWTH,
    "religion_spread": C.CONVERSION,
    "world_balance": C.CONVERSION,
    "god_power": C.DIVINE,
    "gods_fate": C.DIVINE,
}
