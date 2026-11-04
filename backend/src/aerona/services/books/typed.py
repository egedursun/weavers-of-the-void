from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.elements import KeyedColumnElement

from aerona.db.base import Base
from aerona.db.profile_guard import LOCK_COLUMN, shape_of_table, table_name

OWNER_TABLES = frozenset({"entities", "nodes"})
SKIPPED_TABLES = frozenset(
    {
        "action_records",
        "agent_turns",
        "bonds",
        "chronicle",
        "chronicle_entities",
        "creation_motifs",
        "creation_rewards",
        "creation_verdicts",
        "entities",
        "entity_flags",
        "entity_tags",
        "epoch_agents",
        "images",
        "incident_participants",
        "incidents",
        "ledger_entries",
        "lexemes",
        "messages",
        "name_registry",
        "network_reviews",
        "notifications",
        "thread_links",
        "turn_counters",
    }
)
SKIPPED_COLUMNS = frozenset({"id", LOCK_COLUMN, "created_at", "updated_at"})
ID_SUFFIXES = ("_entity_id", "_node_id", "_id")
ORDER_COLUMNS = ("epoch", "since_epoch", "started_epoch", "slot", "position", "rank", "id")


def _identifier(value: str) -> str:
    return value.replace("_", " ") if value.isidentifier() else value


FORMATS: tuple[tuple[type, Callable[[Any], str]], ...] = (
    (bool, lambda value: "yes" if value else "no"),
    (Enum, lambda value: str(value.value).replace("_", " ")),
    (float, lambda value: f"{value:.2f}".rstrip("0").rstrip(".")),
    (datetime, lambda _value: ""),
    (date, lambda _value: ""),
    (str, _identifier),
)


@dataclass(frozen=True)
class TypedFact:
    label: str
    value: str


@dataclass
class TypedSection:
    title: str
    facts: list[TypedFact] = field(default_factory=list)
    rows: list[str] = field(default_factory=list)


def words(key: str) -> str:
    text = key
    for suffix in ID_SUFFIXES:
        if text.endswith(suffix) and text != suffix.lstrip("_"):
            text = text[: -len(suffix)]
            break
    text = text.replace("_pct", " percent").replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def title_of(table: str) -> str:
    for suffix in ("_profiles", "_profile"):
        if table.endswith(suffix):
            return words(table[: -len(suffix)])
    return words(table)


def _links_to_node(column: KeyedColumnElement[Any]) -> bool:
    return any(foreign.column.table.name in OWNER_TABLES for foreign in column.foreign_keys)


def _owner(mapper: Mapper[Any]) -> str | None:
    shape = shape_of_table(table_name(mapper))
    if shape is not None:
        return shape.node_column
    for column in mapper.local_table.columns:
        if _links_to_node(column):
            return column.key
    return None


def _order(mapper: Mapper[Any]) -> list[Any]:
    keys = [name for name in ORDER_COLUMNS if name in mapper.columns]
    return [mapper.columns[name] for name in keys] or list(mapper.primary_key)


class TypedIndex:
    def __init__(self, names: dict[int, str]) -> None:
        self.names = names
        self.sections: dict[int, list[TypedSection]] = defaultdict(list)

    @classmethod
    async def load(cls, session: AsyncSession, names: dict[int, str]) -> "TypedIndex":
        index = cls(names)
        for mapper in sorted(Base.registry.mappers, key=table_name):
            table = table_name(mapper)
            if table in SKIPPED_TABLES:
                continue
            owner = _owner(mapper)
            if owner is None:
                continue
            columns = [column for column in mapper.local_table.columns if column.key not in SKIPPED_COLUMNS and column.key != owner]
            if not columns:
                continue
            grouped: dict[int, list[Any]] = defaultdict(list)
            for row in await session.scalars(select(mapper.class_).order_by(*_order(mapper))):
                key = getattr(row, owner)
                if isinstance(key, int):
                    grouped[key].append(row)
            single = shape_of_table(table) is not None
            for node_id, rows in grouped.items():
                index.sections[node_id].append(index._section(table, columns, rows, single))
        return index

    def _section(self, table: str, columns: list[KeyedColumnElement[Any]], rows: list[Any], single: bool) -> TypedSection:
        section = TypedSection(title_of(table))
        if single and len(rows) == 1:
            section.facts = [TypedFact(words(column.key), text) for column in columns if (text := self.value(column, getattr(rows[0], column.key)))]
            return section
        for row in rows:
            parts = [f"{words(column.key)}: {text}" for column in columns if (text := self.value(column, getattr(row, column.key)))]
            if parts:
                section.rows.append(" · ".join(parts))
        return section

    def value(self, column: KeyedColumnElement[Any], value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, int) and not isinstance(value, bool) and (column.foreign_keys or column.key.endswith(ID_SUFFIXES)):
            return self.names.get(value, f"#{value}")
        plain = next((format_value(value) for kind, format_value in FORMATS if isinstance(value, kind)), None)
        if plain is not None:
            return plain
        composite = self.composite(column, value)
        return composite if composite is not None else str(value)

    def composite(self, column: KeyedColumnElement[Any], value: Any) -> str | None:
        if isinstance(value, list | tuple | set | frozenset):
            return ", ".join(self.value(column, item) or str(item) for item in value)
        if isinstance(value, dict):
            return ", ".join(f"{words(str(key))} {self.value(column, item) or item}" for key, item in value.items())
        if hasattr(value, "model_dump"):
            return self.value(column, value.model_dump(exclude_none=True))
        return None

    def of(self, node_id: int) -> list[TypedSection]:
        return [section for section in self.sections.get(node_id, []) if section.facts or section.rows]
