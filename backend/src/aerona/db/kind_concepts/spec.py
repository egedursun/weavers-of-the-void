from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.kinds import KindConcept


@dataclass(frozen=True)
class KindProperty:
    column: str
    label: str
    hint: str
    low: int = 0
    high: int = 100
    options: Mapping[str, str] | None = None

    def shown(self, value: object) -> tuple[int, str | None, str | None]:
        if self.options is None:
            return int(value) if isinstance(value, int) else 0, None, None
        key = str(value) if value is not None else None
        return 0, key, self.options.get(key) if key is not None else None


@dataclass(frozen=True)
class ConceptSpec:
    concept: KindConcept
    label: str
    plural: str
    hint: str
    table: type[KindRow]
    category: type[StrEnum]
    category_labels: dict[str, str]
    properties: tuple[KindProperty, ...]
    readers: tuple[str, ...]
