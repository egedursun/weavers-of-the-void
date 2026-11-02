import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import StrEnum

VERSION_SEPARATOR = ":"
PERIOD_BASE = 36
PERIOD_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


class ChangeOperation(StrEnum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class TrackedTable(StrEnum):
    ENTITIES = "entities"
    SONS = "sons"
    BONDS = "bonds"
    CHRONICLE = "chronicle"
    WORLDS = "worlds"
    STARS = "stars"
    SON_RELATIONS = "son_relations"
    FOREIGN_GODS = "foreign_gods"
    ROUTES = "routes"
    JOURNEYS = "journeys"
    COSMOS = "cosmos"
    CREATOR = "creator"


TRACKED_TABLE_NAMES = frozenset(table.value for table in TrackedTable)


@dataclass(frozen=True)
class ChangeRecord:
    sequence: int
    table: str
    row_key: str
    operation: ChangeOperation


@dataclass(frozen=True)
class TableChanges:
    changed: tuple[str, ...] = ()
    deleted: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangeSet:
    version: str
    full: bool
    tables: dict[str, TableChanges] = field(default_factory=dict)

    def changed(self, table: TrackedTable) -> tuple[str, ...]:
        found = self.tables.get(table.value)
        return found.changed if found is not None else ()

    def deleted(self, table: TrackedTable) -> tuple[str, ...]:
        found = self.tables.get(table.value)
        return found.deleted if found is not None else ()

    def touched(self, table: TrackedTable) -> bool:
        return table.value in self.tables


def base36(number: int) -> str:
    digits: list[str] = []
    remaining = max(0, number)
    while True:
        remaining, digit = divmod(remaining, PERIOD_BASE)
        digits.append(PERIOD_ALPHABET[digit])
        if remaining == 0:
            return "".join(reversed(digits))


def new_period() -> str:
    return base36(time.time_ns() // 1_000_000)


class ChangeFeed:
    def __init__(self, period: str | None = None) -> None:
        self._period = period or new_period()
        self._sequence = 0
        self._base = 0
        self._records: list[ChangeRecord] = []
        self._lock = threading.Lock()

    @property
    def period(self) -> str:
        return self._period

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def version(self) -> str:
        return f"{self._period}{VERSION_SEPARATOR}{self._sequence}"

    @property
    def size(self) -> int:
        return len(self._records)

    def record(self, table: str, row_key: str, operation: ChangeOperation) -> int | None:
        if table not in TRACKED_TABLE_NAMES:
            return None
        with self._lock:
            self._sequence += 1
            self._records.append(ChangeRecord(self._sequence, table, row_key, operation))
            return self._sequence

    def record_many(self, records: list[tuple[str, str, ChangeOperation]]) -> None:
        for table, row_key, operation in records:
            self.record(table, row_key, operation)

    def changes_since(self, token: str | None, max_changes: int) -> ChangeSet:
        start = self._parse(token)
        if start is None:
            return ChangeSet(version=self.version, full=True)
        latest: OrderedDict[tuple[str, str], ChangeOperation] = OrderedDict()
        for record in self._records:
            if record.sequence > start:
                latest[(record.table, record.row_key)] = record.operation
        if len(latest) > max_changes:
            return ChangeSet(version=self.version, full=True)
        grouped: dict[str, tuple[list[str], list[str]]] = {}
        for (table, row_key), operation in latest.items():
            changed, deleted = grouped.setdefault(table, ([], []))
            (deleted if operation is ChangeOperation.DELETE else changed).append(row_key)
        tables = {table: TableChanges(tuple(changed), tuple(deleted)) for table, (changed, deleted) in grouped.items()}
        return ChangeSet(version=self.version, full=False, tables=tables)

    def reset(self) -> None:
        with self._lock:
            self._sequence += 1
            self._base = self._sequence
            self._records.clear()

    def prune(self, keep: int) -> int:
        with self._lock:
            if self._sequence - keep <= self._base:
                return 0
            self._base = self._sequence - keep
            before = len(self._records)
            self._records = [record for record in self._records if record.sequence > self._base]
            return before - len(self._records)

    def _parse(self, token: str | None) -> int | None:
        if not token or VERSION_SEPARATOR not in token:
            return None
        period, _, raw = token.rpartition(VERSION_SEPARATOR)
        if period != self._period or not raw.isdigit():
            return None
        sequence = int(raw)
        if sequence < self._base or sequence > self._sequence:
            return None
        return sequence
