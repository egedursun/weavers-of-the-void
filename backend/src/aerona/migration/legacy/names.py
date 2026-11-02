from dataclasses import dataclass, field

from aerona.db.repositories.names import FIRST_SUFFIX, clean_display, is_single_word, normalize_name, roman
from aerona.db.tables.node import NameRegistryRow


@dataclass
class NameLedger:
    _taken: set[str] = field(default_factory=set)
    _rows: list[NameRegistryRow] = field(default_factory=list)

    def is_taken(self, name: str) -> bool:
        return normalize_name(name) in self._taken

    def reserve(self, name: str) -> str:
        root = clean_display(name)
        display = root
        suffix = FIRST_SUFFIX
        while self.is_taken(display):
            display = f"{root} {roman(suffix)}"
            suffix += 1
        self._taken.add(normalize_name(display))
        return display

    def bind(self, node_id: int, display: str) -> None:
        self._rows.append(NameRegistryRow(normalized=normalize_name(display), node_id=node_id, display=display, single_word=is_single_word(display)))

    def drain(self) -> list[NameRegistryRow]:
        rows, self._rows = self._rows, []
        return rows

    @property
    def size(self) -> int:
        return len(self._taken)
