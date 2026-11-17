from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.law_grammar import LawCondition, LawOperator, LawTarget
from aerona.domain.enums.society import NaturalLaw

NEUTRAL = 100
T = LawTarget
Op = LawOperator


@dataclass(frozen=True)
class Grammar:
    target: LawTarget
    operator: LawOperator
    key: str
    value: int = NEUTRAL


LEGACY_GRAMMAR: Mapping[NaturalLaw, Grammar | None] = total(
    NaturalLaw,
    {
        NaturalLaw.NONE: None,
        NaturalLaw.IMMORTALITY: Grammar(T.LIFE, Op.SET, "aging", 0),
        NaturalLaw.SHORT_LIFE: Grammar(T.LIFE, Op.MULTIPLY, "aging", 200),
        NaturalLaw.DEAD_RETURN: Grammar(T.DEATH, Op.INVERT, "return"),
        NaturalLaw.MAGIC_PRICE: Grammar(T.MAGIC, Op.REQUIRE, "price"),
        NaturalLaw.WAR_BAN: Grammar(T.WAR, Op.FORBID, "war", 0),
        NaturalLaw.BOUNTY: Grammar(T.HARVEST, Op.MULTIPLY, "harvest", 150),
        NaturalLaw.DROUGHT: Grammar(T.HARVEST, Op.MULTIPLY, "harvest", 50),
        NaturalLaw.SEA_BAN: Grammar(T.TRAVEL, Op.FORBID, "sea", 0),
        NaturalLaw.ONE_LANGUAGE: Grammar(T.LANGUAGE, Op.SET, "tongues", 1),
        NaturalLaw.DISASTERS: Grammar(T.DISASTER, Op.MULTIPLY, "disaster", 200),
        NaturalLaw.SOULS_REINCARNATE: Grammar(T.DEATH, Op.SET, "rebirth"),
        NaturalLaw.GIFT_FLOWERING: Grammar(T.MAGIC, Op.MULTIPLY, "gift", 150),
        NaturalLaw.GIFT_WITHERING: Grammar(T.MAGIC, Op.MULTIPLY, "gift", 50),
        NaturalLaw.NO_IRON: Grammar(T.MATERIAL, Op.FORBID, "iron", 0),
        NaturalLaw.ETERNAL_NIGHT: Grammar(T.LIGHT, Op.SET, "light", 0),
        NaturalLaw.MAGIC_REQUIRES_BLOOD: Grammar(T.MAGIC, Op.REQUIRE, "blood"),
        NaturalLaw.GRAVITY_SHIFT: Grammar(T.WEIGHT, Op.MULTIPLY, "weight", 150),
        NaturalLaw.SEASONS_REVERSED: Grammar(T.SEASON, Op.INVERT, "seasons"),
        NaturalLaw.LONG_SEASONS: Grammar(T.SEASON, Op.MULTIPLY, "season_length", 200),
        NaturalLaw.DREAMS_ARE_REAL: Grammar(T.DREAMS, Op.SET, "dreams"),
        NaturalLaw.OATHS_BIND: Grammar(T.OATHS, Op.REQUIRE, "oaths"),
        NaturalLaw.THE_DEAD_SPEAK: Grammar(T.DEATH, Op.SET, "speech"),
        NaturalLaw.METAL_RUSTS_FAST: Grammar(T.MATERIAL, Op.MULTIPLY, "metal_decay", 300),
        NaturalLaw.NO_GUNPOWDER: Grammar(T.MATERIAL, Op.FORBID, "gunpowder", 0),
    },
)


def direction(operator: LawOperator, value: int) -> int:
    if operator is LawOperator.MULTIPLY:
        return (value > NEUTRAL) - (value < NEUTRAL)
    return 0


def preset_of(target: LawTarget | None, operator: LawOperator | None, key: str | None, value: int) -> NaturalLaw | None:
    if target is None or operator is None or key is None:
        return None
    for law, grammar in LEGACY_GRAMMAR.items():
        if grammar is None or (grammar.target, grammar.operator, grammar.key) != (target, operator, key):
            continue
        if direction(operator, value) == direction(grammar.operator, grammar.value):
            return law
    return None


PRESET_TARGETS = frozenset(grammar.target for grammar in LEGACY_GRAMMAR.values() if grammar is not None)


@dataclass(frozen=True)
class RowTarget:
    table: str
    holder: str
    fields: tuple[str, ...]
    low: int = 0
    high: int = 100


ROW_TARGETS: Mapping[LawTarget, RowTarget | None] = total(
    LawTarget,
    {
        T.STAT: None,
        T.LIFE: None,
        T.DEATH: None,
        T.MAGIC: None,
        T.WAR: None,
        T.HARVEST: None,
        T.TRAVEL: None,
        T.LANGUAGE: None,
        T.DISASTER: None,
        T.MATERIAL: None,
        T.LIGHT: None,
        T.WEIGHT: None,
        T.SEASON: None,
        T.DREAMS: None,
        T.OATHS: None,
        T.MADE_MINDS: RowTarget("mind_profiles", "node_id", ("stability", "fidelity_pct", "maker_bond", "drift_pct")),
        T.COPIES: RowTarget("mind_states", "mind_node_id", ("fidelity_pct",)),
        T.POWERS: RowTarget("powers", "holder_node_id", ("strength", "control")),
        T.SOURCES: RowTarget("power_sources", "scope_node_id", ("stability",)),
        T.CONCEALMENT: RowTarget("hidden_truths", "subject_node_id", ("strength",)),
        T.LIVING_CRAFT: RowTarget("living_lines", "owner_node_id", ("stability", "drift_pct")),
        T.REALMS: RowTarget("made_realm_profiles", "host_node_id", ("fidelity",)),
    },
)
CONDITION_TEXT: Mapping[LawCondition, str] = total(
    LawCondition,
    {
        LawCondition.ALWAYS: "always",
        LawCondition.AT_WAR: "while its peoples are at war",
        LawCondition.AT_PEACE: "while its peoples are at peace",
        LawCondition.COLD_SEASON: "in the cold season",
        LawCondition.DOOM_RISING: "while the doom clock stands past half",
        LawCondition.AUTHOR_WORSHIPPED: "where its author is worshipped",
        LawCondition.AUTHOR_FORGOTTEN: "where its author is not worshipped",
    },
)
OPERATOR_TEXT: Mapping[LawOperator, str] = total(
    LawOperator,
    {
        Op.FORBID: "forbids",
        Op.REQUIRE: "requires at least",
        Op.MULTIPLY: "multiplies",
        Op.SET: "sets",
        Op.INVERT: "inverts",
        Op.BIND_TO_CONDITION: "binds to its condition",
    },
)


def working_text(grammar: Grammar | None, condition: LawCondition) -> str:
    if grammar is None:
        return ""
    return f"It {OPERATOR_TEXT[grammar.operator]} {grammar.key.replace('_', ' ')} at {grammar.value:d}, {CONDITION_TEXT[condition]}."
