from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.military import PeaceTermKind
from aerona.domain.enums.war import CasusBelliKind

K = PeaceTermKind

PEACE_COSTS: MappingProxyType[PeaceTermKind, int] = total(
    PeaceTermKind,
    {
        K.CESSION: 10,
        K.VASSALAGE: 40,
        K.HOSTAGE: 8,
        K.REPARATIONS: 12,
        K.TRIBUTE: 10,
        K.LIBERTY: 15,
        K.THRONE: 35,
        K.BREAK_CULT: 20,
        K.OPEN_TEMPLES: 10,
        K.GOVERNMENT: 30,
        K.MARRIAGE: 5,
        K.DEMILITARISED: 8,
        K.TRADE_CONCESSION: 10,
        K.CAPTIVE_RELEASE: 0,
        K.CHAMPION: 5,
        K.WHITE_PEACE: 0,
    },
)

CASUS_BELLI_LABELS: MappingProxyType[CasusBelliKind, str] = total(
    CasusBelliKind,
    {
        CasusBelliKind.CLAIM: "A claim",
        CasusBelliKind.HOLY_WAR: "Holy war",
        CasusBelliKind.VENDETTA: "Vendetta for killed kin",
        CasusBelliKind.BROKEN_TREATY: "A broken treaty",
        CasusBelliKind.INSULT: "An insult",
        CasusBelliKind.LIBERATION: "Liberation of kin",
        CasusBelliKind.TRADE_DISPUTE: "A trade dispute",
        CasusBelliKind.DEBT_DEFAULT: "A defaulted debt",
        CasusBelliKind.RESOURCE_NEED: "Need of land and food",
        CasusBelliKind.CONQUEST: "Conquest",
    },
)
