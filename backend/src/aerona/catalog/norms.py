from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.collective import NormBehaviour, NormSituation
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.relations import InteractionKind

B = NormBehaviour
S = NormSituation
V = ValueAxis
K = InteractionKind

BEHAVIOUR_READINGS = total(
    NormBehaviour,
    {
        B.JEST: MappingProxyType({V.LEISURE: 40, V.HIERARCHY: -20, V.TRADITION: -10}),
        B.BOAST: MappingProxyType({V.COMPETITION: 40, V.HONOUR: 20, V.MARTIAL: 15}),
        B.INSULT: MappingProxyType({V.HONOUR: -40, V.MERCY: -15, V.COMPETITION: 15}),
        B.FLATTERY: MappingProxyType({V.HIERARCHY: 35, V.TRUTH: -30}),
        B.FLIRTING: MappingProxyType({V.LEISURE: 20, V.PURITY: -40, V.TRADITION: -15}),
        B.GIFTS: MappingProxyType({V.FRIENDSHIP: 30, V.HONOUR: 15, V.KINSHIP: 10, V.WEALTH: 10}),
        B.QUARRELS: MappingProxyType({V.TRUTH: 15, V.COMPETITION: 15, V.HIERARCHY: -15, V.MERCY: -20}),
        B.BLOWS: MappingProxyType({V.MARTIAL: 30, V.MERCY: -40, V.LAW: -30}),
        B.WEAPONS_CARRIED: MappingProxyType({V.MARTIAL: 45, V.HONOUR: 10, V.LAW: -20}),
        B.FINE_DRESS: MappingProxyType({V.WEALTH: 40, V.HIERARCHY: 20, V.PURITY: -10}),
        B.PLAIN_SPEECH: MappingProxyType({V.TRUTH: 45, V.HIERARCHY: -25}),
        B.FORBIDDEN_FOOD: MappingProxyType({V.PURITY: -50, V.PIETY: -30, V.TRADITION: -20}),
        B.SECRETS: MappingProxyType({V.FRIENDSHIP: 10, V.TRUTH: 10, V.LOYALTY: -30}),
    },
)
SOLEMN = MappingProxyType({B.JEST: -35, B.FLIRTING: -35, B.QUARRELS: -30, B.BLOWS: -40, B.INSULT: -30, B.BOAST: -20})
FESTIVE = MappingProxyType({B.JEST: 25, B.BOAST: 20, B.GIFTS: 25, B.FLIRTING: 20, B.FINE_DRESS: 20})
SITUATION_SHIFTS = total(
    NormSituation,
    {
        S.FUNERAL: (SOLEMN, V.DEATH),
        S.MOURNING: (SOLEMN, V.FAMILY),
        S.TEMPLE: (MappingProxyType({**SOLEMN, B.FORBIDDEN_FOOD: -30, B.WEAPONS_CARRIED: -25}), V.PIETY),
        S.SACRED_DAY: (MappingProxyType({**SOLEMN, B.FORBIDDEN_FOOD: -40, B.GIFTS: 15}), V.PIETY),
        S.COURT: (MappingProxyType({B.PLAIN_SPEECH: -25, B.FLATTERY: 25, B.FINE_DRESS: 25, B.JEST: -15, B.BLOWS: -45, B.INSULT: -35}), V.HIERARCHY),
        S.SUPERIOR: (MappingProxyType({B.PLAIN_SPEECH: -20, B.FLATTERY: 25, B.INSULT: -40, B.JEST: -15, B.QUARRELS: -25}), V.HIERARCHY),
        S.FEAST: (FESTIVE, V.LEISURE),
        S.WEDDING: (MappingProxyType({**FESTIVE, B.BLOWS: -30, B.INSULT: -25}), V.FAMILY),
        S.MARKET: (MappingProxyType({B.FLATTERY: 10, B.QUARRELS: 10, B.FINE_DRESS: 10, B.PLAIN_SPEECH: 10}), V.WEALTH),
        S.BATTLE: (MappingProxyType({B.BLOWS: 60, B.WEAPONS_CARRIED: 60, B.BOAST: 20, B.JEST: -10}), V.MARTIAL),
        S.DUEL: (MappingProxyType({B.BLOWS: 40, B.WEAPONS_CARRIED: 40, B.INSULT: 10, B.JEST: -20}), V.HONOUR),
        S.HOSPITALITY: (MappingProxyType({B.GIFTS: 30, B.INSULT: -40, B.BLOWS: -50, B.WEAPONS_CARRIED: -30, B.QUARRELS: -25}), V.KINSHIP),
        S.STRANGER: (MappingProxyType({B.GIFTS: 15, B.SECRETS: -30, B.WEAPONS_CARRIED: 15, B.JEST: -10}), V.XENOPHILIA),
    },
)
INTERACTION_BEHAVIOUR = MappingProxyType(
    {
        K.JOKE: B.JEST,
        K.BOAST: B.BOAST,
        K.INSULT: B.INSULT,
        K.FLATTER: B.FLATTERY,
        K.FLIRT: B.FLIRTING,
        K.COURT: B.FLIRTING,
        K.SEDUCE: B.FLIRTING,
        K.GIFT: B.GIFTS,
        K.QUARREL: B.QUARRELS,
        K.ARGUE: B.QUARRELS,
        K.BRAWL: B.BLOWS,
        K.THREATEN: B.BLOWS,
        K.GOSSIP: B.SECRETS,
        K.CONFIDE_SECRET: B.SECRETS,
    }
)
GATHERING_SITUATIONS = MappingProxyType(
    {
        CollectionKind.FEAST: S.FEAST,
        CollectionKind.WEDDING: S.WEDDING,
        CollectionKind.FUNERAL: S.FUNERAL,
        CollectionKind.COUNCIL: S.COURT,
        CollectionKind.CORONATION: S.COURT,
        CollectionKind.CEREMONY: S.SACRED_DAY,
        CollectionKind.PROCESSION: S.SACRED_DAY,
        CollectionKind.PILGRIMAGE: S.TEMPLE,
        CollectionKind.BATTLE: S.BATTLE,
        CollectionKind.SIEGE: S.BATTLE,
        CollectionKind.DUEL: S.DUEL,
        CollectionKind.SUMMIT: S.HOSPITALITY,
    }
)
