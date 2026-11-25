import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aerona.db.tables.changes import StateChangeRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.war import WarStatus

DISSOLVED = "dissolved"
END_WORDS = frozenset({EntityStatus.DEAD.value, EntityStatus.DESTROYED.value, WarStatus.ENDED.value, DISSOLVED})
STATUS_FIELD = "status"
NODE_TABLE = "nodes"
WORLD_END_TABLE = "world_ends"


def change_value(number: float | None, text: str | None, node: int | None) -> Any:
    if node is not None:
        return node
    if number is not None:
        return int(number) if float(number).is_integer() else number
    return text


def whole_row_name(text: str | None) -> tuple[str, str]:
    if not text:
        return "", ""
    try:
        values = json.loads(text)
    except ValueError:
        return "", ""
    if not isinstance(values, dict):
        return "", ""
    return str(values.get("name") or ""), str(values.get("kind") or "")


@dataclass(frozen=True)
class Reading:
    changes: list[StateChangeRow]
    names: dict[int, str]


def change_line(row: StateChangeRow, names: Mapping[int, str]) -> dict[str, Any]:
    return {
        "table": row.table_name,
        "operation": row.operation.value,
        "key": row.row_key,
        "node_id": row.node_id,
        "node_name": names.get(row.node_id, "") if row.node_id is not None else "",
        "field": row.field or "",
        "before": change_value(row.before_number, row.before_text, row.before_node_id),
        "after": change_value(row.after_number, row.after_text, row.after_node_id),
    }


def summarise(reading: Reading) -> dict[str, Any]:
    names = reading.names
    deleted_nodes: list[dict[str, Any]] = []
    deleted_records: list[dict[str, Any]] = []
    ended: list[dict[str, Any]] = []
    counts: Counter[tuple[str, str]] = Counter()
    for row in reading.changes:
        counts[(row.operation.value, row.table_name)] += 1
        if row.operation is LedgerOperation.DELETE and row.table_name == NODE_TABLE:
            name, kind = whole_row_name(row.before_text)
            deleted_nodes.append({"node_id": row.node_id, "name": name or names.get(row.node_id or 0, ""), "kind": kind})
        elif row.operation is LedgerOperation.DELETE:
            deleted_records.append(change_line(row, names))
        elif (row.operation is LedgerOperation.INSERT and row.table_name == WORLD_END_TABLE) or (
            row.operation is LedgerOperation.UPDATE and row.field == STATUS_FIELD and (row.after_text or "") in END_WORDS
        ):
            ended.append(change_line(row, names))
    tallies = [{"operation": operation, "table": table, "count": count} for (operation, table), count in sorted(counts.items())]
    return {
        "deleted_nodes": deleted_nodes,
        "deleted_records": deleted_records,
        "ended": ended,
        "tallies": tallies,
        "changes": [change_line(row, names) for row in reading.changes],
    }
