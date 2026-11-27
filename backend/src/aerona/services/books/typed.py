import json
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from functools import cache
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Select, Table, select
from sqlalchemy import column as loose_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper
from sqlalchemy.orm.base import instance_state
from sqlalchemy.sql.elements import ColumnElement, KeyedColumnElement

from aerona.cartography.biomes import Biome
from aerona.catalog.season_positions import SEASON_POSITIONS, SeasonPosition
from aerona.constants.control import BOOKKEEPING_TABLES
from aerona.core.grammar import an, singular, spoken
from aerona.db.base import Base
from aerona.db.profile_guard import LOCK_COLUMN, shape_of_table, table_name
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.ledger import LedgerChangeRow
from aerona.db.tables.lore import ChronicleRow, MessageRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.climes import DIRECTIONS
from aerona.domain.enums.environment import SeasonDating, WorldLink
from aerona.domain.enums.meta import LedgerOperation
from aerona.services.books.genome_text import genome_text
from aerona.services.books.kind_tables import KIND_TABLES

KEY_TEXT = re.compile(r"[a-z0-9]+(?:[_.:][a-z0-9]+)*")
OWNER_TABLES = frozenset({"entities", "nodes", "sons", "worlds", "stars", "foreign_gods", "creator", "galaxies", "galaxy_clusters", "dimensions"})
SKIPPED_TABLES = frozenset(
    {
        "achievements",
        "arms",
        "bonds",
        "chronicle",
        "chronicle_entities",
        "cosmos",
        "councils",
        "design_mounts",
        "design_sections",
        "design_techniques",
        "dish_ingredients",
        "divine_will_artifact_nodes",
        "divine_will_artifact_versions",
        "divine_will_artifacts",
        "divine_will_attachments",
        "divine_will_confirmations",
        "divine_will_cycles",
        "divine_will_events",
        "divine_will_forecasts",
        "divine_will_handles",
        "divine_will_plan_steps",
        "divine_will_plans",
        "divine_will_sessions",
        "entities",
        "entity_tags",
        "epoch_stats",
        "epoch_world_narratives",
        "epochs",
        "foreign_god_powers",
        "images",
        "incident_facts",
        "incident_participants",
        "incident_step_states",
        "incident_steps",
        "incident_terms",
        "incidents",
        "ledger_changes",
        "ledger_entries",
        "lexemes",
        "presence_events",
        "presence_exchanges",
        "presence_sessions",
        "scenarios",
        "scores",
        "son_powers",
        "son_relations",
        "state_change_terms",
        "state_changes",
        "state_checkpoints",
        "structure_design_sections",
        "threads",
        "unit_design_equipment",
        "unit_design_techniques",
        "world_maps",
        "world_seasons",
        "season_onsets",
    }
)
SKIPPED_COLUMNS = frozenset({"id", LOCK_COLUMN, "created_at", "updated_at", "undo"})
ID_SUFFIXES = ("_entity_id", "_node_id", "_id")
KIND_WORD = "kind"
ARTICLE = re.compile(r"^(?:the|an?) ", re.IGNORECASE)
NODE_SUFFIXES = ("_entity_id", "_node_id")
INDEXED_LISTS: dict[str, list[str]] = {"biome_mix": [biome.name.lower().replace("_", " ") for biome in Biome]}
ID_LISTS = frozenset(
    {
        "held_node_ids",
        "witness_node_ids",
        "path_region_ids",
        "items",
        "territory",
        "promoters",
        "territories",
        "seen_by",
        "administrators",
        "imposed_laws",
        "members",
        "witnesses",
        "excommunicated",
        "prior_journey_ids",
        "migration_path",
        "pinned_prey",
        "barred_prey",
        "supply_line",
        "agent_ids",
        "known_by",
        "agents",
        "discovered_by",
        "broken_by",
        "seats",
        "tellers",
        "texts",
        "audience",
        "translations",
        "immunities",
        "baseline_rebel_ids",
        "licensed_to",
        "endorsed_by",
        "condemned_by",
        "parent_ids",
        "forbidden_by",
        "regalia",
        "content",
        "stops",
        "circuit",
        "species",
        "creditors",
        "markets",
        "targets",
    }
)
PERCENT_LISTS = frozenset({"milestones"})
NODE_SHARES = frozenset({"sellers"})
REFERENCE_LISTS = {"rivals": "creature_groups", "revealed_aims": "war_aims", "works": "workshops", "incident_ids": "incidents", "journey_ids": "journeys"}
PAIRED_LISTS = {"martial_record": ("won", "lost")}

ORDINAL_LISTS = {"depends_on": "step"}
PERCENT_SIGN = "%"
NOTHING = "none"
UNKEPT = "a record no longer kept"
NODE_VALUE_DICTS = frozenset({"cast", "args"})
NODE_KEY_SUFFIXES = ("_ids", "_id")


def _shares(value: dict[str, Any]) -> str:
    return "; ".join(
        f"{words(str(locus))}: " + ", ".join(f"{words(str(key))} {share}{PERCENT_SIGN}" for key, share in found.items() if share)
        for locus, found in value.items()
        if isinstance(found, dict)
    )


def _debts(value: dict[str, Any]) -> str:
    return ", ".join(f"household {key} is owed {amount}" for key, amount in value.items())


def _mix(value: dict[str, Any]) -> str:
    whole = sum(int(share) for share in value.values() if isinstance(share, int)) or 1
    return ", ".join(f"{words(str(key))} {share} ({round(int(share) * 100 / whole)}{PERCENT_SIGN})" for key, share in value.items() if isinstance(share, int))


COLUMN_FORMATS: dict[str, Callable[[dict[str, Any]], str]] = {"genes": genome_text, "frequencies": _shares, "debts": _debts, "composition": _mix}
NAMED_NUMBERS: dict[str, tuple[str, ...]] = {"wind_from": DIRECTIONS, "heading": DIRECTIONS}
ORDER_COLUMNS = ("epoch", "since_epoch", "started_epoch", "slot", "position", "rank", "id")


def _identifier(value: str) -> str:
    return re.sub(r"[_.:]+", " ", value).strip() if KEY_TEXT.fullmatch(value) else value


FORMATS: tuple[tuple[type, Callable[[Any], str]], ...] = (
    (bool, lambda value: "yes" if value else "no"),
    (Enum, spoken),
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
    spilled: Sequence[str] | None = None

    @property
    def lines(self) -> Sequence[str]:
        return self.spilled if self.spilled is not None else self.rows


@dataclass
class RecordTable:
    title: str
    headers: list[str]
    rows: list[list[str]] = field(default_factory=list)


@dataclass(frozen=True)
class LedgerChange:
    verb: str
    target: str
    details: list[str]


CHANGE_VERBS = {LedgerOperation.INSERT: "Created", LedgerOperation.UPDATE: "Changed", LedgerOperation.DELETE: "Removed"}
LABEL_COLUMNS = ("name", "title", "label", "word", "key")


def _is_time(item: KeyedColumnElement[Any]) -> bool:
    return isinstance(getattr(item.type, "impl", item.type), DateTime | Date)


def _thaw(item: KeyedColumnElement[Any], raw: Any) -> Any:
    kind = getattr(item.type, "impl", item.type)
    if isinstance(kind, Boolean) and isinstance(raw, int):
        return bool(raw)
    if isinstance(kind, JSON) and isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    return raw


@cache
def words(key: str) -> str:
    text = key
    for suffix in ID_SUFFIXES:
        if text.endswith(suffix) and text != suffix.lstrip("_"):
            text = text[: -len(suffix)]
            break
    text = text.replace("_pct", " percent").replace("_", " ").replace(".", " ").strip()
    return text[:1].upper() + text[1:]


def column_labels(columns: list[KeyedColumnElement[Any]]) -> dict[str, str]:
    labels = {column.key: words(column.key) for column in columns}
    shared = Counter(labels.values())
    return {key: shared_label(key, label) if shared[label] > 1 else label for key, label in labels.items()}


def shared_label(key: str, label: str) -> str:
    plain = words(key) == key.replace("_", " ").capitalize()
    if label.lower().endswith(KIND_WORD):
        return label if plain else f"{label} record"
    return f"{label} {KIND_WORD}" if plain else label


PROPERTY_KEYS: dict[tuple[Mapper[Any], str, str], str] = {}


def attribute_of(row: Any, column: KeyedColumnElement[Any]) -> Any:
    mapper = instance_state(row).mapper
    table = column.table.name if isinstance(column.table, Table) else ""
    found = PROPERTY_KEYS.get((mapper, table, column.key))
    if found is None:
        found = PROPERTY_KEYS[(mapper, table, column.key)] = mapper.get_property_by_column(column).key
    return getattr(row, found)


@cache
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
    key = next((column for column in LABEL_COLUMNS if column in mapper.columns), None)
    if key is None:
        return None

    described = _described_label(mapper)

    def label(row: Any, names: dict[int, str]) -> str:
        return str(getattr(row, key) or "") or described(row, names)

    return label


def bare(phrase: str) -> str:
    return ARTICLE.sub("", phrase)


def _described_label(mapper: Mapper[Any]) -> Callable[[Any, dict[int, str]], str]:
    noun = singular(words(table_name(mapper)).lower())
    kind = next((column for column in KIND_COLUMNS if column in mapper.columns), None)
    owners = [column.key for column in mapper.local_table.columns if column.key.endswith(NODE_SUFFIXES)]
    dated = next((column for column in EPOCH_COLUMNS if column in mapper.columns), None)

    def label(row: Any, names: dict[int, str]) -> str:
        sort = getattr(row, kind, None) if kind is not None else None
        head = f"the {bare(spoken(sort))} {noun}" if sort is not None and hasattr(sort, "value") else f"the {noun}"
        whose = next((names[node] for node in (getattr(row, owner) for owner in owners) if isinstance(node, int) and node in names), "")
        epoch = getattr(row, dated, None) if dated is not None else None
        return head + (f" of {whose}" if whose else "") + (f" from epoch {epoch}" if isinstance(epoch, int) else "")

    return label


def label_of(mapper: Mapper[Any]) -> Callable[[Any, dict[int, str]], str]:
    return REFERENCE_LABELS.get(table_name(mapper)) or _named_label(mapper) or _described_label(mapper)


def told_in_entries(table: str) -> bool:
    return table not in SKIPPED_TABLES and table not in KIND_TABLES and table not in BOOKKEEPING_TABLES


async def shown_ids(session: AsyncSession, target: str) -> list[int]:
    found: set[int] = set()
    for mapper in Base.registry.mappers:
        if table_name(mapper) in SKIPPED_TABLES:
            continue
        for column in mapper.local_table.columns:
            if any(foreign.column.table.name == target for foreign in column.foreign_keys):
                found.update(value for value in await session.scalars(select(column).where(column.is_not(None)).distinct()) if isinstance(value, int))
    return sorted(found)


def _incident(row: Any, names: dict[int, str]) -> str:
    place = _named(names, row.place_entity_id)
    return f"{words(str(getattr(row.kind, 'value', row.kind))).lower()} of epoch {row.epoch}" + (f" at {place}" if place else "")


def _named(names: dict[int, str], node_id: int | None) -> str:
    return names.get(node_id, "") if node_id is not None else ""


REFERENCE_LABELS: dict[str, Callable[[Any, dict[int, str]], str]] = {
    "incidents": _incident,
    "bonds": lambda row, names: f"{words(str(getattr(row.kind, 'value', row.kind))).lower()} {_named(names, row.target_node_id)}".strip(),
    "routes": lambda row, names: f"the way between {_named(names, row.world_a_id)} and {_named(names, row.world_b_id)}",
    "journeys": lambda row, names: f"the crossing of {_named(names, row.traveller_entity_id) or 'travellers'} begun in epoch {row.start_epoch}",
    "wars": lambda row, names: _named(names, row.event_entity_id) or f"the war of epoch {row.started_epoch}",
    "sieges": lambda row, names: f"the siege of {_named(names, row.besieged_entity_id)}",
    "war_aims": lambda row, names: f"{words(str(getattr(row.kind, 'value', row.kind))).lower()} {_named(names, row.target_entity_id)}".strip(),
    "workshops": lambda row, names: f"the {spoken(row.kind)} of {_named(names, row.community_entity_id) or 'a lost town'}",
    "oaths": lambda row, names: f"the {words(str(getattr(row.kind, 'value', row.kind))).lower()} oath of {_named(names, row.swearer_entity_id)}",
    "law_proposals": lambda row, names: (
        f"the {words(str(row.kind.value)).lower()} proposal of epoch {row.proposed_epoch} in {_named(names, row.polity_entity_id)}"
    ),
    "crises": lambda row, names: (
        f"the crisis of epoch {row.opened_epoch} between {_named(names, row.demander_entity_id)} and {_named(names, row.target_entity_id)}"
    ),
    "resolutions": lambda row, names: f"the {words(str(row.kind.value)).lower()} resolution of epoch {row.proposed_epoch}",
    "crime_cases": lambda row, names: (
        f"the {spoken(row.crime)} case of epoch {row.opened_epoch}"
        + (f" against {_named(names, row.accused_entity_id)}" if _named(names, row.accused_entity_id) else ", with no one accused")
    ),
    "accounts": lambda row, names: f"the {words(row.kind.value).lower()} of {_named(names, row.holder_entity_id) or 'someone'} from epoch {row.epoch}",
    "designs": lambda row, names: row.name + (f" of {_named(names, row.owner_entity_id)}" if _named(names, row.owner_entity_id) else ""),
    "cascades": lambda row, names: f"the {spoken(row.act)} of epoch {row.epoch} at {_named(names, row.settlement_entity_id)}",
    "storylet_runs": lambda row, names: f"the {words(row.storylet.value).lower()} storylet of epoch {row.opened_epoch}",
    "vehicle_groups": lambda row, names: (
        f"the group of {row.count}" + (f" held by {_named(names, row.holder_node_id)}" if _named(names, row.holder_node_id) else ", held by none")
    ),
    "army_units": lambda row, names: f"the {words(row.kind.value).lower()} of {_named(names, row.army_entity_id) or 'an army'}",
    "gatherings": lambda row, names: (
        f"the {spoken(row.kind)}"
        + (f" of {_named(names, row.host_node_id)}" if _named(names, row.host_node_id) else "")
        + f" in epoch {row.epoch}"
        + (f" for {_named(names, row.honoured_node_id)}" if _named(names, row.honoured_node_id) else "")
    ),
    "battles": lambda row, names: (
        f"the battle of epoch {row.epoch} at {_named(names, row.place_entity_id) or 'an unknown field'}"
        + (f" won by {_named(names, row.winner_entity_id)}" if _named(names, row.winner_entity_id) else "")
    ),
    "gifts": lambda row, names: (
        f"the {words(row.occasion.value).lower()} gift of {_named(names, row.giver_node_id) or 'someone'} to {_named(names, row.receiver_node_id) or 'someone'}"
        f" in epoch {row.epoch}"
    ),
}
LABEL_COLUMNS = ("name", "title", "label", "word", "text")
KIND_COLUMNS = ("kind", "type", "category", "subject_kind", "stage")
EPOCH_COLUMNS = ("epoch", "since_epoch", "started_epoch", "start_epoch", "opened_epoch", "created_epoch", "founded_epoch", "made_epoch")
ID_CHUNK = 900
SOURCE_COLUMN = "source_key"
SOURCE_KEY = re.compile(r"([a-z_]+)[.:](\d+)")
SOURCE_NODES = frozenset({"event", "entity", "node"})
NAMED_TABLES = frozenset({"entities", "nodes", "sons", "worlds", "stars", "foreign_gods", "creator", "galaxies", "galaxy_clusters", "dimensions"})


ROW_FILTERS: dict[str, ColumnElement[bool]] = {"messages": MessageRow.intent == MessageIntent.DISPATCH}


def typed_mappers() -> list[Mapper[Any]]:
    return [mapper for mapper in sorted(Base.registry.mappers, key=table_name) if told_in_entries(table_name(mapper))]


def _rows(mapper: Mapper[Any], table: str) -> Select[Any]:
    statement = select(mapper.class_).order_by(*_order(mapper))
    found = ROW_FILTERS.get(table)
    return statement.where(found) if found is not None else statement


def marked_items(key: str, items: list[Any]) -> str | None:
    if key in PERCENT_LISTS:
        return ", ".join(f"{item}{PERCENT_SIGN}" for item in items)
    ordinal = ORDINAL_LISTS.get(key)
    return ", ".join(f"{ordinal} {item}" for item in items) if ordinal is not None else None


SEASON_COLUMNS: dict[tuple[str, str], SeasonPosition] = {(position.table, position.column): position for position in SEASON_POSITIONS}
MOMENT_DAYS = frozenset((position.table, "day") for position in SEASON_POSITIONS if position.dating is SeasonDating.DAY)


class TypedIndex:
    def __init__(self, names: dict[int, str]) -> None:
        self.names = names
        self.seasons: dict[int, dict[int, str]] = defaultdict(dict)
        self.worlds_of: dict[int, int] = {}
        self.sections: dict[int, list[TypedSection]] = defaultdict(list)
        self.records: list[RecordTable] = []
        self.references: dict[str, dict[int, str]] = {}

    async def load_references(self, session: AsyncSession) -> None:
        targets = {
            foreign.column.table.name
            for mapper in Base.registry.mappers
            for column in mapper.local_table.columns
            for foreign in column.foreign_keys
            if foreign.column.table.name not in NAMED_TABLES
        }
        targets |= set(REFERENCE_LISTS.values())
        for mapper in Base.registry.mappers:
            table = table_name(mapper)
            if table not in targets:
                continue
            label = REFERENCE_LABELS.get(table) or _named_label(mapper)
            key = mapper.get_property_by_column(mapper.primary_key[0]).key
            if label is not None:
                self.references[table] = {getattr(row, key): label(row, self.names) for row in await session.scalars(select(mapper.class_))}
                continue
            described = _described_label(mapper)
            wanted = await shown_ids(session, table)
            self.references[table] = {}
            for start in range(0, len(wanted), ID_CHUNK):
                rows = await session.scalars(select(mapper.class_).where(mapper.primary_key[0].in_(wanted[start : start + ID_CHUNK])))
                self.references[table].update({getattr(row, key): described(row, self.names) for row in rows})
        await self.tell_accounts(session)
        await self.tell_incidents(session)

    async def tell_incidents(self, session: AsyncSession) -> None:
        told = self.references.get(IncidentRow.__tablename__)
        if not told:
            return
        lines = await session.execute(
            select(IncidentRow.id, ChronicleRow.text).join(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id).order_by(IncidentRow.id)
        )
        for incident_id, text in lines:
            if text and incident_id in told:
                told[incident_id] = text.rstrip(".")

    async def tell_accounts(self, session: AsyncSession) -> None:
        histories = self.references.get(CollectionRow.__tablename__, {})
        told = self.references.get(AccountRow.__tablename__)
        if told is None:
            return
        for row in await session.scalars(select(AccountRow).order_by(AccountRow.id)):
            about = _named(self.names, row.subject_node_id) or (histories.get(row.collection_id, "") if row.collection_id is not None else "")
            if about and row.id in told:
                told[row.id] = f"{told[row.id]}, telling of {about}"

    async def load_seasons(self, session: AsyncSession) -> None:
        for season in await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)):
            self.seasons[season.world_id][season.position] = season.name
        rows = await session.execute(select(EntityRow.id, EntityRow.world_id).where(EntityRow.world_id.is_not(None)))
        self.worlds_of = {entity_id: world_id for entity_id, world_id in rows.all() if world_id is not None}

    def season_name(self, position: SeasonPosition, row: Any, value: int) -> str:
        through = getattr(row, position.through, None)
        world = through if position.link is WorldLink.WORLD else self.worlds_of.get(through) if isinstance(through, int) else None
        named = self.seasons.get(world, {}).get(value) if isinstance(world, int) else None
        return named or f"season {value + 1}"

    def source(self, key: str) -> str:
        found = SOURCE_KEY.fullmatch(key)
        if found is None:
            return words(key).lower()
        family, number = found.group(1), int(found.group(2))
        if family in SOURCE_NODES:
            return self.names.get(number, words(family).lower())
        for table in (f"{family}s", family):
            label = self.references.get(table, {}).get(number)
            if label:
                return label
        return words(family).lower()

    def reference(self, column: KeyedColumnElement[Any], value: int) -> str:
        target = next((foreign.column.table.name for foreign in column.foreign_keys), None)
        if target is None or target in NAMED_TABLES:
            return self.names.get(value, f"#{value}")
        return self.references.get(target, {}).get(value) or f"{an(singular(words(target).lower()))} no longer on record"

    @classmethod
    async def load(cls, session: AsyncSession, names: dict[int, str]) -> "TypedIndex":
        index = cls(names)
        await index.load_references(session)
        await index.load_seasons(session)
        for mapper in typed_mappers():
            await index.load_table(session, mapper)
        return index

    async def load_table(self, session: AsyncSession, mapper: Mapper[Any]) -> None:
        table = table_name(mapper)
        owner = _owner(mapper)
        if owner is None:
            await self.load_records(session, mapper)
            return
        columns = [column for column in mapper.local_table.columns if column.key not in SKIPPED_COLUMNS and column.key != owner]
        if not columns:
            return
        grouped: dict[int, list[Any]] = defaultdict(list)
        ownerless: list[Any] = []
        for row in await session.scalars(_rows(mapper, table)):
            key = getattr(row, owner)
            if isinstance(key, int):
                grouped[key].append(row)
            else:
                ownerless.append(row)
        self.add_records(mapper, ownerless)
        single = shape_of_table(table) is not None
        for node_id, rows in grouped.items():
            self.sections[node_id].append(self._section(table, columns, rows, single))

    @classmethod
    async def load_node(cls, session: AsyncSession, names: dict[int, str], node_id: int) -> "TypedIndex":
        index = cls(names)
        await index.load_seasons(session)
        found: list[tuple[str, list[KeyedColumnElement[Any]], list[Any], bool]] = []
        for mapper in sorted(Base.registry.mappers, key=table_name):
            table = table_name(mapper)
            owner = _owner(mapper) if told_in_entries(table) else None
            if owner is None:
                continue
            columns = [column for column in mapper.local_table.columns if column.key not in SKIPPED_COLUMNS and column.key != owner]
            rows = list(await session.scalars(_rows(mapper, table).where(getattr(mapper.class_, owner) == node_id))) if columns else []
            if rows:
                found.append((table, columns, rows, shape_of_table(table) is not None))
        await index.load_referenced(session, [(columns, rows) for _, columns, rows, _ in found])
        index.sections[node_id] = [index._section(table, columns, rows, single) for table, columns, rows, single in found]
        return index

    async def load_referenced(self, session: AsyncSession, groups: list[tuple[list[KeyedColumnElement[Any]], list[Any]]]) -> None:
        wanted: dict[str, set[int]] = defaultdict(set)
        for columns, rows in groups:
            for column in columns:
                listed = REFERENCE_LISTS.get(column.key)
                target = listed or next((foreign.column.table.name for foreign in column.foreign_keys), None)
                if target is None or target in NAMED_TABLES:
                    continue
                for row in rows:
                    value = attribute_of(row, column)
                    items = value if listed is not None and isinstance(value, list) else [value]
                    wanted[target].update(item for item in items if isinstance(item, int) and not isinstance(item, bool))
        mappers = {table_name(mapper): mapper for mapper in Base.registry.mappers}
        for target, ids in sorted(wanted.items()):
            mapper = mappers.get(target)
            label = (REFERENCE_LABELS.get(target) or _named_label(mapper)) if mapper is not None else None
            if mapper is None or label is None or not ids:
                continue
            key = mapper.primary_key[0]
            attribute = mapper.get_property_by_column(key).key
            known = self.references.setdefault(target, {})
            known.update({getattr(row, attribute): label(row, self.names) for row in await session.scalars(select(mapper.class_).where(key.in_(sorted(ids))))})

    async def load_records(self, session: AsyncSession, mapper: Mapper[Any]) -> None:
        self.add_records(mapper, list(await session.scalars(_rows(mapper, table_name(mapper)))))

    def add_records(self, mapper: Mapper[Any], rows: list[Any]) -> None:
        if table_name(mapper) in BOOKKEEPING_TABLES:
            return
        columns = [column for column in mapper.local_table.columns if column.key not in SKIPPED_COLUMNS or column.primary_key]
        labels = column_labels(columns)
        table = RecordTable(title_of(table_name(mapper)), [labels[column.key] for column in columns])
        for row in rows:
            table.rows.append([self.value(column, attribute_of(row, column), row) for column in columns])
        filled = [index for index in range(len(columns)) if any(row[index] for row in table.rows)]
        if table.rows and filled:
            table.headers = [table.headers[index] for index in filled]
            table.rows = [[row[index] for index in filled] for row in table.rows]
            self.records.append(table)

    def _section(self, table: str, columns: list[KeyedColumnElement[Any]], rows: list[Any], single: bool) -> TypedSection:
        section = TypedSection(title_of(table))
        labels = column_labels(columns)
        if single and len(rows) == 1:
            section.facts = [TypedFact(labels[column.key], text) for column in columns if (text := self.value(column, attribute_of(rows[0], column), rows[0]))]
            return section
        for row in rows:
            parts = [f"{labels[column.key]}: {text}" for column in columns if (text := self.value(column, attribute_of(row, column), row))]
            if parts:
                section.rows.append(" · ".join(parts))
        return section

    def calendar_value(self, column: KeyedColumnElement[Any], value: Any, row: Any) -> str | None:
        if not isinstance(column.table, Table) or not isinstance(value, int) or isinstance(value, bool):
            return None
        key = (column.table.name, column.key)
        season = SEASON_COLUMNS.get(key)
        if season is not None and row is not None:
            return self.season_name(season, row, value)
        return str(value + 1) if key in MOMENT_DAYS else None

    def linked(self, column: KeyedColumnElement[Any], value: Any) -> str | None:
        if isinstance(value, int) and not isinstance(value, bool) and (column.foreign_keys or column.key.endswith(NODE_SUFFIXES)):
            return self.reference(column, value)
        if column.key == SOURCE_COLUMN and isinstance(value, str):
            return self.source(value)
        return None

    def value(self, column: KeyedColumnElement[Any], value: Any, row: Any = None) -> str:
        if value is None:
            return ""
        dated = self.calendar_value(column, value, row)
        if dated is not None:
            return dated
        linked = self.linked(column, value)
        if linked is not None:
            return linked
        named = NAMED_NUMBERS.get(column.key)
        if named is not None and isinstance(value, int) and not isinstance(value, bool):
            return named[value % len(named)]
        plain = next((format_value(value) for kind, format_value in FORMATS if isinstance(value, kind)), None)
        if plain is not None:
            return plain
        composite = self.composite(column, value)
        return composite if composite is not None else str(value)

    def formatted(self, column: KeyedColumnElement[Any], value: dict[str, Any]) -> str | None:
        special = COLUMN_FORMATS.get(column.key)
        if special is not None:
            return special(value)
        if column.key in NODE_SHARES:
            return ", ".join(f"{self.names.get(int(key), f'#{key}')} {share}{PERCENT_SIGN}" for key, share in value.items() if str(key).isdigit())
        return None

    def composite(self, column: KeyedColumnElement[Any], value: Any) -> str | None:
        if isinstance(value, dict) and (text := self.formatted(column, value)) is not None:
            return text
        if isinstance(value, list | tuple) and any(isinstance(item, dict) for item in value):
            return "; ".join(f"({self.value(column, item) or NOTHING})" for item in value)
        if isinstance(value, list | tuple | set | frozenset):
            return self.sequence(column, list(value))
        if isinstance(value, dict):
            return ", ".join(self.entry_text(column, str(key), item) for key, item in value.items())
        if hasattr(value, "model_dump"):
            return self.value(column, value.model_dump(exclude_none=True))
        return None

    def entry_text(self, column: KeyedColumnElement[Any], key: str, item: Any) -> str:
        nodes = item if isinstance(item, list) else [item]
        if (
            (column.key in NODE_VALUE_DICTS or key.endswith(NODE_KEY_SUFFIXES))
            and nodes
            and all(isinstance(node, int) and not isinstance(node, bool) for node in nodes)
        ):
            label = words(key.removesuffix("_ids").removesuffix("_id"))
            return f"{label} {', '.join(self.names.get(node, UNKEPT) for node in nodes)}"
        return f"{self.key_text(key)} {self.value(column, item) or NOTHING}"

    def sequence(self, column: KeyedColumnElement[Any], items: list[Any]) -> str:
        labels = INDEXED_LISTS.get(column.key)
        if labels is not None:
            return ", ".join(f"{labels[index]} {item}%" for index, item in enumerate(items) if index < len(labels) and item)
        reference = REFERENCE_LISTS.get(column.key)
        if reference is not None:
            return ", ".join(self.references.get(reference, {}).get(item) or f"{words(reference).lower()} {item}" for item in items)
        if column.key in ID_LISTS:
            return ", ".join(self.names.get(item, f"#{item}") for item in items)
        marked = marked_items(column.key, items)
        if marked is not None:
            return marked
        pair = PAIRED_LISTS.get(column.key)
        if pair is not None and len(items) == len(pair):
            return ", ".join(f"{item} {label}" for item, label in zip(items, pair, strict=True))
        return ", ".join(self.value(column, item) or NOTHING for item in items)

    def ledger_changes(self, changes: Iterable[LedgerChangeRow]) -> dict[int, list[LedgerChange]]:
        mappers = {table_name(mapper): mapper for mapper in Base.registry.mappers}
        found: dict[int, list[LedgerChange]] = defaultdict(list)
        for change in changes:
            found[change.entry_id].append(self.change(change, mappers.get(change.table_name)))
        return found

    def change(self, change: LedgerChangeRow, mapper: Mapper[Any] | None) -> LedgerChange:
        before, after = change.before or {}, change.after or {}
        present = {*before, *after}
        known = [key for key in (mapper.local_table.columns.keys() if mapper is not None else []) if key in present]
        ordered = known + sorted(present - set(known))
        columns = {key: item for key in ordered if key not in SKIPPED_COLUMNS and not _is_time(item := self.column_of(mapper, key))}
        shown = after or before
        if change.operation is LedgerOperation.UPDATE:
            details = [
                f"{words(key)}: {self.value(item, _thaw(item, before.get(key))) or NOTHING} → {self.value(item, _thaw(item, after.get(key))) or NOTHING}"
                for key, item in columns.items()
                if before.get(key) != after.get(key)
            ]
        else:
            details = [f"{words(key)}: {text}" for key, item in columns.items() if key in shown and (text := self.value(item, _thaw(item, shown[key])))]
        return LedgerChange(CHANGE_VERBS[change.operation], self.change_target(change, shown, columns), details)

    def change_target(self, change: LedgerChangeRow, shown: dict[str, Any], columns: dict[str, KeyedColumnElement[Any]]) -> str:
        kind = title_of(change.table_name).lower()
        own = shown.get("id")
        label = self.names.get(own) if change.table_name in NAMED_TABLES and isinstance(own, int) else None
        label = label or next((str(shown[key]) for key in LABEL_COLUMNS if shown.get(key)), None)
        if label is None:
            label = ", ".join(
                text
                for key, item in columns.items()
                if key in shown and (_links_to_node(item) or key.endswith(NODE_SUFFIXES)) and (text := self.value(item, shown[key]))
            )
        return f"{label} in {kind}" if label else kind

    @staticmethod
    def column_of(mapper: Mapper[Any] | None, key: str) -> KeyedColumnElement[Any]:
        if mapper is not None and key in mapper.local_table.columns:
            return mapper.local_table.columns[key]
        return loose_column(key)

    def key_text(self, key: str) -> str:
        if key.isdigit():
            return self.names.get(int(key), f"#{key}")
        return words(key)

    def of(self, node_id: int) -> list[TypedSection]:
        return [section for section in self.sections.get(node_id, []) if section.facts or section.lines]
