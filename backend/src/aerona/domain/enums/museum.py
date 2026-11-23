from enum import StrEnum


class HoardKind(StrEnum):
    CABINET = "cabinet"
    TEMPLE_TREASURY = "temple_treasury"
    ROYAL_COLLECTION = "royal_collection"
    MUSEUM = "museum"
    TROPHY_HALL = "trophy_hall"


class PieceKind(StrEnum):
    ARTIFACT = "artifact"
    RELIC = "relic"
    FOSSIL = "fossil"
    ART = "art"
    SPECIMEN = "specimen"
    MANUSCRIPT = "manuscript"
    TROPHY = "trophy"
    REGALIA = "regalia"
