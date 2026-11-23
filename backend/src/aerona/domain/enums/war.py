from enum import StrEnum


class WarStatus(StrEnum):
    MOBILIZING = "mobilizing"
    ONGOING = "ongoing"
    ENDED = "ended"


class WarEnding(StrEnum):
    VICTORY = "victory"
    CONQUEST = "conquest"
    TRIBUTE = "tribute"
    EXHAUSTION = "exhaustion"
    PEACE = "peace"
    WHITE_PEACE = "white_peace"
    BETRAYAL = "betrayal"
    SAME_FRONT = "same_front"
    NO_SIDE_LEFT = "no_side_left"
    MIRACLE = "miracle"


class WarSide(StrEnum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


class CasusBelliKind(StrEnum):
    CLAIM = "claim"
    HOLY_WAR = "holy_war"
    VENDETTA = "vendetta"
    BROKEN_TREATY = "broken_treaty"
    INSULT = "insult"
    LIBERATION = "liberation"
    TRADE_DISPUTE = "trade_dispute"
    DEBT_DEFAULT = "debt_default"
    RESOURCE_NEED = "resource_need"
    CONQUEST = "conquest"


class WarCause(StrEnum):
    HOSTILITY = "hostility"
    UPRISING = "uprising"
    TRIBUTE_REVOLT = "tribute_revolt"
    INCITED = "incited"
    DECLARED = "declared"
    BETRAYAL = "betrayal"
    CONQUEST_JOURNEY = "conquest_journey"
    FOREIGN_GOD = "foreign_god"
    INDEPENDENCE = "independence"
    VENDETTA = "vendetta"
    GRUDGE = "grudge"
    DIVINE_GRUDGE = "divine_grudge"
    RIVALRY = "rivalry"
    DEBT = "debt"
    ESPIONAGE = "espionage"
    SABOTAGE = "sabotage"
    ENVY = "envy"
    SCHISM = "schism"
    BEAST = "beast"
    RESOURCE = "resource"
    IDEOLOGY = "ideology"
    TRADE_ROUTE = "trade_route"
    CLAIM = "claim"
    HOLY_WAR = "holy_war"
    SUCCESSION = "succession"
    RAID = "raid"
    LIBERATION = "liberation"
    PUNITIVE = "punitive"


class SiegeStatus(StrEnum):
    ONGOING = "ongoing"
    BREACHED = "breached"
    REPULSED = "repulsed"
    LIFTED = "lifted"
    SURRENDERED = "surrendered"


class BattleOutcome(StrEnum):
    FIELD_VICTORY = "field_victory"
    GREAT_VICTORY = "great_victory"
    SIEGE_REPULSED = "siege_repulsed"
    SIEGE_BREACHED = "siege_breached"
    SIEGE_STARVATION = "siege_starvation"
    REFUSED = "refused"


class CaptiveStatus(StrEnum):
    HELD = "held"
    RANSOMED = "ransomed"
    ESCAPED = "escaped"
    EXECUTED = "executed"
    TURNCOAT = "turncoat"
    RESCUED = "rescued"
    RELEASED = "released"
    WARD = "ward"
    PAROLED = "paroled"
    MARRIED_IN = "married_in"


class TributeStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    REVOLTED = "revolted"


class DebtStatus(StrEnum):
    OPEN = "open"
    OVERDUE = "overdue"
    REPAID = "repaid"
    FORGIVEN = "forgiven"


class HeroQuestStatus(StrEnum):
    ACTIVE = "active"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DIED = "died"
    ABANDONED = "abandoned"


class GodConflictOutcome(StrEnum):
    ATTACKER_WON = "attacker_won"
    DEFENDER_WON = "defender_won"
    DRAW = "draw"
