from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.war import WarCause


@dataclass(frozen=True)
class WarCauseSpec:
    over_faith: bool = False
    over_trade: bool = False
    within_realm: bool = False


C = WarCause
WAR_CAUSES: Mapping[WarCause, WarCauseSpec] = total(
    WarCause,
    {
        C.HOSTILITY: WarCauseSpec(),
        C.UPRISING: WarCauseSpec(within_realm=True),
        C.TRIBUTE_REVOLT: WarCauseSpec(within_realm=True),
        C.INCITED: WarCauseSpec(),
        C.DECLARED: WarCauseSpec(),
        C.BETRAYAL: WarCauseSpec(),
        C.CONQUEST_JOURNEY: WarCauseSpec(),
        C.FOREIGN_GOD: WarCauseSpec(),
        C.INDEPENDENCE: WarCauseSpec(within_realm=True),
        C.VENDETTA: WarCauseSpec(),
        C.GRUDGE: WarCauseSpec(),
        C.DIVINE_GRUDGE: WarCauseSpec(over_faith=True),
        C.RIVALRY: WarCauseSpec(),
        C.DEBT: WarCauseSpec(over_trade=True),
        C.ESPIONAGE: WarCauseSpec(),
        C.SABOTAGE: WarCauseSpec(),
        C.ENVY: WarCauseSpec(),
        C.SCHISM: WarCauseSpec(over_faith=True),
        C.BEAST: WarCauseSpec(),
        C.RESOURCE: WarCauseSpec(over_trade=True),
        C.IDEOLOGY: WarCauseSpec(),
        C.TRADE_ROUTE: WarCauseSpec(over_trade=True),
        C.CLAIM: WarCauseSpec(within_realm=True),
        C.HOLY_WAR: WarCauseSpec(over_faith=True),
        C.SUCCESSION: WarCauseSpec(within_realm=True),
        C.RAID: WarCauseSpec(),
        C.LIBERATION: WarCauseSpec(),
        C.PUNITIVE: WarCauseSpec(),
    },
)
