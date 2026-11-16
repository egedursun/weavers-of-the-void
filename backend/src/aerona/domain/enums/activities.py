from enum import StrEnum


class ActivityKind(StrEnum):
    WORK = "work"
    REST = "rest"
    WORSHIP = "worship"
    LEARNING = "learning"
    PLAY = "play"
    CARE = "care"
    TRAVEL = "travel"
    ART = "art"


class SatisfactionSource(StrEnum):
    GOODS = "goods"
    ACTIVITY = "activity"
    RELATION = "relation"
    FAITH = "faith"
    ACHIEVEMENT = "achievement"
