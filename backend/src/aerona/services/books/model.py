from collections import defaultdict
from dataclasses import dataclass, field, fields, is_dataclass

from markupsafe import Markup
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.climate import CLIMATES
from aerona.catalog.cosmography import (
    CAUSALITY_LABELS,
    CLUSTER_KINDS,
    DIMENSION_KINDS,
    ELEMENT_LABELS,
    GALACTIC_ZONES,
    GALAXY_AGE_LABELS,
    GALAXY_TYPES,
    NUCLEUS_LABELS,
    RIFT_STATE_LABELS,
    STAR_AGE_LABELS,
    WORLD_AGE_LABELS,
)
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.entity_types import entity_type_spec
from aerona.catalog.genesis import AGE_CYCLE_LABELS, COSMOS_LABELS, SHAPE_LABELS, STORYTELLER_LABELS, TECHNOLOGY_LABELS, TEMPLATES, TEXTURE_LABELS
from aerona.catalog.knowledge import KNOWLEDGE_BRANCHES, NATURAL_LAWS
from aerona.catalog.powers import POWERS, power_unlock_levels
from aerona.catalog.rarities import RARITY_LABELS, entity_rarity
from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.catalog.stats import PASSIONS, STATS
from aerona.catalog.tongues import BASES
from aerona.catalog.worlds import ATMOSPHERE_LABELS, DISCOVERY_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.core.grammar import several, spoken
from aerona.db.repositories.chronicle import kept_lines, told_kind
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, CosmicBeingProfileRow, DimensionRow, GalaxyRow, RiftRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.dimension_aspects import DimensionAspectRow
from aerona.db.tables.entities import EntityRow, EntityTagRow
from aerona.db.tables.epochs import EpochRow, EpochStatsRow, EpochWorldNarrativeRow
from aerona.db.tables.faith import AfterlifeStratumRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.db.tables.lore import CanonFactRow, ChronicleEntityRow, ChronicleRow, CouncilRow, FolkBeliefRow, HistorianViewRow, LexemeRow, MessageRow, ThreadRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.sons import SonPowerRow, SonRelationRow, SonRow
from aerona.db.tables.warfare import BattleRow, SiegeRow, WarRow, WarSideRow
from aerona.domain.enums.bond import KIN_BOND_KINDS, BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, ThreadStatus
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.son import Passion, SonStatus, Stat
from aerona.domain.enums.war import WarSide, WarStatus
from aerona.domain.enums.world import CosmosShape
from aerona.domain.models.genesis import TECH_LEVEL_CEILING, GenesisSettings
from aerona.domain.models.profiles import EntityDepth
from aerona.domain.models.records import EpochStatsData
from aerona.engine.cosmos.kinds import CLUSTER_KIND_MECHANICS, DIMENSION_KIND_MECHANICS, GALAXY_TYPE_MECHANICS
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.military.records import battle_field
from aerona.engine.primitives.knowledge import laws_of_dimension
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.rules.registry import Rules
from aerona.services.books.armssvg import arms_plan
from aerona.services.books.citysvg import Plan, city_plan, land_plan, type_tables
from aerona.services.books.command import add_command_areas
from aerona.services.books.deeds import DeedsChapter, deeds_chapter
from aerona.services.books.deepsvg import DeepStratum, world_below
from aerona.services.books.divine_will import DivineWillRecord, DivineWillWritings, divine_will_record, divine_will_writings
from aerona.services.books.familysvg import FamilyPlan, family_plan
from aerona.services.books.hands import TeamRecord, team_record
from aerona.services.books.heavensvg import cluster_figure, dimension_figure, galaxy_figure
from aerona.services.books.history import HandEpoch, creator_hand, ending_line, god_fate, son_fate
from aerona.services.books.kinds import add_kind_sections
from aerona.services.books.made import KindArticle, made_kinds
from aerona.services.books.mapsvg import MapPicture, map_picture
from aerona.services.books.presence import SpeakerAudiences, audiences_by_speaker
from aerona.services.books.records import Ledger, add_history_sections, record_tables
from aerona.services.books.seasons import add_season_sections, festival_plan
from aerona.services.books.typed import LedgerChange, RecordTable, TypedIndex, TypedSection, title_of
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
    EntityType.COSMIC_BEING,
    EntityType.PHENOMENON,
    EntityType.CELESTIAL,
    EntityType.NATURAL_LAW,
    EntityType.LAW,
    EntityType.KNOWLEDGE,
    EntityType.THEORY,
    EntityType.ART_FORM,
    EntityType.VEHICLE_TYPE,
    EntityType.UNIT_TYPE,
    EntityType.EQUIPMENT_MODEL,
    EntityType.DISH,
    EntityType.BUILDING_TYPE,
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
    plan: Plan | None = None
    arms: Plan | None = None
    family: FamilyPlan | None = None
    festivals: Plan | None = None
    made: KindArticle | None = None
    audiences: SpeakerAudiences = field(default_factory=SpeakerAudiences)


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
    audiences: SpeakerAudiences = field(default_factory=SpeakerAudiences)


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
    wheel: Markup | None = None
    below: list[DeepStratum] = field(default_factory=list)


EFFECT_LABELS: dict[str, str] = {
    "density": "Star density (%)",
    "formation": "Star formation",
    "metallicity": "Metallicity",
    "capacity": "Travel capacity (%)",
    "leak": "Leak",
    "sanity": "Sanity drain",
    "danger": "Danger",
    "arms_min": "Fewest arms",
    "arms_max": "Most arms",
    "nucleus_none": "Weight of no nucleus",
    "nucleus_dormant": "Weight of a dormant nucleus",
    "nucleus_active": "Weight of an active nucleus",
    "nucleus_quasar": "Weight of a quasar",
    "nucleus_devoured": "Weight of a devoured nucleus",
    "delay": "Epochs added to routes",
    "hide": "Hides its stars",
    "birth": "Star birth",
    "radiation": "Radiation",
    "heat": "Heat of the medium",
    "merger": "Merging pull",
    "veil": "Veil",
    "stability": "Stability",
    "time": "Time (%)",
    "magic": "Magic",
    "hostility": "Hostility",
}


SCALE_RENDERED = frozenset(title_of(table) for table in ("galaxies", "galaxy_clusters", "dimensions", "name_registry"))


@dataclass
class ScaleArticle:
    kind: str
    node_id: int
    name: str
    anchor: str
    level: int
    facts: list[Labelled]
    description: str | None
    cover: str | None
    typed: list[TypedSection]
    stars: list[tuple[str, str]] = field(default_factory=list)
    figure: Markup | None = None
    kind_note: str = ""
    effects: list[Labelled] = field(default_factory=list)
    rifts: list[str] = field(default_factory=list)
    beings: list[str] = field(default_factory=list)
    laws: list[Labelled] = field(default_factory=list)
    depth: EntityDepth | None = None


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
    audiences: SpeakerAudiences = field(default_factory=SpeakerAudiences)


@dataclass
class BattleLine:
    epoch: int
    sequence: int
    name: str | None
    winner: str
    loser: str
    outcome: str
    place: str | None
    field: str = ""


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
    title: str
    creator: CreatorRow | None
    cover: str | None
    epochs_count: int
    world_year: int
    record_count: int
    laws: list[EntityArticle]
    creator_cover: str | None
    creator_beliefs: list[FolkBeliefRow]
    stars: list[StarSection]
    ladder: list[ScaleArticle]
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
    deeds: DeedsChapter
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
    ledger_changes: dict[int, list[LedgerChange]] = field(default_factory=dict)
    creation: list[Labelled] = field(default_factory=list)
    divine_will: DivineWillRecord = field(default_factory=DivineWillRecord)
    team: TeamRecord = field(default_factory=TeamRecord)
    writings: DivineWillWritings = field(default_factory=DivineWillWritings)


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
        self.made: dict[int, KindArticle] = {}
        self.ledger = Ledger({})
        self.wheels: dict[int, Markup] = {}
        self.kin: set[int] = set()
        self.audiences: dict[int, SpeakerAudiences] = {}

    async def load_common(self) -> None:
        rows = await self.session.execute(select(EntityRow.id, EntityRow.name))
        self.names = {entity_id: name for entity_id, name in rows}
        nodes = await self.session.execute(select(SonRow.id, SonRow.name))
        self.son_names = {son_id: name for son_id, name in nodes}
        self.names.update({node_id: name for node_id, name in await self.session.execute(select(NodeRow.id, NodeRow.name))})
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
            if bond.kind in KIN_BOND_KINDS:
                self.kin.update((bond.source_node_id, bond.target_node_id))
        for first, second in await self.session.execute(select(MarriageRow.first_id, MarriageRow.second_id)):
            self.kin.update((first, second))
        self.typed = await TypedIndex.load(self.session, self.names)
        self.made = await made_kinds(self.session, self.names)
        await add_command_areas(self.session, self.typed)
        self.wheels = await add_season_sections(self.session, self.typed)
        await add_kind_sections(self.session, self.typed)
        self.ledger = await add_history_sections(self.session, self.typed)
        self.audiences = await audiences_by_speaker(self.session, self.names)

    def bond_lines(self, node_id: int) -> tuple[list[str], list[str]]:
        active: list[str] = []
        past: list[str] = []
        for bond in self.bonds.get(node_id, []):
            if bond.kind in HIDDEN_BOND_KINDS:
                continue
            text = f"{spoken(bond.kind)} {self.names.get(bond.target_node_id, '?')}"
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
            plan=await self.plan_of(entity),
            arms=await arms_plan(self.session, entity),
            family=await family_plan(self.session, entity.id, entity.name) if entity.id in self.kin else None,
            festivals=await festival_plan(self.session, entity) if entity.entity_type is EntityType.PEOPLE else None,
            made=self.made.get(entity.id),
            audiences=self.audiences.get(entity.id, SpeakerAudiences()),
        )

    async def plan_of(self, entity: EntityRow) -> Plan | None:
        if entity.entity_type is EntityType.SETTLEMENT:
            return await city_plan(self.session, self.rules, entity)
        if entity.entity_type is EntityType.REGION:
            return await land_plan(self.session, entity)
        return None

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
            audiences=self.audiences.get(son.id, SpeakerAudiences()),
        )

    async def sky_worship(self) -> dict[int, list[str]]:
        ladder = await Cosmography.load(self.session)
        stars, galaxies = await flags_by_entity(self.session, EntityFlag.WORSHIPS_STAR), await flags_by_entity(self.session, EntityFlag.WORSHIPS_GALAXY)
        found: dict[int, list[str]] = {}
        for community in sorted(await canon(self.session, COMMUNITY_TYPES), key=lambda row: row.id):
            place = ladder.place_world_id(community.world_id)
            if community.id in stars and place.star is not None:
                found.setdefault(place.star.id, []).append(community.name)
            if community.id in galaxies and place.galaxy is not None:
                found.setdefault(place.galaxy.id, []).append(community.name)
        statement = select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(list(ladder.dimensions))
        )
        for source, target in await self.session.execute(statement.order_by(BondRow.id)):
            found.setdefault(target, []).append(self.names.get(source, "?"))
        return found

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
        worship = await self.sky_worship()
        for star in await self.session.scalars(select(StarRow).order_by(StarRow.id)):
            articles: list[WorldArticle] = []
            for root in children.get(None, []):
                if root.star_id == star.id:
                    articles += await walk(root, 0)
            facts = [
                Labelled("Kind", STAR_TYPE_LABELS[star.star_type]),
                Labelled("Brightness", str(star.brightness)),
                Labelled("Kindled", f"Epoch {star.created_epoch}"),
                Labelled("Age", STAR_AGE_LABELS[star.age_stage]),
                Labelled("Next age in", f"{several(star.lifecycle_clock, 'epoch', 'epochs')}" if star.lifecycle_clock is not None else "unknown"),
                Labelled("Steadiness", f"{star.stability}/100"),
                Labelled("Radiation", f"{star.radiation}/100"),
                Labelled("Sacredness", f"{star.sacredness}/100"),
                Labelled("Place in its galaxy", GALACTIC_ZONES[star.galactic_zone].label),
            ]
            for label, node_id in (("Galaxy", star.galaxy_id), ("Patron", star.patron_son_id)):
                if node_id is not None:
                    facts.append(Labelled(label, self.names.get(node_id) or self.son_names.get(node_id, "?")))
            facts.append(Labelled("Worshipped by", ", ".join(worship.get(star.id, [])) or "no people"))
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

    async def scale_article(self, kind: str, row: DimensionRow | ClusterRow | GalaxyRow, level: int, facts: list[Labelled]) -> ScaleArticle:
        return ScaleArticle(
            kind,
            row.id,
            row.name,
            f"{kind}-{row.id}",
            level,
            facts,
            row.description,
            await cover_of(self.session, row.id),
            [section for section in self.typed.of(row.id) if section.title not in SCALE_RENDERED],
            depth=row.depth,
        )

    def kind_effects(self, mechanics: object) -> list[Labelled]:
        found: list[Labelled] = []
        for item in fields(mechanics) if is_dataclass(mechanics) else ():
            value = getattr(mechanics, item.name)
            if callable(value):
                amount = int(value(self.rules))
                found.append(Labelled(EFFECT_LABELS.get(item.name, item.name.replace("_", " ").capitalize()), str(amount)))
        return found

    async def scale_ladder(self) -> list[ScaleArticle]:
        ladder = await Cosmography.load(self.session)
        found: list[ScaleArticle] = []
        worship = await self.sky_worship()
        strata = list(
            await self.session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.dimension_id.is_not(None)).order_by(AfterlifeStratumRow.id))
        )

        def galaxy_facts(galaxy: GalaxyRow) -> list[Labelled]:
            return [
                Labelled("Type", GALAXY_TYPES[galaxy.galaxy_type].label),
                Labelled("Arms", str(galaxy.arm_count)),
                Labelled("Nucleus", NUCLEUS_LABELS[galaxy.nucleus]),
                Labelled("Star formation", f"{galaxy.star_formation}/100"),
                Labelled("Metallicity", f"{galaxy.metallicity}/100"),
                Labelled("Age", GALAXY_AGE_LABELS[galaxy.age_stage]),
                Labelled("Leak", f"{galaxy.leak}/100"),
                Labelled("Radius", f"{galaxy.radius:g}"),
                Labelled("Patron", self.son_names.get(galaxy.patron_son_id or 0, "none")),
                Labelled(
                    "Merging with",
                    self.names.get(galaxy.merging_with_galaxy_id or 0, "none") + (f" ({galaxy.merge_progress}%)" if galaxy.merging_with_galaxy_id else ""),
                ),
                Labelled("Cluster", self.names.get(galaxy.cluster_id or 0, "none")),
                Labelled("Dimension, outside any cluster", self.names.get(galaxy.dimension_id or 0, "none")),
                Labelled("Place", f"{galaxy.x:g}, {galaxy.y:g}"),
                Labelled("Known", DISCOVERY_LABELS[galaxy.discovery]),
                Labelled("Since", f"epoch {galaxy.created_epoch}"),
                Labelled("Worshipped by", ", ".join(worship.get(galaxy.id, [])) or "no people"),
                Labelled("Held by the god", ", ".join(galaxy.locked) or "nothing"),
            ]

        rifts = list(await self.session.scalars(select(RiftRow).order_by(RiftRow.id)))
        beings = list(await self.session.scalars(select(CosmicBeingProfileRow).order_by(CosmicBeingProfileRow.entity_id)))

        async def add_galaxy(galaxy: GalaxyRow, level: int) -> None:
            article = await self.scale_article("galaxy", galaxy, level, galaxy_facts(galaxy))
            members = sorted(ladder.stars_in_galaxy(galaxy.id), key=lambda row: row.id)
            article.stars = [(star.name, star_anchor(star.id)) for star in members]
            article.figure = galaxy_figure(
                galaxy, [row for row in ladder.structures.values() if row.galaxy_id == galaxy.id], [(star.x, star.y) for star in members], self.rules.galaxies
            )
            article.kind_note = GALAXY_TYPES[galaxy.galaxy_type].description
            article.effects = self.kind_effects(GALAXY_TYPE_MECHANICS[galaxy.galaxy_type])
            article.beings = [self.names.get(row.entity_id, "") for row in beings if row.galaxy_id == galaxy.id and self.names.get(row.entity_id)]
            found.append(article)

        async def add_cluster(cluster: ClusterRow, level: int) -> None:
            facts = [
                Labelled("Kind", CLUSTER_KINDS[cluster.cluster_kind].label),
                Labelled("Heat between its galaxies", f"{cluster.medium_heat}/100"),
                Labelled("Drift", f"{cluster.expansion}/100"),
                Labelled("Radius", f"{cluster.radius:g}"),
                Labelled("Inside cluster", self.names.get(cluster.parent_cluster_id or 0, "none")),
                Labelled("Dimension", self.names.get(cluster.dimension_id or 0, "the dimension of its holder")),
                Labelled("Place", f"{cluster.x:g}, {cluster.y:g}"),
                Labelled("Known", DISCOVERY_LABELS[cluster.discovery]),
                Labelled("Since", f"epoch {cluster.created_epoch}"),
                Labelled("Central galaxy", central.name if (central := ladder.central_galaxy(cluster.id)) is not None else "none yet"),
                Labelled("Held by the god", ", ".join(cluster.locked) or "nothing"),
            ]
            article = await self.scale_article("cluster", cluster, level, facts)
            article.figure = cluster_figure(cluster, sum(1 for row in ladder.galaxies.values() if row.cluster_id == cluster.id))
            article.kind_note = CLUSTER_KINDS[cluster.cluster_kind].description
            article.effects = self.kind_effects(CLUSTER_KIND_MECHANICS[cluster.cluster_kind])
            found.append(article)
            for child in sorted((row for row in ladder.clusters.values() if row.parent_cluster_id == cluster.id), key=lambda row: row.id):
                await add_cluster(child, level + 1)
            for galaxy in sorted((row for row in ladder.galaxies.values() if row.cluster_id == cluster.id), key=lambda row: row.id):
                await add_galaxy(galaxy, level + 1)

        aspects: dict[int, list[DimensionAspectRow]] = {}
        for aspect in await self.session.scalars(select(DimensionAspectRow).order_by(DimensionAspectRow.id)):
            aspects.setdefault(aspect.dimension_id, []).append(aspect)
        for dimension in sorted(ladder.dimensions.values(), key=lambda row: row.id):
            facts = [
                Labelled("Kind", DIMENSION_KINDS[dimension.dimension_kind].label),
                Labelled("Aspects", aspect_words(aspects.get(dimension.id, [])) or "none"),
                Labelled("Veil", f"{dimension.veil}/100"),
                Labelled("Stability", f"{dimension.stability}/100"),
                Labelled("Time", f"{dimension.time_factor:g} times the prime"),
                Labelled("Magic", f"{dimension.magic}/100"),
                Labelled("Hostility", f"{dimension.hostility}/100"),
                Labelled("Sanity drain", str(dimension.sanity_drain)),
                Labelled("Leak", f"{dimension.leak}/100"),
                Labelled("Causality", CAUSALITY_LABELS[dimension.causality]),
                Labelled("Ruler", self.names.get(dimension.ruler_node_id or 0) or self.son_names.get(dimension.ruler_node_id or 0, "none")),
                Labelled("Lies within", self.names.get(dimension.parent_dimension_id or 0, "nothing")),
                Labelled("Known", DISCOVERY_LABELS[dimension.discovery]),
                Labelled("Since", f"epoch {dimension.created_epoch}"),
                Labelled("Worshipped by", ", ".join(worship.get(dimension.id, [])) or "no people"),
                Labelled(
                    "Afterlife strata here",
                    ", ".join(f"{row.name} ({several(row.population, 'soul', 'souls')})" for row in strata if row.dimension_id == dimension.id) or "none",
                ),
                Labelled("Held by the god", ", ".join(dimension.locked) or "nothing"),
            ]
            article = await self.scale_article("dimension", dimension, 0, facts)
            article.figure = dimension_figure(dimension)
            article.kind_note = DIMENSION_KINDS[dimension.dimension_kind].description
            article.effects = self.kind_effects(DIMENSION_KIND_MECHANICS[dimension.dimension_kind])
            article.laws = [
                Labelled(
                    NATURAL_LAWS[row.law].label,
                    f"{self.names.get(row.entity_id, 'A law') if row.entity_id is not None else 'By the nature of its kind'}, strength {row.strength}/100",
                )
                for row in await laws_of_dimension(self.session, dimension.id)
            ]
            article.rifts = [
                f"{self.names.get(row.world_id, 'A world')}: {RIFT_STATE_LABELS[row.state].lower()}, "
                f"size {row.size}, stability {row.stability}, opened in epoch {row.opened_epoch}"
                for row in rifts
                if row.dimension_id == dimension.id
            ]
            article.beings = [self.names.get(row.entity_id, "") for row in beings if row.home_dimension_id == dimension.id and self.names.get(row.entity_id)]
            found.append(article)
            for cluster in sorted(
                (row for row in ladder.clusters.values() if row.dimension_id == dimension.id and row.parent_cluster_id is None), key=lambda row: row.id
            ):
                await add_cluster(cluster, 1)
            for galaxy in sorted(
                (row for row in ladder.galaxies.values() if row.dimension_id == dimension.id and row.cluster_id is None), key=lambda row: row.id
            ):
                await add_galaxy(galaxy, 1)
        placed = {article.node_id for article in found}
        for cluster in sorted((row for row in ladder.clusters.values() if row.id not in placed and row.parent_cluster_id is None), key=lambda row: row.id):
            await add_cluster(cluster, 0)
        placed = {article.node_id for article in found}
        for galaxy in sorted((row for row in ladder.galaxies.values() if row.id not in placed), key=lambda row: row.id):
            await add_galaxy(galaxy, 0)
        return found

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
        facts += [
            Labelled("Magnetism", f"{world.magnetism}/100"),
            Labelled("Radiation", f"{world.radiation}/100"),
            Labelled("Biosphere", f"{world.biosphere_health}/100"),
            Labelled("Age", WORLD_AGE_LABELS[world.age_stage]),
        ]
        if world.mood:
            facts.append(Labelled("Mood toward its peoples", f"{world.mood:+d}"))
        for label, node_id in (("Galaxy", world.galaxy_id), ("Dimension", world.dimension_id)):
            if node_id is not None:
                facts.append(Labelled(label, self.names.get(node_id, "?")))
        return WorldArticle(
            world=world,
            anchor=world_anchor(world.id),
            depth_level=level,
            meta=meta,
            cover=await cover_of(self.session, world.id),
            guide=await traveller_guide(self.session, self.rules, world.id, complete=True),
            picture=await map_picture(self.session, self.rules, world.id, epoch),
            below=await world_below(self.session, self.rules, world.id, epoch, world_anchor(world.id)),
            facts=facts,
            typed=self.typed.of(world.id),
            wheel=self.wheels.get(world.id),
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
                    lines=[ChronicleLine(spoken(line.kind), line.year, clean_lore(line.text), line.son_id) for line in lines if line.visible],
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
                            battle_field(battle, self.names),
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

    def index(
        self, sons: list[SonArticle], groups: list[WorldGroup], worlds: list[StarSection], gods: list["GodArticle"], ladder: list[ScaleArticle]
    ) -> dict[str, list[IndexEntry]]:
        entries = [IndexEntry(article.son.name, article.anchor, "son") for article in sons]
        entries += [IndexEntry(article.name, article.anchor, article.kind) for article in ladder]
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


SEED_CHOOSES = "Chosen by the seed"
BLANK_CANVAS = "Blank canvas"
NO_LAYER = "None"
MOISTURE_SCALE = " (from -100 parched to 100 soaked)"


def chosen(value: int | None, unit: str = "%") -> str:
    return SEED_CHOOSES if value is None else f"{value}{unit}"


def layer_fact(settings: GenesisSettings) -> str:
    if settings.cosmos_shape is not CosmosShape.LAYERED:
        return NO_LAYER
    return DIMENSION_KINDS[settings.layer_kind].label if settings.layer_kind is not None else SEED_CHOOSES


def family_levels(settings: GenesisSettings) -> str:
    if not settings.technology_levels:
        return f"every family at the level of {TECHNOLOGY_LABELS[settings.technology].lower()}"
    return "; ".join(f"{humanize(family.value)} {level}/{TECH_LEVEL_CEILING}" for family, level in sorted(settings.technology_levels.items()))


def settings_facts(settings: GenesisSettings) -> list[Labelled]:
    return [
        Labelled("Template", TEMPLATES[settings.template].name if settings.template is not None else BLANK_CANVAS),
        Labelled("Magic", f"{settings.magic}/100"),
        Labelled("Danger", f"{settings.danger}/100"),
        Labelled("Technology", TECHNOLOGY_LABELS[settings.technology]),
        Labelled("Technology by family", family_levels(settings)),
        Labelled("Made minds", chosen(settings.made_minds, "/100")),
        Labelled("Reach of information", chosen(settings.information_reach, "/100")),
        Labelled("Texture of the language", TEXTURE_LABELS[settings.language_texture]),
        Labelled("Counting of the first tongues", BASES[settings.numeral_base].label if settings.numeral_base is not None else SEED_CHOOSES),
        Labelled("First peoples", str(settings.peoples)),
        Labelled("Cosmos size", COSMOS_LABELS[settings.cosmos_size]),
        Labelled("Shape of the cosmos", SHAPE_LABELS[settings.cosmos_shape]),
        Labelled("Second layer", layer_fact(settings)),
        Labelled("Storyteller", STORYTELLER_LABELS[settings.storyteller]),
        Labelled("Ages", AGE_CYCLE_LABELS[settings.age_cycle]),
        Labelled("Kind of the first world", WORLD_TYPES[settings.world_type].label if settings.world_type is not None else SEED_CHOOSES),
        Labelled("Water", chosen(settings.sea_pct)),
        Labelled("High ground", chosen(settings.mountains_pct)),
        Labelled("Moisture", chosen(settings.moisture_pct, MOISTURE_SCALE)),
        Labelled("Climate age", CLIMATES[settings.climate_era].label if settings.climate_era is not None else SEED_CHOOSES),
        Labelled("Age at the first epoch", WORLD_AGE_LABELS[settings.world_age] if settings.world_age is not None else SEED_CHOOSES),
        Labelled("Tone asked for", settings.tone or "Free"),
    ]


def creation_facts(cosmos: CosmosRow) -> list[Labelled]:
    settings = cosmos.genesis_settings
    return settings_facts(settings) if settings is not None else [Labelled("Genesis settings", "Not kept: this world was made before they were recorded")]


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
    ladder = await builder.scale_ladder()
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
                god,
                builder.names.get(god.world_id, "?"),
                powers,
                stats,
                await cover_of(session, god.id),
                fate,
                god_anchor(god.id),
                builder.typed.of(god.id),
                builder.audiences.get(god.id, SpeakerAudiences()),
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
    record_count = int(await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.status != EntityStatus.REJECTED)) or 0)
    world = await session.get(WorldRow, cosmos.primary_world_id) if cosmos.primary_world_id else None
    return BookModel(
        cosmos=cosmos,
        title=cosmos.name,
        creator=creator,
        cover=(await cover_of(session, world.id) if world else None) or (await cover_of(session, creator.id) if creator else None),
        epochs_count=cosmos.epoch,
        world_year=cosmos.epoch * rules.time.years_per_epoch,
        record_count=record_count,
        laws=laws,
        creator_cover=await cover_of(session, creator.id) if creator else None,
        creator_beliefs=list(await session.scalars(select(FolkBeliefRow).where(FolkBeliefRow.god_node_id == creator_id))),
        stars=stars,
        ladder=ladder,
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
        deeds=await deeds_chapter(session, rules),
        ledger=list(await session.scalars(select(LedgerEntryRow).order_by(LedgerEntryRow.epoch, LedgerEntryRow.id))),
        index=builder.index(sons, groups, stars, gods, ladder),
        multi_world=multi_world,
        names=builder.names,
        knowledge=await builder.knowledge(),
        cosmic=await cosmic_chronicle(session, rules, complete=True) if multi_world else [],
        creator_hand=await creator_hand(session),
        wars=await builder.wars(),
        creator_typed=builder.typed.of(creator.id) if creator is not None else [],
        records=[*builder.typed.records, *await type_tables(session, rules), *await record_tables(session, builder.ledger)],
        ledger_changes=builder.typed.ledger_changes(await session.scalars(select(LedgerChangeRow).order_by(LedgerChangeRow.entry_id, LedgerChangeRow.id))),
        creation=creation_facts(cosmos),
        divine_will=await divine_will_record(session, builder.names),
        team=await team_record(session),
        writings=await divine_will_writings(session, builder.names),
    )


async def entry_chronicle(session: AsyncSession, *, son_id: int | None, entity_id: int | None) -> list[ChronicleLine]:
    statement = select(ChronicleRow).where(kept_lines())
    if entity_id is not None:
        statement = statement.join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRow.id).where(ChronicleEntityRow.entity_id == entity_id)
    else:
        statement = statement.where(ChronicleRow.son_id == son_id)
    rows = await session.scalars(statement.order_by(ChronicleRow.id))
    return [ChronicleLine(spoken(told_kind(row)), row.year, clean_lore(row.text), row.son_id) for row in rows]


def aspect_words(rows: list[DimensionAspectRow]) -> str:
    named = [(ELEMENT_LABELS[row.element] if row.element is not None else (row.form.value if row.form is not None else "")).replace("_", " ") for row in rows]
    return ", ".join(f"{name.lower()} {row.strength}/100" for name, row in zip(named, rows, strict=True))
