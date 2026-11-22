from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.constants.units import PERCENT
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.faith import FanaticismKind, TenetKind
from aerona.domain.enums.modifier import ModifierOp
from aerona.domain.enums.polity import LawKind, TreatyKind
from aerona.rules.registry import Rules

Magnitude = Callable[[Rules], float]


@dataclass(frozen=True)
class StatEffect:
    key: str
    op: ModifierOp
    magnitude: Magnitude


def add(key: str, magnitude: Magnitude) -> StatEffect:
    return StatEffect(key, ModifierOp.ADD, magnitude)


def scale(key: str, magnitude: Magnitude) -> StatEffect:
    return StatEffect(key, ModifierOp.MULTIPLY, magnitude)


LAW_EFFECTS: MappingProxyType[LawKind, tuple[StatEffect, ...]] = MappingProxyType(
    {
        LawKind.STANDING_ARMY: (add("defense", lambda rules: rules.modifiers.law_standing_army_defense),),
        LawKind.SERFDOM: (
            add("prosperity", lambda rules: -rules.modifiers.law_serfdom_prosperity),
            add("wealth", lambda rules: rules.modifiers.law_serfdom_wealth),
        ),
        LawKind.TOLLS: (add("wealth", lambda rules: rules.modifiers.law_tolls_wealth),),
        LawKind.LAND_TENURE: (add("prosperity", lambda rules: rules.modifiers.law_land_tenure_prosperity),),
    }
)

TRADITION_EFFECT_STATS: MappingProxyType[str, str] = MappingProxyType(
    {
        "piety": "piety",
        "martial": "martiality",
        "satisfaction": "prosperity",
        "harvest": "prosperity",
        "cohesion": "defense",
        "hospitality": "wealth",
    }
)

DOCTRINE_EFFECTS: MappingProxyType[TenetKind, tuple[StatEffect, ...]] = MappingProxyType(
    {
        TenetKind.PROSELYTISM: (add("influence", lambda rules: rules.modifiers.doctrine_proselytism_influence),),
        TenetKind.EXCLUSIVITY: (
            add("zeal", lambda rules: rules.modifiers.doctrine_exclusivity_zeal),
            scale("influence", lambda rules: rules.modifiers.doctrine_exclusivity_influence_pct / PERCENT),
        ),
        TenetKind.SYNCRETIC_OPENNESS: (
            add("influence", lambda rules: rules.modifiers.doctrine_syncretic_influence),
            add("zeal", lambda rules: -rules.modifiers.doctrine_syncretic_zeal),
        ),
        TenetKind.HOLY_WAR: (add("zeal", lambda rules: rules.modifiers.doctrine_holy_war_zeal),),
        TenetKind.CELIBATE_CLERGY: (add("zeal", lambda rules: rules.modifiers.doctrine_celibate_zeal),),
    }
)
FANATICISM_EFFECTS: MappingProxyType[FanaticismKind, tuple[StatEffect, ...]] = MappingProxyType(
    {kind: (add("zeal", lambda rules: rules.modifiers.doctrine_fanaticism_zeal),) for kind in FanaticismKind}
)


@dataclass(frozen=True)
class TreatyEffect:
    effect: StatEffect
    obligor_only: bool = False


TREATY_EFFECTS: MappingProxyType[TreatyKind, tuple[TreatyEffect, ...]] = MappingProxyType(
    {
        TreatyKind.PEACE: (TreatyEffect(add("stability", lambda rules: rules.modifiers.treaty_peace_stability)),),
        TreatyKind.TRUCE: (TreatyEffect(add("stability", lambda rules: rules.modifiers.treaty_non_aggression_stability)),),
        TreatyKind.NON_AGGRESSION: (TreatyEffect(add("stability", lambda rules: rules.modifiers.treaty_non_aggression_stability)),),
        TreatyKind.ALLIANCE_DEFENSIVE: (
            TreatyEffect(add("stability", lambda rules: rules.modifiers.treaty_alliance_stability)),
            TreatyEffect(add("legitimacy", lambda rules: rules.modifiers.treaty_alliance_legitimacy)),
            TreatyEffect(add("defense", lambda rules: rules.modifiers.treaty_alliance_stability)),
        ),
        TreatyKind.ALLIANCE_OFFENSIVE: (
            TreatyEffect(add("stability", lambda rules: rules.modifiers.treaty_alliance_stability)),
            TreatyEffect(add("legitimacy", lambda rules: rules.modifiers.treaty_alliance_legitimacy)),
        ),
        TreatyKind.GUARANTEE: (TreatyEffect(add("stability", lambda rules: rules.modifiers.treaty_guarantee_stability)),),
        TreatyKind.MARRIAGE_PACT: (TreatyEffect(add("legitimacy", lambda rules: rules.modifiers.treaty_marriage_legitimacy)),),
        TreatyKind.VASSALAGE: (TreatyEffect(add("legitimacy", lambda rules: -rules.modifiers.treaty_vassal_legitimacy), obligor_only=True),),
        TreatyKind.TRIBUTE: (TreatyEffect(add("stability", lambda rules: -rules.modifiers.treaty_tribute_stability), obligor_only=True),),
        TreatyKind.TRADE_PACT: (TreatyEffect(add("wealth", lambda rules: rules.modifiers.treaty_trade_wealth)),),
        TreatyKind.CONDOTTA: (TreatyEffect(add("defense", lambda rules: rules.modifiers.treaty_alliance_stability)),),
        TreatyKind.INTERWORLD: (TreatyEffect(add("wealth", lambda rules: rules.modifiers.treaty_trade_wealth)),),
        TreatyKind.COALITION: (TreatyEffect(add("defense", lambda rules: rules.modifiers.treaty_alliance_stability)),),
    }
)

LEARNING_KINDS = (EngineKind.LIBRARY, EngineKind.SCHOOL, EngineKind.OBSERVATORY, EngineKind.COSMIC_ARCHIVE)
STRUCTURE_EFFECTS: MappingProxyType[EngineKind, tuple[StatEffect, ...]] = MappingProxyType(
    {
        EngineKind.TEMPLE: (add("piety", lambda rules: rules.modifiers.structure_temple_piety),),
        EngineKind.WALL: (add("defense", lambda rules: rules.modifiers.structure_wall_defense),),
        **{kind: (add("prosperity", lambda rules: rules.modifiers.structure_learning_prosperity),) for kind in LEARNING_KINDS},
    }
)

MORTAL_STAT_KEYS = ("strength", "agility", "intellect", "charisma")
CURSE_KEYS = ("prosperity", "fertility", "abundance", "strength", "wealth")
BLESSING_MORTAL_KEYS = ("strength", "charisma")
BLESSING_COMMUNITY_KEYS = ("prosperity", "piety")
