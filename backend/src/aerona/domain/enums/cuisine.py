from enum import StrEnum


class CookingMethod(StrEnum):
    RAW = "raw"
    BOILED = "boiled"
    STEWED = "stewed"
    STEAMED = "steamed"
    ROASTED = "roasted"
    GRILLED = "grilled"
    BAKED = "baked"
    FRIED = "fried"
    SMOKED = "smoked"
    DRIED = "dried"
    CURED = "cured"
    PICKLED = "pickled"
    FERMENTED = "fermented"
    BRAISED = "braised"
    SIMMERED = "simmered"
    GROUND = "ground"
    PRESSED = "pressed"


class DishCourse(StrEnum):
    STAPLE = "staple"
    SIDE = "side"
    FESTIVE = "festive"
    RITE = "rite"
    RATION = "ration"
    DELICACY = "delicacy"
    REMEDY = "remedy"
    DRINK = "drink"
