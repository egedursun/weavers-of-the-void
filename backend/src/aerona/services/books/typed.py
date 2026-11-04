import re
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

from aerona.cartography.biomes import Biome
from aerona.db.base import Base
from aerona.db.profile_guard import LOCK_COLUMN, shape_of_table, table_name

KEY_TEXT = re.compile(r"[a-z0-9]+(?:[_.:][a-z0-9]+)*")
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
INDEXED_LISTS: dict[str, list[str]] = {"biome_mix": [biome.name.lower().replace("_", " ") for biome in Biome]}
ID_LISTS = frozenset(
    {
        "excommunicated",
        "prior_journey_ids",
        "migration_path",
        "pinned_prey",
        "barred_prey",
        "supply_line",
        "agent_ids",
        "seats",
        "tellers",
        "texts",
        "audience",
        "translations",
        "immunities",
        "baseline_rebel_ids",
    }
)
REFERENCE_LISTS = {"revealed_aims": "war_aims"}
PAIRED_LISTS = {"martial_record": ("won", "lost")}
ORDER_COLUMNS = ("epoch", "since_epoch", "started_epoch", "slot", "position", "rank", "id")


def _identifier(value: str) -> str:
    return re.sub(r"[_.:]+", " ", value).strip() if KEY_TEXT.fullmatch(value) else value


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
    text = text.replace("_pct", " percent").replace("_", " ").replace(".", " ").strip()
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


def _named_label(mapper: Mapper[Any]) -> Callable[[Any, dict[int, str]], str] | None:
    key = next((column for column in ("name", "title", "label") if column in mapper.columns), None)
    if key is None:
        return None

    def label(row: Any, _names: dict[int, str]) -> str:
        return str(getattr(row, key) or "")

    return label


def _incident(row: Any, names: dict[int, str]) -> str:
    place = _named(names, row.place_entity_id)
    return f"{words(str(getattr(row.kind, 'value', row.kind))).lower()} of epoch {row.epoch}" + (f" at {place}" if place else "")


def _named(names: dict[int, str], node_id: int | None) -> str:
    return names.get(node_id, "") if node_id is not None else ""


REFERENCE_LABELS: dict[str, Callable[[Any, dict[int, str]], str]] = {
    "incidents": _incident,
    "bonds": lambda row, names: f"{words(str(getattr(row.kind, 'value', row.kind))).lower()} {_named(names, row.target_node_id)}".strip(),
    "routes": lambda row, names: f"the way between {_named(names, row.world_a_id)} and {_named(names, row.world_b_id)}",
    "wars": lambda row, names: _named(names, row.event_entity_id) or f"the war of epoch {row.started_epoch}",
    "sieges": lambda row, names: f"the siege of {_named(names, row.besieged_entity_id)}",
    "war_aims": lambda row, names: f"{words(str(getattr(row.kind, 'value', row.kind))).lower()} {_named(names, row.target_entity_id)}".strip(),
    "oaths": lambda row, names: f"the {words(str(getattr(row.kind, 'value', row.kind))).lower()} oath of {_named(names, row.swearer_entity_id)}",
}
NAMED_TABLES = frozenset({"entities", "nodes", "sons", "worlds", "stars", "foreign_gods", "creator"})


class TypedIndex:
    def __init__(self, names: dict[int, str]) -> None:
        self.names = names
        self.sections: dict[int, list[TypedSection]] = defaultdict(list)
        self.references: dict[str, dict[int, str]] = {}

    async def load_references(self, session: AsyncSession) -> None:
        targets = {
            foreign.column.table.name
            for mapper in Base.registry.mappers
            for column in mapper.local_table.columns
            for foreign in column.foreign_keys
            if foreign.column.table.name not in NAMED_TABLES
        }
        for mapper in Base.registry.mappers:
            table = table_name(mapper)
            if table not in targets:
                continue
            label = REFERENCE_LABELS.get(table) or _named_label(mapper)
            if label is None:
                continue
            self.references[table] = {row.id: label(row, self.names) for row in await session.scalars(select(mapper.class_))}

    def reference(self, column: KeyedColumnElement[Any], value: int) -> str:
        target = next((foreign.column.table.name for foreign in column.foreign_keys), None)
        if target is None or target in NAMED_TABLES:
            return self.names.get(value, f"#{value}")
        return self.references.get(target, {}).get(value) or words(target).lower().rstrip("s") + f" {value}"

    @classmethod
    async def load(cls, session: AsyncSession, names: dict[int, str]) -> "TypedIndex":
        index = cls(names)
        await index.load_references(session)
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
            return self.reference(column, value)
        plain = next((format_value(value) for kind, format_value in FORMATS if isinstance(value, kind)), None)
        if plain is not None:
            return plain
        composite = self.composite(column, value)
        return composite if composite is not None else str(value)

    def composite(self, column: KeyedColumnElement[Any], value: Any) -> str | None:
        if isinstance(value, list | tuple | set | frozenset):
            return self.sequence(column, list(value))
        if isinstance(value, dict):
            return ", ".join(f"{self.key_text(str(key))} {self.value(column, item) or item}" for key, item in value.items())
        if hasattr(value, "model_dump"):
            return self.value(column, value.model_dump(exclude_none=True))
        return None

    def sequence(self, column: KeyedColumnElement[Any], items: list[Any]) -> str:
        labels = INDEXED_LISTS.get(column.key)
        if labels is not None:
            return ", ".join(f"{labels[index]} {item}%" for index, item in enumerate(items) if index < len(labels) and item)
        reference = REFERENCE_LISTS.get(column.key)
        if reference is not None:
            return ", ".join(self.references.get(reference, {}).get(item) or f"{words(reference).lower()} {item}" for item in items)
        if column.key in ID_LISTS:
            return ", ".join(self.names.get(item, f"#{item}") for item in items)
        pair = PAIRED_LISTS.get(column.key)
        if pair is not None and len(items) == len(pair):
            return ", ".join(f"{item} {label}" for item, label in zip(items, pair, strict=True))
        return ", ".join(self.value(column, item) or str(item) for item in items)

    def key_text(self, key: str) -> str:
        if key.isdigit():
            return self.names.get(int(key), f"#{key}")
        return words(key)

    def of(self, node_id: int) -> list[TypedSection]:
        return [section for section in self.sections.get(node_id, []) if section.facts or section.rows]
