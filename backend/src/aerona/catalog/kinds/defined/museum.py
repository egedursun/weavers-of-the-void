from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.museum import HoardKind, PieceKind

HOARD_KIND = total(
    HoardKind,
    {
        HoardKind.CABINET: Defined("Cabinet of curiosities", checked_by=(), used_by=("engine.museums.hoards.found_hoards", "engine.museums.hoards.restitute")),
        HoardKind.TEMPLE_TREASURY: Defined("Temple treasury", checked_by=("engine.museums.hoards.offered",), used_by=("engine.museums.hoards.HALLS",)),
        HoardKind.ROYAL_COLLECTION: Defined(
            "Royal collection",
            checked_by=("engine.museums.hoards.found_hoards", "engine.museums.hoards.offered"),
            used_by=("engine.museums.hoards.found_hoards", "engine.museums.hoards.loot"),
        ),
        HoardKind.MUSEUM: Defined("Museum", checked_by=(), used_by=("engine.museums.hoards.HALLS", "tools.son.museums.found_museum")),
    },
)

PIECE_KIND = total(
    PieceKind,
    {
        PieceKind.ARTIFACT: Defined(
            "Artifact", checked_by=(), used_by=("catalog.life.museums.MADE_PIECES", "engine.museums.hoards.prized_in", "engine.museums.hoards.prized_of")
        ),
        PieceKind.RELIC: Defined(
            "Relic", checked_by=(), used_by=("catalog.life.museums.MADE_PIECES", "engine.museums.hoards.prized_in", "engine.museums.hoards.prized_of")
        ),
        PieceKind.FOSSIL: Defined("Fossil", checked_by=(), used_by=("catalog.life.museums.NATURAL_PIECES", "engine.museums.hoards.offered")),
        PieceKind.ART: Defined("Work of art", checked_by=(), used_by=("catalog.life.museums.MADE_PIECES", "engine.museums.hoards.offered")),
        PieceKind.SPECIMEN: Defined(
            "Specimen", checked_by=("engine.museums.hoards.gather",), used_by=("catalog.life.museums.NATURAL_PIECES", "engine.museums.hoards.offered")
        ),
    },
)
