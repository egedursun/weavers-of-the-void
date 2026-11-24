from types import MappingProxyType

from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.war import WarCause

CURSE_RULES = {
    CurseKind.BLOODTHIRST: "item_curses.bloodthirst_pct",
    CurseKind.MISFORTUNE: "item_curses.misfortune_pct",
    CurseKind.WASTING: "item_curses.wasting_pct",
    CurseKind.MADNESS: "item_curses.madness_pct",
    CurseKind.BETRAYAL: "item_curses.betrayal_pct",
    **dict.fromkeys(
        (
            CurseKind.BARRENNESS,
            CurseKind.TRANSFORMATION,
            CurseKind.SLEEP,
            CurseKind.SILENCE,
            CurseKind.FORGETTING,
            CurseKind.RESTLESSNESS,
            CurseKind.LINE_CURSE,
            CurseKind.PLACE_CURSE,
            CurseKind.COMPULSION,
            CurseKind.EXPOSURE,
            CurseKind.ISOLATION,
            CurseKind.WEAKNESS,
        ),
        "item_curses.wider_pct",
    ),
    CurseKind.HUNGER: "item_curses.wasting_pct",
    CurseKind.AGING: "item_curses.aging_years",
}


WAR_CAUSE_INCIDENTS: MappingProxyType[WarCause, tuple[str, ...]] = MappingProxyType(
    {
        WarCause.VENDETTA: ("vendetta.", "memory.vengeance", "mortal.death.cause"),
        WarCause.GRUDGE: ("grudges.",),
        WarCause.DIVINE_GRUDGE: ("grudges.holy_war", "grudges."),
        WarCause.BETRAYAL: ("treaty.broken",),
        WarCause.DEBT: ("civilization.debt_late", "civilization.loan"),
        WarCause.INDEPENDENCE: ("civilization.independence", "polity.secession"),
        WarCause.UPRISING: ("polity.succession_war", "polity.usurped", "war.uprising"),
        WarCause.TRIBUTE_REVOLT: ("war.ended_tribute", "tribute"),
        WarCause.RESOURCE: ("resource_conflict", "trade.seize_resource"),
        WarCause.TRADE_ROUTE: ("trade_route.",),
        WarCause.INCITED: ("tools.son.incite",),
        WarCause.SCHISM: ("faith.", "schism"),
        WarCause.ESPIONAGE: ("espionage.",),
        WarCause.SABOTAGE: ("espionage.", "sabotage"),
    }
)
