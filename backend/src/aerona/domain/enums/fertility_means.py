from enum import StrEnum


class FertilityMeans(StrEnum):
    PREVENTION = "prevention"
    REMEDY_FOR_BARRENNESS = "remedy_for_barrenness"
    ENDING_PREGNANCY = "ending_pregnancy"
    ASSISTED_CONCEPTION = "assisted_conception"
    SURROGACY = "surrogacy"
    MADE_BIRTH = "made_birth"


class MeansSource(StrEnum):
    FOLK = "folk"
    MEDICINE = "medicine"
    RITE = "rite"
    POWER = "power"
