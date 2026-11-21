from enum import StrEnum


class DepartureKind(StrEnum):
    ABDICATION = "abdication"
    RETIREMENT = "retirement"
    RESIGNATION = "resignation"
    WITHDRAWAL_TO_RELIGION = "withdrawal_to_religion"
    EXILE_BY_CHOICE = "exile_by_choice"


class DepartureCondition(StrEnum):
    KEEP_TITLE = "keep_title"
    KEEP_LANDS = "keep_lands"
    PENSION = "pension"
    SAFE_CONDUCT = "safe_conduct"
