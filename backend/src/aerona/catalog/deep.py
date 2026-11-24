from collections.abc import Mapping
from dataclasses import dataclass

from aerona.catalog.movement import FLOODED_WAYS, SPIRIT_WAYS
from aerona.core.total import total
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.geology import DeepPassageState


@dataclass(frozen=True)
class PassageStateSpec:
    label: str
    passes: frozenset[MovementMode] | None


PASSAGE_STATES: Mapping[DeepPassageState, PassageStateSpec] = total(
    DeepPassageState,
    {
        DeepPassageState.DIGGING: PassageStateSpec("Being dug", frozenset()),
        DeepPassageState.OPEN: PassageStateSpec("Open", None),
        DeepPassageState.FLOODED: PassageStateSpec("Flooded", FLOODED_WAYS),
        DeepPassageState.COLLAPSED: PassageStateSpec("Collapsed", SPIRIT_WAYS),
        DeepPassageState.SEALED: PassageStateSpec("Sealed", frozenset()),
    },
)
