import enum
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import inspect as inspect_row

from aerona.db.tables.entities import EntityRow
from aerona.db.types import PydanticJSON
from aerona.engine.primitives.stats import set_stats, stat

CHANGE = "change"
ADDED = "added"
MADE = "made"
STAT = "stat"


def plain(value: Any) -> Any:
    return value.value if isinstance(value, enum.Enum) else value


def stored(row: Any, column: str, value: Any) -> Any:
    kind = type(row).__table__.c[column].type
    if isinstance(kind, PydanticJSON) and value is not None:
        return kind.adapter.dump_python(value, mode="json")
    return plain(value)


def key_of(row: Any) -> list[Any]:
    return [plain(value) for value in inspect_row(row).identity or ()]


@dataclass
class Ledger:
    steps: list[dict[str, Any]] = field(default_factory=list)
    seen: set[tuple[str, tuple[Any, ...], str]] = field(default_factory=set)

    def set(self, row: Any, column: str, value: Any) -> None:
        table = str(row.__table__.name)
        key = key_of(row)
        mark = (table, tuple(key), column)
        if mark not in self.seen:
            self.seen.add(mark)
            self.steps.append({"op": CHANGE, "table": table, "key": key, "column": column, "before": stored(row, column, getattr(row, column))})
        setattr(row, column, value)

    def stat(self, entity: EntityRow, key: str, value: int) -> None:
        mark = ("stats", (entity.id,), key)
        if mark not in self.seen:
            self.seen.add(mark)
            self.steps.append({"op": STAT, "node": entity.id, "key": key, "before": stat(entity, key)})
        set_stats(entity, **{key: value})

    def added(self, row: Any) -> None:
        self.steps.append({"op": ADDED, "table": str(row.__table__.name), "key": key_of(row)})

    def made(self, node_id: int) -> None:
        self.steps.append({"op": MADE, "node": node_id})
