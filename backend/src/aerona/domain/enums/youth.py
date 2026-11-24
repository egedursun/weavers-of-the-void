from enum import StrEnum


class YouthPlace(StrEnum):
    YOUTH_HOUSE = "youth_house"
    HOUSEHOLD = "household"
    SCHOOL = "school"
    SERVICE = "service"
    APPRENTICESHIP = "apprenticeship"
    WANDERING = "wandering"


class YouthPurpose(StrEnum):
    SPORT = "sport"
    SERVICE = "service"
    COURTSHIP = "courtship"
    DEFENCE = "defence"
    FAITH = "faith"
    MISCHIEF = "mischief"
    CRIME = "crime"
    POLITICS = "politics"
    LEARNING = "learning"
    LABOUR = "labour"


class YouthMeasure(StrEnum):
    SCHOOLING = "schooling"
    SERVICE = "service"
    SPORT = "sport"
    DISCIPLINE = "discipline"
