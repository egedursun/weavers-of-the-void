from collections.abc import Mapping
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.ecology import SpeciesClass
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.museum import PieceKind

NATURAL_PIECES = (PieceKind.SPECIMEN, PieceKind.FOSSIL)


MADE_PIECES = (PieceKind.ARTIFACT, PieceKind.RELIC, PieceKind.ART, PieceKind.MANUSCRIPT, PieceKind.TROPHY, PieceKind.REGALIA)

PLANTING_SPECIES_CLASSS = (SpeciesClass.PLANT, SpeciesClass.FUNGUS)

C = ItemClass
PIECE_OF_CLASS: Mapping[ItemClass, PieceKind] = MappingProxyType(
    {
        C.HOLY_RELIC: PieceKind.RELIC,
        C.IDOL: PieceKind.RELIC,
        C.CROWN: PieceKind.REGALIA,
        C.SCEPTRE: PieceKind.REGALIA,
        C.SEAL: PieceKind.REGALIA,
        C.STANDARD: PieceKind.ARTIFACT,
        C.JEWEL: PieceKind.ARTIFACT,
        C.RING: PieceKind.ARTIFACT,
        C.ASTROLABE: PieceKind.ARTIFACT,
        C.MAP: PieceKind.ARTIFACT,
        C.MIRROR: PieceKind.ARTIFACT,
        C.INSTRUMENT: PieceKind.ARTIFACT,
        C.DEVICE: PieceKind.ARTIFACT,
        C.BOOK: PieceKind.MANUSCRIPT,
        C.SCROLL: PieceKind.MANUSCRIPT,
        C.PRAYER_BOOK: PieceKind.MANUSCRIPT,
    }
)
WAR_PIECES = frozenset({PieceKind.ARTIFACT, PieceKind.TROPHY})
PIECE_PRESTIGE: Mapping[PieceKind, str] = total(
    PieceKind,
    {
        PieceKind.ARTIFACT: "prestige_per_piece",
        PieceKind.RELIC: "prestige_per_piece",
        PieceKind.FOSSIL: "prestige_per_piece",
        PieceKind.ART: "prestige_per_piece",
        PieceKind.SPECIMEN: "prestige_per_piece",
        PieceKind.MANUSCRIPT: "manuscript_prestige",
        PieceKind.TROPHY: "trophy_prestige",
        PieceKind.REGALIA: "prestige_per_piece",
    },
)

GARDEN_LIFE: Mapping[GardenKind, tuple[SpeciesClass, ...]] = MappingProxyType(
    {GardenKind.HUNTING_PARK: (SpeciesClass.ANIMAL,), GardenKind.MENAGERIE: (SpeciesClass.ANIMAL,)}
)
GATHERING_GARDENS = frozenset({GardenKind.BOTANIC, GardenKind.MENAGERIE})
GARDEN_WILD: Mapping[GardenKind, bool] = total(GardenKind, {kind: kind is GardenKind.MENAGERIE for kind in GardenKind})
