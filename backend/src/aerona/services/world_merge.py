import asyncio
import sqlite3
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import Integer, Table, text
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.maintenance import MERGE_FOREIGN_KEY_CHECK, MERGE_IMAGE_PREFIX, MERGE_PRAGMA_DEFER, MERGE_SKIPPED_NODE_KINDS, MERGE_SKIPPED_TABLES
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.repositories.names import clean_display, is_single_word, normalize_name, roman
from aerona.db.session import Database

NODES = "nodes"
REGISTRY = "name_registry"
IMAGES = "images"
BUILT_IN_KEY = "built_in_key"
FIRST_SUFFIX = 2
INCOMPATIBLE = "The file cannot be merged into this world."


@dataclass(frozen=True)
class RenamedNode:
    old_name: str
    new_name: str


@dataclass(frozen=True)
class MergeSummary:
    rows: dict[str, int]
    skipped: dict[str, int]
    renamed: list[RenamedNode]
    images: dict[str, str]


@dataclass
class GuestTable:
    columns: list[str]
    rows: list[dict[str, Any]]


@dataclass
class HostState:
    max_ids: dict[str, int]
    taken_names: set[str]
    image_names: set[str]
    built_ins: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class MergePlan:
    inserts: list[tuple[str, list[str], list[tuple[Any, ...]]]]
    summary: MergeSummary
    registry: list[tuple[str, int, str, bool]] = field(default_factory=list)


def read_guest(path: Path) -> dict[str, GuestTable]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        present = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        tables: dict[str, GuestTable] = {}
        for table in Base.metadata.sorted_tables:
            if table.name not in present or (table.name in MERGE_SKIPPED_TABLES and table.name != REGISTRY):
                continue
            known = {column.name for column in table.columns}
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table.name}")') if row[1] in known]
            cursor = connection.execute(f'SELECT {", ".join(chr(34) + name + chr(34) for name in columns)} FROM "{table.name}"')
            tables[table.name] = GuestTable(columns, [dict(zip(columns, row, strict=True)) for row in cursor])
        return tables
    except sqlite3.Error as error:
        raise ValidationFailedError(INCOMPATIBLE) from error
    finally:
        connection.close()


async def read_host_state(session: AsyncSession) -> HostState:
    max_ids: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        key = _generated_key(table)
        if key is not None:
            value = await session.scalar(text(f'SELECT COALESCE(MAX("{key}"), 0) FROM "{table.name}"'))
            max_ids[table.name] = int(value or 0)
    taken = set((await session.scalars(text(f'SELECT normalized FROM "{REGISTRY}"'))).all())
    images = set((await session.scalars(text(f'SELECT file_name FROM "{IMAGES}"'))).all())
    built_ins: dict[str, dict[str, int]] = {}
    for table in Base.metadata.sorted_tables:
        key = _generated_key(table)
        if key is not None and BUILT_IN_KEY in table.columns:
            rows = await session.execute(text(f'SELECT "{BUILT_IN_KEY}", "{key}" FROM "{table.name}" WHERE "{BUILT_IN_KEY}" IS NOT NULL'))
            built_ins[table.name] = {str(found): int(row_id) for found, row_id in rows.all()}
    return HostState(max_ids, taken, images, built_ins)


def _generated_key(table: Table) -> str | None:
    keys = list(table.primary_key.columns)
    if len(keys) == 1 and isinstance(keys[0].type, Integer) and not keys[0].foreign_keys:
        return str(keys[0].name)
    return None


def _foreign_keys(table: Table, columns: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for column in table.columns:
        if column.name in columns and column.foreign_keys:
            result[column.name] = next(iter(column.foreign_keys)).column.table.name
    return result


def plan_merge(guest: Mapping[str, GuestTable], host: HostState) -> MergePlan:
    maps: dict[str, dict[Any, Any]] = defaultdict(dict)
    survivors: dict[str, list[dict[str, Any]]] = {}
    skipped: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        data = guest.get(table.name)
        if data is None or table.name in MERGE_SKIPPED_TABLES:
            continue
        links = _foreign_keys(table, data.columns)
        required = [name for name, column in ((c.name, c) for c in table.columns) if name in links and (not column.nullable or column.primary_key)]
        admitted = [row for row in data.rows if _admits(table.name, row, required, links, maps)]
        kept = _without_built_ins(table, admitted, maps, host)
        skipped[table.name] = len(data.rows) - len(admitted)
        survivors[table.name] = kept
        _allocate(table, kept, links, maps, host)
    names = _resolve_names(guest, survivors.get(NODES, []), host)
    renamed = [RenamedNode(old, row["name"]) for row, old in names.renames]
    image_map = _resolve_images(survivors.get(IMAGES, []), host)
    inserts: list[tuple[str, list[str], list[tuple[Any, ...]]]] = []
    counts: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        rows = survivors.get(table.name)
        if not rows:
            continue
        data = guest[table.name]
        translated = [_translate(table, row, data.columns, maps) for row in rows]
        inserts.append((table.name, data.columns, translated))
        counts[table.name] = len(translated)
    registry = [(normalized, maps[NODES][node_id], display, single) for normalized, node_id, display, single in names.registry]
    return MergePlan(inserts, MergeSummary(counts, {k: v for k, v in skipped.items() if v}, renamed, image_map), registry)


def _admits(table: str, row: dict[str, Any], required: list[str], links: dict[str, str], maps: Mapping[str, dict[Any, Any]]) -> bool:
    if table == NODES and row["kind"] in MERGE_SKIPPED_NODE_KINDS:
        return False
    return all(row[name] is not None and row[name] in maps[links[name]] for name in required)


def _without_built_ins(table: Table, rows: list[dict[str, Any]], maps: dict[str, dict[Any, Any]], host: HostState) -> list[dict[str, Any]]:
    known = host.built_ins.get(table.name, {})
    key = _generated_key(table)
    if not known or key is None:
        return rows
    kept: list[dict[str, Any]] = []
    for row in rows:
        found = known.get(str(row.get(BUILT_IN_KEY)))
        if found is None:
            kept.append(row)
        else:
            maps[table.name][row[key]] = found
    return kept


def _allocate(table: Table, kept: list[dict[str, Any]], links: dict[str, str], maps: dict[str, dict[Any, Any]], host: HostState) -> None:
    keys = list(table.primary_key.columns)
    if len(keys) != 1 or not isinstance(keys[0].type, Integer):
        return
    name = str(keys[0].name)
    if name in links:
        parent = links[name]
        for row in kept:
            maps[table.name][row[name]] = maps[parent][row[name]]
        return
    counter = host.max_ids.get(table.name, 0)
    for row in sorted(kept, key=lambda item: item[name]):
        counter += 1
        maps[table.name][row[name]] = counter


@dataclass
class NameResolution:
    renames: list[tuple[dict[str, Any], str]]
    registry: list[tuple[str, int, str, bool]]


def _resolve_names(guest: Mapping[str, GuestTable], nodes: list[dict[str, Any]], host: HostState) -> NameResolution:
    registered = {row["node_id"] for row in guest[REGISTRY].rows} if REGISTRY in guest else set()
    taken = set(host.taken_names)
    renames: list[tuple[dict[str, Any], str]] = []
    registry: list[tuple[str, int, str, bool]] = []
    for row in sorted(nodes, key=lambda item: item["id"]):
        display = clean_display(str(row["name"]))
        if row["id"] not in registered or not normalize_name(display):
            continue
        final = display
        suffix = FIRST_SUFFIX
        while normalize_name(final) in taken:
            final = f"{display} {roman(suffix)}"
            suffix += 1
        taken.add(normalize_name(final))
        if final != row["name"]:
            renames.append((row, str(row["name"])))
            row["name"] = final
        registry.append((normalize_name(final), row["id"], final, is_single_word(final)))
    return NameResolution(renames, registry)


def _resolve_images(rows: list[dict[str, Any]], host: HostState) -> dict[str, str]:
    taken = set(host.image_names)
    mapping: dict[str, str] = {}
    counter = 0
    for row in sorted(rows, key=lambda item: item["id"]):
        original = str(row["file_name"])
        final = original
        while final in taken:
            counter += 1
            final = f"{MERGE_IMAGE_PREFIX}{counter}-{original}"
        taken.add(final)
        mapping[original] = final
        row["file_name"] = final
    return mapping


BONDS_TABLE = "bonds"


def _translate(table: Table, row: dict[str, Any], columns: list[str], maps: Mapping[str, dict[Any, Any]]) -> tuple[Any, ...]:
    links = _foreign_keys(table, columns)
    key = [column.name for column in table.primary_key.columns]
    values: list[Any] = []
    for name in columns:
        value = row[name]
        if name in links and value is not None:
            value = maps[links[name]].get(value)
        elif name in key and len(key) == 1 and table.name in maps:
            value = maps[table.name][value]
        values.append(value)
    if table.name == BONDS_TABLE:
        _refresh_pair(columns, values)
    return tuple(values)


def _refresh_pair(columns: list[str], values: list[Any]) -> None:
    source, target = values[columns.index("source_node_id")], values[columns.index("target_node_id")]
    if source is None or target is None:
        return
    values[columns.index("pair_low")] = min(source, target)
    values[columns.index("pair_high")] = max(source, target)


async def apply_plan(session: AsyncSession, plan: MergePlan) -> None:
    connection = await session.connection()
    await connection.execute(text(MERGE_PRAGMA_DEFER))
    for name, columns, rows in plan.inserts:
        quoted = ", ".join(f'"{column}"' for column in columns)
        marks = ", ".join("?" for _ in columns)
        await connection.exec_driver_sql(f'INSERT INTO "{name}" ({quoted}) VALUES ({marks})', rows)
    for normalized, node_id, display, single in plan.registry:
        await connection.exec_driver_sql(
            f'INSERT INTO "{REGISTRY}" (normalized, node_id, display, single_word) VALUES (?, ?, ?, ?)', (normalized, node_id, display, single)
        )
    violations = (await connection.exec_driver_sql(MERGE_FOREIGN_KEY_CHECK)).fetchall()
    if violations:
        raise ValidationFailedError(INCOMPATIBLE)


class WorldMerger:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def merge(self, guest_path: Path) -> MergeSummary:
        guest = await asyncio.to_thread(read_guest, guest_path)
        async with self._database.write() as session:
            plan = plan_merge(guest, await read_host_state(session))
            await apply_plan(session, plan)
        return plan.summary
