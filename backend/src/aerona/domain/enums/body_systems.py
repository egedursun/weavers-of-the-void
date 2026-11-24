from enum import StrEnum


class BodySystem(StrEnum):
    BREATH = "breath"
    CIRCULATION = "circulation"
    DIGESTION = "digestion"
    REGULATION = "regulation"
    NERVES = "nerves"
    IMMUNITY = "immunity"
    REPRODUCTION = "reproduction"
    STRUCTURE = "structure"
    NONE = "none"
    EXCRETION = "excretion"


class Sensitivity(StrEnum):
    TO_FOOD = "to_food"
    TO_PLANT = "to_plant"
    TO_ANIMAL = "to_animal"
    TO_MATERIAL = "to_material"
    TO_SUBSTANCE = "to_substance"
    TO_LIGHT = "to_light"
    TO_SOUND = "to_sound"
    TO_POWER = "to_power"
    TO_PRESSURE = "to_pressure"


class LimitWay(StrEnum):
    EQUIPMENT = "equipment"
    AUGMENT = "augment"
    GROWN_ORGAN = "grown_organ"
    POWER = "power"
    RITE = "rite"
