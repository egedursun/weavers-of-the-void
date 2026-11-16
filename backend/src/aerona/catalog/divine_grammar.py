from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.divine import DivineMode, DivineObject, DivineScope, DivineVerb
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.son import PowerEffect

V = DivineVerb
T = DivineObject
S = DivineScope
M = DivineMode
P = PowerEffect
F = ForeignGodPowerEffect

VERB_SIGN: Mapping[DivineVerb, int] = total(
    DivineVerb,
    {
        V.GRANT: 1,
        V.BLESS: 1,
        V.CURSE: -1,
        V.CREATE: 1,
        V.DESTROY: -1,
        V.SHAPE: 1,
        V.REVEAL: -1,
        V.CONCEAL: 1,
        V.SUMMON: 1,
        V.BIND: -1,
        V.FREE: 1,
        V.HEAL: 1,
        V.HARM: -1,
        V.RAISE: 1,
        V.INSPIRE: 1,
        V.TERRIFY: -1,
        V.PROTECT: 1,
        V.GUIDE: 1,
        V.JUDGE: -1,
        V.TRANSFORM: 1,
        V.FORESEE: 1,
        V.HASTEN: 1,
        V.SLOW: -1,
        V.MULTIPLY: 2,
        V.STILL: -1,
        V.WAKE: 1,
        V.REMEMBER: 1,
        V.ERASE: -2,
    },
)
SCOPE_RANK: Mapping[DivineScope, int] = total(
    DivineScope,
    {S.PERSON: 0, S.COMMUNITY: 1, S.REGION: 2, S.WORLD: 3, S.SYSTEM: 4, S.DIMENSION: 5},
)


@dataclass(frozen=True)
class Grammar:
    verb: DivineVerb
    object: DivineObject
    key: str | None
    scope: DivineScope
    mode: DivineMode


SON_PRESETS: Mapping[PowerEffect, Grammar] = total(
    PowerEffect,
    {
        P.CHEAP_CREATION: Grammar(V.CREATE, T.STRUCTURE, None, S.WORLD, M.PASSIVE),
        P.DUEL_MASTER: Grammar(V.HARM, T.STAT, "hp", S.PERSON, M.TRIGGERED),
        P.ESSENCE_SPRING: Grammar(V.MULTIPLY, T.SOURCE, None, S.WORLD, M.PASSIVE),
        P.WORSHIPPED: Grammar(V.INSPIRE, T.VALUE, "piety", S.COMMUNITY, M.PASSIVE),
        P.TIRELESS: Grammar(V.HASTEN, T.STAT, "willpower", S.PERSON, M.PASSIVE),
        P.UNTOUCHABLE: Grammar(V.PROTECT, T.STAT, "hp", S.PERSON, M.TRIGGERED),
        P.DREAM_SENDING: Grammar(V.GUIDE, T.MIND, None, S.COMMUNITY, M.ACTIVE),
        P.WAR_LEADER: Grammar(V.INSPIRE, T.STAT, "strength", S.COMMUNITY, M.TRIGGERED),
        P.HARVESTER: Grammar(V.MULTIPLY, T.COMMODITY, "grain", S.COMMUNITY, M.PASSIVE),
        P.SEER: Grammar(V.FORESEE, T.TRUTH, None, S.WORLD, M.ACTIVE),
        P.REVIVING: Grammar(V.RAISE, T.STAT, "hp", S.PERSON, M.TRIGGERED),
        P.BOUNTY_GIVER: Grammar(V.BLESS, T.STAT, "prosperity", S.COMMUNITY, M.PASSIVE),
        P.CURSER: Grammar(V.CURSE, T.STAT, "prosperity", S.COMMUNITY, M.ACTIVE),
    },
)
FOREIGN_PRESETS: Mapping[ForeignGodPowerEffect, Grammar] = total(
    ForeignGodPowerEffect,
    {
        F.SHIELD: Grammar(V.PROTECT, T.STAT, "defense", S.COMMUNITY, M.PASSIVE),
        F.CALLER: Grammar(V.SUMMON, T.SPECIES, None, S.REGION, M.ACTIVE),
        F.THIEF: Grammar(V.ERASE, T.MEMORY, None, S.COMMUNITY, M.ACTIVE),
        F.DESTROYER: Grammar(V.DESTROY, T.STRUCTURE, None, S.COMMUNITY, M.ACTIVE),
        F.FERTILE: Grammar(V.MULTIPLY, T.STAT, "population", S.COMMUNITY, M.PASSIVE),
        F.REVIVING: Grammar(V.RAISE, T.STAT, "hp", S.PERSON, M.TRIGGERED),
        F.DEATHLESS: Grammar(V.PROTECT, T.STAT, "hp", S.PERSON, M.PASSIVE),
        F.PERSUASION: Grammar(V.GUIDE, T.VALUE, "loyalty", S.PERSON, M.ACTIVE),
    },
)
