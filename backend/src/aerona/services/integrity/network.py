import statistics
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.bond_texts import MENTIONED_IN_FATE as MENTIONED
from aerona.constants.bond_texts import NAMES_IT as MENTIONS_IT
from aerona.constants.bond_texts import SYSTEM_RELATED_DESCRIPTIONS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondReviewRow, BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow, NetworkReviewRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import ArmyRow, CaptiveRow, WarRow, WarSideRow
from aerona.domain.enums.bond import VISIBLE_BOND_STATES, BondKind, BondRole, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, LIVING_STATUSES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.engine.phases.sky import eclipse_seers
from aerona.engine.primitives.manual import manual_context
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.integrity.pair_index import PairIndex
from aerona.services.integrity.structural_links import StructuralLinks
from aerona.services.names import find_named_records

PERCENT = 100
DECIMALS = 2
STRUCK = "the place it struck"
DIED_THERE = "died there"
SUBJECT = "its subject"
KEEPS_ALIVE = "keeps it alive"
TELLS = "tells it"
PRODUCED = "produced"
CREATED = "created"
FULFILLED = "fulfilled"
RUINS = "hidden in the ruins"
SIDE = "side of the war"
CAPTURED = "was captured"
COMMANDER = "commander"
WAR_KINDS = frozenset({EngineKind.WAR, EngineKind.BATTLE, EngineKind.SIEGE})


def died_in(entity: EntityRow, event: EntityRow) -> bool:
    if entity.status is not EntityStatus.DEAD:
        return False
    if entity.death_event_entity_id is not None:
        return entity.death_event_entity_id == event.id
    return entity.end_epoch == event.birth_epoch


NARRATIVE_TYPES = frozenset({EntityType.LEGEND, EntityType.TRADITION, EntityType.ARTWORK})
CARRIER_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT, EntityType.FACTION, EntityType.MORTAL})
CARRIER_KINDS = frozenset({BondKind.CELEBRATES, BondKind.TELLS_OF, BondKind.PRODUCED})
STRUCK_TYPES = COMMUNITY_TYPES | {EntityType.STRUCTURE}
PRIORITY_TYPES = (EntityType.EVENT, EntityType.LEGEND, EntityType.TRADITION)
VAGUE_ROLES = frozenset({BondRole.SIDE, BondRole.VICTOR, BondRole.LOSER})
DESTROYED_TEMPLE = "destroyed its temple"
DUPLICATE = "duplicate"
LEGACY_MENTIONED = "kaderinde an\u0131l\u0131r"
MENTION_DESCRIPTIONS = frozenset({MENTIONED, LEGACY_MENTIONED})
LEGACY_KIND_WORDS = {
    "yasar": BondKind.LIVES_IN,
    "bilir": BondKind.KNOWS,
    "ticaret": BondKind.TRADES_WITH,
    "sahip": BondKind.OWNS,
    "kutlar": BondKind.CELEBRATES,
    "yonetir": BondKind.RULES,
    "tapar": BondKind.WORSHIPS,
    "konusur": BondKind.SPEAKS,
    "korur": BondKind.PROTECTS,
    "sever": BondKind.LOVES,
    "uyesi": BondKind.MEMBER_OF,
    "komutan": BondKind.COMMANDS,
    "muttefik": BondKind.ALLY,
    "dusman": BondKind.ENEMY,
    "avlar": BondKind.HUNTS,
    "evcil": BondKind.TAMED,
    "esir": BondKind.HOLDS_CAPTIVE,
    "kaptan": BondKind.CAPTAIN_OF,
    "yolcusu": BondKind.PASSENGER_OF,
    "ustasi": BondKind.APPRENTICE_OF,
    "yoldas": BondKind.COMPANION,
    "hasim": BondKind.RIVAL,
    "pesinde": BondKind.PURSUES,
    "casus": BondKind.SPY_NETWORK,
    "ateskes": BondKind.TRUCE,
    "harac_oder": BondKind.PAYS_TRIBUTE,
    "icinde": BondKind.INSIDE,
}
ENGINE_RELATED = {
    "the foreign god who raised it": (BondKind.PRODUCED, True),
    "co-creator": (BondKind.PRODUCED, True),
    "mortal past": (BondKind.DESCENDS_FROM, False),
    "born from within": (BondKind.DESCENDS_FROM, False),
}


@dataclass(frozen=True)
class WeakNode:
    id: int
    name: str
    kind: str
    degree: int


@dataclass(frozen=True)
class RepairLogEntry:
    at: datetime
    kind: str
    text: str
    bonds: list[tuple[int, BondKind, int, str | None]] = field(default_factory=list)


class RepairLog:
    def __init__(self) -> None:
        self._entries: deque[RepairLogEntry] = deque()

    def add(self, entry: RepairLogEntry, limit: int) -> None:
        self._entries.appendleft(entry)
        while len(self._entries) > limit:
            self._entries.pop()

    def recent(self, limit: int) -> list[RepairLogEntry]:
        return list(self._entries)[:limit]

    def clear(self) -> None:
        self._entries.clear()


@dataclass(frozen=True)
class NetworkHealth:
    nodes: int
    edges: int
    past_edges: int
    active_edges: int
    mean_degree: float
    median_degree: float
    density: float
    components: int
    largest_component: int
    largest_share_pct: float
    isolated: int
    single_link: int
    weak: int
    related: int
    related_undescribed: int
    related_to_review: int
    weakest: list[WeakNode]
    log: list[RepairLogEntry]
    priority: int
    healthy: bool


@dataclass
class RepairCounters:
    inside: int = 0
    caused: int = 0
    produced: int = 0
    event: int = 0
    narrative: int = 0
    prophecy: int = 0
    remnant: int = 0
    destruction: int = 0
    lost: int = 0
    dead_language: int = 0
    related_converted: int = 0
    structure: int = 0
    mentioned: int = 0
    cleaned: int = 0

    @property
    def total(self) -> int:
        return (
            self.inside
            + self.caused
            + self.produced
            + self.event
            + self.narrative
            + self.prophecy
            + self.remnant
            + self.destruction
            + self.structure
            + self.mentioned
        )

    def as_dict(self) -> dict[str, int]:
        return {**self.__dict__, "total": self.total}


@dataclass
class Graph:
    nodes: dict[int, tuple[str, str]]
    degree: Counter[int]
    edges: list[BondRow]


async def visible_graph(session: AsyncSession) -> Graph:
    nodes: dict[int, tuple[str, str]] = {}
    living = select(EntityRow.id, EntityRow.name, EntityRow.entity_type).where(EntityRow.status.in_(list(LIVING_STATUSES)), EntityRow.pending_name.is_(False))
    for entity_id, name, entity_type in await session.execute(living):
        nodes[entity_id] = (name, entity_type.value)
    for son_id, name in await session.execute(select(SonRow.id, SonRow.name)):
        nodes[son_id] = (name, "son")
    for god_id, name in await session.execute(select(ForeignGodRow.id, ForeignGodRow.name)):
        nodes[god_id] = (name, "foreign_god")
    creator = await CosmosRepository(session).creator()
    if creator is not None:
        nodes[creator.id] = (creator.name, "creator")
    edges = [
        bond
        for bond in await session.scalars(select(BondRow).where(BondRow.state.in_(list(VISIBLE_BOND_STATES))))
        if bond.source_node_id in nodes and bond.target_node_id in nodes and bond.source_node_id != bond.target_node_id
    ]
    degree: Counter[int] = Counter()
    for bond in edges:
        degree[bond.source_node_id] += 1
        degree[bond.target_node_id] += 1
    return Graph(nodes, degree, edges)


async def related_awaiting_review(session: AsyncSession) -> int:
    statement = (
        select(func.count())
        .select_from(BondRow)
        .where(
            BondRow.kind == BondKind.RELATED,
            BondRow.state == BondState.ACTIVE,
            BondRow.description.is_not(None),
            BondRow.role.is_(None),
            BondRow.description.not_in(list(SYSTEM_RELATED_DESCRIPTIONS)),
            BondRow.id.not_in(select(BondReviewRow.bond_id)),
        )
    )
    return int(await session.scalar(statement) or 0)


def components(graph: Graph) -> list[int]:
    parent = {node: node for node in graph.nodes}

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for bond in graph.edges:
        first, second = find(bond.source_node_id), find(bond.target_node_id)
        if first != second:
            parent[first] = second
    sizes = Counter(find(node) for node in graph.nodes)
    return sorted(sizes.values(), reverse=True)


async def _importance(session: AsyncSession) -> dict[int, int]:
    return {entity_id: importance or 0 for entity_id, importance in await session.execute(select(EntityRow.id, EntityRow.importance))}


async def health(session: AsyncSession, rules: Rules, log: RepairLog, epoch: int) -> NetworkHealth:
    graph = await visible_graph(session)
    network = rules.link_graph
    count = len(graph.nodes)
    degrees = [graph.degree.get(node, 0) for node in graph.nodes]
    sizes = components(graph)
    largest = sizes[0] if sizes else 0
    importance = await _importance(session)
    weakest = sorted(graph.nodes, key=lambda node: (graph.degree.get(node, 0), -importance.get(node, 0), node))[: network.summary_list]
    related = [bond for bond in graph.edges if bond.kind is BondKind.RELATED and bond.state is BondState.ACTIVE]
    share = round(largest / count * PERCENT, DECIMALS) if count else 0.0
    return NetworkHealth(
        nodes=count,
        edges=len(graph.edges),
        past_edges=sum(1 for bond in graph.edges if bond.state is BondState.PAST),
        active_edges=sum(1 for bond in graph.edges if bond.state is BondState.ACTIVE),
        mean_degree=round(sum(degrees) / count, DECIMALS) if count else 0.0,
        median_degree=float(statistics.median(degrees)) if degrees else 0.0,
        density=round(2 * len(graph.edges) / (count * (count - 1)), DECIMALS + 2) if count > 1 else 0.0,
        components=len(sizes),
        largest_component=largest,
        largest_share_pct=share,
        isolated=sum(1 for value in degrees if value == 0),
        single_link=sum(1 for value in degrees if value == 1),
        weak=sum(1 for value in degrees if value <= network.weak_degree),
        related=len(related),
        related_undescribed=sum(1 for bond in related if not bond.description),
        related_to_review=await related_awaiting_review(session),
        weakest=[WeakNode(node, graph.nodes[node][0], graph.nodes[node][1], graph.degree.get(node, 0)) for node in weakest],
        log=log.recent(network.summary_list),
        priority=len(await priority_records(session, rules, epoch, network.summary_list)),
        healthy=share > network.main_cluster_healthy_pct,
    )


class DanglingEndRepair:
    def __init__(self, session: AsyncSession, rules: Rules, epoch: int) -> None:
        self.session = session
        self.rules = rules
        self.epoch = epoch
        self.bonds = BondRepository(session)
        self.counters = RepairCounters()
        self.added: list[tuple[int, BondKind, int, str | None]] = []
        self.index = PairIndex()
        self._fated: list[EntityRow] = []
        self._tree: dict[int, list[EntityRow]] | None = None

    async def single(
        self, source: int, target: int, kind: BondKind, description: str | None, *, epoch: int | None = None, role: BondRole | None = None
    ) -> bool:
        if source == target or self.index.kind_between(source, target, kind):
            return False
        bond = await self.bonds.connect(BondDraft(source, target, kind, epoch if epoch is not None else self.epoch, description=description, role=role))
        self.index.add_visible(bond.source_node_id, bond.target_node_id, bond.kind)
        self.added.append((source, kind, target, description))
        return True

    async def _visible_degree(self, node_id: int) -> int:
        return self.index.degree[node_id]

    async def _living(self, types: list[EntityType] | None = None) -> list[EntityRow]:
        statement = select(EntityRow).where(EntityRow.status.in_(list(LIVING_STATUSES)), EntityRow.pending_name.is_(False))
        if types is not None:
            statement = statement.where(EntityRow.entity_type.in_(types))
        return list(await self.session.scalars(statement.order_by(EntityRow.id)))

    async def run(self) -> RepairCounters:
        await self.convert_vague()
        await self.dedupe_mentions()
        self.index = await PairIndex.load(self.session)
        await self.inside()
        await self.events_to_places()
        await self.lost_and_dead()
        await self.prophecies()
        await self.previous_creation()
        await self.destruction()
        await self.event_centres()
        await self.narratives()
        self.counters.structure += await StructuralLinks(self.session, self.single, self.index).run()
        await self.isolated()
        await self.named_isolated()
        await self.named_isolated_gods()
        return self.counters

    async def _kind_between(self, first: int, second: int, kind: BondKind, exclude: int | None = None) -> bool:
        if exclude is None and self.index.every:
            return self.index.kind_between(first, second, kind)
        statement = select(BondRow.id).where(
            BondRow.kind == kind,
            BondRow.state.in_(list(VISIBLE_BOND_STATES)),
            ((BondRow.source_node_id == first) & (BondRow.target_node_id == second)) | ((BondRow.source_node_id == second) & (BondRow.target_node_id == first)),
        )
        if exclude is not None:
            statement = statement.where(BondRow.id != exclude)
        return await self.session.scalar(statement.limit(1)) is not None

    async def _retype(self, bond: BondRow, kind: BondKind, description: str | None, swap: bool) -> None:
        source, target = (bond.target_node_id, bond.source_node_id) if swap else (bond.source_node_id, bond.target_node_id)
        if await self._kind_between(source, target, kind, exclude=bond.id):
            await self.bonds.deactivate(bond, self.epoch, DUPLICATE, state=BondState.HIDDEN_CLOSED)
            self.counters.cleaned += 1
            return
        normalized = await self.bonds.normalize(BondDraft(source, target, kind, bond.epoch, description))
        if normalized.kind is not kind:
            bond.description = kind.value.replace("_", " ") + (f": {description}" if description else "")
            return
        bond.source_node_id = normalized.source_node_id
        bond.target_node_id = normalized.target_node_id
        bond.kind = kind
        bond.description = normalized.description
        self.counters.related_converted += 1

    async def convert_vague(self) -> None:
        statement = select(BondRow).where(BondRow.kind == BondKind.RELATED, BondRow.state == BondState.ACTIVE)
        for bond in list(await self.session.scalars(statement)):
            if bond.role in VAGUE_ROLES:
                bond.kind = BondKind.PARTY_TO
                self.counters.related_converted += 1
                continue
            description = (bond.description or "").strip()
            if description in ENGINE_RELATED:
                kind, swap = ENGINE_RELATED[description]
                await self._retype(bond, kind, description, swap)
                continue
            word, _, rest = description.partition(":")
            kind_word = LEGACY_KIND_WORDS.get(word.strip())
            if kind_word is not None:
                await self._retype(bond, kind_word, rest.strip() or None, False)
        await self.session.flush()

    async def dedupe_mentions(self) -> None:
        statement = select(BondRow).where(
            BondRow.kind == BondKind.RELATED,
            BondRow.state == BondState.ACTIVE,
            (BondRow.role == BondRole.MENTIONED_IN_FATE) | BondRow.description.in_(list(MENTION_DESCRIPTIONS)),
        )
        for bond in list(await self.session.scalars(statement)):
            if bond.description == LEGACY_MENTIONED:
                bond.description = MENTIONED
                bond.role = BondRole.MENTIONED_IN_FATE
            others = select(BondRow.id).where(
                BondRow.id != bond.id,
                BondRow.state.in_(list(VISIBLE_BOND_STATES)),
                ((BondRow.source_node_id == bond.source_node_id) & (BondRow.target_node_id == bond.target_node_id))
                | ((BondRow.source_node_id == bond.target_node_id) & (BondRow.target_node_id == bond.source_node_id)),
            )
            if await self.session.scalar(others.limit(1)) is not None:
                await self.bonds.deactivate(bond, self.epoch, DUPLICATE, state=BondState.HIDDEN_CLOSED)
                self.counters.cleaned += 1
        await self.session.flush()

    async def destruction(self) -> None:
        gods = list(await self.session.scalars(select(ForeignGodRow)))
        if not gods:
            return
        statement = (
            select(ChronicleRow, ChronicleEntityRow.entity_id)
            .join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRow.id)
            .where(ChronicleRow.kind == ChronicleKind.FOREIGN_GOD)
        )
        for line, entity_id in list(await self.session.execute(statement)):
            temple = await self.session.get(EntityRow, entity_id)
            if temple is None or temple.engine_kind is not EngineKind.TEMPLE or temple.status is not EntityStatus.DESTROYED:
                continue
            god = next((item for item in gods if line.text.startswith(item.name)), None)
            if god is None or await self._kind_between(god.id, temple.id, BondKind.DESTROYED):
                continue
            self.counters.destruction += await self.single(god.id, temple.id, BondKind.DESTROYED, DESTROYED_TEMPLE, epoch=line.epoch)

    async def inside(self) -> None:
        statuses = {entity_id: status for entity_id, status in await self.session.execute(select(EntityRow.id, EntityRow.status))}
        for entity in await self._living():
            if entity.status is EntityStatus.DEAD:
                for bond in await self.bonds.outgoing(entity.id, BondKind.INSIDE):
                    if bond.role is not BondRole.SPIRIT_BINDING:
                        await self.bonds.deactivate(bond, entity.end_epoch if entity.end_epoch is not None else self.epoch)
                        self.counters.cleaned += 1
            location = entity.location_id
            if location is None or statuses.get(location) not in LIVING_STATUSES:
                continue
            if self.index.any_between(entity.id, location):
                continue
            if entity.status is EntityStatus.DEAD:
                bond = await self.bonds.connect(BondDraft(entity.id, location, BondKind.INSIDE, self.epoch))
                await self.bonds.deactivate(bond, entity.end_epoch if entity.end_epoch is not None else self.epoch)
                self.index.add_visible(entity.id, location, BondKind.INSIDE)
                self.added.append((entity.id, BondKind.INSIDE, location, None))
                self.counters.inside += 1
                continue
            self.counters.inside += await self.single(entity.id, location, BondKind.INSIDE, None)

    async def _any_between(self, first: int, second: int) -> bool:
        return self.index.any_between(first, second)

    async def events_to_places(self) -> None:
        for event in await self._living([EntityType.EVENT]):
            if event.location_id is None:
                continue
            outgoing = await self.bonds.outgoing(event.id, active_only=False)
            if any(bond.kind is BondKind.CAUSED for bond in outgoing) or any(
                bond.kind is not BondKind.INSIDE and bond.state in VISIBLE_BOND_STATES for bond in await self.bonds.touching(event.id, VISIBLE_BOND_STATES)
            ):
                continue
            self.counters.caused += await self.single(event.id, event.location_id, BondKind.CAUSED, STRUCK)

    async def lost_and_dead(self) -> None:
        entities = EntityRepository(self.session)
        for knowledge in await self._living([EntityType.KNOWLEDGE]):
            if not await self.bonds.incoming(knowledge.id, BondKind.KNOWS) and await entities.add_flag(knowledge.id, EntityFlag.LOST, self.epoch):
                self.counters.lost += 1
        for language in await self._living([EntityType.LANGUAGE]):
            if not await self.bonds.incoming(language.id, BondKind.SPEAKS) and await entities.add_flag(language.id, EntityFlag.DEAD_LANGUAGE, self.epoch):
                self.counters.dead_language += 1

    async def prophecies(self) -> None:
        for prophecy in await self._living([EntityType.PROPHECY]):
            if prophecy.engine_kind is EngineKind.ECLIPSE_PROPHECY and await self._visible_degree(prophecy.id) == 0:
                world = await self.session.get(WorldRow, prophecy.world_id)
                if world is not None:
                    ctx = await manual_context(self.session, "network.eclipse", self.rules)
                    self.counters.prophecy += len(await eclipse_seers(ctx, prophecy, world))
            if prophecy.status is not EntityStatus.FULFILLED or await self.bonds.outgoing(prophecy.id, BondKind.PROPHESIES):
                continue
            for named in await find_named_records(self.session, self.rules, prophecy.fate_note or "", world_id=prophecy.world_id, exclude=[prophecy.id]):
                self.counters.prophecy += await self.single(prophecy.id, named.id, BondKind.PROPHESIES, FULFILLED, role=BondRole.FULFILLED_PROPHECY)

    async def previous_creation(self) -> None:
        flagged = set(await self.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.PREVIOUS_CREATION)))
        if not flagged:
            return
        places = [entity for entity in await self._living([EntityType.PLACE, EntityType.REGION, EntityType.STRUCTURE]) if entity.id in flagged]
        for knowledge in await self._living([EntityType.KNOWLEDGE]):
            if knowledge.id not in flagged or await self.bonds.incoming(knowledge.id, BondKind.SOURCE_OF, active_only=False):
                continue
            ruin = next((place for place in places if place.world_id == knowledge.world_id), None)
            if ruin is not None:
                self.counters.remnant += await self.single(ruin.id, knowledge.id, BondKind.SOURCE_OF, RUINS)

    async def event_centres(self) -> None:
        disasters = set(await self.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DISASTER)))
        noted = select(EntityRow).where(EntityRow.status.in_(list(LIVING_STATUSES)), EntityRow.pending_name.is_(False), EntityRow.fate_note.is_not(None))
        self._fated = list(await self.session.scalars(noted))
        for event in await self._living([EntityType.EVENT]):
            if event.id in disasters:
                await self._disaster(event)
            if event.engine_kind in WAR_KINDS:
                await self._war(event)
            await self._mentions(event)

    async def _children(self) -> dict[int, list[EntityRow]]:
        if self._tree is None:
            tree: dict[int, list[EntityRow]] = {}
            for entity in await self.session.scalars(select(EntityRow).where(EntityRow.location_id.is_not(None))):
                tree.setdefault(entity.location_id or 0, []).append(entity)
            self._tree = tree
        return self._tree

    async def _descendants(self, root: int) -> list[EntityRow]:
        tree = await self._children()
        found: list[EntityRow] = []
        frontier = deque([root])
        seen = {root}
        while frontier:
            current = frontier.popleft()
            for child in tree.get(current, []):
                if child.id not in seen:
                    seen.add(child.id)
                    found.append(child)
                    frontier.append(child.id)
        return found

    async def _disaster(self, event: EntityRow) -> None:
        caused = [bond.target_node_id for bond in await self.bonds.outgoing(event.id, BondKind.CAUSED, active_only=False)]
        target = caused[0] if caused else event.location_id
        if target is None:
            return
        for entity in await self._descendants(target):
            alive_then = entity.birth_epoch <= event.birth_epoch and (entity.end_epoch is None or entity.end_epoch >= event.birth_epoch)
            if entity.entity_type in STRUCK_TYPES and alive_then and entity.status in LIVING_STATUSES:
                self.counters.event += await self.single(event.id, entity.id, BondKind.CAUSED, STRUCK, epoch=event.birth_epoch)
            elif entity.entity_type is EntityType.MORTAL and died_in(entity, event):
                self.counters.event += await self.single(event.id, entity.id, BondKind.CAUSED, DIED_THERE, epoch=event.birth_epoch)

    async def _war(self, event: EntityRow) -> None:
        war = await self.session.scalar(select(WarRow).where(WarRow.event_entity_id == event.id))
        if war is None:
            return
        for side in await self.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id)):
            self.counters.event += await self.single(side.entity_id, event.id, BondKind.PARTY_TO, SIDE, role=BondRole.SIDE)
        for captive in await self.session.scalars(select(CaptiveRow).where(CaptiveRow.war_id == war.id)):
            self.counters.event += await self.single(event.id, captive.captive_entity_id, BondKind.CAUSED, CAPTURED)
        for army in await self.session.scalars(select(ArmyRow).where(ArmyRow.war_id == war.id, ArmyRow.commander_entity_id.is_not(None))):
            if army.commander_entity_id is not None:
                self.counters.event += await self.single(army.commander_entity_id, event.id, BondKind.PARTY_TO, COMMANDER, role=BondRole.COMMANDER)

    async def _mentions(self, event: EntityRow) -> None:
        if len(event.name) < self.rules.link_graph.name_min_chars:
            return
        mentioned = [entity for entity in self._fated if entity.id != event.id and event.name in (entity.fate_note or "")]
        for entity in mentioned:
            epoch = max(event.birth_epoch, entity.birth_epoch)
            if died_in(entity, event):
                if not await self._kind_between(event.id, entity.id, BondKind.CAUSED):
                    self.counters.event += await self.single(event.id, entity.id, BondKind.CAUSED, DIED_THERE, epoch=epoch)
            elif not await self._any_visible_between(event.id, entity.id):
                self.counters.event += await self.single(event.id, entity.id, BondKind.RELATED, MENTIONED, epoch=epoch, role=BondRole.MENTIONED_IN_FATE)

    async def narratives(self) -> None:
        cap = self.rules.link_graph.subject_cap
        for record in await self._living(list(NARRATIVE_TYPES)):
            text = f"{record.description} {record.fate_note or ''}"
            subjects = await find_named_records(self.session, self.rules, text, world_id=record.world_id, exclude=[record.id], limit=cap)
            for subject in subjects:
                if not await self._any_visible_between(record.id, subject.id):
                    self.counters.narrative += await self.single(record.id, subject.id, BondKind.TELLS_OF, SUBJECT)
            await self._carrier(record, subjects)

    async def _any_visible_between(self, first: int, second: int) -> bool:
        return self.index.visible_between(first, second)

    async def _narrated_between(self, first: int, second: int) -> bool:
        statement = select(BondRow.id).where(
            BondRow.kind.in_([BondKind.TELLS_OF, BondKind.CELEBRATES]),
            BondRow.state.in_(list(VISIBLE_BOND_STATES)),
            ((BondRow.source_node_id == first) & (BondRow.target_node_id == second)) | ((BondRow.source_node_id == second) & (BondRow.target_node_id == first)),
        )
        return await self.session.scalar(statement.limit(1)) is not None

    async def _carrier(self, record: EntityRow, subjects: list[EntityRow]) -> None:
        for bond in await self.bonds.incoming(record.id, active_only=False):
            if bond.kind in CARRIER_KINDS and bond.state in VISIBLE_BOND_STATES:
                source = await self.session.get(EntityRow, bond.source_node_id)
                if source is not None and source.entity_type in CARRIER_TYPES:
                    return
        carrier: EntityRow | None = None
        maker = await self.session.get(EntityRow, record.maker_entity_id) if record.maker_entity_id is not None else None
        location = await self.session.get(EntityRow, record.location_id) if record.location_id is not None else None
        if maker is not None and maker.entity_type in CARRIER_TYPES:
            carrier = maker
        elif location is not None and location.entity_type in COMMUNITY_TYPES:
            carrier = location
        else:
            carrier = next((subject for subject in subjects if subject.entity_type in COMMUNITY_TYPES), None)
        if carrier is None:
            return
        if await self._narrated_between(carrier.id, record.id):
            return
        kind, description = (BondKind.CELEBRATES, KEEPS_ALIVE) if record.entity_type is EntityType.TRADITION else (BondKind.TELLS_OF, TELLS)
        self.counters.narrative += await self.single(carrier.id, record.id, kind, description)

    async def isolated(self) -> None:
        for entity in await self._living():
            if await self._visible_degree(entity.id) > 0:
                continue
            if entity.maker_entity_id is not None and await self.session.get(EntityRow, entity.maker_entity_id) is not None:
                self.counters.produced += await self.single(entity.maker_entity_id, entity.id, BondKind.PRODUCED, PRODUCED)
            elif entity.creator_son_id is not None:
                self.counters.produced += await self.single(entity.creator_son_id, entity.id, BondKind.PRODUCED, CREATED)

    async def _mentioning(self, name: str, exclude: int, limit: int) -> list[EntityRow]:
        statement = (
            select(EntityRow)
            .where(
                EntityRow.status.in_(list(LIVING_STATUSES)),
                EntityRow.pending_name.is_(False),
                EntityRow.id != exclude,
                EntityRow.description.contains(name) | EntityRow.fate_note.contains(name),
            )
            .order_by(EntityRow.importance.desc(), EntityRow.id)
            .limit(limit)
        )
        return list(await self.session.scalars(statement))

    async def named_isolated_gods(self) -> None:
        minimum = self.rules.link_graph.name_min_chars
        cap = self.rules.link_graph.proposal_cap
        for god in list(await self.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id))):
            if len(god.name) < minimum or await self._visible_degree(god.id) > 0:
                continue
            for mentioner in await self._mentioning(god.name, god.id, cap):
                self.counters.mentioned += await self.single(mentioner.id, god.id, BondKind.RELATED, MENTIONS_IT)
            if await self._visible_degree(god.id) > 0:
                continue
            text = f"{god.description or ''} {god.title or ''}"
            for named in await find_named_records(self.session, self.rules, text, world_id=god.world_id, exclude=[god.id], limit=cap):
                self.counters.mentioned += await self.single(god.id, named.id, BondKind.RELATED, MENTIONS_IT)

    async def named_isolated(self) -> None:
        minimum = self.rules.link_graph.name_min_chars
        cap = self.rules.link_graph.proposal_cap
        for entity in await self._living():
            if len(entity.name) < minimum or await self._visible_degree(entity.id) > 0:
                continue
            for mentioner in await self._mentioning(entity.name, entity.id, cap):
                self.counters.mentioned += await self.single(mentioner.id, entity.id, BondKind.RELATED, MENTIONS_IT)
            if await self._visible_degree(entity.id) > 0:
                continue
            text = f"{entity.description} {entity.fate_note or ''}"
            for named in await find_named_records(self.session, self.rules, text, world_id=entity.world_id, exclude=[entity.id], limit=cap):
                self.counters.mentioned += await self.single(entity.id, named.id, BondKind.RELATED, MENTIONS_IT)


async def repair_dangling_ends(session: AsyncSession, rules: Rules, epoch: int, log: RepairLog, bus: EventBus | None = None) -> RepairCounters:
    repair = DanglingEndRepair(session, rules, epoch)
    counters = await repair.run()
    text = (
        f"{counters.total} dangling ends connected (inside {counters.inside}, struck place {counters.caused}, event {counters.event}, "
        f"narrative {counters.narrative}, prophecy {counters.prophecy}, ruin {counters.remnant}, destruction {counters.destruction}, "
        f"structure {counters.structure}, produced {counters.produced}, named {counters.mentioned}); "
        f"{counters.related_converted} vague bonds converted to concrete types, {counters.cleaned} duplicates hidden."
    )
    log.add(RepairLogEntry(datetime.now(UTC), "rule", text, repair.added), rules.link_graph.summary_list)
    if bus is not None:
        bus.publish(EventKind.NETWORK_REPAIRED, {"kind": "rule", "text": text, **counters.as_dict()})
    return counters


async def _recently_reviewed(session: AsyncSession, rules: Rules, epoch: int) -> set[int]:
    statement = select(NetworkReviewRow.entity_id).where(NetworkReviewRow.epoch > epoch - rules.link_graph.revisit_epochs)
    return set(await session.scalars(statement))


async def weak_records(session: AsyncSession, rules: Rules, epoch: int, limit: int | None = None) -> list[EntityRow]:
    graph = await visible_graph(session)
    reviewed = await _recently_reviewed(session, rules, epoch)
    importance = await _importance(session)
    candidates = [
        entity
        for entity in await session.scalars(select(EntityRow).where(EntityRow.status.in_(list(LIVING_STATUSES)), EntityRow.pending_name.is_(False)))
        if entity.id not in reviewed and graph.degree.get(entity.id, 0) <= rules.link_graph.weak_degree
    ]
    candidates.sort(key=lambda entity: (graph.degree.get(entity.id, 0), -importance.get(entity.id, 0), entity.id))
    return candidates[: limit or rules.link_graph.fate_batch]


async def _co_mentions(session: AsyncSession, entity_id: int) -> Counter[int]:
    lines = select(ChronicleEntityRow.chronicle_id).where(ChronicleEntityRow.entity_id == entity_id)
    statement = select(ChronicleEntityRow.entity_id).where(ChronicleEntityRow.chronicle_id.in_(lines), ChronicleEntityRow.entity_id != entity_id)
    return Counter(await session.scalars(statement))


async def priority_records(session: AsyncSession, rules: Rules, epoch: int, limit: int) -> list[tuple[EntityRow, int]]:
    reviewed = await _recently_reviewed(session, rules, epoch)
    living = set(await session.scalars(select(EntityRow.id).where(EntityRow.status.in_(list(LIVING_STATUSES)))))
    importance = await _importance(session)
    ranked: list[tuple[EntityRow, int]] = []
    statement = select(EntityRow).where(
        EntityRow.entity_type.in_(list(PRIORITY_TYPES)), EntityRow.status.in_(list(LIVING_STATUSES)), EntityRow.pending_name.is_(False)
    )
    for record in await session.scalars(statement):
        if record.id in reviewed:
            continue
        bonded = {bond.other_end(record.id) for bond in await BondRepository(session).touching(record.id, VISIBLE_BOND_STATES)}
        unbonded = [other for other in await _co_mentions(session, record.id) if other in living and other not in bonded]
        if unbonded:
            ranked.append((record, len(unbonded)))
    ranked.sort(key=lambda item: (-item[1], -importance.get(item[0].id, 0), item[0].id))
    return ranked[:limit]


@dataclass(frozen=True)
class Candidate:
    id: int
    reason: str


async def candidate_neighbours(session: AsyncSession, rules: Rules, record: EntityRow) -> list[Candidate]:
    network = rules.link_graph
    cap = max(network.proposal_cap, network.event_proposal_cap) if record.entity_type is EntityType.EVENT else network.proposal_cap
    width = max(network.candidates, cap * 2)
    found: dict[int, str] = {}
    for other, _count in (await _co_mentions(session, record.id)).most_common(width):
        found.setdefault(other, "mentioned together in the chronicle")
    if record.location_id is not None:
        found.setdefault(record.location_id, "its location")
    if record.maker_entity_id is not None:
        found.setdefault(record.maker_entity_id, "its maker")
    if record.creator_son_id is not None:
        found.setdefault(record.creator_son_id, "its creator")
    if record.location_id is not None:
        siblings = await session.scalars(
            select(EntityRow.id)
            .where(EntityRow.location_id == record.location_id, EntityRow.id != record.id, EntityRow.status.in_(list(LIVING_STATUSES)))
            .order_by(func.coalesce(EntityRow.importance, 0).desc())
            .limit(network.candidates)
        )
        for sibling in siblings:
            found.setdefault(sibling, "same place")
    important = await session.scalars(
        select(EntityRow.id)
        .where(
            EntityRow.world_id == record.world_id,
            EntityRow.id != record.id,
            EntityRow.entity_type != EntityType.REGION,
            EntityRow.status.in_(list(LIVING_STATUSES)),
        )
        .order_by(func.coalesce(EntityRow.importance, 0).desc())
        .limit(network.candidates)
    )
    for other in important:
        found.setdefault(other, "important in its world")
    found.pop(record.id, None)
    return [Candidate(node_id, reason) for node_id, reason in list(found.items())[: width * 2]]


async def mark_reviewed(session: AsyncSession, entity_ids: list[int], epoch: int) -> None:
    for entity_id in dict.fromkeys(entity_ids):
        row = await session.get(NetworkReviewRow, entity_id)
        if row is None:
            session.add(NetworkReviewRow(entity_id=entity_id, epoch=epoch))
        else:
            row.epoch = epoch
    await session.flush()
