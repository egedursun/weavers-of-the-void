from enum import StrEnum


class HoardKind(StrEnum):
    CABINET = "cabinet"
    TEMPLE_TREASURY = "temple_treasury"
    ROYAL_COLLECTION = "royal_collection"
    MUSEUM = "museum"


class PieceKind(StrEnum):
    ARTIFACT = "artifact"
    RELIC = "relic"
    FOSSIL = "fossil"
    ART = "art"
    SPECIMEN = "specimen"
