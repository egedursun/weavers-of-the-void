import json
from dataclasses import dataclass
from typing import Any, TypeIs

from aerona.db.tables.ledger import LedgerChangeRow
from aerona.domain.enums.meta import LedgerOperation

RowValues = dict[str, Any]

WHITELISTED_TABLES = frozenset(
    {
        "nodes",
        "entities",
        "entity_tags",
        "entity_flags",
        "entity_traits",
        "bonds",
        "sons",
        "son_relations",
        "community_relations",
        "chronicle",
        "canon_facts",
        "threads",
        "thread_links",
        "lexemes",
        "folk_beliefs",
        "routes",
        "worlds",
        "journeys",
        "messages",
        "cosmos",
        "creator",
        "stars",
        "foreign_gods",
        "epochs",
        "epoch_world_narratives",
        "historian_views",
        "images",
        "scenarios",
        "bodies",
        "injuries",
        "conditions",
        "prostheses",
        "maimed_cohorts",
        "body_customs",
        "minds",
        "culture_values",
        "personality_values",
        "traits",
        "skills",
        "memories",
        "needs",
        "pressures",
        "region_environment",
        "place_environment",
        "world_seasons",
        "calendars",
        "ley_lines",
        "notable_years",
        "forced_weather",
        "modifiers",
        "incidents",
        "incident_participants",
        "wars",
        "community_societies",
    }
)
PERMANENT_BIRTH_TABLES = frozenset({"sons", "worlds"})
BIRTH_COST_COLUMNS: dict[str, frozenset[str]] = {"sons": frozenset({"essence"}), "creator": frozenset({"essence"})}
IGNORED_COLUMNS = frozenset({"created_at", "updated_at"})
IDENTITY_COLUMNS = (
    "created_at",
    "kind",
    "entity_type",
    "source_node_id",
    "target_node_id",
    "son_a_id",
    "son_b_id",
    "entity_a_id",
    "entity_b_id",
    "language_entity_id",
    "people_entity_id",
)
KEEP_COLUMNS = frozenset(
    {"id", "name", "kind", "text", "entity_type", "source_node_id", "target_node_id", "son_a_id", "son_b_id", "entity_a_id", "entity_b_id"}
)
QUANTITY_COLUMNS = frozenset(
    {
        "power_level",
        "hp",
        "essence",
        "faith",
        "fame",
        "xp",
        "level",
        "sleep_epochs_left",
        "stars",
        "existence",
        "value",
        "duration_epochs",
        "danger",
        "leakage",
        "population",
        "epochs_left",
        "time_factor",
        "doom_clock",
        "brightness",
        "stance",
        "power",
        "awakening_pressure",
    }
)
MERGEABLE_JSON_COLUMNS = frozenset({"stats"})


@dataclass(frozen=True)
class Change:
    id: int
    entry_id: int
    table: str
    key: RowValues
    operation: LedgerOperation
    before: RowValues | None
    after: RowValues | None

    @property
    def row_id(self) -> int | None:
        value = self.key.get("id")
        return int(value) if isinstance(value, int) else None

    @property
    def label_key(self) -> str:
        return f"{self.table}:{json.dumps(self.key, sort_keys=True)}"

    def diff_columns(self) -> list[str]:
        if self.operation is not LedgerOperation.UPDATE or self.before is None or self.after is None:
            return []
        return [column for column in self.after if column not in IGNORED_COLUMNS and self.before.get(column) != self.after.get(column)]

    @property
    def visible(self) -> bool:
        return self.table in WHITELISTED_TABLES and self.table != "nodes" and (self.operation is not LedgerOperation.UPDATE or bool(self.diff_columns()))


def parse_key(raw: str) -> RowValues:
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def to_change(row: LedgerChangeRow) -> Change:
    return Change(
        id=row.id,
        entry_id=row.entry_id,
        table=row.table_name,
        key=parse_key(row.row_key),
        operation=row.operation,
        before=row.before,
        after=row.after,
    )


def compacted(change: Change) -> tuple[RowValues | None, RowValues | None]:
    if change.operation is not LedgerOperation.UPDATE or change.before is None or change.after is None:
        return change.before, change.after
    kept = set(change.diff_columns()) | (KEEP_COLUMNS & set(change.after)) | set(change.key)
    return ({column: change.before.get(column) for column in kept}, {column: change.after.get(column) for column in kept})


def parse_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def is_number(value: Any) -> TypeIs[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def delta_undo(current: float, before: float, after: float) -> float:
    low = min(before, after, current)
    high = max(before, after, current)
    return max(low, min(high, current + (before - after)))


def merge_json(current: Any, before: Any, after: Any) -> tuple[Any, bool]:
    if isinstance(current, dict) and isinstance(before, dict) and isinstance(after, dict):
        merged = dict(current)
        for key in set(before) | set(after):
            old, new, now = before.get(key), after.get(key), current.get(key)
            if old == new:
                continue
            if now == new:
                if old is None:
                    merged.pop(key, None)
                else:
                    merged[key] = old
            elif is_number(now) and is_number(old) and is_number(new):
                merged[key] = type(now)(delta_undo(now, old, new))
        return merged, True
    if isinstance(current, list) and isinstance(before, list) and isinstance(after, list):
        added = [item for item in after if item not in before]
        removed = [item for item in before if item not in after]
        merged_list = [item for item in current if item not in added]
        merged_list.extend(item for item in removed if item not in merged_list)
        return merged_list, True
    return current, False
