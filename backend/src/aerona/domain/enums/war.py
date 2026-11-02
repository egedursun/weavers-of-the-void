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


class SiegeStatus(StrEnum):
    ONGOING = "ongoing"
    BREACHED = "breached"
    REPULSED = "repulsed"
    LIFTED = "lifted"


class BattleOutcome(StrEnum):
    FIELD_VICTORY = "field_victory"
    GREAT_VICTORY = "great_victory"
    SIEGE_REPULSED = "siege_repulsed"
    SIEGE_BREACHED = "siege_breached"
    SIEGE_STARVATION = "siege_starvation"


class CaptiveStatus(StrEnum):
    HELD = "held"
    RANSOMED = "ransomed"
    ESCAPED = "escaped"
    EXECUTED = "executed"
    TURNCOAT = "turncoat"
    RESCUED = "rescued"
    RELEASED = "released"


class TributeStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    REVOLTED = "revolted"


class DebtStatus(StrEnum):
    OPEN = "open"
    OVERDUE = "overdue"
    REPAID = "repaid"
    FORGIVEN = "forgiven"


class HeroQuestKind(StrEnum):
    HUNT = "hunt"
    THREAD = "thread"
    RELIC = "relic"
    KNOWLEDGE = "knowledge"
    VENGEANCE = "vengeance"


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
