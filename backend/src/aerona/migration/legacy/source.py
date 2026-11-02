import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

from aerona.migration.legacy.vocabulary import LegacyTable, Vocabulary

READ_ONLY_URI = "file:{path}?mode=ro"


class LegacyRow:
    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = dict(values)

    def raw(self, column: str) -> Any:
        return self._values.get(column)

    def text(self, column: str) -> str | None:
        value = self._values.get(column)
        if value is None:
            return None
        text = str(value)
        return text if text.strip() else None

    def required_text(self, column: str, fallback: str = "") -> str:
        return self.text(column) or fallback

    def integer(self, column: str) -> int | None:
        value = self._values.get(column)
        if value is None:
            return None
        try:
            return round(float(value))
        except (TypeError, ValueError):
            return None

    def number(self, column: str) -> float | None:
        value = self._values.get(column)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def flag(self, column: str) -> bool:
        return bool(self.integer(column) or 0)

    def json(self, column: str) -> Any:
        value = self._values.get(column)
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except ValueError:
            return None

    def as_dict(self) -> dict[str, Any]:
        return dict(self._values)


class LegacySource:
    def __init__(self, path: Path, vocabulary: Vocabulary) -> None:
        self.path = path
        self.vocabulary = vocabulary
        self._connection = sqlite3.connect(READ_ONLY_URI.format(path=path.resolve()), uri=True)
        self._connection.row_factory = sqlite3.Row
        self._physical_columns: dict[str, set[str]] = {}

    def close(self) -> None:
        self._connection.close()

    def physical_tables(self) -> set[str]:
        with closing(self._connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")) as cursor:
            return {str(row[0]) for row in cursor}

    def has(self, table: str) -> bool:
        return self.vocabulary.table(table).name in self.physical_tables()

    def physical_columns(self, table: str) -> set[str]:
        physical = self.vocabulary.table(table).name
        if physical not in self._physical_columns:
            with closing(self._connection.execute("SELECT name FROM pragma_table_info(?)", (physical,))) as cursor:
                self._physical_columns[physical] = {str(row[0]) for row in cursor}
        return self._physical_columns[physical]

    def columns(self, table: str) -> set[str]:
        spec = self.vocabulary.table(table)
        present = self.physical_columns(table)
        return {english for english, physical in spec.columns.items() if physical in present}

    def missing_columns(self, table: str) -> list[str]:
        spec = self.vocabulary.table(table)
        present = self.physical_columns(table)
        return sorted(english for english, physical in spec.columns.items() if physical not in present)

    def unknown_columns(self, table: str) -> list[str]:
        spec = self.vocabulary.table(table)
        known = set(spec.columns.values())
        return sorted(column for column in self.physical_columns(table) if column not in known)

    def count(self, table: str) -> int:
        if not self.has(table):
            return 0
        physical = self.vocabulary.table(table).name
        with closing(self._connection.execute(f'SELECT COUNT(*) FROM "{physical}"')) as cursor:
            row = cursor.fetchone()
        return int(row[0]) if row is not None else 0

    def rows(self, table: str, order_by: tuple[str, ...] = ()) -> list[LegacyRow]:
        return list(self.iterate(table, order_by))

    def iterate(self, table: str, order_by: tuple[str, ...] = ()) -> Iterator[LegacyRow]:
        if not self.has(table):
            return
        spec = self.vocabulary.table(table)
        present = self.physical_columns(table)
        selected = {english: physical for english, physical in spec.columns.items() if physical in present}
        if not selected:
            return
        projection = ", ".join(f'"{physical}" AS "{english}"' for english, physical in selected.items())
        ordering = [f'"{spec.physical(column)}"' for column in order_by if spec.columns.get(column) in present]
        statement = f'SELECT {projection} FROM "{spec.name}"' + (f" ORDER BY {', '.join(ordering)}" if ordering else "")
        with closing(self._connection.execute(statement)) as cursor:
            for record in cursor:
                yield LegacyRow(dict(zip(record.keys(), tuple(record), strict=True)))

    def single(self, table: str) -> LegacyRow | None:
        return next(self.iterate(table), None)

    def table_spec(self, table: str) -> LegacyTable:
        return self.vocabulary.table(table)
