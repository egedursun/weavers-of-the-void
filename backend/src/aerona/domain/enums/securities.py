from enum import StrEnum


class SecurityKind(StrEnum):
    SHARE = "share"
    BOND = "bond"
    ANNUITY = "annuity"
    NOTE = "note"
    FUTURE = "future"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class MoodDirection(StrEnum):
    UP = "up"
    DOWN = "down"


DEBT_KINDS = frozenset({SecurityKind.BOND, SecurityKind.ANNUITY, SecurityKind.NOTE})
