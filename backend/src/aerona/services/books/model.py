from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.entity_types import entity_type_spec
from aerona.catalog.knowledge import KNOWLEDGE_BRANCHES, NATURAL_LAWS
from aerona.catalog.powers import POWERS, power_unlock_levels
from aerona.catalog.rarities import RARITY_LABELS, entity_rarity
from aerona.catalog.scenarios import SCENARIOS
from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.catalog.stats import PASSIONS, STATS
from aerona.catalog.worlds import ATMOSPHERE_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow, EntityTagRow
from aerona.db.tables.epochs import EpochRow, EpochStatsRow, EpochWorldNarrativeRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.lore import CanonFactRow, ChronicleEntityRow, ChronicleRow, CouncilRow, FolkBeliefRow, HistorianViewRow, LexemeRow, MessageRow, ThreadRow
from aerona.db.tables.meta import AchievementRow, ScenarioRow, ScoreRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.sons import SonPowerRow, SonRelationRow, SonRow
from aerona.db.tables.warfare import BattleRow, SiegeRow, WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, ThreadStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import Passion, SonStatus, Stat
from aerona.domain.enums.war import WarSide, WarStatus
from aerona.domain.models.records import EpochStatsData
from aerona.rules.registry import Rules
from aerona.services.books.history import HandEpoch, creator_hand, ending_line, god_fate, son_fate
from aerona.services.books.mapsvg import MapPicture, map_picture
from aerona.services.books.typed import RecordTable, TypedIndex, TypedSection
from aerona.services.codex import CosmicEpoch, TravellerGuide, cosmic_chronicle, traveller_guide
from aerona.services.images.records import cover_of
from aerona.services.narrative import clean_lore
from aerona.services.search import fold

ENCYCLOPEDIA_ORDER: tuple[EntityType, ...] = (
    EntityType.REGION,
    EntityType.PLACE,
    EntityType.SETTLEMENT,
    EntityType.PEOPLE,
    EntityType.FACTION,
    EntityType.CULT,
    EntityType.MORTAL,
    EntityType.SPECIES,
    EntityType.RESOURCE,
    EntityType.STRUCTURE,
    EntityType.ITEM,
    EntityType.VESSEL,
    EntityType.ARMY,
    EntityType.TRADE_ROUTE,
    EntityType.DISEASE,
    EntityType.POLITY,
    EntityType.HOUSE,
    EntityType.TREATY,
    EntityType.TITLE,
    EntityType.IDEOLOGY,
    EntityType.BEAST,
    EntityType.RITE,
    EntityType.SPIRIT,
    EntityType.OUTER_BEING,
    EntityType.CELESTIAL,
    EntityType.NATURAL_LAW,
    EntityType.LAW,
    EntityType.KNOWLEDGE,
    EntityType.TRADITION,
    EntityType.LEGEND,
    EntityType.PROPHECY,
    EntityType.ARTWORK,
    EntityType.EVENT,
)
NESTING_TYPES = frozenset({EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT})
HIDDEN_BOND_KINDS = frozenset({BondKind.INSIDE})
MAX_HEADING_DEPTH = 6
UNKNOWN_WORLD = "World unknown"
CREATED_BY_GOD = "the god created"
WORLD_COURSE = "from the world's course"
ROMAN_STEPS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)
ENDED = (EntityStatus.DEAD, EntityStatus.DESTROYED)


def roman(number: int) -> str:
    parts: list[str] = []
    remaining = max(1, number)
    for value, symbol in ROMAN_STEPS:
        while remaining >= value:
            parts.append(symbol)
            remaining -= value
    return "".join(parts)


@dataclass
class Labelled:
    label: str
    value: str


@dataclass
class EntityArticle:
    entity: EntityRow
    anchor: str
    type_label: str
    meta: list[str]
    description: str
    stats: list[Labelled]
    tags: list[str]
    bonds: list[str]
    past_bonds: list[str]
    cover: str | None
    depth_level: int = 0
    children: list["EntityArticle"] = field(default_factory=list)
    ending: str | None = None
    typed: list[TypedSection] = field(default_factory=list)


@dataclass
class SonArticle:
    son: SonRow
    anchor: str
    meta: list[str]
    personality: list[Labelled]
    powers: list[Labelled]
    stats: list[Labelled]
    passions: list[Labelled]
    relations: list[Labelled]
    bonds: list[str]
    past_bonds: list[str]
    creations: list[tuple[int, str]]
    cover: str | None
    fate: list[str] = field(default_factory=list)
    typed: list[TypedSection] = field(default_factory=list)


@dataclass
class WorldArticle:
    world: WorldRow
    anchor: str
    depth_level: int
    meta: list[str]
    cover: str | None
    guide: TravellerGuide
    picture: MapPicture | None
    facts: list[Labelled] = field(default_factory=list)
    typed: list[TypedSection] = field(default_factory=list)


@dataclass
class StarSection:
    star: StarRow | None
    type_label: str | None
    worlds: list[WorldArticle]
    anchor: str | None = None
    cover: str | None = None
    facts: list[Labelled] = field(default_factory=list)
    typed: list[TypedSection] = field(default_factory=list)


@dataclass
class GodArticle:
    god: ForeignGodRow
    world: str
    powers: list[Labelled]
    stats: list[Labelled]
    cover: str | None
    fate: list[str] = field(default_factory=list)
    anchor: str = ""
    typed: list[TypedSection] = field(default_factory=list)


@dataclass
class BattleLine:
    epoch: int
    sequence: int
    name: str | None
    winner: str
    loser: str
    outcome: str
    place: str | None


@dataclass
class SiegeLine:
    besieger: str
    besieged: str
    status: str
    started_epoch: int
    ended_epoch: int | None
    rounds: int


@dataclass
class WarArticle:
    war: WarRow
    name: str
    anchor: str
    event_anchor: str
    world: str
    attackers: list[str]
    defenders: list[str]
    victor: str | None
    loser: str | None
    instigator: str | None
    battles: list[BattleLine]
    sieges: list[SiegeLine]


@dataclass
class ChronicleLine:
    kind: str
    year: int | None
    text: str
    son_id: int | None


@dataclass
class EpochChapter:
    epoch: int
    anchor: str
    numeral: str
    row: EpochRow | None
    plates: list[tuple[int, str, str]]
    world_chapters: list[tuple[str, EpochWorldNarrativeRow]]
    stats: EpochStatsData | None
    perspectives: list[tuple[str, HistorianViewRow]]
    councils: list[CouncilRow]
    lines: list[ChronicleLine]
    born: list[tuple[int, str]]
    raw_lines: list[str]


@dataclass
class WorldGroup:
    name: str
    groups: list[tuple[str, list[EntityArticle]]]


@dataclass
class LanguageArticle:
    article: EntityArticle
    speakers: list[str]
    words: list[LexemeRow]


@dataclass
class IndexEntry:
    name: str
    anchor: str
    kind: str


@dataclass
class BookModel:
    cosmos: CosmosRow
    creator: CreatorRow | None
    cover: str | None
    epochs_count: int
    world_year: int
    record_count: int
    laws: list[EntityArticle]
    creator_cover: str | None
    creator_beliefs: list[FolkBeliefRow]
    stars: list[StarSection]
    foreign_gods: list[GodArticle]
    routes: list[tuple[str, str, RouteRow]]
    journeys: list[tuple[str, JourneyRow]]
    sons: list[SonArticle]
    chapters: list[EpochChapter]
    encyclopedia: list[WorldGroup]
    languages: list[LanguageArticle]
    open_threads: list[ThreadRow]
    closed_threads: list[ThreadRow]
    facts: list[tuple[str, CanonFactRow, str]]
    prayers: list[tuple[str, str, MessageRow]]
    achievements: list[tuple[str, int]]
    scenarios: list[tuple[str, ScenarioRow]]
    scores: list[ScoreRow]
    ledger: list[LedgerEntryRow]
    index: dict[str, list[IndexEntry]]
    multi_world: bool
    names: dict[int, str]
    knowledge: list[tuple[EntityRow, str | None, int | None, list[str]]] = field(default_factory=list)
    cosmic: list[CosmicEpoch] = field(default_factory=list)
    single_chronicle: list[ChronicleLine] = field(default_factory=list)
    focus_anchor: str | None = None
    creator_hand: list[HandEpoch] = field(default_factory=list)
    wars: list[WarArticle] = field(default_factory=list)
    creator_typed: list[TypedSection] = field(default_factory=list)
    records: list[RecordTable] = field(default_factory=list)


def humanize(value: str) -> str:
    text = value.replace("_", " ")
    return text[:1].upper() + text[1:]


def entity_anchor(entity_id: int) -> str:
    return f"entity-{entity_id}"


def son_anchor(son_id: int) -> str:
    return f"son-{son_id}"


def world_anchor(world_id: int) -> str:
    return f"world-{world_id}"


def epoch_anchor(epoch: int) -> str:
    return f"epoch-{epoch}"


def star_anchor(star_id: int) -> str:
    return f"star-{star_id}"


def god_anchor(god_id: int) -> str:
    return f"foreign-god-{god_id}"


def war_anchor(war_id: int) -> str:
    return f"war-{war_id}"


class BookBuilder:
    def __init__(self, session: AsyncSession, rules: Rules) -> None:
        self.session = session
        self.rules = rules
        self.names: dict[int, str] = {}
        self.tags: dict[int, list[str]] = defaultdict(list)
        self.bonds: dict[int, list[BondRow]] = defaultdict(list)
        self.son_names: dict[int, str] = {}
        self.typed = TypedIndex({})

    async def load_common(self) -> None:
        rows = await self.session.execute(select(EntityRow.id, EntityRow.name))
        self.names = {entity_id: name for entity_id, name in rows}
        nodes = await self.session.execute(select(SonRow.id, SonRow.name))
        self.son_names = {son_id: name for son_id, name in nodes}
        others = await NodeRepository(self.session).names_of([])
        self.names.update(others)
        self.names.update(self.son_names)
        for world_id, name in await self.session.execute(select(WorldRow.id, WorldRow.name)):
            self.names[world_id] = name
        for god_id, name in await self.session.execute(select(ForeignGodRow.id, ForeignGodRow.name)):
            self.names[god_id] = name
        creator = await CosmosRepository(self.session).creator()
        if creator is not None:
            self.names[creator.id] = creator.name
        for entity_id, tag in await self.session.execute(select(EntityTagRow.entity_id, EntityTagRow.tag)):
            self.tags[entity_id].append(tag)
        for bond in await self.session.scalars(select(BondRow).where(BondRow.state.in_([BondState.ACTIVE, BondState.PAST])).order_by(BondRow.id)):
            self.bonds[bond.source_node_id].append(bond)
        self.typed = await TypedIndex.load(self.session, self.names)

    def bond_lines(self, node_id: int) -> tuple[list[str], list[str]]:
        active: list[str] = []
        past: list[str] = []
        for bond in self.bonds.get(node_id, []):
            if bond.kind in HIDDEN_BOND_KINDS:
                continue
            text = f"{bond.kind.value.replace('_', ' ')} {self.names.get(bond.target_node_id, '?')}"
            if bond.description:
                text += f" ({clean_lore(bond.description)})"
            (active if bond.state is BondState.ACTIVE else past).append(text)
        return active, past

    async def entity_article(self, entity: EntityRow, depth_level: int = 0) -> EntityArticle:
        spec = entity_type_spec(entity.entity_type)
        origin = self.son_names.get(entity.creator_son_id or 0) or (
            CREATED_BY_GOD if entity.creator_son_id is None and entity.origin.value == "creator" else WORLD_COURSE
        )
        meta = [
            part
            for part in (spec.label, entity.subtype, RARITY_LABELS[entity_rarity(self.rules, entity.power_level)], f"Epoch {entity.birth_epoch}", origin)
            if part
        ]
        if entity.status is not EntityStatus.CANON:
            meta.append(entity.status.value)
        stats = [Labelled(field_spec.label, str(value)) for field_spec in spec.stats if (value := getattr(entity.stats, field_spec.key, None)) is not None]
        active, past = self.bond_lines(entity.id)
        return EntityArticle(
            entity=entity,
            anchor=entity_anchor(entity.id),
            type_label=spec.label,
            meta=meta,
            description=clean_lore(entity.description),
            stats=stats,
            tags=sorted(self.tags.get(entity.id, [])),
            bonds=active,
            past_bonds=past,
            cover=await cover_of(self.session, entity.id),
            depth_level=depth_level,
            ending=ending_line(entity.status.value, entity.end_epoch, entity.fate_note) if entity.status in ENDED else None,
            typed=self.typed.of(entity.id),
        )

    async def son_article(self, son: SonRow, relations: list[SonRelationRow]) -> SonArticle:
        powers = list(await self.session.scalars(select(SonPowerRow).where(SonPowerRow.son_id == son.id).order_by(SonPowerRow.slot)))
        unlocks = power_unlock_levels(self.rules)
        meta = [
            son.title,
            f"{RARITY_LABELS[son.rarity]} {'★' * son.stars}",
            f"{DOMAIN_LABELS[son.domain_primary]} / {DOMAIN_LABELS[son.domain_secondary]}",
            f"level {son.level}",
            f"born in Epoch {son.birth_epoch}",
        ]
        if son.status is SonStatus.DEAD and son.death_epoch is not None:
            meta.append(f"died in Epoch {son.death_epoch}")
        personality = [Labelled(label, value) for label, value in son.personality.model_dump().items() if value]
        own = [(row.son_b_id if row.son_a_id == son.id else row.son_a_id, row.value) for row in relations if son.id in (row.son_a_id, row.son_b_id)]
        active, past = self.bond_lines(son.id)
        creations = [
            (entity_id, name)
            for entity_id, name in await self.session.execute(
                select(EntityRow.id, EntityRow.name).where(EntityRow.creator_son_id == son.id, EntityRow.status != EntityStatus.REJECTED).order_by(EntityRow.id)
            )
        ]
        return SonArticle(
            son=son,
            anchor=son_anchor(son.id),
            meta=meta,
            personality=personality,
            powers=[Labelled(f"{power.name or POWERS[power.effect].name} (level {unlocks[power.slot]})", power.description) for power in powers],
            stats=[Labelled(STATS[stat].label, str(son.stat(stat))) for stat in Stat],
            passions=[Labelled(PASSIONS[passion].label, str(getattr(son, passion.value))) for passion in Passion],
            relations=[Labelled(self.son_names.get(other, "?"), str(value)) for other, value in sorted(own, key=lambda item: -item[1])],
            bonds=active,
            past_bonds=past,
            creations=creations,
            cover=await cover_of(self.session, son.id),
            fate=await son_fate(self.session, son, self.names),
            typed=self.typed.of(son.id),
        )

    async def world_tree(self, epoch: int) -> list[StarSection]:
        worlds = list(await self.session.scalars(select(WorldRow).order_by(WorldRow.id)))
        children: dict[int | None, list[WorldRow]] = defaultdict(list)
        known = {world.id for world in worlds}
        for world in worlds:
            children[world.parent_world_id if world.parent_world_id in known else None].append(world)
        written: set[int] = set()

        async def walk(world: WorldRow, level: int) -> list[WorldArticle]:
            if world.id in written:
                return []
            written.add(world.id)
            article = await self.world_article(world, level, epoch)
            nested = [article]
            for moon in children.get(world.id, []):
                nested += await walk(moon, level + 1)
            return nested

        sections: list[StarSection] = []
        for star in await self.session.scalars(select(StarRow).order_by(StarRow.id)):
            articles: list[WorldArticle] = []
            for root in children.get(None, []):
                if root.star_id == star.id:
                    articles += await walk(root, 0)
            facts = [
                Labelled("Kind", STAR_TYPE_LABELS[star.star_type]),
                Labelled("Brightness", str(star.brightness)),
                Labelled("Kindled", f"Epoch {star.created_epoch}"),
            ]
            sections.append(
                StarSection(
                    star,
                    STAR_TYPE_LABELS[star.star_type],
                    articles,
                    star_anchor(star.id),
                    await cover_of(self.session, star.id),
                    facts,
                    self.typed.of(star.id),
                )
            )
        leftovers: list[WorldArticle] = []
        for world in worlds:
            leftovers += await walk(world, 0)
        if leftovers:
            sections.append(StarSection(None, None, leftovers))
        return sections

    async def world_article(self, world: WorldRow, level: int, epoch: int) -> WorldArticle:
        meta = [WORLD_TYPES[world.world_type].label]
        if world.parent_world_id is not None:
            meta.append(f"moon of {self.names.get(world.parent_world_id, '?')}")
        facts = [
            Labelled("Kind", WORLD_TYPES[world.world_type].label),
            Labelled("Gravity", GRAVITY_LABELS[world.gravity]),
            Labelled("Air", ATMOSPHERE_LABELS[world.atmosphere]),
            Labelled("Time", "Normal pace" if world.time_factor == 1 else f"{world.time_factor:g} times as fast"),
            Labelled("Danger", f"{world.danger}/100"),
            Labelled("Leakage", f"{world.leakage}/100"),
            Labelled("Known", humanize(world.discovery.value)),
            Labelled("Born", f"Epoch {world.created_epoch}"),
        ]
        if world.climate_era is not None:
            facts.append(Labelled("Climate", humanize(world.climate_era.value)))
        for label, son_id in (("Shaped by", world.creator_son_id), ("Patron", world.patron_son_id)):
            if son_id is not None and son_id in self.son_names:
                facts.append(Labelled(label, self.son_names[son_id]))
        if world.mirror_twin_id is not None:
            facts.append(Labelled("Mirror twin", self.names.get(world.mirror_twin_id, "?")))
        return WorldArticle(
            world=world,
            anchor=world_anchor(world.id),
            depth_level=level,
            meta=meta,
            cover=await cover_of(self.session, world.id),
            guide=await traveller_guide(self.session, self.rules, world.id, complete=True),
            picture=await map_picture(self.session, self.rules, world.id, epoch),
            facts=facts,
            typed=self.typed.of(world.id),
        )

    async def chapters(self) -> list[EpochChapter]:
        epochs = sorted(set(await self.session.scalars(select(EpochRow.epoch))) | set(await self.session.scalars(select(ChronicleRow.epoch).distinct())))
        stats = {row.epoch: row.data for row in await self.session.scalars(select(EpochStatsRow))}
        chapters: list[EpochChapter] = []
        for epoch in epochs:
            lines = list(await self.session.scalars(select(ChronicleRow).where(ChronicleRow.epoch == epoch).order_by(ChronicleRow.id)))
            born = list(
                await self.session.scalars(
                    select(EntityRow)
                    .where(EntityRow.birth_epoch == epoch, EntityRow.status != EntityStatus.REJECTED)
                    .order_by(EntityRow.power_level.desc(), EntityRow.id)
                )
            )
            plates = [(entity.id, entity.name, cover) for entity in born if (cover := await cover_of(self.session, entity.id))]
            worlds = [
                (self.names.get(row.world_id, "?"), row)
                for row in await self.session.scalars(select(EpochWorldNarrativeRow).where(EpochWorldNarrativeRow.epoch == epoch))
            ]
            views = [
                (self.names.get(row.people_entity_id, "?"), row)
                for row in await self.session.scalars(select(HistorianViewRow).where(HistorianViewRow.epoch == epoch))
            ]
            chapters.append(
                EpochChapter(
                    epoch=epoch,
                    anchor=epoch_anchor(epoch),
                    numeral=roman(epoch),
                    row=await self.session.get(EpochRow, epoch),
                    plates=plates,
                    world_chapters=worlds,
                    stats=stats.get(epoch),
                    perspectives=views,
                    councils=list(await self.session.scalars(select(CouncilRow).where(CouncilRow.epoch == epoch).order_by(CouncilRow.id))),
                    lines=[ChronicleLine(line.kind.value.replace("_", " "), line.year, clean_lore(line.text), line.son_id) for line in lines if line.visible],
                    born=[(entity.id, entity.name) for entity in born],
                    raw_lines=[clean_lore(line.text) for line in lines if line.kind is ChronicleKind.ENGINE_RAW],
                )
            )
        return chapters

    async def encyclopedia(self, multi_world: bool) -> list[WorldGroup]:
        entities = list(
            await self.session.scalars(
                select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED, EntityRow.entity_type != EntityType.LANGUAGE).order_by(EntityRow.id)
            )
        )
        by_parent: dict[int | None, list[EntityRow]] = defaultdict(list)
        ids = {entity.id for entity in entities}
        for entity in entities:
            by_parent[entity.location_id if entity.location_id in ids else None].append(entity)
        written: set[int] = set()

        async def article(entity: EntityRow, level: int) -> EntityArticle:
            written.add(entity.id)
            built = await self.entity_article(entity, level)
            if entity.entity_type in NESTING_TYPES:
                for child in by_parent.get(entity.id, []):
                    if child.id not in written:
                        built.children.append(await article(child, min(level + 1, MAX_HEADING_DEPTH)))
            return built

        world_names = {world.id: world.name for world in await self.session.scalars(select(WorldRow).order_by(WorldRow.id))}
        groups: list[WorldGroup] = []
        for world_id, world_name in world_names.items() if multi_world else [(None, "")]:
            sections: list[tuple[str, list[EntityArticle]]] = []
            for entity_type in ENCYCLOPEDIA_ORDER:
                roots = [
                    entity
                    for entity in by_parent.get(None, [])
                    if entity.entity_type is entity_type and (world_id is None or entity.world_id == world_id) and entity.id not in written
                ]
                if roots:
                    sections.append((entity_type_spec(entity_type).plural, [await article(entity, 0) for entity in roots]))
            if sections:
                groups.append(WorldGroup(world_name, sections))
        rest = [entity for entity in entities if entity.id not in written]
        if rest:
            groups.append(WorldGroup(UNKNOWN_WORLD, [("Other records", [await article(entity, 0) for entity in rest])]))
        return groups

    async def languages(self) -> list[LanguageArticle]:
        found: list[LanguageArticle] = []
        for language in await self.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status != EntityStatus.REJECTED).order_by(EntityRow.id)
        ):
            speakers = [
                self.names.get(source, "?")
                for source in await self.session.scalars(
                    select(BondRow.source_node_id).where(
                        BondRow.target_node_id == language.id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE
                    )
                )
            ]
            words = list(await self.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id)))
            found.append(LanguageArticle(await self.entity_article(language), speakers, words))
        return found

    async def knowledge(self) -> list[tuple[EntityRow, str | None, int | None, list[str]]]:
        rows: list[tuple[EntityRow, str | None, int | None, list[str]]] = []
        statement = select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status != EntityStatus.REJECTED).order_by(EntityRow.id)
        for item in await self.session.scalars(statement):
            knowers = [
                self.names.get(source, "?")
                for source in await self.session.scalars(
                    select(BondRow.source_node_id).where(BondRow.target_node_id == item.id, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
                )
            ]
            branch = KNOWLEDGE_BRANCHES[item.knowledge_branch].label if item.knowledge_branch is not None else None
            level = getattr(item.stats, "level", None)
            rows.append((item, branch, level if isinstance(level, int) else None, knowers))
        return rows

    def named(self, node_id: int | None) -> str | None:
        return self.names.get(node_id, "?") if node_id is not None else None

    async def wars(self) -> list[WarArticle]:
        sides: dict[int, list[WarSideRow]] = defaultdict(list)
        for side in await self.session.scalars(select(WarSideRow).order_by(WarSideRow.joined_epoch)):
            sides[side.war_id].append(side)
        battles: dict[int, list[BattleRow]] = defaultdict(list)
        for battle in await self.session.scalars(select(BattleRow).order_by(BattleRow.epoch, BattleRow.sequence)):
            battles[battle.war_id].append(battle)
        sieges: dict[int, list[SiegeRow]] = defaultdict(list)
        for siege in await self.session.scalars(select(SiegeRow).order_by(SiegeRow.started_epoch, SiegeRow.id)):
            sieges[siege.war_id].append(siege)
        found: list[WarArticle] = []
        named = self.named
        for war in await self.session.scalars(select(WarRow).order_by(WarRow.started_epoch, WarRow.id)):
            found.append(
                WarArticle(
                    war=war,
                    name=self.names.get(war.event_entity_id, f"War {war.id}"),
                    anchor=war_anchor(war.id),
                    event_anchor=entity_anchor(war.event_entity_id),
                    world=self.names.get(war.world_id, "?"),
                    attackers=[self.names.get(side.entity_id, "?") for side in sides[war.id] if side.side is WarSide.ATTACKER],
                    defenders=[self.names.get(side.entity_id, "?") for side in sides[war.id] if side.side is WarSide.DEFENDER],
                    victor=named(war.victor_entity_id),
                    loser=named(war.loser_entity_id),
                    instigator=self.son_names.get(war.incited_by_son_id) if war.incited_by_son_id is not None else None,
                    battles=[
                        BattleLine(
                            battle.epoch,
                            battle.sequence,
                            named(battle.record_entity_id),
                            self.names.get(battle.winner_entity_id, "?"),
                            self.names.get(battle.loser_entity_id, "?"),
                            humanize(battle.outcome.value),
                            named(battle.place_entity_id),
                        )
                        for battle in battles[war.id]
                    ],
                    sieges=[
                        SiegeLine(
                            self.names.get(siege.besieger_entity_id, "?"),
                            self.names.get(siege.besieged_entity_id, "?"),
                            humanize(siege.status.value),
                            siege.started_epoch,
                            siege.ended_epoch,
                            siege.rounds,
                        )
                        for siege in sieges[war.id]
                    ],
                )
            )
        found.sort(key=lambda article: (article.war.status is WarStatus.ENDED, -article.war.started_epoch))
        return found

    def index(self, sons: list[SonArticle], groups: list[WorldGroup], worlds: list[StarSection], gods: list["GodArticle"]) -> dict[str, list[IndexEntry]]:
        entries = [IndexEntry(article.son.name, article.anchor, "son") for article in sons]
        entries += [IndexEntry(article.god.name, article.anchor, "foreign god") for article in gods]
        entries += [IndexEntry(section.star.name, section.anchor, "star") for section in worlds if section.star is not None and section.anchor]

        def collect(article: EntityArticle) -> None:
            entries.append(IndexEntry(article.entity.name, article.anchor, article.type_label))
            for child in article.children:
                collect(child)

        for group in groups:
            for _label, articles in group.groups:
                for item in articles:
                    collect(item)
        entries += [IndexEntry(world.world.name, world.anchor, "world") for section in worlds for world in section.worlds]
        letters: dict[str, list[IndexEntry]] = defaultdict(list)
        for entry in sorted(entries, key=lambda item: fold(item.name)):
            letters[(fold(entry.name)[:1] or "#").upper()].append(entry)
        return dict(letters)


async def build_book(session: AsyncSession, rules: Rules) -> BookModel | None:
    repository = CosmosRepository(session)
    cosmos = await repository.get()
    if cosmos is None:
        return None
    builder = BookBuilder(session, rules)
    await builder.load_common()
    creator = await repository.creator()
    multi_world = int(await session.scalar(select(func.count()).select_from(WorldRow)) or 0) > 1
    relations = list(await session.scalars(select(SonRelationRow)))
    sons = [await builder.son_article(son, relations) for son in await session.scalars(select(SonRow).order_by(SonRow.id))]
    stars = await builder.world_tree(cosmos.epoch)
    groups = await builder.encyclopedia(multi_world)
    laws = [
        await builder.entity_article(entity)
        for entity in await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.NATURAL_LAW, EntityRow.status == EntityStatus.CANON))
    ]
    gods = []
    for god in await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)):
        powers = [
            Labelled(power.name, power.description) for power in await session.scalars(select(ForeignGodPowerRow).where(ForeignGodPowerRow.god_id == god.id))
        ]
        stats = [Labelled(STATS[stat].label, str(getattr(god, stat.value))) for stat in Stat]
        fate = await god_fate(session, god, builder.names)
        gods.append(
            GodArticle(
                god, builder.names.get(god.world_id, "?"), powers, stats, await cover_of(session, god.id), fate, god_anchor(god.id), builder.typed.of(god.id)
            )
        )
    routes = [
        (builder.names.get(route.world_a_id, "?"), builder.names.get(route.world_b_id, "?"), route)
        for route in await session.scalars(select(RouteRow).order_by(RouteRow.id))
    ]
    journeys = [(builder.names.get(journey.traveller_entity_id, "?"), journey) for journey in await session.scalars(select(JourneyRow).order_by(JourneyRow.id))]
    threads = list(await session.scalars(select(ThreadRow).order_by(ThreadRow.id)))
    facts = [
        (builder.names.get(fact.subject_entity_id, "?"), fact, builder.names.get(fact.object_entity_id or 0) or fact.object_text or "")
        for fact in await session.scalars(select(CanonFactRow).where(CanonFactRow.active.is_(True)).order_by(CanonFactRow.id))
    ]
    creator_id = creator.id if creator is not None else -1
    prayers = [
        (builder.names.get(message.sender_node_id, "?"), builder.names.get(message.recipient_node_id, "?"), message)
        for message in await session.scalars(
            select(MessageRow).where(or_(MessageRow.recipient_node_id == creator_id, MessageRow.sender_node_id == creator_id)).order_by(MessageRow.id)
        )
    ]
    achievements = [(ACHIEVEMENTS[row.key].name(rules), row.epoch) for row in await session.scalars(select(AchievementRow).order_by(AchievementRow.epoch))]
    scenarios = [(SCENARIOS[row.key].name(rules), row) for row in await session.scalars(select(ScenarioRow).order_by(ScenarioRow.id))]
    record_count = int(await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.status != EntityStatus.REJECTED)) or 0)
    world = await session.get(WorldRow, cosmos.primary_world_id) if cosmos.primary_world_id else None
    return BookModel(
        cosmos=cosmos,
        creator=creator,
        cover=(await cover_of(session, world.id) if world else None) or (await cover_of(session, creator.id) if creator else None),
        epochs_count=cosmos.epoch,
        world_year=cosmos.epoch * rules.time.years_per_epoch,
        record_count=record_count,
        laws=laws,
        creator_cover=await cover_of(session, creator.id) if creator else None,
        creator_beliefs=list(await session.scalars(select(FolkBeliefRow).where(FolkBeliefRow.god_node_id == creator_id))),
        stars=stars,
        foreign_gods=gods,
        routes=routes,
        journeys=journeys,
        sons=sons,
        chapters=await builder.chapters(),
        encyclopedia=groups,
        languages=await builder.languages(),
        open_threads=[thread for thread in threads if thread.status is ThreadStatus.OPEN],
        closed_threads=[thread for thread in threads if thread.status is ThreadStatus.CLOSED],
        facts=facts,
        prayers=prayers,
        achievements=achievements,
        scenarios=scenarios,
        scores=list(await session.scalars(select(ScoreRow).order_by(ScoreRow.epoch))),
        ledger=list(await session.scalars(select(LedgerEntryRow).order_by(LedgerEntryRow.epoch, LedgerEntryRow.id))),
        index=builder.index(sons, groups, stars, gods),
        multi_world=multi_world,
        names=builder.names,
        knowledge=await builder.knowledge(),
        cosmic=await cosmic_chronicle(session, rules, complete=True) if multi_world else [],
        creator_hand=await creator_hand(session),
        wars=await builder.wars(),
        creator_typed=builder.typed.of(creator.id) if creator is not None else [],
        records=builder.typed.records,
    )


async def entry_chronicle(session: AsyncSession, *, son_id: int | None, entity_id: int | None) -> list[ChronicleLine]:
    statement = select(ChronicleRow).where(ChronicleRow.kind != ChronicleKind.ENGINE_RAW)
    if entity_id is not None:
        statement = statement.join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRow.id).where(ChronicleEntityRow.entity_id == entity_id)
    else:
        statement = statement.where(ChronicleRow.son_id == son_id)
    rows = await session.scalars(statement.order_by(ChronicleRow.id))
    return [ChronicleLine(row.kind.value.replace("_", " "), row.year, clean_lore(row.text), row.son_id) for row in rows]


def natural_law_label(entity: EntityRow) -> str | None:
    return NATURAL_LAWS[entity.natural_law].label if entity.natural_law is not None else None
