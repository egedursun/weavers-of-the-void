from enum import StrEnum


class ConditionCause(StrEnum):
    AGE = "age"
    DIET = "diet"
    EXPOSURE = "exposure"
    HEREDITY = "heredity"
    INJURY_AFTERMATH = "injury_aftermath"
    STRAIN = "strain"
    UNKNOWN = "unknown"


class ConditionCourse(StrEnum):
    STABLE = "stable"
    WORSENING = "worsening"
    EPISODIC = "episodic"
