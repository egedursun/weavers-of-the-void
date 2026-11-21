from enum import StrEnum


class CultInstrument(StrEnum):
    IMAGES_IN_PUBLIC = "images_in_public"
    OFFICIAL_BIOGRAPHY = "official_biography"
    HOLIDAYS = "holidays"
    OATHS_OF_LOYALTY = "oaths_of_loyalty"
    NAMING_OF_PLACES = "naming_of_places"
    TEACHING_IN_SCHOOLS = "teaching_in_schools"
    STAGED_GATHERINGS = "staged_gatherings"
    BAN_ON_CRITICISM = "ban_on_criticism"


class CultFate(StrEnum):
    LIVING = "living"
    PASSED_ON = "passed_on"
    FADED = "faded"
    BECAME_FAITH = "became_faith"
    TORN_DOWN = "torn_down"
