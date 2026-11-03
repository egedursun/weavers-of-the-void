from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.interconnect.registry import Subsystem
from aerona.rules.registry import Rules

S = ModifierSource

SOURCE_SUBSYSTEMS: MappingProxyType[ModifierSource, Subsystem] = MappingProxyType(
    {
        S.INJURY: Subsystem.BODY,
        S.CONDITION: Subsystem.BODY,
        S.TRAIT: Subsystem.MIND,
        S.LAW: Subsystem.LAW,
        S.TRADITION: Subsystem.CULTURE,
        S.ARTWORK: Subsystem.CULTURE,
        S.DOCTRINE: Subsystem.FAITH,
        S.TREATY: Subsystem.POLITY,
        S.STRUCTURE: Subsystem.ECONOMY,
        S.WONDER: Subsystem.CULTURE,
        S.TERRAIN: Subsystem.ENVIRONMENT,
        S.WEATHER: Subsystem.ENVIRONMENT,
        S.SEASON: Subsystem.ENVIRONMENT,
        S.NATURAL_LAW: Subsystem.COSMOS,
        S.GOD_POWER: Subsystem.GODS,
        S.BLESSING: Subsystem.GODS,
        S.CURSE: Subsystem.GODS,
        S.DOMINION: Subsystem.GODS,
        S.PHENOMENON: Subsystem.COSMOS,
        S.GOD_DEATH: Subsystem.GODS,
        S.PLAYER: Subsystem.CORE,
        S.SUPPRESSION: Subsystem.CORE,
        S.PIN: Subsystem.CORE,
    }
)

REASONS: MappingProxyType[str, str] = MappingProxyType(
    {
        "player.modifier": "set by your hand",
        "player.pin": "held by your hand",
        "player.suppression": "a mechanic you stopped",
        "modifier.wonder": "the wonder {source} draws pilgrims, trade and pride",
        "modifier.blessing": "a blessing",
        "modifier.curse": "a curse",
        "modifier.condition.chronic_illness": "a lingering illness saps their strength",
        "modifier.condition.withered_limb": "a withered limb weakens them",
        "modifier.condition.melancholy": "melancholy dulls their mind",
        "modifier.condition.rage": "fits of rage make them dangerous and unwise",
        "modifier.condition.paranoia": "paranoia clouds their judgement",
        "modifier.condition.endless_hunger": "an endless hunger gnaws at them",
        "modifier.condition.void_taint": "the taint of the void unsettles everyone near them",
        "modifier.condition.chosen_mark": "the mark of the chosen awes those who see it",
        "modifier.condition.divine_brand": "a god's brand marks them for all to see",
    }
)


def reason_text(key: str, source: str | None = None) -> str:
    template = REASONS.get(key, key.replace(".", " ").replace("_", " "))
    return template.format(source=source or "it")


@dataclass(frozen=True)
class DerivedEffect:
    key: str
    op: ModifierOp
    magnitude: Callable[[Rules], float]


CONDITION_EFFECTS: MappingProxyType[ConditionKind, tuple[DerivedEffect, ...]] = MappingProxyType(
    {
        ConditionKind.CHRONIC_ILLNESS: (
            DerivedEffect("strength", ModifierOp.MULTIPLY, lambda rules: rules.modifiers.illness_strength_pct / 100),
            DerivedEffect("agility", ModifierOp.MULTIPLY, lambda rules: rules.modifiers.illness_strength_pct / 100),
        ),
        ConditionKind.WITHERED_LIMB: (DerivedEffect("strength", ModifierOp.MULTIPLY, lambda rules: rules.modifiers.withered_strength_pct / 100),),
        ConditionKind.MELANCHOLY: (DerivedEffect("intellect", ModifierOp.ADD, lambda rules: -rules.modifiers.melancholy_intellect),),
        ConditionKind.RAGE: (
            DerivedEffect("strength", ModifierOp.ADD, lambda rules: rules.modifiers.rage_strength),
            DerivedEffect("intellect", ModifierOp.ADD, lambda rules: -rules.modifiers.rage_intellect),
        ),
        ConditionKind.PARANOIA: (DerivedEffect("charisma", ModifierOp.ADD, lambda rules: -rules.modifiers.paranoia_charisma),),
        ConditionKind.ENDLESS_HUNGER: (DerivedEffect("charisma", ModifierOp.ADD, lambda rules: -rules.modifiers.hunger_charisma),),
        ConditionKind.VOID_TAINT: (DerivedEffect("charisma", ModifierOp.ADD, lambda rules: -rules.modifiers.void_taint_charisma),),
        ConditionKind.CHOSEN_MARK: (DerivedEffect("charisma", ModifierOp.ADD, lambda rules: rules.modifiers.chosen_charisma),),
        ConditionKind.DIVINE_BRAND: (DerivedEffect("charisma", ModifierOp.ADD, lambda rules: rules.modifiers.brand_charisma),),
    }
)
DERIVED_SOURCES = frozenset({ModifierSource.WONDER, ModifierSource.CONDITION})
