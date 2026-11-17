from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.faith import FanaticismKind, TenetKind
from aerona.domain.enums.mind import ActKind

F = FanaticismKind
T = TenetKind
FAVOURED = 0
ORTHODOX = 1
FALLBACK = 2


@dataclass(frozen=True)
class Fanaticism:
    act: ActKind | None
    favoured_by: frozenset[TenetKind] = frozenset()
    barred_by: frozenset[TenetKind] = frozenset()
    orthodox: bool = False
    fallback_rank: int | None = None


FANATICISMS: Mapping[FanaticismKind, Fanaticism] = total(
    FanaticismKind,
    {
        F.CRUSADE: Fanaticism(ActKind.CONVERSION_BY_FORCE, frozenset({T.HOLY_WAR}), frozenset({T.PACIFISM}), fallback_rank=3),
        F.INQUISITION: Fanaticism(ActKind.CONVERSION_BY_FORCE, orthodox=True, fallback_rank=2),
        F.ICONOCLASM: Fanaticism(ActKind.ICONOCLASM, fallback_rank=1),
        F.PURGE: Fanaticism(ActKind.CONVERSION_BY_FORCE, frozenset({T.EXCLUSIVITY}), frozenset({T.SYNCRETIC_OPENNESS}), orthodox=True),
        F.FORCED_CONVERSION: Fanaticism(ActKind.CONVERSION_BY_FORCE, frozenset({T.PROSELYTISM}), frozenset({T.SYNCRETIC_OPENNESS})),
        F.MARTYRDOM: Fanaticism(None, frozenset({T.MARTYRDOM_GLORY})),
        F.MORTIFICATION: Fanaticism(ActKind.RITUAL_SCARRING, frozenset({T.ASCETICISM, T.SACRED_SUFFERING, T.PURITY_OF_BODY})),
        F.BOOK_BURNING: Fanaticism(ActKind.BURNING_BOOKS, frozenset({T.ANTI_MAGIC}), frozenset({T.MONASTIC_LEARNING})),
        F.PERSECUTION: Fanaticism(ActKind.CONVERSION_BY_FORCE, frozenset({T.EXCLUSIVITY}), frozenset({T.PACIFISM, T.SYNCRETIC_OPENNESS})),
        F.MILLENARIAN_FLIGHT: Fanaticism(ActKind.ABANDONING_ELDERS, frozenset({T.PILGRIMAGE_DUTY})),
    },
)


def fanaticism_order(tenets: frozenset[TenetKind], orthodox: bool) -> list[FanaticismKind]:
    ranked: list[tuple[int, int, FanaticismKind]] = []
    for index, (kind, spec) in enumerate(FANATICISMS.items()):
        if tenets & spec.barred_by:
            continue
        if tenets & spec.favoured_by:
            ranked.append((FAVOURED, index, kind))
        elif spec.orthodox and orthodox:
            ranked.append((ORTHODOX, index, kind))
        elif spec.fallback_rank is not None:
            ranked.append((FALLBACK, spec.fallback_rank, kind))
    return [kind for _, _, kind in sorted(ranked)]
