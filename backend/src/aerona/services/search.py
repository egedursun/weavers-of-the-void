import asyncio
import sqlite3
import unicodedata
from collections import deque
from dataclasses import dataclass, field, replace
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.rarities import RARITY_LABELS
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow, CouncilRow, LexemeRow, MessageRow
from aerona.db.tables.meta import MapNoteRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.rarity import Rarity
from aerona.rules.registry import Rules
from aerona.services.images.records import all_covers

MIN_QUERY_LENGTH = 2
SNIPPET_LENGTH = 110
SNIPPET_LEAD = 40
ELLIPSIS = "…"
DEFAULT_PATH_DEPTH = 6
TOKENIZER = "unicode61 remove_diacritics 2"
CREATED = "created"
INSIDE = "inside"
IN_WORLD = "in world"
ROUTE = "route"
CREATOR_OF = "creator of"
SON_BASE_SIZE = 4
SON_SIZE_STEP = 2
ENTITY_BASE_SIZE = 2
CREATOR_SIZE = SON_BASE_SIZE + Rarity.MYTHIC.rank * SON_SIZE_STEP
FOREIGN_GOD_SIZE = SON_BASE_SIZE + Rarity.LEGENDARY.rank * SON_SIZE_STEP
CREATOR_STATUS = "active"


class SearchCategory(StrEnum):
    SON = "son"
    FOREIGN_GOD = "foreign_god"
    WORLD = "world"
    STAR = "star"
    ENTITY = "entity"
    WORD = "word"
    EPOCH = "epoch"
    CHRONICLE = "chronicle"
    NOTE = "note"
    MAP_NOTE = "map_note"
    MESSAGE = "message"
    COUNCIL = "council"


@dataclass(frozen=True)
class SearchHit:
    category: SearchCategory
    id: int
    title: str
    subtitle: str | None
    snippet: str | None
    epoch: int | None = None


@dataclass(frozen=True)
class NameEntry:
    kind: NodeKind
    id: int
    name: str
    type: str
    status: str | None = None
    world_id: int | None = None
    cover: str | None = None


@dataclass(frozen=True)
class PathStep:
    source: int
    target: int
    kind: str
    forward: bool
    description: str | None


@dataclass(frozen=True)
class PathResult:
    path: list[int]
    names: dict[int, str]
    steps: list[PathStep]
    found: bool


@dataclass(frozen=True)
class GraphNode:
    id: int
    kind: NodeKind
    name: str
    type: str
    size: int
    epoch: int
    status: str
    creator_son_id: int | None = None
    location_id: int | None = None
    world_id: int | None = None


@dataclass(frozen=True)
class GraphLink:
    source: int
    target: int
    kind: BondKind
    epoch: int
    past: bool


@dataclass(frozen=True)
class Graph:
    nodes: list[GraphNode] = field(default_factory=list)
    links: list[GraphLink] = field(default_factory=list)


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def snippet(text: str, query: str) -> str:
    folded = fold(text)
    position = folded.find(fold(query))
    start = max(0, position - SNIPPET_LEAD) if position >= 0 else 0
    piece = text[start : start + SNIPPET_LENGTH]
    prefix = ELLIPSIS if start > 0 else ""
    suffix = ELLIPSIS if start + SNIPPET_LENGTH < len(text) else ""
    return f"{prefix}{piece}{suffix}".strip()


def match_expression(query: str) -> str:
    terms = [term.replace('"', "") for term in fold(query).split() if term]
    return " ".join(f'"{term}"*' for term in terms)


class SearchIndex:
    def __init__(self) -> None:
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.execute(
            f"CREATE VIRTUAL TABLE documents USING fts5(category UNINDEXED, record UNINDEXED, epoch UNINDEXED, title, body, tokenize='{TOKENIZER}')"
        )
        self._version: str | None = None
        self._lock = asyncio.Lock()

    @property
    def version(self) -> str | None:
        return self._version

    async def ensure(self, session: AsyncSession, version: str) -> None:
        async with self._lock:
            if self._version == version:
                return
            documents = await self._documents(session)
            self._connection.execute("DELETE FROM documents")
            self._connection.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?)", documents)
            self._connection.commit()
            self._version = version

    def invalidate(self) -> None:
        self._version = None

    async def _documents(self, session: AsyncSession) -> list[tuple[str, int, int | None, str, str]]:
        rows: list[tuple[str, int, int | None, str, str]] = []
        for son in await session.scalars(select(SonRow)):
            rows.append((SearchCategory.SON, son.id, son.birth_epoch, son.name, f"{son.title} {son.domain_primary.value} {son.domain_secondary.value}"))
        for god in await session.scalars(select(ForeignGodRow)):
            rows.append((SearchCategory.FOREIGN_GOD, god.id, god.created_epoch, god.name, f"{god.title or ''} {god.description or ''}"))
        for world in await session.scalars(select(WorldRow)):
            rows.append((SearchCategory.WORLD, world.id, world.created_epoch, world.name, f"{world.description or ''} {world.cosmology or ''}"))
        for star in await session.scalars(select(StarRow)):
            rows.append((SearchCategory.STAR, star.id, star.created_epoch, star.name, star.description or ""))
        for entity in await session.scalars(select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED)):
            depth = entity.depth.history if entity.depth is not None else ""
            rows.append((SearchCategory.ENTITY, entity.id, entity.birth_epoch, entity.name, f"{entity.subtype or ''} {entity.description} {depth}"))
            if entity.private_note:
                rows.append((SearchCategory.NOTE, entity.id, entity.birth_epoch, entity.name, entity.private_note))
        for word in await session.scalars(select(LexemeRow)):
            rows.append((SearchCategory.WORD, word.language_entity_id, word.epoch, word.word, word.meaning))
        for epoch in await session.scalars(select(EpochRow)):
            rows.append((SearchCategory.EPOCH, epoch.epoch, epoch.epoch, epoch.name or "", f"{epoch.narrative or ''} {epoch.summary or ''}"))
        for line in await session.scalars(select(ChronicleRow).where(ChronicleRow.kind != ChronicleKind.SYSTEM, shown_lines())):
            rows.append((SearchCategory.CHRONICLE, line.id, line.epoch, "", line.text))
        for note in await session.scalars(select(MapNoteRow)):
            rows.append((SearchCategory.MAP_NOTE, note.id, note.world_id, "", note.text))
        for message in await session.scalars(select(MessageRow)):
            rows.append((SearchCategory.MESSAGE, message.id, message.epoch, "", f"{message.text} {message.wish or ''}"))
        for council in await session.scalars(select(CouncilRow)):
            rows.append((SearchCategory.COUNCIL, council.id, council.epoch, council.topic, council.minutes.summary))
        return [(str(category), record, epoch, fold(title), fold(body)) for category, record, epoch, title, body in rows]

    def query(self, category: SearchCategory, query: str, limit: int) -> list[tuple[int, int | None, bool]]:
        if limit <= 0:
            return []
        expression = match_expression(query)
        if not expression:
            return []
        like = f"%{fold(query)}%"
        try:
            rows = self._connection.execute(
                "SELECT record, epoch, title LIKE ? FROM documents WHERE documents MATCH ? AND category = ? ORDER BY (title LIKE ?) DESC, record DESC LIMIT ?",
                (like, expression, str(category), like, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [(int(row[0]), int(row[1]) if row[1] is not None else None, bool(row[2])) for row in rows]


async def search(session: AsyncSession, rules: Rules, index: SearchIndex, query: str, version: str) -> list[SearchHit]:
    text = query.strip()
    if len(fold(text)) < MIN_QUERY_LENGTH:
        return []
    await index.ensure(session, version)
    server = rules.server
    limits = {
        SearchCategory.SON: server.search_sons,
        SearchCategory.FOREIGN_GOD: server.search_cosmos,
        SearchCategory.WORLD: server.search_cosmos,
        SearchCategory.STAR: server.search_cosmos,
        SearchCategory.ENTITY: server.search_entities,
        SearchCategory.WORD: server.search_lexicon,
        SearchCategory.EPOCH: server.search_epochs,
        SearchCategory.CHRONICLE: server.search_chronicle,
        SearchCategory.NOTE: server.search_personal_notes,
        SearchCategory.MAP_NOTE: server.search_map_notes,
        SearchCategory.MESSAGE: server.search_messages,
        SearchCategory.COUNCIL: server.search_councils,
    }
    hits: list[SearchHit] = []
    for category, limit in limits.items():
        for record, epoch, _by_name in index.query(category, text, limit):
            hits.append(await _hit(session, category, record, epoch, text))
            if len(hits) >= server.search_total:
                return hits
    return hits


async def _hit(session: AsyncSession, category: SearchCategory, record: int, epoch: int | None, query: str) -> SearchHit:
    title, subtitle, body = await _describe(session, category, record)
    return SearchHit(category=category, id=record, title=title, subtitle=subtitle, snippet=snippet(body, query) if body else None, epoch=epoch)


Description = tuple[str, str | None, str]
EMPTY_DESCRIPTION: Description = ("", None, "")


async def _describe_node(session: AsyncSession, record: int) -> Description:
    node = await NodeRepository(session).load(record)
    return node.name, getattr(node, "title", None), str(getattr(node, "description", "") or "")


async def _describe_entity(session: AsyncSession, record: int, note: bool) -> Description:
    entity = await session.get(EntityRow, record)
    if entity is None:
        return EMPTY_DESCRIPTION
    return entity.name, entity.entity_type.value, (entity.private_note or "") if note else entity.description


async def _describe_text(session: AsyncSession, category: SearchCategory, record: int) -> Description:
    if category is SearchCategory.WORD:
        return await NodeRepository(session).name_of(record) or "", None, ""
    if category is SearchCategory.EPOCH:
        epoch = await session.get(EpochRow, record)
        return (epoch.name or "", None, epoch.narrative or epoch.summary or "") if epoch else EMPTY_DESCRIPTION
    if category is SearchCategory.CHRONICLE:
        line = await session.get(ChronicleRow, record)
        return ("", None, line.text) if line else EMPTY_DESCRIPTION
    if category is SearchCategory.MAP_NOTE:
        note = await session.get(MapNoteRow, record)
        return ("", None, note.text) if note else EMPTY_DESCRIPTION
    if category is SearchCategory.MESSAGE:
        message = await session.get(MessageRow, record)
        return ("", message.intent.value, message.text) if message else EMPTY_DESCRIPTION
    council = await session.get(CouncilRow, record)
    return (council.topic, None, council.minutes.summary) if council else EMPTY_DESCRIPTION


NODE_CATEGORIES = frozenset({SearchCategory.SON, SearchCategory.FOREIGN_GOD, SearchCategory.WORLD, SearchCategory.STAR})


async def _describe(session: AsyncSession, category: SearchCategory, record: int) -> Description:
    if category in NODE_CATEGORIES:
        return await _describe_node(session, record)
    if category in {SearchCategory.ENTITY, SearchCategory.NOTE}:
        return await _describe_entity(session, record, category is SearchCategory.NOTE)
    return await _describe_text(session, category, record)


async def search_entities(session: AsyncSession, rules: Rules, query: str, limit: int | None = None) -> list[EntityRow]:
    needle = f"%{fold(query.strip())}%"
    if len(needle) - 2 < MIN_QUERY_LENGTH:
        return []
    cap = limit or rules.context.search_results_max
    statement = (
        select(EntityRow)
        .where(
            EntityRow.status != EntityStatus.REJECTED,
            or_(EntityRow.name.ilike(needle), EntityRow.subtype.ilike(needle), EntityRow.description.ilike(needle)),
        )
        .order_by(EntityRow.birth_epoch.desc(), EntityRow.id.desc())
        .limit(cap)
    )
    return list(await session.scalars(statement))


async def names_index(session: AsyncSession) -> list[NameEntry]:
    entries: list[NameEntry] = [
        NameEntry(NodeKind.ENTITY, entity.id, entity.name, entity.entity_type.value, entity.status.value, entity.world_id)
        for entity in await session.scalars(select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED).order_by(EntityRow.id))
    ]
    entries += [
        NameEntry(NodeKind.SON, son.id, son.name, RARITY_LABELS[son.rarity], son.status.value)
        for son in await session.scalars(select(SonRow).order_by(SonRow.id))
    ]
    entries += [
        NameEntry(NodeKind.FOREIGN_GOD, god.id, god.name, NodeKind.FOREIGN_GOD.value, god.status.value, god.world_id)
        for god in await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id))
    ]
    entries += [
        NameEntry(NodeKind.WORLD, world.id, world.name, world.world_type.value, world.discovery.value, world.id)
        for world in await session.scalars(select(WorldRow).order_by(WorldRow.id))
    ]
    entries += [
        NameEntry(NodeKind.STAR, star.id, star.name, star.star_type.value, None, None) for star in await session.scalars(select(StarRow).order_by(StarRow.id))
    ]
    entries += [
        NameEntry(NodeKind.GALAXY, row.id, row.name, row.galaxy_type.value, row.discovery.value, None)
        for row in await session.scalars(select(GalaxyRow).order_by(GalaxyRow.id))
    ]
    entries += [
        NameEntry(NodeKind.CLUSTER, row.id, row.name, row.cluster_kind.value, row.discovery.value, None)
        for row in await session.scalars(select(ClusterRow).order_by(ClusterRow.id))
    ]
    entries += [
        NameEntry(NodeKind.DIMENSION, row.id, row.name, row.dimension_kind.value, row.discovery.value, None)
        for row in await session.scalars(select(DimensionRow).order_by(DimensionRow.id))
    ]
    creator = await session.scalar(select(CreatorRow))
    if creator is not None:
        entries.append(NameEntry(NodeKind.CREATOR, creator.id, creator.name, NodeKind.CREATOR.value, None, None))
    covers = await all_covers(session)
    return [replace(entry, cover=covers.get(entry.id)) for entry in entries]


Neighbour = tuple[int, PathStep]


async def _bond_neighbours(session: AsyncSession, node_id: int) -> list[Neighbour]:
    bonds = await session.scalars(
        select(BondRow).where(or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id), BondRow.state == BondState.ACTIVE)
    )
    found: list[Neighbour] = []
    for bond in bonds:
        forward = bond.source_node_id == node_id
        other = bond.target_node_id if forward else bond.source_node_id
        found.append((other, PathStep(node_id, other, bond.kind.value, forward, bond.description)))
    return found


async def _entity_neighbours(session: AsyncSession, node_id: int) -> list[Neighbour]:
    entity = await session.get(EntityRow, node_id)
    if entity is None:
        return []
    found = [(entity.world_id, PathStep(node_id, entity.world_id, IN_WORLD, True, None))]
    if entity.location_id is not None:
        found.append((entity.location_id, PathStep(node_id, entity.location_id, INSIDE, True, None)))
    if entity.creator_son_id is not None:
        found.append((entity.creator_son_id, PathStep(node_id, entity.creator_son_id, CREATED, False, None)))
    return found


async def _son_neighbours(session: AsyncSession, node_id: int) -> list[Neighbour]:
    created = await session.scalars(select(EntityRow.id).where(EntityRow.creator_son_id == node_id, EntityRow.status != EntityStatus.REJECTED))
    found = [(entity_id, PathStep(node_id, entity_id, CREATED, True, None)) for entity_id in created]
    son = await session.get(SonRow, node_id)
    if son is not None and son.current_world_id is not None:
        found.append((son.current_world_id, PathStep(node_id, son.current_world_id, IN_WORLD, True, None)))
    creator = await session.scalar(select(CreatorRow.id))
    if creator is not None:
        found.append((creator, PathStep(node_id, creator, CREATOR_OF, False, None)))
    return found


async def _creator_neighbours(session: AsyncSession, node_id: int) -> list[Neighbour]:
    return [(son_id, PathStep(node_id, son_id, CREATOR_OF, True, None)) for son_id in await session.scalars(select(SonRow.id))]


async def _foreign_god_neighbours(session: AsyncSession, node_id: int) -> list[Neighbour]:
    god = await session.get(ForeignGodRow, node_id)
    return [(god.world_id, PathStep(node_id, god.world_id, IN_WORLD, True, None))] if god is not None else []


async def _world_neighbours(session: AsyncSession, node_id: int) -> list[Neighbour]:
    routes = await session.scalars(select(RouteRow).where(or_(RouteRow.world_a_id == node_id, RouteRow.world_b_id == node_id), RouteRow.active.is_(True)))
    found: list[Neighbour] = [
        (son_id, PathStep(node_id, son_id, IN_WORLD, False, None))
        for son_id in await session.scalars(select(SonRow.id).where(SonRow.current_world_id == node_id))
    ]
    found += [
        (god_id, PathStep(node_id, god_id, IN_WORLD, False, None))
        for god_id in await session.scalars(select(ForeignGodRow.id).where(ForeignGodRow.world_id == node_id))
    ]
    for route in routes:
        other = route.world_b_id if route.world_a_id == node_id else route.world_a_id
        found.append((other, PathStep(node_id, other, ROUTE, route.world_a_id == node_id, route.description)))
    return found


KIND_NEIGHBOURS = {
    NodeKind.ENTITY: _entity_neighbours,
    NodeKind.SON: _son_neighbours,
    NodeKind.CREATOR: _creator_neighbours,
    NodeKind.FOREIGN_GOD: _foreign_god_neighbours,
    NodeKind.WORLD: _world_neighbours,
}


async def _neighbours(session: AsyncSession, node_id: int, kind: NodeKind) -> list[Neighbour]:
    found = await _bond_neighbours(session, node_id)
    extra = KIND_NEIGHBOURS.get(kind)
    if extra is not None:
        found.extend(await extra(session, node_id))
    return found


async def neighbours(session: AsyncSession, node_id: int) -> list[Neighbour]:
    kind = await NodeRepository(session).kind_of(node_id)
    return await _neighbours(session, node_id, kind) if kind is not None else []


async def find_path(session: AsyncSession, first: int, second: int, max_depth: int = DEFAULT_PATH_DEPTH) -> PathResult:
    nodes = NodeRepository(session)
    kinds = await nodes.kinds_of([first, second])
    if first not in kinds or second not in kinds:
        return PathResult([], {}, [], False)
    if first == second:
        return PathResult([first], await nodes.names_of([first]), [], True)
    previous: dict[int, tuple[int, PathStep]] = {}
    frontier: deque[tuple[int, int]] = deque([(first, 0)])
    seen = {first}
    while frontier:
        node_id, depth = frontier.popleft()
        if depth >= max_depth:
            continue
        kind = await nodes.kind_of(node_id)
        if kind is None:
            continue
        for other, step in await _neighbours(session, node_id, kind):
            if other in seen:
                continue
            seen.add(other)
            previous[other] = (node_id, step)
            if other == second:
                return await _trace(session, first, second, previous)
            frontier.append((other, depth + 1))
    return PathResult([], {}, [], False)


async def _trace(session: AsyncSession, first: int, second: int, previous: dict[int, tuple[int, PathStep]]) -> PathResult:
    path = [second]
    steps: list[PathStep] = []
    current = second
    while current != first:
        parent, step = previous[current]
        steps.append(step)
        path.append(parent)
        current = parent
    path.reverse()
    steps.reverse()
    return PathResult(path, await NodeRepository(session).names_of(path), steps, True)


async def graph(session: AsyncSession) -> Graph:
    nodes: list[GraphNode] = []
    for son in await session.scalars(select(SonRow).order_by(SonRow.id)):
        nodes.append(
            GraphNode(
                son.id,
                NodeKind.SON,
                son.name,
                NodeKind.SON.value,
                SON_BASE_SIZE + son.rarity.rank * SON_SIZE_STEP,
                son.birth_epoch,
                son.status.value,
                world_id=son.current_world_id,
            )
        )
    visible = select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED, EntityRow.pending_name.is_(False)).order_by(EntityRow.id)
    for entity in await session.scalars(visible):
        nodes.append(
            GraphNode(
                entity.id,
                NodeKind.ENTITY,
                entity.name,
                entity.entity_type.value,
                ENTITY_BASE_SIZE + entity.power_level,
                entity.birth_epoch,
                entity.status.value,
                entity.creator_son_id,
                entity.location_id,
                entity.world_id,
            )
        )
    creator = await session.scalar(select(CreatorRow))
    if creator is not None:
        nodes.append(GraphNode(creator.id, NodeKind.CREATOR, creator.name, NodeKind.CREATOR.value, CREATOR_SIZE, 0, CREATOR_STATUS))
    for god in await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)):
        nodes.append(
            GraphNode(god.id, NodeKind.FOREIGN_GOD, god.name, NodeKind.FOREIGN_GOD.value, FOREIGN_GOD_SIZE, 0, god.status.value, world_id=god.world_id)
        )
    present = {node.id for node in nodes}
    links = [
        GraphLink(bond.source_node_id, bond.target_node_id, bond.kind, bond.epoch, bond.state is BondState.PAST)
        for bond in await session.scalars(select(BondRow).where(BondRow.state.in_([BondState.ACTIVE, BondState.PAST])).order_by(BondRow.id))
        if bond.source_node_id in present and bond.target_node_id in present and bond.source_node_id != bond.target_node_id
    ]
    return Graph(nodes, links)
