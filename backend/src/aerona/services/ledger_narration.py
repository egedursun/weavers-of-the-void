from collections.abc import Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import bond_spec
from aerona.catalog.entity_types import entity_type_spec
from aerona.db.ledger_rows import Change, is_number, parse_json
from aerona.db.repositories.nodes import NodeRepository
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import LedgerOperation

NODE_TABLES = frozenset({"nodes", "entities", "sons", "worlds", "stars", "foreign_gods", "creator"})
PAIR_COLUMNS: dict[str, tuple[str, str]] = {
    "bonds": ("source_node_id", "target_node_id"),
    "son_relations": ("son_a_id", "son_b_id"),
    "community_relations": ("entity_a_id", "entity_b_id"),
}
TABLE_LABELS: dict[str, str] = {
    "entities": "New entity",
    "bonds": "New bond",
    "sons": "Son",
    "chronicle": "Chronicle",
    "canon_facts": "Fact",
    "threads": "Thread",
    "thread_links": "Thread link",
    "lexemes": "Word",
    "son_relations": "Relation",
    "community_relations": "Community relation",
    "folk_beliefs": "Belief",
    "routes": "Route",
    "worlds": "World",
    "journeys": "Journey",
    "messages": "Message",
    "cosmos": "Cosmos",
    "creator": "Creator",
    "stars": "Star",
    "foreign_gods": "Foreign god",
    "epochs": "Epoch narrative",
    "epoch_world_narratives": "World's epoch narrative",
    "historian_views": "Historian's view",
    "images": "Image",
    "scenarios": "Scenario",
    "entity_tags": "Tag",
    "entity_flags": "Flag",
    "entity_traits": "Trait",
}
COLUMN_LABELS: dict[str, str] = {
    "essence": "essence",
    "fame": "fame",
    "xp": "experience",
    "world_id": "world",
    "stats": "features",
    "value": "value",
    "state": "active",
    "existence": "existence",
    "location_id": "location",
    "population": "population",
    "power_level": "power",
    "faith": "faith",
    "spread": "spread",
    "followers": "followers",
}
NAMED_REFERENCE_COLUMNS = frozenset({"world_id", "location_id"})
CHRONICLE_PREVIEW = 90
VALUE_PREVIEW = 40
SHOWN_DIFFS = 4
NULL_MARK = "∅"
EMPTY_MARK = "none"
ACTIVE_STATE = "active"
MINUS = "\u2212"
ENTITY_TYPE_VALUES = frozenset(item.value for item in EntityType)
BOND_KIND_VALUES = frozenset(item.value for item in BondKind)


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _row(change: Change) -> dict[str, Any]:
    return change.after or change.before or {}


def referenced_node_ids(changes: Iterable[Change]) -> set[int]:
    found: set[int] = set()
    for change in changes:
        row = _row(change)
        if change.table in NODE_TABLES and change.row_id is not None:
            found.add(change.row_id)
        for column in (*PAIR_COLUMNS.get(change.table, ()), *NAMED_REFERENCE_COLUMNS):
            value = row.get(column)
            if isinstance(value, int):
                found.add(value)
    return found


def record_name(change: Change, names: dict[int, str]) -> str:
    row = _row(change)
    if change.table in NODE_TABLES and change.row_id is not None:
        return str(row.get("name") or names.get(change.row_id) or f"#{change.row_id}")
    if change.table == "bonds":
        kind = row.get("kind")
        label = bond_spec(BondKind(kind)).label if kind in BOND_KIND_VALUES else str(kind)
        return f"{names.get(row.get('source_node_id', 0), '?')} → {names.get(row.get('target_node_id', 0), '?')} ({label})"
    if change.table == "chronicle":
        return _truncate(str(row.get("text", "")), CHRONICLE_PREVIEW)
    if change.table in PAIR_COLUMNS:
        first, second = PAIR_COLUMNS[change.table]
        return f"{names.get(row.get(first, 0), '?')} ↔ {names.get(row.get(second, 0), '?')}"
    return str(row.get("name") or (f"#{change.row_id}" if change.row_id is not None else change.table))


def _shown(value: Any, column: str, names: dict[int, str]) -> str:
    if value is None:
        return NULL_MARK
    if column in NAMED_REFERENCE_COLUMNS and isinstance(value, int):
        return names.get(value, f"#{value}")
    if column == "state":
        return "yes" if value == ACTIVE_STATE else "no"
    text = str(value)
    return _truncate(text, VALUE_PREVIEW) if text else EMPTY_MARK


def field_diff(column: str, before: Any, after: Any, names: dict[int, str]) -> str:
    old, new = parse_json(before), parse_json(after)
    label = COLUMN_LABELS.get(column, column.replace("_", " "))
    if isinstance(old, list) and isinstance(new, list):
        added = [str(item) for item in new if item not in old]
        removed = [str(item) for item in old if item not in new]
        parts = [f"+{item}" for item in added] + [f"{MINUS}{item}" for item in removed]
        return f"{label}: {', '.join(parts)}"
    if isinstance(old, dict) and isinstance(new, dict):
        keys = sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))
        return ", ".join(f"{key}: {_shown(old.get(key), key, names)} → {_shown(new.get(key), key, names)}" for key in keys)
    if is_number(old) and is_number(new):
        return f"{label}: {old} → {new}"
    return f"{label}: {_shown(old, column, names)} → {_shown(new, column, names)}"


def narrate(change: Change, names: dict[int, str]) -> str:
    name = record_name(change, names)
    if change.operation is LedgerOperation.INSERT:
        label = TABLE_LABELS.get(change.table, change.table.replace("_", " ").capitalize())
        entity_type = _row(change).get("entity_type")
        known = change.table == "entities" and entity_type in ENTITY_TYPE_VALUES
        suffix = f" ({entity_type_spec(EntityType(str(entity_type))).label})" if known else ""
        return f"{label}: {name}{suffix}"
    if change.operation is LedgerOperation.DELETE:
        return f"Deleted: {name}"
    columns = change.diff_columns()
    before, after = change.before or {}, change.after or {}
    diffs = [field_diff(column, before.get(column), after.get(column), names) for column in columns[:SHOWN_DIFFS]]
    extra = f" +{len(columns) - SHOWN_DIFFS}" if len(columns) > SHOWN_DIFFS else ""
    return f"{name} · {'; '.join(diffs)}{extra}"


async def node_names(session: AsyncSession, changes: Iterable[Change]) -> dict[int, str]:
    return await NodeRepository(session).names_of(sorted(referenced_node_ids(changes)))


def label_names(changes: Iterable[Change], names: dict[int, str]) -> dict[str, str]:
    return {change.label_key: record_name(change, names) for change in changes}
