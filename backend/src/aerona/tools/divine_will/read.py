from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from pydantic import Field
from sqlalchemy import JSON, Boolean, Float, Integer, Select, String, and_, func, or_, select
from sqlalchemy import inspect as inspected
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.elements import ColumnElement, KeyedColumnElement

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.control import BOOKKEEPING_TABLES
from aerona.core.errors import AeronaError
from aerona.core.grammar import several, spoken
from aerona.db.profile_guard import NODE_TABLES, held_columns, owned_shape, table_name
from aerona.db.repositories.chronicle import kept_lines
from aerona.db.repositories.nodes import NODE_TABLES as NODE_ROWS
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.repositories.wars import wars_under_way
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow, EntityTagRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind, NodeKind
from aerona.domain.models.moment import Moment
from aerona.engine.interconnect.incidents import causality_graph
from aerona.engine.recording.accounts import Account, account_of
from aerona.engine.recording.then import node_then
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool
from aerona.tools.divine_will.paging import failed, paged, paged_stream, plain
from aerona.tools.divine_will.ports import LinkView, will_reads
from aerona.tools.divine_will.rows import (
    attributes,
    change_text,
    every_table,
    is_long_text,
    keys_of,
    mapper_of,
    names_for,
    node_ids,
    rendered_rows,
    row_line,
    shown,
    streamed,
)

W = DivineWillToolId
READ = frozenset({Toolset.READ})
TABLES_KIND = "tables"
TRUE_WORDS = frozenset({"true", "yes", "1"})
DESCENDING = "-"
HEAD_COLUMNS = frozenset({"id", "kind", "name"})


class NodePart(StrEnum):
    ALL = "all"
    IDENTITY = "identity"
    LORE = "lore"
    SECTIONS = "sections"
    BONDS = "bonds"
    CHANGES = "changes"


class ReadNodeInput(PagedInput):
    node_id: int = Field(ge=1)
    part: NodePart = NodePart.ALL


class ReadRecordsInput(PagedInput):
    node_id: int = Field(ge=1)
    table: str = Field(default="", max_length=120)


Scalar = str | int | float | bool | None


class EnumerateInput(PagedInput):
    kind: str = Field(min_length=1, max_length=120)
    filters: dict[str, Scalar] = Field(default_factory=dict)
    contains: str = Field(default="", max_length=200)
    sort: list[str] = Field(default_factory=list)


class GraphNeighboursInput(PagedInput):
    node_id: int = Field(ge=1)
    bond_kinds: list[str] = Field(default_factory=list)
    depth: int = Field(default=1, ge=1, le=4)


class GraphPathInput(PagedInput):
    first_id: int = Field(ge=1)
    second_id: int = Field(ge=1)
    depth: int = Field(default=6, ge=1, le=12)


class ChronicleInput(PagedInput):
    epoch_from: int | None = Field(default=None, ge=0)
    epoch_to: int | None = Field(default=None, ge=0)
    world_id: int | None = None
    node_id: int | None = None
    kind: ChronicleKind | None = None
    contains: str = Field(default="", max_length=200)
    newest_first: bool = False


class ExplainInput(PagedInput):
    incident_id: int | None = None
    node_id: int | None = None
    depth: int = Field(default=6, ge=1, le=50)


class StateAtInput(PagedInput):
    epoch: int = Field(ge=0)
    node_id: int = Field(ge=1)
    year: int | None = Field(default=None, ge=0)
    season: int | None = Field(default=None, ge=0)
    day: int | None = Field(default=None, ge=0)
    hour: int | None = Field(default=None, ge=0)


class LedgerInput(PagedInput):
    epoch: int | None = Field(default=None, ge=0)
    actor_kind: ActorKind | None = None
    actor_node_id: int | None = None
    tool: str = Field(default="", max_length=120)
    undone: bool | None = None
    newest_first: bool = True


def words_of(key: str) -> str:
    return key.replace("_", " ")


def paragraphs(text: str) -> list[str]:
    return [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]


async def node_of(session: AsyncSession, node_id: int) -> NodeRow | None:
    try:
        return await NodeRepository(session).load(node_id)
    except AeronaError:
        return None


def missing_node(node_id: int) -> WillResult:
    return failed(f"There is no node {node_id}. Find nodes with search_lore or enumerate.")


STATS_COLUMN = "stats"
STATS_LEVER = "Each of these stats is set with the act entity:stat (entity_id, stat, value)."


def identity_blocks(node: NodeRow, names: dict[int, str]) -> tuple[list[str], list[str]]:
    mapper: Mapper[Any] = inspected(node).mapper
    facts: list[str] = []
    lore: list[str] = []
    for key, column in attributes(mapper):
        value = getattr(node, key)
        if key in HEAD_COLUMNS or value is None or (isinstance(value, str | list | dict) and not value):
            continue
        if is_long_text(column) and isinstance(value, str):
            lore.append(f"## {words_of(key).capitalize()}")
            lore.extend(paragraphs(value))
            continue
        facts.append(f"{key}: {shown(column, value, names)}")
        if key == STATS_COLUMN:
            facts.append(STATS_LEVER)
    return facts, lore


async def bond_lines(session: AsyncSession, node_id: int) -> list[str]:
    bonds = list(await session.scalars(select(BondRow).where(or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id)).order_by(BondRow.id)))
    names = await names_for(session, [bond.source_node_id for bond in bonds] + [bond.target_node_id for bond in bonds])
    lines: list[str] = []
    for bond in bonds:
        forward = bond.source_node_id == node_id
        other = bond.target_node_id if forward else bond.source_node_id
        arrow = "->" if forward else "<-"
        extra = f" · {bond.description}" if bond.description else ""
        lines.append(f"- {spoken(bond.kind)} {arrow} {names.get(other, 'unnamed')} (node {other}) · {spoken(bond.state)} since epoch {bond.epoch}{extra}")
    return lines


async def read_node(call: WillCall, query: ReadNodeInput) -> WillResult:
    async with call.database.read() as session:
        node = await node_of(session, query.node_id)
        if node is None:
            return missing_node(query.node_id)
        mapper: Mapper[Any] = inspected(node).mapper
        names = await names_for(session, node_ids(mapper, [node]))
        facts, lore = identity_blocks(node, names)
        head = f"# {node.name} (node {node.id}, {spoken(node.kind)})"
        items: list[str] = []
        every: dict[int, str] = {}
        if query.part in (NodePart.ALL, NodePart.IDENTITY):
            items += ["## Identity", *facts]
            if isinstance(node, EntityRow):
                tags = list(await session.scalars(select(EntityTagRow.tag).where(EntityTagRow.entity_id == node.id).order_by(EntityTagRow.tag)))
                if tags:
                    items.append(f"tags: {', '.join(tags)}")
        if query.part in (NodePart.ALL, NodePart.LORE):
            items += lore
        if query.part in (NodePart.ALL, NodePart.SECTIONS):
            every = {node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name))}
            for section in await will_reads(call).typed_sections(session, every, node.id):
                items.append(f"## {section.title}")
                items += [f"{label}: {value}" for label, value in section.facts]
                items += [f"- {line}" for line in section.lines]
        if query.part in (NodePart.ALL, NodePart.BONDS):
            bonds = await bond_lines(session, node.id)
            if bonds:
                items += ["## Bonds", *bonds]
        if query.part in (NodePart.ALL, NodePart.CHANGES):
            every = every or {node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name))}
            changes = await will_reads(call).change_lines(session, every, node.id)
            if changes:
                items += ["## Changes", *[f"- {line}" for line in changes]]
    return await paged(call, W.READ_NODE, query, items, head=head, empty="Nothing recorded in this part.")


def shaped_tables() -> list[Mapper[Any]]:
    return [
        mapper
        for mapper in every_table()
        if table_name(mapper) not in NODE_TABLES and table_name(mapper) not in BOOKKEEPING_TABLES and owned_shape(mapper) is not None
    ]


async def read_records(call: WillCall, query: ReadRecordsInput) -> WillResult:
    tables = shaped_tables()
    if query.table:
        tables = [mapper for mapper in tables if table_name(mapper) == query.table]
        if not tables:
            return failed(f"{query.table} is not a record table owned by a node. Leave the table out to list every record of the node.")
    items: list[str] = []
    async with call.database.read() as session:
        if await NodeRepository(session).kind_of(query.node_id) is None:
            return missing_node(query.node_id)
        for mapper in tables:
            shape = owned_shape(mapper)
            if shape is None:
                continue
            statement = select(mapper.class_).where(or_(*(getattr(mapper.class_, owner) == query.node_id for owner in shape.owners)))
            rows = list(await session.scalars(statement.order_by(*mapper.primary_key)))
            if not rows:
                continue
            keys = keys_of(mapper)
            names = await names_for(session, node_ids(mapper, rows))
            items.append(f"## {table_name(mapper)} · key columns: {', '.join(keys)} · {several(len(rows), 'row', 'rows')}")
            for row in rows:
                held = sorted(held_columns(row))
                key = ", ".join(f"{name}={plain(getattr(row, name))}" for name in keys)
                line = f"- key [{key}] · {row_line(mapper, row, names, skip=frozenset(keys))}"
                items.append(line + (f" · held: {', '.join(held)}" if held else ""))
    return await paged(call, W.READ_RECORDS, query, items, head=f"Every record of node {query.node_id}, row by row.", empty="This node owns no records.")


def kind_statement(kind: str) -> tuple[Mapper[Any], Select[Any]] | None:
    if kind in EntityType:
        return inspected(EntityRow), select(EntityRow).where(EntityRow.entity_type == EntityType(kind))
    if kind in NodeKind:
        row = NODE_ROWS[NodeKind(kind)]
        return inspected(row), select(row)
    mapper = mapper_of(kind)
    return (mapper, select(mapper.class_)) if mapper is not None else None


def coerced(column: KeyedColumnElement[Any], value: Scalar) -> Any:
    if value is None:
        return None
    kind = column.type
    enum_class = getattr(kind, "enum_class", None)
    if enum_class is not None:
        return enum_class(str(value))
    if isinstance(kind, Boolean):
        return value if isinstance(value, bool) else str(value).casefold() in TRUE_WORDS
    if isinstance(kind, Integer):
        return int(value)
    if isinstance(kind, Float):
        return float(value)
    return value if isinstance(kind, JSON) else str(value)


def condition(column: KeyedColumnElement[Any], value: Scalar) -> ColumnElement[bool]:
    target = coerced(column, value)
    return column.is_(None) if target is None else column == target


STAT_KEYS = frozenset(stat.key for spec in ENTITY_TYPES.values() for stat in spec.stats)


def resolved(columns: Mapping[str, KeyedColumnElement[Any]], name: str) -> ColumnElement[Any] | None:
    if name in columns:
        return columns[name]
    stats = columns.get(STATS_COLUMN)
    return func.json_extract(stats, f"$.{name}") if stats is not None and name in STAT_KEYS else None


def stat_condition(columns: Mapping[str, KeyedColumnElement[Any]], name: str, value: Scalar) -> ColumnElement[bool]:
    if name in columns:
        return condition(columns[name], value)
    found = resolved(columns, name)
    if found is None:
        raise ValueError(f"no column {name}")
    return found.is_(None) if value is None else found == value


def ordered(columns: Mapping[str, KeyedColumnElement[Any]], name: str) -> ColumnElement[Any]:
    found = resolved(columns, name.lstrip(DESCENDING))
    if found is None:
        raise ValueError(f"no column {name}")
    return found.desc() if name.startswith(DESCENDING) else found


def text_columns(mapper: Mapper[Any]) -> list[KeyedColumnElement[Any]]:
    return [column for _, column in attributes(mapper) if isinstance(column.type, String) and getattr(column.type, "enum_class", None) is None]


async def table_list(call: WillCall, query: EnumerateInput) -> WillResult:
    lines = [f"- {table_name(mapper)}: {', '.join(key for key, _ in attributes(mapper))}" for mapper in every_table()]
    head = "Every table of the world with its columns. Enumerate any of them by name, or an entity type, or a kind of node."
    return await paged(call, W.ENUMERATE, query, lines, head=head, empty="No tables.")


def tables_naming(kind: str) -> list[str]:
    word = kind.strip().lower()
    names = sorted(table_name(mapper) for mapper in every_table())
    return [name for name in names if any(part in (word, f"{word}s", f"{word}es") for part in name.split("_"))]


def unknown_kind(kind: str) -> WillResult:
    types = ", ".join(item.value for item in EntityType)
    nodes = ", ".join(item.value for item in NodeKind)
    near = tables_naming(kind)
    tables = f" Tables whose names hold this word: {', '.join(near)}." if near else ""
    return failed(f"No kind called {kind}.{tables} Use an entity type ({types}), a kind of node ({nodes}), a table name, or {TABLES_KIND} to list every table.")


async def enumerate_records(call: WillCall, query: EnumerateInput) -> WillResult:
    if query.kind == TABLES_KIND:
        return await table_list(call, query)
    found = kind_statement(query.kind)
    if found is None:
        return unknown_kind(query.kind)
    mapper, statement = found
    columns = dict(attributes(mapper))
    wanted = {*query.filters, *(name.lstrip(DESCENDING) for name in query.sort)}
    unknown = sorted(name for name in wanted if resolved(columns, name) is None)
    if unknown:
        stats = f" Stats of a thing ({', '.join(sorted(STAT_KEYS))}) also filter and sort." if STATS_COLUMN in columns else ""
        return failed(f"{table_name(mapper)} has no column {', '.join(unknown)}. Its columns: {', '.join(columns)}.{stats}")
    try:
        conditions = [stat_condition(columns, name, value) for name, value in sorted(query.filters.items())]
    except (ValueError, TypeError) as error:
        return failed(f"A filter value does not fit its column: {error}.")
    if query.contains:
        searched = text_columns(mapper)
        if searched:
            conditions.append(or_(*(column.ilike(f"%{query.contains}%") for column in searched)))
    if conditions:
        statement = statement.where(and_(*conditions))
    order = [ordered(columns, name) for name in query.sort]
    statement = statement.order_by(*order, *mapper.primary_key)
    async with call.database.read() as session:
        total = int(await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0)
        head = f"{several(total, 'record', 'records')} of {query.kind}, every one in order."

        async def render(rows: Sequence[Any]) -> list[str]:
            return [f"- {line}" for line in await rendered_rows(session, mapper, rows)]

        return await paged_stream(call, W.ENUMERATE, query, streamed(session, statement, render), total, head=head, empty="Nothing matches.")


async def reached(call: WillCall, session: AsyncSession, query: GraphNeighboursInput) -> list[tuple[int, LinkView]]:
    wanted = {kind.casefold() for kind in query.bond_kinds}
    seen = {query.node_id}
    frontier = [query.node_id]
    found: list[tuple[int, LinkView]] = []
    listed: set[tuple[int, int, str, bool]] = set()
    for depth in range(1, query.depth + 1):
        following: list[int] = []
        for node_id in frontier:
            links = await will_reads(call).links(session, node_id)
            for link in sorted(links, key=lambda item: (item.kind, item.target)):
                if wanted and link.kind.casefold() not in wanted and link.kind.casefold().replace(" ", "_") not in wanted:
                    continue
                if (link.source, link.target, link.kind, link.forward) in listed:
                    continue
                listed.add((link.source, link.target, link.kind, link.forward))
                found.append((depth, link))
                if link.target not in seen:
                    seen.add(link.target)
                    following.append(link.target)
        frontier = following
    return found


async def graph_neighbours(call: WillCall, query: GraphNeighboursInput) -> WillResult:
    async with call.database.read() as session:
        kinds = NodeRepository(session)
        if await kinds.kind_of(query.node_id) is None:
            return missing_node(query.node_id)
        found = await reached(call, session, query)
        ids = {link.source for _, link in found} | {link.target for _, link in found}
        names = await names_for(session, ids)
        node_kinds = await kinds.kinds_of(sorted(ids))
    lines = []
    for depth, link in found:
        arrow = "->" if link.forward else "<-"
        target_kind = spoken(node_kinds[link.target]) if link.target in node_kinds else "node"
        note = f" · {link.description}" if link.description else ""
        lines.append(
            f"- step {depth} · {names.get(link.source, 'unnamed')} (node {link.source}) {link.kind} {arrow} "
            f"{names.get(link.target, 'unnamed')} (node {link.target}, {target_kind}){note}"
        )
    head = f"Every link of node {query.node_id} out to {several(query.depth, 'step', 'steps')}."
    return await paged(call, W.GRAPH_NEIGHBOURS, query, lines, head=head, empty="No links.")


async def graph_path(call: WillCall, query: GraphPathInput) -> WillResult:
    async with call.database.read() as session:
        result = await will_reads(call).path(session, query.first_id, query.second_id, query.depth)
    if not result.found:
        return await paged(call, W.GRAPH_PATH, query, [], empty=f"No path within {several(query.depth, 'step', 'steps')} joins these nodes.")
    lines = [f"Path of {several(len(result.steps), 'step', 'steps')}:"]
    for step in result.steps:
        arrow = "->" if step.forward else "<-"
        source, target = result.names.get(step.source, "unnamed"), result.names.get(step.target, "unnamed")
        note = f" · {step.description}" if step.description else ""
        lines.append(f"- {source} (node {step.source}) {step.kind} {arrow} {target} (node {step.target}){note}")
    return await paged(call, W.GRAPH_PATH, query, lines, empty="The two nodes are the same.")


def chronicle_statement(query: ChronicleInput) -> Select[Any]:
    statement = select(ChronicleRow).where(kept_lines())
    if query.epoch_from is not None:
        statement = statement.where(ChronicleRow.epoch >= query.epoch_from)
    if query.epoch_to is not None:
        statement = statement.where(ChronicleRow.epoch <= query.epoch_to)
    if query.world_id is not None:
        statement = statement.where(ChronicleRow.world_id == query.world_id)
    if query.kind is not None:
        statement = statement.where(ChronicleRow.kind == query.kind)
    if query.contains:
        statement = statement.where(ChronicleRow.text.ilike(f"%{query.contains}%"))
    if query.node_id is not None:
        named = select(ChronicleEntityRow.chronicle_id).where(ChronicleEntityRow.entity_id == query.node_id)
        statement = statement.where(or_(ChronicleRow.son_id == query.node_id, ChronicleRow.world_id == query.node_id, ChronicleRow.id.in_(named)))
    if query.newest_first:
        return statement.order_by(ChronicleRow.epoch.desc(), ChronicleRow.year.desc(), ChronicleRow.id.desc())
    return statement.order_by(ChronicleRow.epoch, ChronicleRow.year, ChronicleRow.id)


def chronicle_line(row: ChronicleRow) -> str:
    year = f" year {row.year}" if row.year is not None else ""
    return f"- epoch {row.epoch}{year} · {spoken(row.kind)} · line {row.id}: {row.text}"


async def chronicle(call: WillCall, query: ChronicleInput) -> WillResult:
    statement = chronicle_statement(query)
    async with call.database.read() as session:
        total = int(await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0)

        async def render(rows: Sequence[Any]) -> list[str]:
            return [chronicle_line(row) for row in rows]

        head = f"{several(total, 'line', 'lines')} of the chronicle."
        return await paged_stream(call, W.CHRONICLE, query, streamed(session, statement, render), total, head=head, empty="No line matches.")


def account_lines(account: Account) -> list[str]:
    moment = account.moment
    when = f"epoch {moment.epoch}" + (f" year {moment.year}" if moment.year is not None else "")
    lines = [f"# Incident {account.id} · {account.kind} · {when}", f"family: {account.family} · tier: {spoken(account.tier)} · magnitude {account.magnitude}"]
    for label, text in (
        ("name", account.name),
        ("place", account.place_name),
        ("from", account.origin_name),
        ("to", account.destination_name),
        ("told", account.line),
        ("retold", account.retold),
        ("note", account.note),
    ):
        if text:
            lines.append(f"{label}: {text}")
    lines += [f"- participant {item.name or 'unnamed'} (node {item.node_id}) as {spoken(item.role)}" for item in account.participants]
    for fact in account.facts:
        value = fact.node_name or fact.name or fact.enum_value or (plain(fact.number) if fact.number is not None else "")
        lines.append(f"- fact {fact.key}: {value}" + (f" {spoken(fact.unit)}" if fact.unit is not None else ""))
    for step in account.steps:
        actor = step.actor_name or (f"node {step.actor_node_id}" if step.actor_node_id else "no one")
        target = step.target_name or (f"node {step.target_node_id}" if step.target_node_id else "")
        amount = f" {plain(step.amount)}" if step.amount is not None else ""
        outcome = f" -> {spoken(step.outcome)}" if step.outcome is not None else ""
        lines.append(f"- step {step.position}: {actor} {spoken(step.action)} {target}{amount}{outcome}".rstrip())
    lines += [
        f"- term {term.term}: {spoken(term.op)} {plain(term.amount)}" + (f" from {term.source_name}" if term.source_name else "") for term in account.terms
    ]
    for change in account.changes:
        before = change.before_node_name or change.before_text or (plain(change.before_number) if change.before_number is not None else "none")
        after = change.after_node_name or change.after_text or (plain(change.after_number) if change.after_number is not None else "none")
        terms = "; ".join(f"{term.term} {spoken(term.op)} {plain(term.amount)}" for term in change.terms)
        lines.append(f"- change {change.table_name} {change.row_key} {change.field or ''}: {before} -> {after}" + (f" ({terms})" if terms else ""))
    for rumour in account.rumours:
        lines.append(f"- rumour carried by {rumour.carrier_name or 'unnamed'} at fidelity {rumour.fidelity} over {several(rumour.hops, 'hop', 'hops')}")
    lines += [f"- caused by incident {link.id} ({link.kind}, epoch {link.epoch})" + (f": {link.text}" if link.text else "") for link in account.causes]
    lines += [f"- led to incident {link.id} ({link.kind}, epoch {link.epoch})" + (f": {link.text}" if link.text else "") for link in account.effects]
    return lines


async def explain(call: WillCall, query: ExplainInput) -> WillResult:
    if (query.incident_id is None) == (query.node_id is None):
        return failed("Name one incident_id or one node_id.")
    async with call.database.read() as session:
        if query.incident_id is not None:
            try:
                account = await account_of(session, query.incident_id)
            except AeronaError as error:
                return failed(str(error))
            return await paged(call, W.EXPLAIN, query, account_lines(account), empty="This incident holds nothing more.")
        node_id = query.node_id or 0
        if await NodeRepository(session).kind_of(node_id) is None:
            return missing_node(node_id)
        graph = await causality_graph(session, node_id, query.depth)
    causes = {child: cause for cause, child in graph.edges}
    effects: dict[int, list[int]] = {}
    for cause, child in graph.edges:
        effects.setdefault(cause, []).append(child)
    lines = []
    for incident_id in sorted(graph.incidents, key=lambda key: (graph.incidents[key].epoch, key)):
        row = graph.incidents[incident_id]
        role = f" · as {spoken(graph.roles[incident_id])}" if incident_id in graph.roles else ""
        caused = f" · caused by {causes[incident_id]}" if incident_id in causes else ""
        led = f" · led to {', '.join(str(item) for item in sorted(effects.get(incident_id, [])))}" if incident_id in effects else ""
        lines.append(f"- incident {incident_id} · epoch {row.epoch}{role}{caused}{led}: {graph.texts.get(incident_id, row.kind)}")
    head = f"Causes and effects around node {node_id}. Ask explain with an incident_id for an incident's steps, terms and changes."
    return await paged(call, W.EXPLAIN, query, lines, head=head, empty="Nothing has happened to this node yet.")


async def state_at(call: WillCall, query: StateAtInput) -> WillResult:
    moment = Moment(year=query.year, season=query.season, day=query.day, hour=query.hour) if query.year is not None else None
    async with call.database.read() as session:
        try:
            page = await node_then(session, query.node_id, epoch=query.epoch, moment=moment)
        except AeronaError as error:
            return failed(str(error))
    lines: list[str] = []
    for row in page.rows:
        state = "existed then" if row.existed else "did not exist then"
        lines.append(f"## {row.table_name} {row.row_key} · {state} · {'exists now' if row.exists_now else 'gone now'}")
        lines += [f"- {item.field}: then {item.then or 'none'} · now {item.now or 'none'}" + (" · changed" if item.changed else "") for item in row.fields]
    head = f"Node {query.node_id} as it stood in epoch {query.epoch}" + (f", year {query.year}" if query.year is not None else "") + "."
    return await paged(call, W.STATE_AT, query, lines, head=head, empty="No record of this node at that moment.")


def ledger_statement(query: LedgerInput) -> Select[Any]:
    statement = select(LedgerEntryRow)
    if query.epoch is not None:
        statement = statement.where(LedgerEntryRow.epoch == query.epoch)
    if query.actor_kind is not None:
        statement = statement.where(LedgerEntryRow.actor_kind == query.actor_kind)
    if query.actor_node_id is not None:
        statement = statement.where(LedgerEntryRow.actor_node_id == query.actor_node_id)
    if query.tool:
        statement = statement.where(LedgerEntryRow.tool == query.tool)
    if query.undone is not None:
        statement = statement.where(LedgerEntryRow.undone.is_(query.undone))
    return statement.order_by(LedgerEntryRow.id.desc() if query.newest_first else LedgerEntryRow.id)


async def ledger(call: WillCall, query: LedgerInput) -> WillResult:
    statement = ledger_statement(query)
    async with call.database.read() as session:
        total = int(await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0)

        async def render(rows: Sequence[Any]) -> list[str]:
            changes: dict[int, list[LedgerChangeRow]] = {}
            for change in await session.scalars(
                select(LedgerChangeRow).where(LedgerChangeRow.entry_id.in_([row.id for row in rows])).order_by(LedgerChangeRow.entry_id, LedgerChangeRow.id)
            ):
                changes.setdefault(change.entry_id, []).append(change)
            lines = []
            for row in rows:
                state = " · undone" if row.undone else ""
                summary = f" · {row.input_summary}" if row.input_summary else ""
                body = [f"- entry {row.id} · epoch {row.epoch} · {row.actor_name} ({spoken(row.actor_kind)}) · {row.tool}{state}{summary}"]
                body += [change_text(change) for change in changes.get(row.id, [])]
                lines.append("\n".join(body))
            return lines

        head = f"{several(total, 'ledger entry', 'ledger entries')}; undo a creator entry with undo_action."
        return await paged_stream(call, W.LEDGER, query, streamed(session, statement, render), total, head=head, empty="No entry matches.")


async def overview_lines(session: AsyncSession) -> list[str]:
    lines: list[str] = []
    cosmos = await session.scalar(select(CosmosRow))
    if cosmos is None:
        return ["There is no world yet."]
    lines += [
        f"# {cosmos.name}",
        f"epoch: {cosmos.epoch} · lore language: {plain(cosmos.lore_language)}",
    ]
    for label, text in (("seed", cosmos.seed_idea), ("tone", cosmos.tone), ("cosmology", cosmos.cosmology)):
        if text:
            lines.append(f"## {label.capitalize()}")
            lines += paragraphs(text)
    creator = await session.scalar(select(CreatorRow))
    if creator is not None:
        lines.append(f"## The Creator\n{creator.name} (node {creator.id}) · essence {creator.essence}")
    counts = await session.execute(
        select(EntityRow.entity_type, EntityRow.status, func.count())
        .group_by(EntityRow.entity_type, EntityRow.status)
        .order_by(EntityRow.entity_type, EntityRow.status)
    )
    tally = [f"- {spoken(kind)} ({spoken(status)}): {amount}" for kind, status, amount in counts]
    if tally:
        lines += ["## Records by type", *tally]
    sons = list(await session.scalars(select(SonRow).order_by(SonRow.id)))
    names = await names_for(session, [son.current_world_id for son in sons if son.current_world_id is not None])
    if sons:
        lines.append("## Sons")
        lines += [
            f"- {son.name}, {son.title} (node {son.id}) · {spoken(son.status)} · {spoken(son.rarity)} · essence {son.essence}"
            + (f" · on {names.get(son.current_world_id, 'unnamed')} (node {son.current_world_id})" if son.current_world_id else "")
            for son in sons
        ]
    worlds = list(await session.scalars(select(WorldRow).order_by(WorldRow.id)))
    if worlds:
        lines.append("## Worlds")
        lines += [f"- {world.name} (node {world.id}) · {spoken(world.world_type)}" for world in worlds]
    stars = list(await session.scalars(select(StarRow).order_by(StarRow.id)))
    if stars:
        lines.append("## Stars")
        lines += [f"- {star.name} (node {star.id}) · {spoken(star.star_type)}" for star in stars]
    gods = list(await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)))
    if gods:
        lines.append("## Foreign gods")
        lines += [f"- {god.name} (node {god.id}) · {spoken(god.status)}" for god in gods]
    wars = await wars_under_way(session)
    lines.append(f"## Wars\n{several(wars, 'war', 'wars')} under way")
    return lines


async def world_overview(call: WillCall, query: PagedInput) -> WillResult:
    async with call.database.read() as session:
        lines = await overview_lines(session)
    return await paged(call, W.WORLD_OVERVIEW, query, lines, empty="There is no world yet.")


def tools() -> list[WillTool[Any]]:
    return [
        WillTool(W.READ_NODE, READ, ReadNodeInput, read_node),
        WillTool(W.READ_RECORDS, READ, ReadRecordsInput, read_records),
        WillTool(W.ENUMERATE, READ, EnumerateInput, enumerate_records),
        WillTool(W.GRAPH_NEIGHBOURS, READ, GraphNeighboursInput, graph_neighbours),
        WillTool(W.GRAPH_PATH, READ, GraphPathInput, graph_path),
        WillTool(W.CHRONICLE, READ, ChronicleInput, chronicle),
        WillTool(W.EXPLAIN, READ, ExplainInput, explain),
        WillTool(W.STATE_AT, READ, StateAtInput, state_at),
        WillTool(W.LEDGER, READ, LedgerInput, ledger),
        WillTool(W.WORLD_OVERVIEW, READ, PagedInput, world_overview),
    ]
