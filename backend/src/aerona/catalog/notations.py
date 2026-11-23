from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.crafts import Notation


@dataclass(frozen=True)
class NotationSpec:
    label: str
    rank: int
    phrase: str


NOTATIONS: Mapping[Notation, NotationSpec] = total(
    Notation,
    {
        Notation.TALLY: NotationSpec("Tally", 0, "kept in tallies"),
        Notation.ADDITIVE: NotationSpec("Additive", 1, "written by adding signs"),
        Notation.POSITIONAL: NotationSpec("Positional", 2, "written by place"),
        Notation.SYMBOLIC: NotationSpec("Symbolic", 3, "written by place, with signs for unknowns"),
    },
)
BY_RANK: tuple[Notation, ...] = tuple(sorted(NOTATIONS, key=lambda notation: NOTATIONS[notation].rank))
