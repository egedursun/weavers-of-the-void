from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.aspirations import PERKS
from aerona.catalog.modifier_effects import (
    BLESSING_COMMUNITY_KEYS,
    BLESSING_MORTAL_KEYS,
    CURSE_KEYS,
    DOCTRINE_EFFECTS,
    FANATICISM_EFFECTS,
    LAW_EFFECTS,
    MORTAL_STAT_KEYS,
    STRUCTURE_EFFECTS,
    TERRAIN_EFFECTS,
    TRADITION_EFFECT_STATS,
    TREATY_EFFECTS,
)
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
        S.PERK: Subsystem.MIND,
        S.COSMOS: Subsystem.COSMOS,
        S.RIFT: Subsystem.COSMOS,
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
        "modifier.condition.nightmares": "nights of the same nightmare wear down their will",
    }
)


REASON_FAMILIES: MappingProxyType[str, str] = MappingProxyType(
    {
        "modifier.injury": "wounds and the state of their body",
        "perk": "the perk of {kind} their mastery earned",
        "modifier.trait": "their temperament",
        "modifier.law": "the {kind} law {source} binds them",
        "modifier.tradition": "the {kind} of {source} they keep",
        "modifier.artwork": "the fame of {source}",
        "modifier.doctrine": "their faith's tenet of {kind}",
        "modifier.fanaticism": "a fanatic fervour ({kind})",
        "modifier.treaty": "the {kind} of {source}",
        "modifier.structure": "the {kind} {source} stands for them",
        "modifier.curse": "a curse laid by {source}",
        "modifier.blessing": "a blessing from {source}",
        "modifier.god_power": "{source}'s gift ({kind})",
        "modifier.god_death": "the corpse of a god, {source}, lies here",
        "modifier.phenomenon": "the {kind} {source} that broke here",
        "modifier.terrain": "the {kind} ground they live on",
        "modifier.season": "the harshness of the seasons",
        "modifier.weather": "{kind} weather this epoch",
        "modifier.natural_law": "the natural law of {kind}",
    }
)


def reason_text(key: str, source: str | None = None) -> str:
    if key in REASONS:
        return REASONS[key].format(source=source or "it")
    family = next((name for name in sorted(REASON_FAMILIES, key=len, reverse=True) if key == name or key.startswith(f"{name}.")), None)
    if family is None:
        return key.replace(".", " ").replace("_", " ")
    kind = key.removeprefix(family).strip(".").replace("_", " ")
    return REASON_FAMILIES[family].format(source=source or "it", kind=kind or "it")


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
        ConditionKind.NIGHTMARES: (DerivedEffect("willpower", ModifierOp.ADD, lambda rules: -rules.modifiers.nightmares_willpower),),
    }
)
DERIVED_SOURCES = frozenset({ModifierSource.WONDER, ModifierSource.CONDITION})
SOURCE_KEYS: MappingProxyType[ModifierSource, frozenset[str]] = MappingProxyType(
    {
        S.INJURY: frozenset(MORTAL_STAT_KEYS),
        S.TRAIT: frozenset(MORTAL_STAT_KEYS),
        S.LAW: frozenset(effect.key for effects in LAW_EFFECTS.values() for effect in effects),
        S.TRADITION: frozenset(TRADITION_EFFECT_STATS.values()),
        S.ARTWORK: frozenset({"prosperity"}),
        S.DOCTRINE: frozenset(effect.key for table in (DOCTRINE_EFFECTS, FANATICISM_EFFECTS) for effects in table.values() for effect in effects),
        S.TREATY: frozenset(item.effect.key for items in TREATY_EFFECTS.values() for item in items),
        S.STRUCTURE: frozenset(effect.key for effects in STRUCTURE_EFFECTS.values() for effect in effects),
        S.CURSE: frozenset(CURSE_KEYS),
        S.BLESSING: frozenset((*BLESSING_MORTAL_KEYS, *BLESSING_COMMUNITY_KEYS)),
        S.GOD_POWER: frozenset({"growth"}),
        S.GOD_DEATH: frozenset({"magic", "fertility"}),
        S.PHENOMENON: frozenset({"magic", "prosperity"}),
        S.TERRAIN: frozenset(effect.key for effects in TERRAIN_EFFECTS.values() for effect in effects),
        S.SEASON: frozenset({"prosperity"}),
        S.WEATHER: frozenset({"prosperity", "morale"}),
        S.NATURAL_LAW: frozenset({"fertility"}),
        S.PERK: frozenset(spec.stat for spec in PERKS.values()),
    }
)
SOURCE_WRITERS: MappingProxyType[ModifierSource, str] = MappingProxyType(
    {
        **{source: "modifier_upkeep" for source in SOURCE_KEYS},
        S.TERRAIN: "environment_modifiers",
        S.SEASON: "environment_modifiers",
        S.WEATHER: "environment_modifiers",
        S.NATURAL_LAW: "natural_law_fertility",
        S.PERK: "aspirations",
    }
)
