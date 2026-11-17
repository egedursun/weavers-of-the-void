from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.collective import HeraldicCharge
from aerona.domain.enums.creator import CreatorNature
from aerona.domain.enums.demography import MotifSource
from aerona.domain.enums.entity import EntityStatus, EntityType


@dataclass(frozen=True)
class MotifSpec:
    label: str
    entity_types: frozenset[EntityType]
    status: EntityStatus
    charges: tuple[HeraldicCharge, ...]
    nature: CreatorNature | None


M = MotifSource
E = EntityType
C = HeraldicCharge
N = CreatorNature
CANON = EntityStatus.CANON
MOTIF_SOURCES: Mapping[MotifSource, MotifSpec] = total(
    MotifSource,
    {
        M.LIVING_THINGS: MotifSpec(
            "Living things", frozenset({E.SPECIES, E.BEAST}), CANON, (C.BEAST, C.BIRD, C.FISH, C.FEATHER, C.PAW, C.WING, C.SHELL), N.SOURCE
        ),
        M.LAND: MotifSpec(
            "The land",
            frozenset({E.REGION, E.PLACE, E.RESOURCE}),
            CANON,
            (C.MOUNTAIN, C.PEAK, C.TREE, C.GROVE, C.WAVE, C.DROPLET, C.LEAF),
            N.SOURCE,
        ),
        M.SKY: MotifSpec(
            "The sky",
            frozenset({E.CELESTIAL, E.PHENOMENON}),
            CANON,
            (C.STAR, C.SUN, C.MOON, C.MOON_STAR, C.ESTOILE, C.CLOUD, C.ORBIT),
            N.UNKNOWABLE,
        ),
        M.GODS: MotifSpec("The gods", frozenset({E.CULT, E.RITE, E.SPIRIT}), CANON, (C.EYE, C.TEMPLE, C.TORCH, C.CROSS, C.ANNULET), N.MANY_FACED),
        M.ANCESTORS: MotifSpec("The ancestors", frozenset({E.MORTAL}), EntityStatus.DEAD, (C.HAND, C.HEARTH, C.FOOTPRINTS, C.HOURGLASS), N.ABSENT_ONE),
        M.PEOPLE: MotifSpec("Living people", frozenset({E.MORTAL}), CANON, (C.HAND, C.FIST, C.ARM, C.HANDSHAKE, C.HEART), N.JUDGE),
        M.MADE_THINGS: MotifSpec(
            "Made things",
            frozenset({E.ITEM, E.STRUCTURE, E.VESSEL, E.ARTWORK}),
            CANON,
            (C.TOWER, C.KEY, C.WHEEL, C.COLUMN, C.HAMMER, C.COG, C.SHIP),
            N.MAKER,
        ),
        M.WRITING: MotifSpec(
            "Signs and writing",
            frozenset({E.LANGUAGE, E.LEGEND, E.KNOWLEDGE, E.LAW}),
            CANON,
            (C.BOOK, C.OPEN_BOOK, C.SCROLL, C.QUILL),
            N.UNKNOWABLE,
        ),
        M.PATTERN: MotifSpec("Pure pattern", frozenset(), CANON, (C.LOZENGE, C.MASCLE, C.HEXAGON, C.TRIANGLE, C.ANNULET, C.INFINITY), None),
    },
)
MOTIF_LABELS: Mapping[MotifSource, str] = total(MotifSource, {source: spec.label for source, spec in MOTIF_SOURCES.items()})
