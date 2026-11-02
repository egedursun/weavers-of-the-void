from collections.abc import Callable, Sequence
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.domain.enums.entity import EntityType
from aerona.language.lexicon import LexiconEntry
from aerona.language.titles import community_phrase
from aerona.rules.registry import Rules

UnitRandom = Callable[[], float]


@dataclass(frozen=True)
class DialectPlan:
    name: str
    power: int
    spread: int
    complexity: int
    sacredness: int
    description: str
    note: str
    inherited_words: tuple[LexiconEntry, ...]


def dialect_name(community_name: str) -> str:
    return f"{community_name} Dialect"


def founded_dialect_subtype(parent_name: str, subtype: str | None) -> str:
    base = f"{parent_name} dialect"
    return f"{base}: {subtype}" if subtype else base


def dialect_should_split(settlement_age: int, homeland_size: int, homeland_in_contact: bool, random: UnitRandom, rules: Rules) -> bool:
    if settlement_age < rules.world_effects.dialect_min_settlement_age:
        return False
    if homeland_size == 0 or homeland_in_contact:
        return False
    return random() < rules.world_engine.dialect_split_chance / PERCENT


def shuffled(items: Sequence[LexiconEntry], random: UnitRandom) -> list[LexiconEntry]:
    order = list(items)
    for index in range(len(order) - 1, 0, -1):
        swap = int(random() * (index + 1))
        order[index], order[swap] = order[swap], order[index]
    return order


def plan_engine_dialect(
    parent_name: str,
    community_name: str,
    parent_lexicon: Sequence[LexiconEntry],
    random: UnitRandom,
    rules: Rules,
    *,
    community_type: EntityType = EntityType.SETTLEMENT,
) -> DialectPlan:
    place = community_phrase(community_type, community_name)
    effects = rules.world_effects
    carried = shuffled(parent_lexicon, random)[: effects.dialect_inherited_words]
    inherited = tuple(entry.model_copy(update={"origin": f'from the word "{entry.word}" in the {parent_name} language', "example": ""}) for entry in carried)
    return DialectPlan(
        name=dialect_name(community_name),
        power=effects.dialect_power,
        spread=effects.dialect_spread,
        complexity=effects.dialect_complexity,
        sacredness=effects.dialect_sacredness,
        description=f"The branch of the {parent_name} language that diverged over time {place}, far from its homeland.",
        note=f"The {parent_name} spoken {place} broke from its homeland and began to diverge into a new language.",
        inherited_words=inherited,
    )
