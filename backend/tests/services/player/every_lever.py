import enum
import types
import typing
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.core.random import SeededRandom
from aerona.db.base import Base
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.agency import CreationRewardRow
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.ages import EcoTransformationRow
from aerona.db.tables.agrarian import BrandRow, CommonsRow
from aerona.db.tables.arts import ArtMovementRow, ClubRow, LeagueRow
from aerona.db.tables.body_systems import BodySystemRow, SensitivityRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.childhood import PedagogyRow
from aerona.db.tables.city_rules import ConurbationRow, LandUseRuleRow, MunicipalServiceRow
from aerona.db.tables.collective import LearningEventRow
from aerona.db.tables.commerce import LeaseRow, PromotionRow, ShopRow, SupplyTierRow
from aerona.db.tables.competition import CartelRow, MarketStructureRow, PriceWarRow
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.couplings import SociolectRow
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.culture import ArtworkProfileRow, BookContentRow
from aerona.db.tables.cycles import ManumissionRow
from aerona.db.tables.daily_life import HouseworkRow, LeisurePursuitRow
from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import CurrencyRow, WorkshopRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.epochs import DeferredStepRow, EpochRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.fertility_means import FertilityUseRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.db.tables.folk_knowledge import FolkClassRow, FolkKnowledgeRow
from aerona.db.tables.forecasting import ObservationMethodRow, WeatherWorkRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgCliqueRow, OrgMergerRow, OrgResearchRow, OrgSeatRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.honours import HonourHeldRow, HonourKindRow, NamedUnitRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.interworld import InterworldCampaignRow, InterworldMigrationRow, OrbitalControlRow
from aerona.db.tables.intimacy import RestraintCustomRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.kin import KinGroupRow
from aerona.db.tables.kin_dynamics import ElderSwayRow, KinBlendRow, KinDisowningRow, KinDynamicRow, KinFavourRow, KinRivalryRow
from aerona.db.tables.labour import LabourContractRow, LabourDisputeRow
from aerona.db.tables.law_depth import MoleHuntRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.leagues import LeagueDecisionRow, LeagueMemberRow
from aerona.db.tables.lore import HistorianViewRow, MessageRow
from aerona.db.tables.mass_weapons import DeterrencePostureRow, MassWeaponRow, WarRemnantRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow, RecordMediumRow
from aerona.db.tables.military import ArmyUnitRow, OccupationRow
from aerona.db.tables.mind import TraitRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.museums import MuseumPieceRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationMeasureRow, OccupationRegimeRow
from aerona.db.tables.operations import SupplyFlowRow
from aerona.db.tables.orders import BillOfExchangeRow
from aerona.db.tables.plants import PlantPartRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.population import PopulationPolicyRow
from aerona.db.tables.prehistory import DeepTimeEventRow, DeepTimeRunRow, PrehistoryEventRow, PrehistoryRow
from aerona.db.tables.protected_nature import ConservationMovementRow, ProtectedAreaRow, SpeciesProtectionRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.tables.region import RegionDangerRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.routes import HorizonIntuitionRow, RouteRow
from aerona.db.tables.sacred import DivinationSystemRow, DoctrineSacramentRow, GeniusLocusRow
from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow, WaveWarningRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, SecurityPriceRow, StockExchangeRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.space_weather import SpaceWeatherEventRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import ArmyRow, HeroQuestRow, WarRow, WarSideRow
from aerona.db.tables.water import SedimentFlowRow
from aerona.db.tables.works import PublicWorksRow, PublicWorkStageRow, StateEnterpriseRow
from aerona.db.tables.youth import YouthGroupRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.agrarian import CommonsKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import SocialBias
from aerona.domain.enums.cosmography import (
    BeingKind,
    ClusterKind,
    DimensionalEventKind,
    DimensionKind,
    GalacticEventKind,
    GalaxyType,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
)
from aerona.domain.enums.cycles import ManumissionPath
from aerona.domain.enums.death_work import DeathRole
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.epoch import DeferredStepStatus
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.law_depth import MoleHuntOutcome
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import TraitKind, ValueAxis
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.prehistory import DeepTimeState, PrehistoryKind, PrehistorySource, PrehistoryState
from aerona.domain.enums.sacred import DivinationKind, SacramentKind, SacramentProtection
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.enums.war import HeroQuestStatus
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import CelestialStats, IdeologyStats, NaturalLawStats, OuterBeingStats, StructureStats, VesselStats
from aerona.engine.arts.movements import found_movement, makers_by_town
from aerona.engine.cosmos import control
from aerona.engine.cosmos.beings import create_being
from aerona.engine.cosmos.control import dimensional_event, galactic_event
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.cosmos.ladder import ClusterDraft, DimensionDraft, GalaxyDraft, create_cluster, create_dimension, create_galaxy, ensure_ladder
from aerona.engine.cosmos.phenomena import form_phenomenon
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.rifts import open_rift
from aerona.engine.economy.route_control import route_of
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.phases.heroes import load_hero_world
from aerona.engine.phases.society_support.quests import quest_options
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import connect, spoken_language
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import set_stats
from aerona.engine.sacred.places import town_of
from aerona.engine.services.war import sides_of
from aerona.engine.water.ice import COAST_OF_KIND
from aerona.rules.registry import Rules

Setup = Callable[[AsyncSession], Awaitable[None]]
TYPES = {kind.value: kind for kind in EntityType}
ROLES: Mapping[str, EntityType] = {
    "realm": EntityType.POLITY,
    "overlord": EntityType.POLITY,
    "vassal": EntityType.POLITY,
    "demander": EntityType.POLITY,
    "power": EntityType.POLITY,
    "client": EntityType.POLITY,
    "issuer": EntityType.SETTLEMENT,
    "lender": EntityType.SETTLEMENT,
    "borrower": EntityType.SETTLEMENT,
    "mother": EntityType.SETTLEMENT,
    "colony": EntityType.SETTLEMENT,
    "community": EntityType.SETTLEMENT,
    "home": EntityType.SETTLEMENT,
    "town": EntityType.SETTLEMENT,
    "keeper": EntityType.SETTLEMENT,
    "host": EntityType.SETTLEMENT,
    "capital": EntityType.SETTLEMENT,
    "first": EntityType.SETTLEMENT,
    "second": EntityType.SETTLEMENT,
    "into": EntityType.SETTLEMENT,
    "attacker": EntityType.SETTLEMENT,
    "defender": EntityType.SETTLEMENT,
    "market": EntityType.SETTLEMENT,
    "core": EntityType.SETTLEMENT,
    "traitor": EntityType.SETTLEMENT,
    "victim": EntityType.SETTLEMENT,
    "holder": EntityType.MORTAL,
    "bearer": EntityType.MORTAL,
    "subject": EntityType.MORTAL,
    "owner": EntityType.MORTAL,
    "target": EntityType.MORTAL,
    "source": EntityType.MORTAL,
    "member": EntityType.MORTAL,
    "node": EntityType.MORTAL,
    "entity": EntityType.MORTAL,
    "hero": EntityType.MORTAL,
    "heir": EntityType.MORTAL,
    "mourner": EntityType.MORTAL,
    "deceased": EntityType.MORTAL,
    "learner": EntityType.MORTAL,
    "teacher": EntityType.MORTAL,
    "agent": EntityType.MORTAL,
    "spymaster": EntityType.MORTAL,
    "commander": EntityType.MORTAL,
    "founder": EntityType.MORTAL,
    "suitor": EntityType.MORTAL,
    "spouse": EntityType.MORTAL,
    "child": EntityType.MORTAL,
    "parent": EntityType.MORTAL,
    "plant": EntityType.SPECIES,
    "pest": EntityType.SPECIES,
    "prey": EntityType.SPECIES,
    "hunter": EntityType.SPECIES,
}
SONS = frozenset({"son", "god", "patron", "witness_son", "sibling", "parent_son", "child_son", "killer_son"})


class Selector:
    async def read(self, session: AsyncSession) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class Pick(Selector):
    kind: EntityType | str
    skip: int = 0

    async def read(self, session: AsyncSession) -> Any:
        return await pick(session, self.kind, self.skip)


@dataclass(frozen=True)
class Newest(Selector):
    kind: EntityType | str

    async def read(self, session: AsyncSession) -> Any:
        return await newest(session, self.kind)


@dataclass(frozen=True)
class Where(Selector):
    table: str
    key: str
    filters: Mapping[str, Any] = field(default_factory=dict)

    async def read(self, session: AsyncSession) -> Any:
        found = TABLES[self.table]
        column = getattr(found, self.key)
        statement = select(column).where(*(getattr(found, name) == wanted for name, wanted in self.filters.items()))
        return await session.scalar(statement.order_by(column).limit(1))


@dataclass(frozen=True)
class All(Selector):
    table: str
    key: str
    filters: Mapping[str, Any] = field(default_factory=dict)

    async def read(self, session: AsyncSession) -> Any:
        found = TABLES[self.table]
        column = getattr(found, self.key)
        filters = [getattr(found, name) == await resolved(session, wanted) for name, wanted in self.filters.items()]
        return list(await session.scalars(select(column).where(*filters).order_by(column.desc())))


@dataclass(frozen=True)
class Computed(Selector):
    compute: Callable[[AsyncSession], Awaitable[Any]]

    async def read(self, session: AsyncSession) -> Any:
        return await self.compute(session)


@dataclass(frozen=True)
class Lever:
    values: Mapping[str, Any] = field(default_factory=dict)
    before: tuple[tuple[str, Mapping[str, Any]], ...] = ()
    setup: Setup | None = None
    then: Setup | None = None


async def canon(session: AsyncSession, kind: EntityType, skip: int) -> int | None:
    rows = list(
        await session.scalars(
            select(EntityRow.id).where(EntityRow.entity_type == kind, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(skip + 1)
        )
    )
    return rows[skip] if len(rows) > skip else (rows[-1] if rows else None)


TABLES = {mapper.class_.__tablename__: mapper.class_ for mapper in Base.registry.mappers}


def exact_table(name: str, *, strict: bool = False) -> Any:
    for table in (f"{name}s", f"{name}es", f"{name[:-1]}ies" if name.endswith("y") else "", f"{name[:-2]}es" if name.endswith("is") else "", name):
        found = TABLES.get(table)
        if found is not None and "id" in found.__table__.c:
            return found
    endings = [found for table, found in TABLES.items() if table.endswith(f"_{name}s") and "id" in found.__table__.c]
    if strict and len(endings) > 1:
        raise LookupError(f"{name} names more than one table: {sorted(found.__tablename__ for found in endings)}; name the table in full")
    return endings[0] if endings else None


async def row_id(session: AsyncSession, name: str, skip: int) -> int | None:
    found = exact_table(name)
    if found is None:
        return None
    rows = list(await session.scalars(select(found.id).order_by(found.id).limit(skip + 1)))
    return rows[skip] if len(rows) > skip else (rows[-1] if rows else None)


def kind_of(name: str) -> EntityType | str:
    base = name.removesuffix("_ids").removesuffix("_id")
    last = base.split("_")[-1]
    if base in SONS or last in {"son", "god", "patron"}:
        return "son"
    if base == "foreign_god" or last in {"world", "star"}:
        return base if base == "foreign_god" else last
    for key in (base, last):
        if key in TYPES or key in ROLES:
            return TYPES.get(key) or ROLES[key]
    return base if exact_table(base) is not None else EntityType.MORTAL


async def nth(session: AsyncSession, column: Any, skip: int) -> int | None:
    rows = list(await session.scalars(select(column).order_by(column).limit(skip + 1)))
    return rows[min(skip, len(rows) - 1)] if rows else None


GODS: Mapping[str, Any] = {"son": SonRow.id, "foreign_god": ForeignGodRow.id, "world": WorldRow.id, "star": StarRow.id}


async def pick(session: AsyncSession, chosen: EntityType | str, skip: int) -> int | None:
    if isinstance(chosen, EntityType):
        return await canon(session, chosen, skip)
    if chosen in GODS:
        return await nth(session, GODS[chosen], skip)
    found = await row_id(session, chosen, skip)
    return found if found is not None else await canon(session, EntityType.MORTAL, skip)


def bounds(info: FieldInfo) -> tuple[int | None, int | None]:
    low = high = None
    for item in info.metadata:
        if getattr(item, "ge", None) is not None:
            low = item.ge
        elif getattr(item, "gt", None) is not None:
            low = item.gt + 1
        if getattr(item, "le", None) is not None:
            high = item.le
        elif getattr(item, "lt", None) is not None:
            high = item.lt - 1
    return low, high


class Filler:
    def __init__(self, session: AsyncSession, number: int) -> None:
        self.session = session
        self.number = number
        self.taken: dict[EntityType | str, int] = {}

    async def entity(self, name: str) -> int | None:
        chosen = kind_of(name)
        skip = self.taken.get(chosen, 0)
        self.taken[chosen] = skip + 1
        return await pick(self.session, chosen, skip)

    async def value(self, name: str, annotation: Any, info: FieldInfo) -> Any:
        origin, args = typing.get_origin(annotation), typing.get_args(annotation)
        if origin in (typing.Union, types.UnionType):
            inner = [arg for arg in args if arg is not type(None)]
            return await self.value(name, inner[0], info) if inner else None
        if origin is not None:
            return await self.compound(name, origin, args)
        return await self.scalar(name, annotation, info)

    async def compound(self, name: str, origin: Any, args: tuple[Any, ...]) -> Any:
        if origin is typing.Literal:
            return args[0]
        if origin is dict:
            return {}
        found = await self.entity(name) if name.endswith("_ids") else None
        return [found] if found is not None else []

    async def scalar(self, name: str, annotation: Any, info: FieldInfo) -> Any:
        if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
            return next(iter(annotation)).value
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return {key: await self.value(key, sub.annotation, sub) for key, sub in annotation.model_fields.items() if sub.is_required()}
        if annotation is int:
            return await self.entity(name) if name.endswith("_id") else number_within(info)
        if annotation is str:
            return f"Aldermere {self.number}" if "name" in name else "a plain account"
        return PLAIN_VALUES.get(annotation)


def number_within(info: FieldInfo) -> int:
    low, high = bounds(info)
    wanted = 5 if low is None or low <= 5 else low
    return min(wanted, high) if high is not None else wanted


PLAIN_VALUES: Mapping[Any, Any] = {bool: True, float: 1.0}


async def newest(session: AsyncSession, kind: EntityType | str) -> int | None:
    if isinstance(kind, EntityType):
        return await session.scalar(select(EntityRow.id).where(EntityRow.entity_type == kind).order_by(EntityRow.id.desc()).limit(1))
    found = exact_table(kind, strict=True)
    return await session.scalar(select(found.id).order_by(found.id.desc()).limit(1)) if found is not None else None


async def resolved(session: AsyncSession, value: Any) -> Any:
    if isinstance(value, Selector):
        return await value.read(session)
    if isinstance(value, list):
        return [await resolved(session, item) for item in value]
    if isinstance(value, dict):
        return {key: await resolved(session, item) for key, item in value.items()}
    return value


async def payload_for(session: AsyncSession, model: type[BaseModel], explicit: Mapping[str, Any], number: int) -> dict[str, Any]:
    filler = Filler(session, number)
    found: dict[str, Any] = {}
    for name, info in model.model_fields.items():
        if name in explicit:
            found[name] = await resolved(session, explicit[name])
        elif info.is_required():
            found[name] = await filler.value(name, info.annotation, info)
    return found


def setup_then(setup: Setup, *steps: str | tuple[str, Mapping[str, Any]], **values: Any) -> Lever:
    return Lever(values=values, before=tuple(step if isinstance(step, tuple) else (step, {}) for step in steps), setup=setup)


def after(*steps: str | tuple[str, Mapping[str, Any]], **values: Any) -> Lever:
    return Lever(values=values, before=tuple(step if isinstance(step, tuple) else (step, {}) for step in steps))


def given(**values: Any) -> Lever:
    return Lever(values=values)


async def first_world_mortal(session: AsyncSession, skip: int) -> int | None:
    world = select(func.min(WorldRow.id)).scalar_subquery()
    query = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world)
    return await session.scalar(query.order_by(EntityRow.id).offset(skip).limit(1))


async def ruling_mortal(session: AsyncSession) -> int | None:
    rulers = select(BondRow.source_node_id).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE)
    query = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.in_(rulers))
    return await session.scalar(query.order_by(EntityRow.id).limit(1))


async def heir_beside(session: AsyncSession) -> int | None:
    ruler = await ruling_mortal(session)
    query = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id != ruler)
    return await session.scalar(query.order_by(EntityRow.id).limit(1))


async def town_without_guild(session: AsyncSession) -> int | None:
    guilded = select(FactionProfileRow.home_entity_id).where(FactionProfileRow.kind == FactionKind.CRAFT_GUILD, FactionProfileRow.home_entity_id.is_not(None))
    query = select(EntityRow.id).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(guilded))
    return await session.scalar(query.order_by(EntityRow.id).limit(1))


async def known_bond(session: AsyncSession) -> BondRow | None:
    lore = select(EntityRow.id).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON)
    knowers = select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
    query = select(BondRow).where(
        BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(lore), BondRow.source_node_id.in_(knowers)
    )
    return await session.scalar(query.order_by(BondRow.id).limit(1))


async def knower(session: AsyncSession) -> int | None:
    bond = await known_bond(session)
    return bond.source_node_id if bond is not None else None


async def known_lore(session: AsyncSession) -> int | None:
    bond = await known_bond(session)
    return bond.target_node_id if bond is not None else None


HOME_MORTAL = Computed(lambda session: first_world_mortal(session, 0))
HOME_NEIGHBOUR = Computed(lambda session: first_world_mortal(session, 1))


REALM = EntityType.POLITY
TOWN = EntityType.SETTLEMENT
MORTAL = EntityType.MORTAL
TONGUE = EntityType.LANGUAGE
SOUND = ("sound_change:add", {"language_id": Pick(TONGUE), "kind": "shift", "source": "a", "target": "e"})
VEIL = ("word:veil", {"language_id": Pick(TONGUE), "node_id": Pick(MORTAL)})
SCRIPT = ("script:create", {"language_id": Pick(TONGUE), "system": "alphabet"})
DECIPHER = ("decipherment:start", {"language_id": Pick(TONGUE), "scholar_id": Pick(MORTAL)})
POLICY = ("language_policy:set", {"holder_id": Pick(REALM), "language_id": Pick(TONGUE), "policy": "official"})
TONGUE_GIVEN = ("divine_tongue:set", {"god_id": Pick("son")})
BEAST = ("beast:create", {"name": "Grimtooth"})
CRISIS = ("crisis:open", {"demander_id": Pick(REALM), "target_id": Pick(REALM, 1), "demand": "pay"})
IDEOLOGY = ("lore:create", {"entity_type": "ideology", "name": "The Open Hand", "world_id": Pick("world"), "values": {"tenets": ["legalism"]}})
PLANT = (
    "species:create",
    {
        "name": "Field Barley",
        "region_id": Pick(EntityType.REGION),
        "body_plan": "arboreal",
        "size_class": "small",
        "diet": "photosynthetic",
        "species_class": "plant",
    },
)
HERESY = ("cult:heresy", {"heresy_id": Pick(EntityType.CULT), "parent_id": Pick(EntityType.CULT, 1)})
DEED = ("deed:record", {"doer_id": Pick(MORTAL), "magnitude": 20})
ARTWORK = ("art:commission", {"patron_id": Pick(MORTAL), "medium": "musical"})
ITEM_DEED = ("item:deed", {"item_id": Pick(EntityType.ITEM), "deed": "battle"})
REPUTATION = ("renown:set", {"subject_id": Pick(MORTAL), "community_id": Pick(TOWN), "axis": "heroism", "value": 60})
CONTEST = ("contest:hold", {"challenger_id": Pick(MORTAL), "defender_id": Pick(MORTAL, 1), "kind": "riddle_game"})
DISEASE = ("disease:create", {"region_id": Pick(EntityType.REGION), "name": "Grey Cough"})


async def route_region(session: AsyncSession) -> int:
    route = await canon(session, EntityType.TRADE_ROUTE, 0)
    assert route is not None
    found = await route_of(await manual_context(session, "lever", Rules()), route)
    return found.path[0]


async def convicted_case(session: AsyncSession) -> int:
    town = await canon(session, EntityType.SETTLEMENT, 0)
    accused = await canon(session, EntityType.MORTAL, 0)
    case = CrimeCaseRow(
        settlement_entity_id=town, crime=CrimeKind.THEFT, accused_entity_id=accused, stage=CaseStage.CLOSED, verdict=Verdict.GUILTY, closed_epoch=0, locked=[]
    )
    session.add(case)
    await session.flush()
    return case.id


async def town_work(session: AsyncSession, kind: StructureKind) -> int:
    town = await canon(session, EntityType.SETTLEMENT, 0)
    found = await session.scalar(
        select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.kind == kind, StructureProfileRow.host_entity_id == town).limit(1)
    )
    if found is not None:
        return int(found)
    town_row = await session.get(EntityRow, town)
    assert town_row is not None
    work = await EntityRepository(session).create(
        EntityDraft(
            name=f"The Town {kind.value.replace('_', ' ').title()}",
            entity_type=EntityType.STRUCTURE,
            description="A work of the town.",
            stats=StructureStats(),
            power_level=1,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=town_row.world_id,
            location_id=town,
        )
    )
    session.add(StructureProfileRow(structure_entity_id=work.id, kind=kind, host_entity_id=town))
    await session.flush()
    return work.id


async def town_prison(session: AsyncSession) -> int:
    return await town_work(session, StructureKind.PRISON)


async def town_granary(session: AsyncSession) -> int:
    return await town_work(session, StructureKind.GRANARY)


async def town_beacon(session: AsyncSession) -> int:
    return await town_work(session, StructureKind.BEACON)


async def office_in_realm(session: AsyncSession, kind: OfficeKind) -> int:
    realm = await canon(session, EntityType.POLITY, 0)
    assert realm is not None
    holder = await canon(session, EntityType.MORTAL, 1)
    living = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)
    office = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm, OfficeRow.kind == kind).order_by(OfficeRow.id).limit(1))
    if office is None:
        session.add(OfficeRow(polity_entity_id=realm, kind=kind, holder_entity_id=holder))
    elif await session.scalar(select(OfficeRow.id).where(OfficeRow.id == office.id, OfficeRow.holder_entity_id.in_(living))) is None:
        office.holder_entity_id = holder
    await session.flush()
    return realm


async def spied_realm(session: AsyncSession) -> int:
    return await office_in_realm(session, OfficeKind.SPYMASTER)


async def ruled_realm(session: AsyncSession) -> int:
    return await office_in_realm(session, OfficeKind.RULER)


async def any_hunt(session: AsyncSession) -> int:
    found = await session.scalar(select(MoleHuntRow.id).order_by(MoleHuntRow.id.desc()).limit(1))
    if found is not None:
        return int(found)
    hunt = MoleHuntRow(outcome=next(iter(MoleHuntOutcome)), epoch=0)
    session.add(hunt)
    await session.flush()
    return hunt.id


async def profiled_town(session: AsyncSession) -> int:
    town = await canon(session, EntityType.SETTLEMENT, 0)
    assert town is not None
    if await session.get(SettlementProfileRow, town) is None:
        session.add(SettlementProfileRow(settlement_entity_id=town, size_tier=SizeTier.TOWN, locked=[], foreigners={}))
        await session.flush()
    return town


async def any_collection(session: AsyncSession) -> int:
    found = await session.scalar(select(CollectionRow.id).order_by(CollectionRow.id.desc()).limit(1))
    if found is not None:
        return int(found)
    world = await session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    event = CollectionRow(kind=CollectionKind.CORONATION, name="A crowning", world_id=world, start_epoch=0, locked=[])
    session.add(event)
    await session.flush()
    return event.id


async def any_vessel(session: AsyncSession) -> int:
    found = await session.scalar(select(VesselProfileRow.entity_id).order_by(VesselProfileRow.entity_id).limit(1))
    if found is not None:
        return int(found)
    town = await profiled_town(session)
    town_row = await session.get(EntityRow, town)
    assert town_row is not None
    ship = await EntityRepository(session).create(
        EntityDraft(
            name="The Tern",
            entity_type=EntityType.VESSEL,
            description="A ship of the town.",
            stats=VesselStats(),
            power_level=1,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=town_row.world_id,
            location_id=town,
        )
    )
    session.add(VesselProfileRow(entity_id=ship.id, kind=VehicleKind.SHIP, frame=VehicleFrame.COG, home_port_entity_id=town, locked=[]))
    await session.flush()
    return ship.id


async def heir_at_court(session: AsyncSession) -> None:
    realm = await ruled_realm(session)
    town = await profiled_town(session)
    profile = await session.get(PolityProfileRow, realm)
    assert profile is not None
    profile.capital_entity_id = profile.capital_entity_id or town
    stranger = await canon(session, EntityType.MORTAL, 3)
    row = await session.get(EntityRow, stranger)
    assert row is not None
    row.location_id = profile.capital_entity_id
    await session.flush()


async def a_lesson(session: AsyncSession) -> None:
    learner = await canon(session, EntityType.MORTAL, 0)
    assert learner is not None
    session.add(LearningEventRow(learner_entity_id=learner, bias=SocialBias.CONFORMITY, axis=ValueAxis.PIETY, shift=2, epoch=0))
    await session.flush()


async def town_district(session: AsyncSession) -> int:
    town = await canon(session, EntityType.SETTLEMENT, 0)
    found = await session.scalar(select(DistrictRow.id).where(DistrictRow.settlement_entity_id == town).order_by(DistrictRow.id).limit(1))
    assert found is not None
    return int(found)


async def first_son(session: AsyncSession) -> SonRow:
    son = await session.scalar(select(SonRow).order_by(SonRow.id).limit(1))
    assert son is not None
    return son


async def seasoned_son(session: AsyncSession) -> None:
    son = await first_son(session)
    son.level, son.fame = 9, 90


async def ascended_son(session: AsyncSession) -> None:
    son = await first_son(session)
    son.level, son.fame, son.stars = 9, 90, 5


async def placed_son(session: AsyncSession) -> None:
    (await first_son(session)).manually_assigned_epoch = 1


async def son_creation(session: AsyncSession) -> int | None:
    son = await first_son(session)
    return await session.scalar(
        select(EntityRow.id).where(EntityRow.creator_son_id == son.id, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )


async def living_planet(session: AsyncSession) -> None:
    world = await session.scalar(select(WorldRow).order_by(WorldRow.id).limit(1))
    assert world is not None
    world.world_type = WorldType.LIVING


async def prayer(session: AsyncSession) -> None:
    creator = await session.scalar(select(CreatorRow.id).limit(1))
    mortal = await canon(session, EntityType.MORTAL, 0)
    assert creator is not None and mortal is not None
    session.add(MessageRow(epoch=1, sender_node_id=mortal, recipient_node_id=creator, intent=MessageIntent.PRAYER, text="Let the rain come."))
    await session.flush()


async def historian_view(session: AsyncSession) -> None:
    people = await canon(session, EntityType.PEOPLE, 0)
    assert people is not None
    session.add(HistorianViewRow(epoch=1, people_entity_id=people, historian="Oren", text="They came from the coast."))
    await session.flush()


async def bartering_towns(session: AsyncSession) -> None:
    for skip in (0, 1):
        town = await canon(session, EntityType.SETTLEMENT, skip)
        resource = await canon(session, EntityType.RESOURCE, skip)
        assert town is not None and resource is not None
        await connect(session, town, resource, BondKind.OWNS, 1)


async def dead_sibling(session: AsyncSession) -> None:
    sons = list(await session.scalars(select(SonRow).order_by(SonRow.id).limit(2)))
    sons[1].status, sons[1].death_epoch = SonStatus.DEAD, 1


Town = aliased(EntityRow)


async def peopled_town(session: AsyncSession) -> int:
    found = await session.scalar(
        select(EntityRow.location_id)
        .join(Town, Town.id == EntityRow.location_id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, Town.entity_type == EntityType.SETTLEMENT)
        .order_by(EntityRow.location_id)
        .limit(1)
    )
    assert found is not None
    return int(found)


async def free_hero(session: AsyncSession) -> int:
    ctx = await manual_context(session, "free_hero", Rules())
    world = await load_hero_world(ctx)
    questing = select(HeroQuestRow.hero_entity_id).where(HeroQuestRow.status == HeroQuestStatus.ACTIVE)
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(questing))
    found = next((hero.id for hero in await session.scalars(query.order_by(EntityRow.id)) if quest_options(ctx.rules, world.quests, hero)), None)
    assert found is not None
    return int(found)


async def questing_hero(session: AsyncSession) -> int:
    query = select(HeroQuestRow.hero_entity_id).where(HeroQuestRow.status == HeroQuestStatus.ACTIVE)
    found = await session.scalar(query.order_by(HeroQuestRow.id.desc()).limit(1))
    assert found is not None
    return int(found)


async def unbrave_mortal(session: AsyncSession) -> int:
    brave = select(TraitRow.node_id).where(TraitRow.trait == TraitKind.BRAVE)
    query = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(brave))
    found = await session.scalar(query.order_by(EntityRow.id).limit(1))
    assert found is not None
    return int(found)


async def dead_sibling_and_rich_town(session: AsyncSession) -> None:
    await dead_sibling(session)
    town = await session.scalar(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )
    assert town is not None
    set_stats(town, wealth=100, prosperity=100)


async def dead_and_rich(session: AsyncSession) -> None:
    await dead_sibling(session)
    await rich_creator(session)


async def rich_creator(session: AsyncSession) -> None:
    creator = await session.scalar(select(CreatorRow).limit(1))
    assert creator is not None
    creator.essence += 1000


async def soul_eating(session: AsyncSession) -> None:
    kind = await canon(session, EntityType.SPECIES, 0)
    assert kind is not None
    await EntityRepository(session).add_trait(kind, CreatureTrait.SOUL_EATER)


async def underworld(session: AsyncSession) -> None:
    region = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.REGION).order_by(EntityRow.id).limit(1))
    assert region is not None
    region.is_underworld = True


async def mirrored(session: AsyncSession) -> None:
    worlds = list(await session.scalars(select(WorldRow).order_by(WorldRow.id).limit(2)))
    worlds[1].mirror_twin_id = worlds[0].id


async def far_town(session: AsyncSession) -> int | None:
    home = await session.scalar(select(EntityRow.world_id).where(EntityRow.id == await canon(session, EntityType.SETTLEMENT, 0)))
    return await session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id != home)
        .order_by(EntityRow.id)
        .limit(1)
    )


async def astronomy(session: AsyncSession) -> None:
    record = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE).order_by(EntityRow.id).limit(1))
    assert record is not None
    record.knowledge_branch = KnowledgeBranch.ASTRONOMY


async def bilingual(session: AsyncSession) -> None:
    town = await canon(session, EntityType.SETTLEMENT, 0)
    assert town is not None
    for skip in (0, 1, 2):
        language = await canon(session, EntityType.LANGUAGE, skip)
        assert language is not None
        await connect(session, town, language, BondKind.SPEAKS, 1)


async def strangers(session: AsyncSession) -> None:
    first, second = await canon(session, EntityType.SETTLEMENT, 0), await canon(session, EntityType.SETTLEMENT, 1)
    assert first is not None and second is not None
    own = await spoken_language(session, first)
    others = [await canon(session, EntityType.LANGUAGE, skip) for skip in (0, 1, 2)]
    other = next(item for item in others if item is not None and (own is None or item != own.id))
    await session.execute(update(BondRow).where(BondRow.source_node_id == second, BondRow.kind == BondKind.SPEAKS).values(state=BondState.PAST))
    await connect(session, second, other, BondKind.SPEAKS, 1)


async def ruin(session: AsyncSession) -> None:
    town = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT).order_by(EntityRow.id.desc()).limit(1))
    assert town is not None
    town.status, town.end_epoch = EntityStatus.DEAD, 1
    await EntityRepository(session).add_flag(town.id, EntityFlag.RUIN)


async def occupied(session: AsyncSession) -> None:
    region = await canon(session, EntityType.REGION, 0)
    town = await canon(session, EntityType.SETTLEMENT, 0)
    assert region is not None and town is not None
    session.add(OccupationRow(region_entity_id=region, occupier_entity_id=town, since_epoch=1))
    await session.flush()


async def intuition(session: AsyncSession) -> None:
    mortal = await canon(session, EntityType.MORTAL, 0)
    assert mortal is not None
    session.add(HorizonIntuitionRow(mortal_entity_id=mortal, epoch=1, how="a light beyond the sky"))
    await session.flush()


async def rewarded(session: AsyncSession) -> None:
    son = await first_son(session)
    entity = await canon(session, EntityType.MORTAL, 0)
    assert entity is not None
    session.add(CreationRewardRow(entity_id=entity, son_id=son.id, epoch=1, xp=20, renown=10, essence=5))
    await session.flush()


async def hunted(session: AsyncSession) -> None:
    prey = await canon(session, EntityType.SPECIES, 0)
    hunter = await canon(session, EntityType.SPECIES, 1)
    assert prey is not None and hunter is not None
    await connect(session, hunter, prey, BondKind.HUNTS, 1)


async def gate_lore(session: AsyncSession) -> None:
    record = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE).order_by(EntityRow.id.desc()).limit(1))
    assert record is not None
    record.knowledge_branch = KnowledgeBranch.GATE_LORE


async def ruled_town(session: AsyncSession) -> None:
    subject = await canon(session, EntityType.SETTLEMENT, 0)
    ruler = await canon(session, EntityType.SETTLEMENT, 4)
    assert subject is not None and ruler is not None
    await connect(session, ruler, subject, BondKind.RULES, 1)


async def failed_birth(session: AsyncSession) -> None:
    step = await session.scalar(select(DeferredStepRow).order_by(DeferredStepRow.id.desc()).limit(1))
    assert step is not None
    step.status = DeferredStepStatus.FAILED


async def older_vessel(session: AsyncSession) -> int:
    found = await session.scalar(select(VesselProfileRow.entity_id).order_by(VesselProfileRow.entity_id.desc()).offset(1).limit(1))
    assert found is not None
    return int(found)


async def battered_vessel(session: AsyncSession) -> None:
    vessel = await session.scalar(select(VesselProfileRow).order_by(VesselProfileRow.entity_id.desc()).limit(1))
    assert vessel is not None and vessel.home_port_entity_id is not None
    vessel.condition = 20
    session.add(WorkshopRow(community_entity_id=vessel.home_port_entity_id, kind=WorkshopKind.SHIPYARD, level=2, built_epoch=1))
    port = await session.get(EntityRow, vessel.home_port_entity_id)
    assert port is not None
    set_stats(port, wealth=100)
    await session.flush()


async def allied_side(session: AsyncSession) -> int | None:
    war = await session.scalar(select(WarRow).order_by(WarRow.id.desc()).limit(1))
    assert war is not None
    leaders = await sides_of(session, war)
    sides = list(await session.scalars(select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id).order_by(WarSideRow.entity_id)))
    return next((side for side in sides if leaders is None or side not in leaders), None)


async def soul_range(session: AsyncSession) -> int | None:
    kind = await canon(session, EntityType.SPECIES, 0)
    return await session.scalar(
        select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == kind).order_by(SpeciesRangeRow.region_entity_id).limit(1)
    )


async def market_goods(session: AsyncSession) -> None:
    ledger = GoodsLedger(session, 1)
    for skip in (0, 1):
        town = await canon(session, EntityType.SETTLEMENT, skip)
        assert town is not None
        await ledger.add(town, CommodityKind.GRAIN, 40, GoodsFlow.PRODUCTION)
        await ledger.add(town, CommodityKind.TIMBER, 40, GoodsFlow.PRODUCTION)


async def armoury(session: AsyncSession) -> None:
    town = await canon(session, EntityType.SETTLEMENT, 0)
    assert town is not None
    await GoodsLedger(session, 1).add(town, CommodityKind.WEAPONS, 40, GoodsFlow.PRODUCTION)


async def first_epoch(session: AsyncSession) -> None:
    if await session.get(EpochRow, 1) is None:
        session.add(EpochRow(epoch=1, name="The Dawn"))
        await session.flush()


async def foreign_god(session: AsyncSession) -> None:
    world = await session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    assert world is not None
    await add_foreign_god(session, Rules(), SeededRandom.for_epoch(1, 1, "lever"), 1, NewForeignGod(name="Ussamar", world_id=world, domains=(Domain.SEA, None)))


async def natural_law(session: AsyncSession) -> int:
    world = await session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    assert world is not None
    known = await session.scalar(select(EntityRow.id).where(EntityRow.name == "The Long Summer", EntityRow.entity_type == EntityType.NATURAL_LAW))
    if known is not None:
        return known
    law = await EntityRepository(session).create(
        EntityDraft(
            name="The Long Summer",
            entity_type=EntityType.NATURAL_LAW,
            description="A law of the world.",
            stats=NaturalLawStats(),
            power_level=2,
            origin=EntityOrigin.CREATOR,
            birth_epoch=1,
            world_id=world,
            natural_law=NaturalLaw.BOUNTY,
        )
    )
    await session.flush()
    return law.id


async def prime_dimension(session: AsyncSession) -> int:
    await ensure_ladder(session, Rules())
    prime = (await Cosmography.load(session)).prime
    assert prime is not None
    return prime.id


async def bound_law(session: AsyncSession) -> None:
    law = await natural_law(session)
    prime = await prime_dimension(session)
    await control.bind_law(await manual_context(session, "bound_law", Rules()), prime, law)


async def heavens(session: AsyncSession) -> None:
    rules = Rules()
    await ensure_ladder(session, rules)
    ctx = await manual_context(session, "heavens", rules)
    plane = await create_dimension(session, rules, DimensionDraft("Astral Deep", DimensionKind.ASTRAL, ctx.epoch))
    group = await create_cluster(session, rules, ClusterDraft("Far Group", ClusterKind.GALAXY_GROUP, ctx.epoch, dimension_id=plane.id))
    galaxy = await create_galaxy(session, rules, GalaxyDraft("Far Spiral", GalaxyType.SPIRAL, ctx.epoch, cluster_id=group.id))
    await galactic_event(ctx, galaxy.id, GalacticEventKind.STARBURST, intensity=20, other_id=None, star_id=None)
    await dimensional_event(ctx, plane.id, DimensionalEventKind.VEIL_THINNING, intensity=10, other_id=None, world_id=None)
    world = await session.scalar(select(WorldRow).order_by(WorldRow.id).limit(1))
    assert world is not None
    region = await session.scalar(
        select(EntityRow).where(EntityRow.entity_type == EntityType.REGION, EntityRow.world_id == world.id).order_by(EntityRow.id).limit(1)
    )
    assert region is not None
    await open_rift(ctx, world, region, plane, RiftCause.CREATOR)
    await create_being(ctx, BeingKind.BOUNDARY_KEEPER, world, region=region, home_dimension_id=plane.id)
    await form_phenomenon(ctx, PhenomenonKind.MINERAL_GROWTH, region, PhenomenonCause.DIVINE, intensity=40)
    await EntityRepository(session).create(
        EntityDraft(
            name="The Pale Wanderer",
            entity_type=EntityType.CELESTIAL,
            description="A body that returns.",
            stats=CelestialStats(brightness=40, influence=30, cycle=75),
            power_level=2,
            origin=EntityOrigin.CREATOR,
            birth_epoch=1,
            world_id=world.id,
        )
    )
    await session.flush()


async def rich_heavens(session: AsyncSession) -> None:
    await heavens(session)
    await rich_creator(session)


async def outer_being(session: AsyncSession) -> int:
    found = await session.scalar(select(EntityRow.id).where(EntityRow.entity_type == EntityType.OUTER_BEING).order_by(EntityRow.id).limit(1))
    if found is not None:
        return found
    world = await session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    assert world is not None
    being = await EntityRepository(session).create(
        EntityDraft(
            name="The Far Listener",
            entity_type=EntityType.OUTER_BEING,
            description="From outside.",
            stats=OuterBeingStats(size=40, interest=50, influence=30),
            power_level=3,
            origin=EntityOrigin.CREATOR,
            birth_epoch=1,
            world_id=world,
        )
    )
    await session.flush()
    return being.id


CUSTOM_KIND = ("kind:create", {"catalog": "technique", "base": "phalanx_drill", "name": "Shieldwall Drill"})
SPEAKERS = ("language:speakers", {"community_id": Pick(TOWN), "language_id": Pick(EntityType.LANGUAGE, 2), "share": 30, "kind": "second"})
TEMPLE = ("structure:commission", {"site_id": Pick(TOWN), "kind": "temple"})
CRIME = ("faction:found", {"community_id": Pick(TOWN), "kind": "crime_family"})
HOUSE = ("faction:found", {"community_id": Pick(TOWN, 2), "kind": "merchant_guild"})
ORDER = ("faction:edit", {"faction_id": Newest(EntityType.FACTION), "values": {"kind": "mage_order"}})
DISTRICT = Computed(town_district)
TURF = ("turf:set", {"district_id": DISTRICT, "faction_id": Newest(EntityType.FACTION), "strength": 40})
RACKET = ("racket:set", {"faction_id": Newest(EntityType.FACTION), "settlement_id": Pick(TOWN), "racket": "gambling"})
PAYROLL = ("payroll:add", {"faction_id": Newest(EntityType.FACTION), "official_id": Pick(MORTAL)})
STANCE = ("crime_stance:set", {"polity_id": Pick(REALM), "faction_id": Newest(EntityType.FACTION), "stance": "suppress"})
LAW = ("order_law:set", {"faction_id": Newest(EntityType.FACTION), "law": "share_discoveries", "strength": 40})
TRIAL = ("tribunal:convene", {"faction_id": Newest(EntityType.FACTION), "law": "share_discoveries", "accused_id": Pick(MORTAL)})
POST = ("trading_post:open", {"owner_id": Newest(EntityType.FACTION), "host_id": Pick(TOWN)})
SERVICE_SET = ("district_service:set", {"district_id": DISTRICT, "service": "watch", "coverage": 60})
CONVOY = ("convoy:send", {"route_id": Pick(EntityType.TRADE_ROUTE)})
FLEET = ("fleet:set", {"owner_id": Pick(TOWN), "kind": "animal_carts", "count": 12})
CONVICTION = Computed(convicted_case)
PRISON = Computed(town_prison)
SYSTEM = ("legal_system:set", {"holder_id": Pick(REALM), "system": "precedent"})
PRECEDENT = ("precedent:add", {"holder_id": Pick(REALM), "crime": "theft", "verdict": "guilty"})
APPEAL = ("appeal:file", {"case_id": CONVICTION, "to_court": "provincial", "fee": 0})
DEED = ("registry:add", {"holder_id": Pick(REALM), "kind": "debt", "owner_id": Pick(MORTAL), "counterparty_id": Pick(MORTAL, 1), "amount": 30})
CLAIM = ("jurisdiction:set", {"holder_id": Pick(REALM), "claimant_id": Pick(EntityType.CULT), "claim": "clergy", "strength": 40})
OUTLAW = ("outlaw:declare", {"mortal_id": Pick(MORTAL, 2), "polity_id": Pick(REALM), "bounty": 20})
PARDON = ("pardon:grant", {"granter_id": Pick(MORTAL), "mortal_id": Pick(MORTAL, 2)})
PRISON_SET = ("prison:set", {"structure_id": PRISON, "values": {"food": 60}})
JAIL = ("prisoner:jail", {"mortal_id": Pick(MORTAL, 2), "prison_id": PRISON, "term": 3})
SPY_NET = ("faction:spy", {"spymaster_id": Pick(REALM), "target_id": Pick(TOWN)})
CELL = ("spy_cell:add", {"network_id": Newest("spy_network"), "dead_drops": 2})
HUNT = ("mole_hunt:order", {"polity_id": Computed(spied_realm)})
DEFECT = ("defection:make", {"mortal_id": Pick(MORTAL, 2), "to_id": Pick(REALM), "protected": True})
KILLING = ("killing:add", {"victim_id": Pick(MORTAL, 2), "method": "poison", "recognised": True})
PLAY = ("market_play:set", {"holder_id": Newest(EntityType.FACTION), "settlement_id": Pick(TOWN), "commodity": "grain", "play": "corner"})
TRAIT = ("species_trait:set", {"species_id": Pick(EntityType.SPECIES), "region_id": Pick(EntityType.REGION), "trait": "speed", "mean": 60})
LINE = ("lineage:mark", {"species_id": Pick(EntityType.SPECIES), "package": "divine_blessing", "blessing": True})
SERVICE = ("ecosystem_service:set", {"region_id": Pick(EntityType.REGION), "role": "pollinator", "strength": 50})
HERD = ("herd:edit", {"community_id": Pick(TOWN), "species_id": Pick(EntityType.SPECIES), "values": {"head": 10}})
CARRIER = ("carrier:add", {"mortal_id": Pick(MORTAL), "disease_id": Newest(EntityType.DISEASE)})
RESPONSE = ("plague_response:set", {"community_id": Pick(TOWN), "disease_id": Newest(EntityType.DISEASE), "response": "prayer"})
HOSPITAL = ("structure:commission", {"site_id": Pick(TOWN), "kind": "hospital"})
RESEARCH = ("cure_research:start", {"institution_id": Newest(EntityType.STRUCTURE), "disease_id": Newest(EntityType.DISEASE)})
FINISHED = ("structure:finish", {"structure_id": Newest(EntityType.STRUCTURE)})
RITE = ("rite:devise", {"inventor_id": Pick(MORTAL)})
WAR = ("war:open", {"attacker_id": Pick(TOWN), "defender_id": Pick(TOWN, 1)})
DEAD = Where("entities", "id", {"status": EntityStatus.DEAD, "entity_type": EntityType.MORTAL})
THEORY = ("lore:create", {"entity_type": "theory", "name": "The Turning Sky", "world_id": Pick("world"), "values": {"domain": "cosmology"}})
VARIANT = ("variant:create", {"family": "skill", "base": "blade", "name": "Long Blade"})
CASE = ("case:open", {"settlement_id": Pick(TOWN), "crime": "theft", "accused_id": Pick(MORTAL)})
COMPANY = (
    ("faction:found", {"community_id": Pick(TOWN, 2), "kind": "merchant_guild"}),
    ("faction:edit", {"faction_id": Newest(EntityType.FACTION), "values": {"kind": "chartered_company"}}),
)
HOLY = (
    ("faction:found", {"community_id": Pick(TOWN, 2), "kind": "warrior_order"}),
    ("faction:edit", {"faction_id": Newest(EntityType.FACTION), "values": {"kind": "holy_order"}}),
)
WRITTEN = ("incident:create", {"text": "A god set down a happening in the town.", "participants": [{"node_id": Pick(MORTAL), "role": "actor"}]})
FACT_SET = ("incident_fact:create", {"incident_id": Newest("incident"), "key": "amount", "number": 12, "unit": "count"})
STEP_SET = ("incident_step:create", {"incident_id": Newest("incident"), "step_action": "strike", "actor_node_id": Pick(MORTAL)})
WITNESS_SET = ("incident_witness:create", {"incident_id": Newest("incident"), "node_id": Pick(MORTAL, 1)})
WHISPER = ("rumour:plant", {"community_id": Pick(TOWN), "subject_id": Pick(MORTAL), "text": "they say the council met at night", "fidelity": 70})
DISTORTED = ("rumour_distortion:create", {"rumour_id": Newest("rumour"), "distortion": "moment_changed", "told_year": 3})
CRIME_SET = ("settlement:edit", {"settlement_id": Pick(TOWN), "values": {"crime": 23}})
FEDERATION = ("federation", {"member_ids": [Pick(TOWN), Computed(far_town)], "name": "The Concord"})
ASSEMBLY = Where("entities", "id", {"engine_kind": EngineKind.INTERWORLD_FEDERATION})
PASSION = ("passion:set", {"holder_id": Pick(MORTAL), "kind": "love", "object_id": Pick(MORTAL, 1), "strength": 90})
GATE_LORE = ("research:level", {"holder_id": Pick(EntityType.PEOPLE), "branch": "gate_lore", "level": 2})
PROPHECY = (
    "lore:create",
    {"entity_type": "prophecy", "name": "The Second Dawn", "world_id": Pick("world"), "values": {"predicate": "dies", "subject_id": Pick(MORTAL)}},
)
MAIMED = ("body:maim", {"bearer_id": Pick(MORTAL), "part": "left_arm", "severity": 3, "lethal": False})


async def town_debt(session: AsyncSession) -> int | None:
    lender, borrower = await pick(session, TOWN, 0), await pick(session, TOWN, 1)
    statement = select(BondRow.id).where(
        BondRow.kind == BondKind.OWES, BondRow.state == BondState.ACTIVE, BondRow.source_node_id == borrower, BondRow.target_node_id == lender
    )
    return await session.scalar(statement.order_by(BondRow.id.desc()).limit(1))


async def held_danger(session: AsyncSession) -> int | None:
    region = await pick(session, EntityType.REGION, 0)
    statement = select(RegionDangerRow.id).where(RegionDangerRow.region_entity_id == region, RegionDangerRow.held.is_(True))
    return await session.scalar(statement.order_by(RegionDangerRow.id.desc()).limit(1))


async def unruled_community(session: AsyncSession) -> int | None:
    living_rulers = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)
    ruled = select(BondRow.target_node_id).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(living_rulers))
    statement = select(EntityRow.id).where(
        EntityRow.entity_type.in_((EntityType.PEOPLE, TOWN)), EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(ruled)
    )
    return await session.scalar(statement.order_by(EntityRow.id).limit(1))


async def mortal_without_apprentice(session: AsyncSession) -> int | None:
    taught = select(BondRow.target_node_id).where(BondRow.kind == BondKind.APPRENTICE_OF, BondRow.state == BondState.ACTIVE)
    statement = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(taught))
    return await session.scalar(statement.order_by(EntityRow.id).limit(1))


LOANED = ("civilization:loan", {"lender_id": Pick(TOWN), "borrower_id": Pick(TOWN, 1), "amount": 10})

GOAL = ("god_goal:set", {"god_id": Pick("son"), "kind": "be_worshipped", "amount": 3})
STANDING = ("divine_standing:set", {"community_id": Pick(TOWN), "god_id": Pick("son"), "values": {"love": 40}})
WOUND = ("divine_wound:inflict", {"god_id": Pick("son"), "kind": "stolen_name", "severity": 40})
AVATAR = ("avatar:manifest", {"god_id": Pick("son"), "place_id": Pick(TOWN)})
DECREE = ("ruling:decree", {"motion": "cosmic_truce"})
BREACH = ("breach:open", {"being_id": Computed(outer_being), "region_id": Pick(EntityType.REGION), "strength": 30})

LEVERS: dict[str, Lever] = {
    **{name: after("affliction:give") for name in ("affliction:cure", "affliction:delete", "affliction:edit", "affliction:hold")},
    "aspiration:dream_remove": after("aspiration:dream"),
    "aspiration:inspiration_edit": after("aspiration:inspire"),
    "aspiration:inspiration_remove": after("aspiration:inspire"),
    "aspiration:want_edit": after("aspiration:want"),
    "aspiration:want_remove": after("aspiration:want"),
    "aspiration:fear_remove": after("aspiration:fear"),
    "aspiration:perk_remove": after("aspiration:perk"),
    **{f"beast:{verb}": after(BEAST) for verb in ("edit", "rouse", "bind", "lair", "slay", "treasure")},
    "pet:set": after(BEAST),
    "domain_hook:set": given(world_id=Pick("world"), domain="sea", hook="naval_might", pct=150),
    "domain_hook:clear": after(
        ("domain_hook:set", {"world_id": Pick("world"), "domain": "sea", "hook": "naval_might", "pct": 150}),
        world_id=Pick("world"),
        domain="sea",
        hook="naval_might",
    ),
    "god_goal:set": given(god_id=Pick("son"), kind="be_worshipped", amount=3),
    **{name: after(GOAL, goal_id=Where("son_goals", "id")) for name in ("god_goal:edit", "god_goal:drop")},
    "divine_standing:set": given(community_id=Pick(TOWN), god_id=Pick("son")),
    "divine_standing:clear": after(STANDING, community_id=Pick(TOWN), god_id=Pick("son")),
    "divine_wound:inflict": given(god_id=Pick("son"), kind="stolen_name", severity=40),
    **{name: after(WOUND, wound_id=Where("divine_wounds", "id")) for name in ("divine_wound:edit", "divine_wound:remove")},
    "avatar:manifest": given(god_id=Pick("son"), place_id=Pick(TOWN)),
    **{name: after(AVATAR, avatar_id=Where("avatars", "avatar_entity_id")) for name in ("avatar:edit", "avatar:withdraw")},
    "taboo:set": given(act="torture", severity=60),
    "taboo:remove": after(("taboo:set", {"act": "torture", "severity": 60}), act="torture"),
    "attention:set": given(world_id=Pick("world")),
    "attention:clear": after(("attention:set", {"world_id": Pick("world"), "values": {"watched": True}}), world_id=Pick("world")),
    "divine_pact:seal": setup_then(foreign_god, son_id=Pick("son"), god_id=Pick("foreign_god")),
    "ruling:decree": given(motion="cosmic_truce"),
    "decree": given(entity_id=HOME_MORTAL, target_id=HOME_NEIGHBOUR),
    "opinion:delete": after(("opinion:set", {"approval": 10})),
    "standing:remove": after(("standing:set", {"prestige": 10})),
    "ruler:heir": given(ruler_id=Computed(ruling_mortal), heir_id=Computed(heir_beside)),
    **{name: after(DECREE, ruling_id=Where("council_rulings", "id")) for name in ("ruling:edit", "ruling:revoke")},
    "law_profile:edit": given(law_id=Computed(natural_law)),
    "outer_profile:edit": given(being_id=Computed(outer_being)),
    "breach:open": given(being_id=Computed(outer_being), region_id=Pick(EntityType.REGION), strength=30),
    **{name: after(BREACH, breach_id=Where("breach_points", "id")) for name in ("breach:edit", "breach:close")},
    "anatomy:edit": after(BEAST, node_id=Pick(EntityType.BEAST)),
    "anatomy:reroll": after(BEAST, node_id=Pick(EntityType.BEAST)),
    "crisis:open": given(target_id=Pick(REALM, 1), demand="pay"),
    **{f"crisis:{verb}": after(CRISIS) for verb in ("hold", "delete")},
    "crisis:edit": after(CRISIS, escalation=10),
    "crisis:resolve": after(CRISIS, state="backed_down"),
    "backer:set": after(CRISIS, backer_id=Pick(REALM, 2)),
    "backer:remove": after(CRISIS, ("backer:set", {"backer_id": Pick(REALM, 2)}), backer_id=Pick(REALM, 2)),
    "body:set": given(field="pain", value=10),
    "body:unlock": after(("body:set", {"field": "pain", "value": 10, "lock": True}), field="pain"),
    "body:customs": given(field="seer_eye", value=True),
    "body:customs_unlock": after(("body:customs", {"field": "seer_eye", "value": True, "lock": True}), field="seer_eye"),
    "body:digit": given(digit="left_hand.thumb", lost=True),
    "body:maim": given(part="left_arm", severity=3, lethal=False),
    "body:heal": after(MAIMED),
    "body:treat": after(MAIMED),
    "body:injury": after(MAIMED),
    "body:injury_hold": after(MAIMED),
    **{
        name: after(MAIMED, ("body:prosthesis", {"injury_id": Newest("injury"), "material": "wood", "quality": 40}))
        for name in ("body:prosthesis_edit", "body:prosthesis_remove")
    },
    "allele_pool:frequency": given(locus="height", allele="tall", frequency=40),
    "allele_pool:share": given(gifted_share=20),
    "alliance:betray": after(("alliance:marriage", {"first_id": Pick(TOWN), "second_id": Pick(TOWN, 1)}), traitor_id=Pick(TOWN), victim_id=Pick(TOWN, 1)),
    "archive:read": after("archive:raise"),
    "army:bless": given(morale=60),
    "art:commission": given(patron_id=Pick(MORTAL)),
    "bond:add": given(kind="ally", source_id=Pick(TOWN), target_id=Pick(TOWN, 1)),
    "bond:remove": after(("bond:add", {"kind": "ally", "source_id": Pick(TOWN), "target_id": Pick(TOWN, 1)}), bond_id=Newest("bond")),
    "canon:set": given(status="rejected"),
    "captive:take": given(captor_id=Pick(TOWN), mortal_id=Pick(MORTAL, 1)),
    **{
        name: after(("captive:take", {"captor_id": Pick(TOWN), "mortal_id": Pick(MORTAL, 1)}), captive_id=Pick(MORTAL, 1))
        for name in ("captive:free", "captive:ransom")
    },
    "case:open": given(settlement_id=Pick(TOWN), crime="theft", accused_id=Pick(MORTAL)),
    **{
        name: after(("case:open", {"settlement_id": Pick(TOWN), "crime": "theft", "accused_id": Pick(MORTAL)}), case_id=Newest("crime_case"))
        for name in ("case:hold", "case:try", "case:delete")
    },
    "case:edit": after(("case:open", {"settlement_id": Pick(TOWN), "crime": "theft", "accused_id": Pick(MORTAL)}), case_id=Newest("crime_case"), evidence=50),
    "chronicle:edit": given(text="The plain account was written again."),
    **{
        name: after(("cipher:set", {"owner_id": Pick(TOWN), "strength": 40}), owner_id=Pick(TOWN), breaker_id=Pick(MORTAL))
        for name in ("cipher:break", "cipher:mend", "cipher:delete")
    },
    "cipher:set": given(owner_id=Pick(TOWN), strength=40),
    **{
        name: after(("circle:found", {"place_id": Pick(TOWN), "kind": "study_circle"}), circle_id=Newest(EntityType.FACTION))
        for name in ("circle:edit", "circle:member", "circle:disband")
    },
    "civilization:tier": given(entity_id=Pick(TOWN), tier=2),
    **{name: after(LOANED, bond_id=Computed(town_debt)) for name in ("civilization:forgive_debt", "civilization:enforce_debt")},
    **{
        name: after(("claim:grant", {"mortal_id": Pick(MORTAL), "polity_id": Pick(REALM)}), claim_id=Newest("claim")) for name in ("claim:edit", "claim:revoke")
    },
    "community:contact": given(source_id=Pick(TOWN), target_id=Pick(TOWN, 1)),
    "community:exodus": given(origin_id=Pick(TOWN), share_pct=10),
    "community:mint": given(entity_id=Pick(TOWN)),
    "contest:hold": given(challenger_id=Pick(MORTAL), defender_id=Pick(MORTAL, 1), kind="riddle_game"),
    "council:task": given(diligence=60),
    "court:edit": given(grandeur=60),
    "creator:edit": given(title="the Maker"),
    "creator:passions": given(passions=["order"]),
    "creator:reputation": given(love=10),
    "credit:set": given(subject_id=Pick(TOWN), rating=60),
    "credit:remove": after(("credit:set", {"subject_id": Pick(TOWN), "rating": 60}), subject_id=Pick(TOWN)),
    **{name: after(IDEOLOGY, ideology_id=Newest(EntityType.IDEOLOGY)) for name in ("creed:adherent", "creed:custom_tenet", "creed:suppress", "creed:tenet")},
    "crop:set": after(PLANT, plant_id=Newest(EntityType.SPECIES)),
    "crop:drop": after(PLANT, ("crop:set", {"plant_id": Newest(EntityType.SPECIES)}), plant_id=Newest(EntityType.SPECIES)),
    "crop_pest:set": after(PLANT, plant_id=Newest(EntityType.SPECIES), pest_id=Pick(EntityType.SPECIES)),
    "plant:edit": after(PLANT, species_id=Newest(EntityType.SPECIES)),
    "cult:heresy": given(heresy_id=Pick(EntityType.CULT), parent_id=Pick(EntityType.CULT, 1)),
    **{name: after(HERESY, heresy_id=Pick(EntityType.CULT)) for name in ("cult:edit_heresy", "cult:judge_heresy", "cult:undeclare_heresy")},
    "cult:merge": given(source_id=Pick(EntityType.CULT), into_id=Pick(EntityType.CULT, 1)),
    "cult:tenet": given(tenet="holy_war"),
    "currency:create": given(issuer_id=Pick(TOWN)),
    **{
        name: after(("currency:create", {"issuer_id": Pick(TOWN), "name": "Crown"}), currency_id=Newest("currency"))
        for name in ("currency:debase", "currency:delete", "currency:edit", "currency:release", "currency:use")
    },
    "deed_claim:set": after(DEED, deed_id=Newest("deed"), claimant_id=Pick(MORTAL, 1)),
    "deed:edit": after(DEED, deed_id=Newest("deed"), magnitude=30, note="told again"),
    "deed:remove": after(DEED, deed_id=Newest("deed")),
    "item:deed_remove": after(ITEM_DEED, deed_id=Newest("item_history")),
    "art:canonise": after(ARTWORK, artwork_id=Newest(EntityType.ARTWORK)),
    "discovery:ban": after(ARTWORK, polity_id=Pick(REALM), work_id=Newest(EntityType.ARTWORK)),
    "renown:remove": after(REPUTATION, reputation_id=Newest("reputation")),
    "contest:edit": after(CONTEST, contest_id=Newest("contest"), famous=True),
    "contest:remove": after(CONTEST, contest_id=Newest("contest")),
    **{
        name: after(DEED, ("deed_claim:set", {"deed_id": Newest("deed"), "claimant_id": Pick(MORTAL, 1), "kind": "false"}), claim_id=Newest("deed_claim"))
        for name in ("deed_claim:expose", "deed_claim:remove")
    },
    "demand:remove": after(("demand:set", {"mortal_id": Pick(MORTAL)}), mortal_id=Pick(MORTAL)),
    "diplomacy:edit": given(capacity=60),
    "discovery:incident": given(holder_id=Pick(TOWN)),
    "disease:create": given(region_id=Pick(EntityType.REGION)),
    "disease:loose": after(DISEASE, target_id=Pick(EntityType.REGION), disease_id=Newest(EntityType.DISEASE)),
    **{
        name: after(DISEASE, disease_id=Newest(EntityType.DISEASE), region_id=Pick(EntityType.REGION))
        for name in ("disease:cure", "disease:edit", "disease:immunity", "endemic:set", "endemic:remove", "disease:quarantine")
    },
    "dispatch:send": given(sender_id=Pick(TOWN), recipient_id=Pick(TOWN, 1)),
    **{
        name: after(("dispatch:send", {"sender_id": Pick(TOWN), "recipient_id": Pick(TOWN, 1)}), message_id=Newest("message"))
        for name in ("dispatch:delete", "dispatch:hold")
    },
    "dispatch:edit": after(("dispatch:send", {"sender_id": Pick(TOWN), "recipient_id": Pick(TOWN, 1)}), message_id=Newest("message"), forged=True),
    "district:build": given(settlement_id=Pick(TOWN), kind="market"),
    "district:design": given(base_kind="market"),
    **{
        name: after(("district:design", {"base_kind": "market", "name": "Lantern Row"}), design_id=Newest("district_design"))
        for name in ("district:design_edit", "district:design_delete")
    },
    **{
        name: after(("drift:impose", {"community_id": Pick(TOWN), "amount": 10}), imposition_id=Newest("drift_imposition"))
        for name in ("drift:cancel", "drift:edit")
    },
    "election:delete": after(("election:call", {"polity_id": Pick(REALM)}), election_id=Newest("election")),
    "engine:run_phase": given(phase="flora_cycles"),
    "entity:move": given(entity_id=Pick(MORTAL), location_id=Pick(TOWN)),
    "entity:stat": given(stat="strength", value=60.0),
    "entity:tags": given(add_flags=["oathbreaker"]),
    "environment:mineral": given(material="iron", richness=40),
    "environment:set": given(region_id=Pick(EntityType.REGION), field="moisture", value=50),
    "environment:unlock": after(
        ("environment:set", {"region_id": Pick(EntityType.REGION), "field": "moisture", "value": 50, "lock": True}),
        region_id=Pick(EntityType.REGION),
        field="moisture",
    ),
    "environment:place": given(place_id=Pick(EntityType.PLACE), field="height_advantage", value=30),
    "epoch:edit": Lever(values={"epoch": 1, "name": "The First Age"}, setup=first_epoch),
    **{name: after(("estate:found", {"realm_id": Pick(REALM)}), estate_id=Newest(EntityType.FACTION)) for name in ("estate:privilege", "estate:remove")},
    "estate:edit": after(("estate:found", {"realm_id": Pick(REALM)}), estate_id=Newest(EntityType.FACTION), loyalty=60),
    "ethics:honour": given(holder_id=Pick(EntityType.PEOPLE)),
    "ethics:set": given(holder_id=Pick(EntityType.PEOPLE)),
    "fact:add": given(object_text="the old river"),
    "fact:remove": after(("fact:add", {"subject_id": Pick(MORTAL), "relation": "remembers", "object_text": "the old river"}), fact_id=Newest("canon_facts")),
    "faction:spy": given(spymaster_id=Pick(REALM), target_id=Pick(TOWN)),
    "feud:end": after(("feud:start", {"first_id": Pick(TOWN), "second_id": Pick(TOWN, 1)})),
    **{name: setup_then(foreign_god, god_id=Pick("foreign_god")) for name in ("foreign_god:raise_land", "kill:foreign_god", "drain:foreign_god")},
    "foreign_god:edit": setup_then(foreign_god, god_id=Pick("foreign_god"), stance=10),
    "foreign_god:strike": setup_then(foreign_god, god_id=Pick("foreign_god"), entity_id=HOME_MORTAL),
    "foreign_god:raid_temple": setup_then(foreign_god, TEMPLE, FINISHED, god_id=Pick("foreign_god"), temple_id=Newest(EntityType.STRUCTURE)),
    "genome:edit": given(beauty=60),
    "genome:gene": given(locus="height", first="tall", second="short"),
    "harvest": given(entity_id=Pick(TOWN)),
    "herd:drop": after(
        ("herd:edit", {"community_id": Pick(TOWN), "species_id": Pick(EntityType.SPECIES), "values": {"head": 10}}),
        community_id=Pick(TOWN),
        species_id=Pick(EntityType.SPECIES),
    ),
    "horror:cult": given(entity_id=Pick(TOWN)),
    "household:edit": given(wealth=60),
    "household:debt": after(
        ("household:found", {"head_id": Pick(MORTAL, 2)}),
        ("household:found", {"head_id": Pick(MORTAL, 3)}),
        household_id=Newest("household"),
        lender_household_id=Pick("household"),
        amount=5,
    ),
    **{
        name: after(("favour:owe", {"owed_by_id": Pick(MORTAL), "owed_to_id": Pick(MORTAL, 1), "magnitude": 20, "origin": "gift"}), favour_id=Newest("favour"))
        for name in ("favour:call", "favour:edit", "favour:delete")
    },
    "household:hold": given(fields=["wealth"]),
    "household_aggregate:edit": given(community_id=Pick(TOWN), wealth=60),
    **{
        name: after(("identity:assume", {"mortal_id": Pick(MORTAL), "false_name": "Wren"}), mortal_id=Pick(MORTAL))
        for name in ("identity:delete", "identity:edit", "identity:unmask")
    },
    "indicator:edit": given(output=60),
    "industry:set": given(community_id=Pick(TOWN), muscle=40),
    "intervene": given(miracle="healing"),
    "kin:betroth": given(first_id=Pick(MORTAL), second_id=Pick(MORTAL, 1)),
    "kin:marry": given(first_id=Pick(MORTAL), second_id=Pick(MORTAL, 1)),
    "kind:create": given(catalog="technique", base="phalanx_drill"),
    **{name: after(CUSTOM_KIND, kind_id=Newest("custom_kind")) for name in ("kind:delete", "kind:edit")},
    "knowledge:set": given(entity_id=Computed(knower), knowledge_id=Computed(known_lore), known=False),
    "body:condition_end": given(condition_id=Where("conditions", "id", {"ended_epoch": None})),
    "land:shape": given(region_id=Pick(EntityType.REGION), desertification=20),
    "land:release": after(
        ("land:shape", {"region_id": Pick(EntityType.REGION), "desertification": 20, "hold": True}), region_id=Pick(EntityType.REGION), field="desertification"
    ),
    "language:edit": given(alphabet="abcdefghik"),
    "language:intelligibility": given(first_id=Pick(EntityType.LANGUAGE), second_id=Pick(EntityType.LANGUAGE, 1), value=40),
    "language:release_understanding": after(
        ("language:intelligibility", {"first_id": Pick(EntityType.LANGUAGE), "second_id": Pick(EntityType.LANGUAGE, 1), "value": 40}),
        first_id=Pick(EntityType.LANGUAGE),
        second_id=Pick(EntityType.LANGUAGE, 1),
    ),
    "language:register": given(holder_id=Pick(EntityType.PEOPLE)),
    "language:release_speakers": after(SPEAKERS, community_id=Pick(TOWN), language_id=Pick(EntityType.LANGUAGE, 2), kind="second"),
    "language:words": given(words=[{"word": "velo", "meaning": "river"}]),
    "law:enact": given(holder_id=Pick(REALM)),
    "lever:set": given(key="strength", value=60),
    "lever:pin": given(key="strength"),
    "lever:unpin": after(("lever:pin", {"node_id": Pick(MORTAL), "key": "strength"}), key="strength"),
    "lever:suppress": given(mechanic="pets", epochs=2),
    "lever:unsuppress": after(("lever:suppress", {"node_id": Pick(MORTAL), "mechanic": "pets", "epochs": 2}), mechanic="pets"),
    "lever:run": given(mechanic="pets"),
    "ley:forge": given(first_region_id=Pick(EntityType.REGION), second_region_id=Pick(EntityType.REGION, 1)),
    **{
        name: after(("ley:forge", {"first_region_id": Pick(EntityType.REGION), "second_region_id": Pick(EntityType.REGION, 1)}), line_id=Newest("ley_line"))
        for name in ("ley:dissolve", "ley:restore", "ley:sever", "ley:strength", "ley:unforge")
    },
    "loan:grant": given(lender_id=Pick(TOWN), borrower_id=Pick(TOWN, 1), principal=10),
    **{
        name: after(("loan:grant", {"lender_id": Pick(TOWN), "borrower_id": Pick(TOWN, 1), "principal": 10}), loan_id=Newest("loan"))
        for name in ("loan:delete", "loan:edit", "loan:forgive", "loan:release")
    },
    "lore:create": given(entity_type="legend", world_id=Pick("world"), values={"archetype": "hero_quest"}),
    "lore:edit": given(entity_id=Pick(EntityType.LEGEND)),
    "lore_trade:make": given(seller_id=Pick(MORTAL), buyer_id=Pick(MORTAL, 1), kind="technique", key="phalanx_drill"),
    "lore_trade:remove": after(
        ("lore_trade:make", {"seller_id": Pick(MORTAL), "buyer_id": Pick(MORTAL, 1), "kind": "technique", "key": "phalanx_drill"}),
        trade_id=Newest("lore_trade"),
    ),
    "loyalty:edit": given(polity_id=Where("polity_members", "polity_entity_id"), member_id=Where("polity_members", "member_entity_id"), values={"loyalty": 60}),
    "mandate:edit": after(("mandate:issue", {"polity_id": Pick(REALM)}), mandate_id=Newest("mandate"), amount=5),
    "map_note:remove": after(("map_note:add", {"world_id": Pick("world"), "x": 0.5, "y": 0.5, "text": "here"}), note_id=Newest("map_note")),
    "market:disband": after(("faction:found", {"community_id": Pick(TOWN, 2), "kind": "wandering_market"}), faction_id=Newest(EntityType.FACTION)),
    **{name: given(material="iron") for name in ("material:hold", "material:release")},
    "material:delete": after(("material:edit", {"world_id": Pick("world"), "material": "iron", "values": {"hardness": 60}}), material="iron"),
    "material:edit": given(material="iron", values={"hardness": 60}),
    "memorial:order": given(target_id=Where("entities", "id", {"status": EntityStatus.DEAD, "entity_type": EntityType.MORTAL})),
    "military:create": given(kind="unit_design", values={"name": "Spearwall", "base_kind": "line_infantry", "owner_entity_id": Pick(TOWN)}),
    **{
        name: after(
            ("military:create", {"kind": "unit_design", "values": {"name": "Spearwall", "base_kind": "line_infantry", "owner_entity_id": Pick(TOWN)}}),
            kind="unit_design",
            record_id=Newest("unit_design"),
        )
        for name in ("military:delete", "military:edit", "military:release")
    },
    "mind:lock": given(field="traits"),
    "mind:unlock": after(("mind:lock", {"node_id": Pick(MORTAL), "field": "traits"}), field="traits"),
    "mind:pressure": given(node_id=Pick(TOWN)),
    "mind:skill_remove": after(("mind:skill", {"node_id": Pick(MORTAL), "skill": "blade", "level": 30})),
    "mind:trait": given(node_id=Computed(unbrave_mortal), trait="brave"),
    "mind:trait_remove": after(("mind:trait", {"node_id": Computed(unbrave_mortal), "trait": "brave"})),
    "modifier:add": given(key="strength", magnitude=5.0),
    "modifier:create": given(key="strength", magnitude=5.0),
    "modifier:release": after(("modifier:hold", {"modifier_id": Pick("modifier")})),
    "mortal:child": given(first_id=Pick(MORTAL), second_id=Pick(MORTAL, 1)),
    "mortal:equip_release": after(("mortal:equip", {"mortal_id": Pick(MORTAL), "slot": "wielded_main", "hold": True})),
    "mortal:pardon": after(("mortal:sentence", {"mortal_id": Pick(MORTAL), "crime": "theft", "punishment": "exile"})),
    "mortal:set": given(field="wealth", value=40),
    "mortal:release": after(("mortal:set", {"mortal_id": Pick(MORTAL), "field": "wealth", "value": 40, "hold": True}), field="wealth"),
    "node_material:set": given(node_id=Pick(EntityType.ITEM), material="iron"),
    "node_material:clear": given(node_id=Pick(EntityType.ITEM)),
    "node_material:release": after(("node_material:set", {"node_id": Pick(EntityType.ITEM), "material": "iron", "hold": True}), node_id=Pick(EntityType.ITEM)),
    "office:create": given(kind="chancellor"),
    "office:abolish": after(("office:create", {"polity_id": Pick(REALM), "kind": "chancellor"}), office_id=Newest("office")),
    "polity:appoint": given(office="chancellor"),
    **{
        name: after(
            DISEASE, ("disease:loose", {"target_id": Pick(EntityType.REGION), "disease_id": Newest(EntityType.DISEASE)}), outbreak_id=Newest("outbreak")
        )
        for name in ("outbreak:edit", "outbreak:end")
    },
    "pardon": after(("entity:tags", {"entity_id": Pick(MORTAL), "add_flags": ["oathbreaker"]})),
    "passion:set": given(object_id=Pick(MORTAL, 1), strength=60),
    "passion:invoke": after(
        ("passion:set", {"holder_id": Pick(MORTAL), "kind": "love", "object_id": Pick(MORTAL, 1), "strength": 90}), passion_id=Newest("passion")
    ),
    "people:found": given(population=1000),
    "people:unite": given(source_id=Pick(EntityType.PEOPLE), into_id=Pick(EntityType.PEOPLE, 1)),
    "persuasion:attempt": given(target_id=Pick(MORTAL, 1), appeal="authority", axis="tradition"),
    "persuasion:remove": after(
        ("persuasion:attempt", {"speaker_id": Pick(MORTAL), "target_id": Pick(MORTAL, 1), "appeal": "authority", "axis": "tradition"}),
        persuasion_id=Newest("persuasion"),
    ),
    "pilgrimage:declare": given(entity_id=Pick(EntityType.PLACE)),
    "pilgrimage:clear": after(("pilgrimage:declare", {"entity_id": Pick(EntityType.PLACE)}), entity_id=Pick(EntityType.PLACE)),
    "place:edit": given(sacredness=40),
    "place:release": after(("place:edit", {"place_id": Pick(EntityType.PLACE), "sacredness": 40, "hold": True}), field="sacredness"),
    **{
        name: after(("place:secret", {"place_id": Pick(EntityType.PLACE)}), secret_id=Newest("place_secret"))
        for name in ("place:reveal", "place:secret_delete")
    },
    "place:secret_edit": after(("place:secret", {"place_id": Pick(EntityType.PLACE)}), secret_id=Newest("place_secret"), strength=40),
    "polity:member": given(polity_id=Where("polity_members", "polity_entity_id"), member_id=Where("polity_members", "member_entity_id"), autonomy=20),
    "polity:merge": given(polity_id=Pick(REALM), into_id=Pick(REALM, 1)),
    "pollution:set": given(region_id=Pick(EntityType.REGION), air=10),
    "position:remove": after(("position:set", {"polity_id": Pick(REALM), "position": "steward", "holder_id": Pick(MORTAL)}), position="steward"),
    "preference:set": given(target="iron", strength=40),
    "profile:set": given(table="mortal_profiles", column="wealth", value=40),
    "profile:release": after(
        ("profile:set", {"node_id": Pick(MORTAL), "table": "mortal_profiles", "column": "wealth", "value": 40, "hold": True}),
        table="mortal_profiles",
        column="wealth",
    ),
    **{
        name: after(("proposal:create", {"polity_id": Pick(REALM), "kind": "succession_rule"}), proposal_id=Newest("law_proposal"), support=40)
        for name in ("proposal:edit",)
    },
    "rank:remove": after(
        ("rank:set", {"group_id": Pick(TOWN), "member_id": Pick(MORTAL), "group_kind": "court", "rank": 1}), group_id=Pick(TOWN), member_id=Pick(MORTAL)
    ),
    "record:edit": given(title="the Elder"),
    "record:end": given(entity_id=Pick(EntityType.LAW), end="repeal"),
    "record:merge": given(entity_id=Pick(MORTAL), other_id=Pick(MORTAL, 1), confirm="MERGE"),
    "regard:set": given(holder_id=Pick(REALM), subject_id=Pick(REALM, 1), trust=40),
    "regard:remove": after(
        ("regard:set", {"holder_id": Pick(REALM), "subject_id": Pick(REALM, 1), "trust": 40}), holder_id=Pick(REALM), subject_id=Pick(REALM, 1)
    ),
    "region:danger_release": after(
        ("region:danger_create", {"region_id": Pick(EntityType.REGION), "strength": 30, "hold": True}), danger_id=Computed(held_danger)
    ),
    "region:knowledge_release": after(
        ("region:knowledge_set", {"polity_id": Pick(REALM), "region_id": Pick(EntityType.REGION), "level": 50, "hold": True}),
        polity_id=Pick(REALM),
        region_id=Pick(EntityType.REGION),
    ),
    **{
        name: after(
            (
                "cult:canonise",
                {
                    "cult_id": Pick(EntityType.CULT),
                    "saint_id": Where("entities", "id", {"status": EntityStatus.DEAD, "entity_type": EntityType.MORTAL}),
                    "item_id": Pick(EntityType.ITEM),
                },
            ),
            item_id=Pick(EntityType.ITEM),
        )
        for name in ("relic:edit", "relic:remove")
    },
    **{f"research:{verb}": given(holder_id=Pick(TOWN)) for verb in ("boost", "focus", "holder", "level", "technique")},
    "research:custom_technique": after(CUSTOM_KIND, holder_id=Pick(TOWN), kind_id=Newest("custom_kind")),
    "resemblance:set": given(locus="height", allele="tall"),
    "resemblance:remove": after(
        ("resemblance:set", {"house_id": Pick(EntityType.HOUSE), "locus": "height", "allele": "tall"}), house_id=Pick(EntityType.HOUSE)
    ),
    "resource:mechanic": after(
        ("entity:tags", {"entity_id": Pick(EntityType.RESOURCE), "add_mechanics": ["decaying"]}), resource_id=Pick(EntityType.RESOURCE), mechanic="decaying"
    ),
    "resource:pact": given(owner_id=Pick(TOWN)),
    **{
        name: after(("resource:pact", {"resource_id": Pick(EntityType.RESOURCE), "owner_id": Pick(TOWN)}), treaty_id=Newest(EntityType.TREATY))
        for name in ("resource:pact_terms", "resource:pact_end")
    },
    "resurrect:mortal": given(entity_id=Where("entities", "id", {"status": EntityStatus.DEAD, "entity_type": EntityType.MORTAL})),
    **{f"rite:{verb}": after(RITE, rite_id=Newest(EntityType.RITE)) for verb in ("effect", "requirements", "teach")},
    "rite:dispel": after(
        RITE,
        ("profile:set", {"node_id": Newest(EntityType.RITE), "table": "rite_profiles", "column": "backlash_chance", "value": 0}),
        ("rite:cast", {"rite_id": Newest(EntityType.RITE), "caster_id": Pick(MORTAL)}),
        rite_id=Newest(EntityType.RITE),
    ),
    "rite:cast": after(RITE, rite_id=Newest(EntityType.RITE), caster_id=Pick(MORTAL)),
    "rite:forbid": after(RITE, rite_id=Newest(EntityType.RITE), authority_id=Pick(REALM)),
    "rumour:plant": given(subject_id=Pick(MORTAL), text="they say the well runs dry"),
    "scheme:begin": given(target_id=Pick(MORTAL, 1)),
    **{
        name: after(("scheme:begin", {"owner_id": Pick(MORTAL), "kind": "murder", "target_id": Pick(MORTAL, 1)}), scheme_id=Newest("scheme"))
        for name in ("scheme:delete", "scheme:hold")
    },
    "scheme:edit": after(("scheme:begin", {"owner_id": Pick(MORTAL), "kind": "murder", "target_id": Pick(MORTAL, 1)}), scheme_id=Newest("scheme"), progress=20),
    "seasons:moons": given(moon_count=1),
    "seasons:reorder": given(order=All("world_seasons", "position", {"world_id": Pick("world")})),
    "seasons:calendar_release": after(("seasons:calendar", {"world_id": Pick("world"), "axial_tilt": 20}), fields=["axial_tilt"]),
    "seat:remove": after(("seat:set", {"polity_id": Pick(REALM), "holder_id": Pick(MORTAL), "seats": 2}), holder_id=Pick(MORTAL)),
    **{
        name: after(("secret:keep", {"holder_id": Pick(MORTAL), "about_id": Pick(MORTAL, 1)}), secret_id=Newest("secret"))
        for name in ("secret:delete", "secret:expose", "secret:hold")
    },
    "secret:edit": after(("secret:keep", {"holder_id": Pick(MORTAL), "about_id": Pick(MORTAL, 1)}), secret_id=Newest("secret"), severity=30),
    "war:open": given(attacker_id=Pick(TOWN), defender_id=Pick(TOWN, 1)),
    "siege:start": after(
        WAR,
        ("army:raise", {"community_id": Pick(TOWN), "size": 200, "war_id": Newest("war")}),
        war_id=Newest("war"),
        army_id=Newest(EntityType.ARMY),
        settlement_id=Pick(TOWN, 1),
    ),
    "siege:edit": after(
        WAR,
        ("army:raise", {"community_id": Pick(TOWN), "size": 200, "war_id": Newest("war")}),
        ("siege:start", {"war_id": Newest("war"), "army_id": Newest(EntityType.ARMY), "settlement_id": Pick(TOWN, 1)}),
        siege_id=Newest("siege"),
    ),
    "signal:build": given(owner_id=Pick(REALM), from_region_id=Pick(EntityType.REGION), to_region_id=Pick(EntityType.REGION, 1)),
    **{
        name: after(
            ("signal:build", {"owner_id": Pick(REALM), "from_region_id": Pick(EntityType.REGION), "to_region_id": Pick(EntityType.REGION, 1)}),
            link_id=Newest("signal_link"),
        )
        for name in ("signal:delete",)
    },
    "signal:edit": after(
        ("signal:build", {"owner_id": Pick(REALM), "from_region_id": Pick(EntityType.REGION), "to_region_id": Pick(EntityType.REGION, 1)}),
        link_id=Newest("signal_link"),
        owner_id=Pick(REALM),
    ),
    "site_profit:edit": given(revenue=10),
    **{name: given(entity_id=Pick(TOWN)) for name in ("society:famine", "society:plenty", "society:uprising")},
    "society:forge": Lever(values={"entity_id": Pick(TOWN)}, setup=armoury),
    "society:satisfaction": given(entity_id=Pick(TOWN), values={"farmer": 50}),
    "society:shares": given(entity_id=Pick(TOWN), shares={"farmer": 100}),
    "society:stores": given(entity_id=Pick(TOWN), stocks={"food": 10}),
    "son:edit": given(title="of the Long Road"),
    "son:duel": given(challenger_id=Pick("son"), defender_id=Pick("son", 1)),
    "son:relation": given(first_id=Pick("son"), second_id=Pick("son", 1), value=10),
    "son:god_war": setup_then(foreign_god, god_id=Pick("foreign_god")),
    "soul:raise": given(mortal_id=DEAD),
    **{name: after(("soul:raise", {"mortal_id": DEAD}), spirit_id=Newest(EntityType.SPIRIT)) for name in ("soul:reread_deeds",)},
    "soul:reincarnate": after(("soul:raise", {"mortal_id": DEAD}), spirit_id=Newest(EntityType.SPIRIT), community_id=Pick(TOWN)),
    "soul:possess": given(host_id=Pick(MORTAL)),
    "soul:possession": after(("soul:possess", {"spirit_id": Pick(EntityType.SPIRIT), "host_id": Pick(MORTAL)}), host_id=Pick(MORTAL)),
    "soul:exorcise": after(("soul:possess", {"spirit_id": Pick(EntityType.SPIRIT), "host_id": Pick(MORTAL)}), host_id=Pick(MORTAL)),
    "species:merge": given(first_id=Pick(EntityType.SPECIES), second_id=Pick(EntityType.SPECIES, 1)),
    "species:custom_use": after(("use_kind:create", {"name": "Lantern Bearer", "base_use": "meat"}), kind_id=Newest("species_use_kind")),
    "species:host": after(DISEASE, disease_id=Newest(EntityType.DISEASE)),
    "species:drop_range": after(
        ("species:range", {"species_id": Pick(EntityType.SPECIES), "region_id": Pick(EntityType.REGION)}), region_id=Pick(EntityType.REGION)
    ),
    "species:move_range": after(
        ("species:range", {"species_id": Pick(EntityType.SPECIES), "region_id": Pick(EntityType.REGION)}),
        source_id=Pick(EntityType.REGION),
        target_id=Pick(EntityType.REGION, 1),
    ),
    "sphere:remove": after(
        ("sphere:set", {"power_id": Pick(REALM), "client_id": Pick(REALM, 1), "strength": 20}), power_id=Pick(REALM), client_id=Pick(REALM, 1)
    ),
    "spy:edit_network": after(("faction:spy", {"spymaster_id": Pick(REALM), "target_id": Pick(TOWN)}), network_id=Newest("spy_network")),
    "star:depth": given(history="It burned before the first world."),
    "scale:depth": given(node_id=Pick("galaxy"), history="It turned before the first star."),
    "son:outer_bargain": after(("horror:outer_being", {"world_id": Pick("world")}), outer_id=Newest(EntityType.OUTER_BEING), request="a clear sky"),
    "star:edit": given(brightness=60, patron_son_id=Pick("son")),
    "strip_power": after(("son:power", {"son_id": Pick("son"), "slot": 1, "name": "Long Stride", "effect": "tireless"}), slot=1),
    "structure:commission": given(site_id=Pick(TOWN), kind="temple"),
    "structure:fund": after(TEMPLE, structure_id=Newest(EntityType.STRUCTURE), amount=50),
    "structure:abandon": after(TEMPLE, structure_id=Newest(EntityType.STRUCTURE)),
    "structure:finish": after(TEMPLE, structure_id=Newest(EntityType.STRUCTURE)),
    "proposal:pass": after(("proposal:create", {"polity_id": Pick(REALM), "kind": "succession_rule"}), proposal_id=Newest("law_proposal")),
    **{
        name: after(
            ("research:boost", {"holder_id": Pick(TOWN), "technique": "railways", "trigger": "survived_siege", "progress": 10}),
            boost_id=Newest("research_boost"),
        )
        for name in ("research:boost_edit", "research:boost_remove")
    },
    "structure:undedicate": after(
        ("structure:dedicate", {"structure_id": Pick(EntityType.STRUCTURE), "son_id": Pick("son")}), structure_id=Pick(EntityType.STRUCTURE)
    ),
    "structure_design:create": given(world_id=Pick("world"), values={"name": "Long Hall", "base_kind": "temple"}),
    **{
        name: after(
            ("structure_design:create", {"world_id": Pick("world"), "values": {"name": "Long Hall", "base_kind": "temple"}}),
            design_id=Newest("structure_design"),
        )
        for name in ("structure_design:edit", "structure_design:retire")
    },
    "tax:set": given(rate=10),
    **{
        name: after(THEORY, theory_id=Newest(EntityType.THEORY), holder_id=Pick(MORTAL), community_id=Pick(TOWN))
        for name in ("theory:adherent", "theory:anomaly", "theory:reveal")
    },
    "title:edit": given(emblem="a white tower"),
    "trade_policy:remove": after(("trade_policy:set", {"issuer_id": Pick(REALM), "rate_pct": 10}), policy_id=Newest("trade_policy")),
    "trade_route:found": after(("trade_route:delete", {"route_id": Pick(EntityType.TRADE_ROUTE)}), first_id=Pick(TOWN), second_id=Pick(TOWN, 1)),
    "trade_route:open": after(("trade_route:close", {"route_id": Pick(EntityType.TRADE_ROUTE)}), route_id=Pick(EntityType.TRADE_ROUTE)),
    **{name: given(route_id=Pick(EntityType.TRADE_ROUTE)) for name in ("trade_route:close", "trade_route:delete", "trade_route:edit")},
    "trade_route:toll_stop": given(route_id=Pick(EntityType.TRADE_ROUTE), region_id=Computed(route_region), controller_id=Pick(TOWN), rate=5),
    "trade_route:toll_remove": after(
        ("trade_route:toll_stop", {"route_id": Pick(EntityType.TRADE_ROUTE), "region_id": Computed(route_region), "controller_id": Pick(TOWN), "rate": 5}),
        route_id=Pick(EntityType.TRADE_ROUTE),
        region_id=Computed(route_region),
    ),
    "treaty:sign": given(kind="alliance_defensive", parties=[{"party_id": Pick(TOWN)}, {"party_id": Pick(TOWN, 1)}]),
    "treaty:party_remove": after(("treaty:party_add", {"treaty_id": Pick(EntityType.TREATY), "party_id": Pick(TOWN, 2)}), party_id=Pick(TOWN, 2)),
    "tribute:impose": given(payer_id=Pick(TOWN), receiver_id=Pick(TOWN, 1)),
    "tribute:forgive": after(
        ("tribute:impose", {"payer_id": Pick(TOWN), "receiver_id": Pick(TOWN, 1)}),
        bond_id=Where("bonds", "id", {"kind": BondKind.PAYS_TRIBUTE, "state": BondState.ACTIVE}),
    ),
    "true_name:set": given(name="Aeloth"),
    **{
        name: after(("true_name:set", {"bearer_id": Pick(MORTAL), "name": "Aeloth"}), learner_id=Pick(MORTAL, 1))
        for name in ("true_name:delete", "true_name:teach")
    },
    **{
        name: after(("use_kind:create", {"name": "Lantern Bearer", "base_use": "meat"}), kind_id=Newest("species_use_kind"))
        for name in ("use_kind:drop", "use_kind:edit")
    },
    "variant:create": given(family="trait", base="brave"),
    **{name: after(VARIANT, variant_id=Newest("kind_variant")) for name in ("variant:delete", "variant:edit")},
    "variant:release": after(
        VARIANT,
        ("variant:edit", {"variant_id": Newest("kind_variant"), "strength_pct": 120, "hold": True}),
        variant_id=Newest("kind_variant"),
        field="strength_pct",
    ),
    "variant:assign": after(
        VARIANT,
        ("mind:skill", {"node_id": Pick(MORTAL), "skill": "blade", "level": 30}),
        family="skill",
        row_id=Newest("skill"),
        variant_id=Newest("kind_variant"),
    ),
    "vassal:edit": after(("vassal:create", {"vassal_id": Pick(REALM, 1), "overlord_id": Pick(REALM)}), vassal_id=Pick(REALM, 1)),
    **{
        name: after(("vessel:create", {"owner_id": Pick(TOWN), "name": "Gull"}), vessel_id=Newest(EntityType.VESSEL))
        for name in ("vessel:refit", "vessel:repair")
    },
    **{
        name: after(WAR, war_id=Newest("war"), side_id=Pick(TOWN), community_id=Pick(TOWN), victor_id=Pick(TOWN))
        for name in (
            "war:aim",
            "war:army",
            "war:battle",
            "war:battle_at",
            "war:call_allies",
            "war:edit_side",
            "war:end",
            "war:impose_peace",
            "war:peace",
            "war:separate_peace",
            "war:victory",
            "war:weariness",
        )
    },
    "war:duel": given(first_id=Pick(MORTAL), second_id=Pick(MORTAL, 1)),
    **{
        name: after(("weather:force", {"region_id": Pick(EntityType.REGION)}), forced_id=Newest("forced_weather"))
        for name in ("weather:edit", "weather:release")
    },
    "witness:set": after(CASE, case_id=Newest("crime_case"), witness_id=Pick(MORTAL, 1)),
    "witness:remove": after(
        CASE,
        ("witness:set", {"case_id": Newest("crime_case"), "witness_id": Pick(MORTAL, 1), "testimony": "accuses", "reliability": 50}),
        case_id=Newest("crime_case"),
        witness_id=Pick(MORTAL, 1),
    ),
    **{
        name: after(("workshop_design:create", {"world_id": Pick("world"), "base_kind": "forge", "name": "Long Forge"}), design_id=Newest("workshop_design"))
        for name in ("workshop_design:delete", "workshop_design:edit", "workshop_design:release")
    },
    "world:date_golden_age": after(("world:golden_age", {"world_id": Pick("world")}), since_epoch=1),
    "world:depth": given(history="It rose from the deep."),
    "world:edit": given(cosmology="Three rings of sky."),
    "world:end_golden_age": after(("world:golden_age", {"world_id": Pick("world")})),
    "world:orbit": given(star_id=Pick("star")),
    "wrath": given(entity_id=Pick(TOWN)),
    **{
        name: after(("year:force_notable", {"region_id": Pick(EntityType.REGION), "magnitude": 20}), notable_id=Newest("notable_year"))
        for name in ("year:delete", "year:edit")
    },
    "art_form:practitioner": after(
        ("lore:create", {"entity_type": "art_form", "name": "Reed Song", "world_id": Pick("world"), "values": {"discipline": "musical"}}),
        art_form_id=Newest(EntityType.ART_FORM),
    ),
    "community:crown": given(community_id=Computed(unruled_community)),
    "hero:apprentice": given(hero_id=Computed(mortal_without_apprentice)),
    "company:edit": after(*COMPANY, company_id=Newest(EntityType.FACTION), dividend_pct=10),
    **{
        name: after(
            *COMPANY,
            ("company:edit", {"company_id": Newest(EntityType.FACTION), "dividend_pct": 10}),
            company_id=Newest(EntityType.FACTION),
            holder_id=Pick(MORTAL),
        )
        for name in ("company:remove", "company:share")
    },
    "company:share_remove": after(
        *COMPANY,
        ("company:edit", {"company_id": Newest(EntityType.FACTION), "dividend_pct": 10}),
        ("company:share", {"company_id": Newest(EntityType.FACTION), "holder_id": Pick(MORTAL), "share": 10}),
        company_id=Newest(EntityType.FACTION),
        holder_id=Pick(MORTAL),
    ),
    "cosmic:forget_world": given(world_id=Pick("world", 1)),
    "cosmic:rekindle_star": after(("cosmic:extinguish_star", {"star_id": Pick("star")}), star_id=Pick("star")),
    "cosmic:legendary_quest": after(
        ("cosmic:extinguish_star", {"star_id": Pick("star")}), aim="restore", target_kind="star", obstacle="riddle", reward="peace"
    ),
    "cosmic:sky_event": given(world_id=Pick("world")),
    "cosmic:soul_bind": after(("soul:raise", {"mortal_id": DEAD}), soul_id=Newest(EntityType.SPIRIT), target_id=Pick(EntityType.ITEM)),
    "cosmos:deposit": after(("cosmos:resource", {"name": "Starsalt"}), place_id=Pick(EntityType.PLACE)),
    "deposit:owner": after(
        ("cosmos:resource", {"name": "Starsalt"}),
        ("cosmos:deposit", {"place_id": Pick(EntityType.PLACE)}),
        deposit_id=Newest(EntityType.RESOURCE),
        owner_id=Pick(TOWN),
    ),
    "de_jure:set": given(member_id=Pick(EntityType.REGION)),
    "de_jure:remove": after(("de_jure:set", {"title_id": Pick(EntityType.TITLE), "member_id": Pick(EntityType.REGION)}), member_id=Pick(EntityType.REGION)),
    "event:release": after(("event:phase", {"event_id": Pick(EntityType.EVENT), "phase": "peak", "hold": True}), event_id=Pick(EntityType.EVENT)),
    "exile": given(entity_id=HOME_MORTAL, world_id=Pick("world", 1)),
    "faction:contract": after(
        ("faction:found", {"community_id": Pick(TOWN, 2), "kind": "mercenary_company"}), faction_id=Newest(EntityType.FACTION), polity_id=Pick(REALM)
    ),
    "faith:syncretize": setup_then(foreign_god, entity_id=Pick(EntityType.PEOPLE), god_id=Pick("foreign_god")),
    "faith:unsyncretize": setup_then(
        foreign_god,
        ("faith:syncretize", {"entity_id": Pick(EntityType.PEOPLE), "god_id": Pick("foreign_god")}),
        entity_id=Pick(EntityType.PEOPLE),
        god_id=Pick("foreign_god"),
    ),
    "furnishing:remove": after(("furnishing:add", {"household_id": Pick("household"), "item_id": Pick(EntityType.ITEM)}), item_id=Pick(EntityType.ITEM)),
    "guild:secret": after(
        ("research:technique", {"holder_id": Computed(town_without_guild), "technique": "phalanx_drill"}),
        ("faction:found", {"community_id": Computed(town_without_guild), "kind": "craft_guild"}),
        guild_id=Newest(EntityType.FACTION),
    ),
    "hero:hunt": given(monster_id=Pick(EntityType.SPECIES)),
    "hero:quest": given(hero_id=Computed(free_hero)),
    **{name: after(("hero:quest", {"hero_id": Computed(free_hero)}), hero_id=Computed(questing_hero)) for name in ("hero:recall", "hero:resolve")},
    "holy_order:edit": after(*HOLY, order_id=Newest(EntityType.FACTION), tithe_share=10),
    "holy_order:remove": after(*HOLY, ("holy_order:edit", {"order_id": Newest(EntityType.FACTION), "tithe_share": 10}), order_id=Newest(EntityType.FACTION)),
    "horror:suppress_cult": after(("horror:cult", {"entity_id": Pick(TOWN)}), cult_id=Newest(EntityType.CULT)),
    "house:merge": given(house_id=Pick(EntityType.HOUSE), into_id=Pick(EntityType.HOUSE, 1)),
    "identity:edit": after(("identity:assume", {"mortal_id": Pick(MORTAL), "false_name": "Wren"}), mortal_id=Pick(MORTAL), exposure=20),
    "incident:unlink_cause": after(
        ("incident:link_cause", {"incident_id": Newest("incident"), "cause_incident_id": Pick("incident")}), incident_id=Newest("incident")
    ),
    "incident:hold": after(WRITTEN, incident_id=Newest("incident"), fields=["text", "steps"]),
    "incident_fact:create": after(WRITTEN, incident_id=Newest("incident"), key="amount", number=12, unit="count"),
    **{
        name: after(WRITTEN, FACT_SET, incident_fact_id=Newest("incident_fact"), **values)
        for name, values in (("incident_fact:edit", {"number": 20, "unit": "count"}), ("incident_fact:delete", {}))
    },
    "incident_step:create": after(
        WRITTEN,
        incident_id=Newest("incident"),
        step_action="strike",
        actor_node_id=Pick(MORTAL),
        target_node_id=Pick(MORTAL, 1),
        damage_type="blunt",
        amount=3,
        unit="hp",
        outcome="wounded",
        states=[{"node_id": Pick(MORTAL, 1), "state": "prone"}],
    ),
    **{
        name: after(WRITTEN, STEP_SET, incident_step_id=Newest("incident_step"), **values)
        for name, values in (("incident_step:edit", {"step_action": "parry", "outcome": "parried"}), ("incident_step:delete", {}))
    },
    "incident_witness:create": after(WRITTEN, incident_id=Newest("incident"), node_id=Pick(MORTAL, 1), witness_mode="heard", fidelity=60),
    **{
        name: after(WRITTEN, WITNESS_SET, incident_id=Newest("incident"), node_id=Pick(MORTAL, 1), **values)
        for name, values in (("incident_witness:edit", {"witness_mode": "was_told", "fidelity": 40}), ("incident_witness:delete", {}))
    },
    **{name: after(CRIME_SET, state_change_id=Newest("state_change")) for name in ("state_change:revert", "state_change:delete")},
    "rumour_distortion:create": after(WHISPER, rumour_id=Newest("rumour"), distortion="moment_changed", told_year=3),
    **{
        name: after(WHISPER, DISTORTED, rumour_distortion_id=Newest("rumour_distortion"), **values)
        for name, values in (
            ("rumour_distortion:edit", {"distortion": "place_changed", "told_node_id": Pick(TOWN, 1), "hold": ["told"]}),
            ("rumour_distortion:delete", {}),
        )
    },
    "incident_name:set": after(WRITTEN, incident_id=Newest("incident"), name="Kerovan", hold=True),
    "incident_name:delete": after(WRITTEN, ("incident_name:set", {"incident_id": Newest("incident"), "name": "Kerovan"}), incident_id=Newest("incident")),
    "item:transfer": given(receiver_id=Pick(MORTAL, 1)),
    "kin:end_marriage": after(("kin:marry", {"first_id": Pick(MORTAL), "second_id": Pick(MORTAL, 1)}), marriage_id=Newest("marriage")),
    "kin:unbond": after(("kin:bond", {"source_id": Pick(MORTAL), "target_id": Pick(MORTAL, 1), "kind": "parent_of"}), bond_id=Newest("bond")),
    "market:write_off": after(LOANED, bond_id=Computed(town_debt)),
    **{
        name: after(("movement:found", {"realm_id": Pick(REALM), "home_id": Pick(TOWN)}), movement_id=Newest(EntityType.FACTION), community_id=Pick(TOWN))
        for name in ("movement:remove", "movement:support")
    },
    "movement:edit": after(("movement:found", {"realm_id": Pick(REALM), "home_id": Pick(TOWN)}), movement_id=Newest(EntityType.FACTION), support=40),
    "movement:support_remove": after(
        ("movement:found", {"realm_id": Pick(REALM), "home_id": Pick(TOWN)}),
        ("movement:support", {"movement_id": Newest(EntityType.FACTION), "community_id": Pick(TOWN), "share": 20}),
        movement_id=Newest(EntityType.FACTION),
        community_id=Pick(TOWN),
    ),
    "research:institution": given(technique="bureaucracy"),
    "answer_prayer": Lever(values={"message_id": Newest("message")}, setup=prayer),
    **{name: Lever(values={"view_id": Newest("historian_view")}, setup=historian_view) for name in ("voices:delete_view", "voices:edit_view")},
    "belief:rename": after(
        ("belief:edit", {"people_id": Pick(EntityType.PEOPLE), "son_id": Pick("son"), "narrative": "The god came down with the rain."}), son_id=Pick("son")
    ),
    "belief:forget": after(
        ("belief:edit", {"people_id": Pick(EntityType.PEOPLE), "god_id": Pick("foreign_god"), "narrative": "The god came down with the rain."}),
        people_id=Pick(EntityType.PEOPLE),
        god_id=Pick("foreign_god"),
    ),
    "civilization:barter": Lever(values={"first_id": Pick(TOWN), "second_id": Pick(TOWN, 1)}, setup=bartering_towns),
    "speculation:open": Lever(values={"merchant_id": Pick(MORTAL), "market_id": Pick(TOWN), "commodity": "grain", "units": 5, "price": 10}, setup=market_goods),
    **{
        name: Lever(
            values={"speculation_id": Newest("speculation")},
            before=(("speculation:open", {"merchant_id": Pick(MORTAL), "market_id": Pick(TOWN), "commodity": "grain", "units": 5, "price": 10}),),
            setup=market_goods,
        )
        for name in ("speculation:remove",)
    },
    "speculation:edit": Lever(
        values={"speculation_id": Newest("speculation"), "price": 12},
        before=(("speculation:open", {"merchant_id": Pick(MORTAL), "market_id": Pick(TOWN), "commodity": "grain", "units": 5, "price": 10}),),
        setup=market_goods,
    ),
    "creed:custom_tenet": after(
        IDEOLOGY,
        ("kind:create", {"catalog": "tenet", "base": "legalism", "name": "Open Ledger"}),
        ideology_id=Newest(EntityType.IDEOLOGY),
        kind_id=Newest("custom_kind"),
    ),
    "resurrect:son": Lever(values={"son_id": Pick("son", 1)}, setup=dead_and_rich),
    "rite": Lever(values={"entity_id": Pick(TOWN), "son_id": Pick("son", 1), "kind": "rite"}, setup=dead_sibling_and_rich_town),
    **{name: Lever(values={"sibling_id": Pick("son"), "son_id": Pick("son", 1)}, setup=dead_sibling) for name in ("sibling:hinder_return", "sibling:scheme")},
    "son:star": Lever(values={"son_id": Pick("son")}, setup=seasoned_son),
    "son:ascend": Lever(values={"son_id": Pick("son")}, setup=ascended_son),
    "son:protection": Lever(values={"son_id": Pick("son")}, setup=placed_son),
    "son:power": given(slot=1, name="Long Stride", effect="tireless"),
    "son:world": given(world_id=Pick("world", 1)),
    "son:anchor": given(entity_id=Computed(son_creation)),
    "son:clear_anchor": after(("son:anchor", {"son_id": Pick("son"), "entity_id": Computed(son_creation)})),
    "world:guardian": given(son_id=Pick("son", 1)),
    "world:planet_stirs": Lever(values={"world_id": Pick("world")}, setup=living_planet),
    "star:delete": after(("cosmic:hang_star", {"name": "Pale Lamp", "star_type": "yellow_dwarf"}), star_id=Newest("star")),
    "soul:descend": Lever(values={"mortal_id": DEAD}, setup=underworld),
    "soul:mirror": Lever(values={"mortal_id": DEAD}, setup=mirrored),
    "soul:harvest": after(("soul:raise", {"mortal_id": DEAD}), cult_id=Pick(EntityType.CULT), soul_id=Newest(EntityType.SPIRIT)),
    "soul:judge": after(
        ("soul:raise", {"mortal_id": DEAD}),
        ("afterlife:stratum", {"realm_id": Pick(REALM), "kind": "common", "name": "The Grey Field"}),
        spirit_id=Newest(EntityType.SPIRIT),
        stratum_id=Newest("afterlife_strata"),
    ),
    "stance:remove": after(
        ("proposal:create", {"polity_id": Pick(REALM), "kind": "succession_rule"}),
        ("stance:set", {"proposal_id": Newest("law_proposal"), "node_id": Pick(MORTAL), "weight": 10}),
        proposal_id=Newest("law_proposal"),
        node_id=Pick(MORTAL),
    ),
    "settings": given(mortal_agents_per_epoch=2),
    "scenario:abandon": after(("scenario:start", {"key": "doom_far"}), scenario_id=Newest("scenario")),
    "scenario:start": given(key="many_worlds", target=3, deadline_epochs=6),
    "scenario:custom": given(metric="languages", comparator="at_least", basis="gained", target=2, hold_epochs=1, deadline_epochs=5, title="New tongues"),
    "scenario:edit": after(("scenario:start", {"key": "doom_far"}), scenario_id=Newest("scenario"), target=25, deadline_epochs=10),
    "scenario:hold": after(("scenario:start", {"key": "doom_far"}), scenario_id=Newest("scenario"), held=True),
    "scenario:delete": after(("scenario:start", {"key": "doom_far"}), scenario_id=Newest("scenario")),
    "quest:abandon": after(
        ("cosmic:extinguish_star", {"star_id": Pick("star")}), ("cosmic:legendary_quest", {"aim": "restore", "target_kind": "star"}), thread_id=Newest("thread")
    ),
    **{name: Lever(values={"knowledge_id": Pick(EntityType.KNOWLEDGE)}, setup=astronomy) for name in ("calendar:adopt",)},
    **{
        name: Lever(
            values={"knowledge_id": Pick(EntityType.KNOWLEDGE), "anchor_year": 5},
            before=(("calendar:adopt", {"knowledge_id": Pick(EntityType.KNOWLEDGE)}),),
            setup=astronomy,
        )
        for name in ("calendar:anchor", "calendar:drop")
    },
    "calendar:holy_day": Lever(
        values={"knowledge_id": Pick(EntityType.KNOWLEDGE), "name": "Lantern Night"},
        before=(("calendar:adopt", {"knowledge_id": Pick(EntityType.KNOWLEDGE)}),),
        setup=astronomy,
    ),
    "calendar:rename": Lever(
        values={"knowledge_id": Pick(EntityType.KNOWLEDGE), "names": ["Thaw", "Bloom", "Harvest", "Frost", "Dark"]},
        before=(("calendar:adopt", {"knowledge_id": Pick(EntityType.KNOWLEDGE)}),),
        setup=astronomy,
    ),
    "calendar:holy_day_remove": Lever(
        values={"knowledge_id": Pick(EntityType.KNOWLEDGE), "index": 0},
        before=(
            ("calendar:adopt", {"knowledge_id": Pick(EntityType.KNOWLEDGE)}),
            ("calendar:holy_day", {"knowledge_id": Pick(EntityType.KNOWLEDGE), "name": "Lantern Night"}),
        ),
        setup=astronomy,
    ),
    "language:creole": Lever(values={"community_id": Pick(TOWN)}, setup=bilingual),
    "settlement:resettle": Lever(values={"ruin_id": Newest(EntityType.SETTLEMENT), "population": 50, "source_id": Pick(TOWN)}, setup=ruin),
    "occupation:edit": Lever(values={"region_id": Pick(EntityType.REGION), "control": 40}, setup=occupied),
    "intuition:discard": Lever(values={"intuition_id": Newest("horizon_intuition")}, setup=intuition),
    "sensed_world:request": Lever(values={"intuition_id": Newest("horizon_intuition")}, setup=intuition),
    **{
        name: Lever(
            values={"step_id": Newest("deferred_step")}, before=(("sensed_world:request", {"intuition_id": Newest("horizon_intuition")}),), setup=intuition
        )
        for name in ("sensed_world:cancel", "sensed_world:hold", "sensed_world:retry")
    },
    "creation:reward": Lever(values={"entity_id": Pick(MORTAL), "taken_back_pct": 50}, setup=rewarded),
    "species:spare_prey": Lever(values={"species_id": Pick(EntityType.SPECIES)}, setup=hunted),
    "seasons:release": after(("seasons:edit", {"season_id": Pick("world_season"), "growth": 60}), season_id=Pick("world_season")),
    "creed:found": after(("mind:values", {"node_id": Pick(MORTAL), "values": {"martial": 95}})),
    "federation": given(member_ids=[Pick(TOWN), Pick(TOWN, 1)], name="The Concord"),
    "resolution:propose": after(FEDERATION, assembly_id=ASSEMBLY),
    **{
        name: after(FEDERATION, ("resolution:propose", {"assembly_id": ASSEMBLY}), resolution_id=Newest("resolution"), member_id=Pick(TOWN))
        for name in ("resolution:delete", "resolution:edit", "resolution:hold", "vote:set")
    },
    "vote:remove": after(
        FEDERATION,
        ("resolution:propose", {"assembly_id": ASSEMBLY}),
        ("vote:set", {"resolution_id": Newest("resolution"), "member_id": Pick(TOWN), "aye": True}),
        resolution_id=Newest("resolution"),
        member_id=Pick(TOWN),
    ),
    "record_row:create": given(table="entity_tags", values={"entity_id": Pick(MORTAL), "tag": "wanderer"}),
    "record_row:delete": after(
        ("record_row:create", {"table": "entity_tags", "values": {"entity_id": Pick(MORTAL), "tag": "wanderer"}}),
        table="entity_tags",
        key={"entity_id": Pick(MORTAL), "tag": "wanderer"},
    ),
    "record_row:edit": after(PASSION, table="passions", key={"id": Newest("passion")}, values={"strength": 50}),
    "resolution:edit": after(FEDERATION, ("resolution:propose", {"assembly_id": ASSEMBLY}), resolution_id=Newest("resolution"), votes_for=2),
    "sensed_world:retry": Lever(
        values={"step_id": Newest("deferred_step")},
        before=(("sensed_world:request", {"intuition_id": Newest("horizon_intuition")}),),
        setup=intuition,
        then=failed_birth,
    ),
    "community:rise_up": Lever(values={"community_id": Pick(TOWN)}, setup=ruled_town),
    "expedition": Lever(values={"entity_id": Pick(EntityType.PEOPLE), "route_id": Pick("route")}, before=(GATE_LORE,), setup=gate_lore),
    "journey:recall": Lever(
        values={"journey_id": Newest("journey")},
        before=(GATE_LORE, ("expedition", {"entity_id": Pick(EntityType.PEOPLE), "route_id": Pick("route")})),
        setup=gate_lore,
    ),
    "foundation:hold": after(("world:golden_age", {"world_id": Pick("world")}), kind="golden_age", node_id=Pick("world")),
    "item:content": after(
        ("lore:create", {"entity_type": "item", "name": "Ledger of Tides", "world_id": Pick("world"), "values": {"item_class": "book"}}),
        book_id=Newest(EntityType.ITEM),
    ),
    "engagement:force": after(
        ("vessel:create", {"owner_id": Pick(TOWN), "name": "Gull", "frame": "warship"}),
        ("vessel:create", {"owner_id": Pick(TOWN, 1), "name": "Tern", "frame": "warship"}),
        vessel_id=Newest(EntityType.VESSEL),
        foe_vessel_id=Computed(older_vessel),
    ),
    "vessel:repair": Lever(
        values={"vessel_id": Newest(EntityType.VESSEL)},
        before=(("vessel:create", {"owner_id": Pick(TOWN), "name": "Gull", "home_port_id": Pick(TOWN)}),),
        then=battered_vessel,
    ),
    "war:separate_peace": after(
        ("bond:add", {"kind": "ally", "source_id": Pick(TOWN), "target_id": Pick(TOWN, 2)}),
        WAR,
        ("war:call_allies", {"war_id": Newest("war"), "side_id": Pick(TOWN)}),
        war_id=Newest("war"),
        side_id=Computed(allied_side),
    ),
    "species:feed": Lever(
        values={"species_id": Pick(EntityType.SPECIES)}, before=(("soul:raise", {"mortal_id": DEAD, "place_id": Computed(soul_range)}),), setup=soul_eating
    ),
    **{name: after(PROPHECY, prophecy_id=Newest(EntityType.PROPHECY)) for name in ("prophecy:forget", "prophecy:fulfil", "prophecy:resolve")},
    "dimension:create": Lever(values={"name": "Shadow Deep", "kind": "shadow", "element": "shadow", "form": "image"}, setup=rich_creator),
    "dimension:bind_law": given(dimension_id=Computed(prime_dimension), law_id=Computed(natural_law)),
    "dimension:release_law": Lever(values={"law_id": Newest(EntityType.NATURAL_LAW)}, setup=bound_law),
    "heavens:worship": given(community_id=Pick(EntityType.PEOPLE), sky="dimension", worships=True, dimension_id=Computed(prime_dimension)),
    **{
        name: setup_then(heavens, dimension_id=Where("dimensions", "id", {"dimension_kind": DimensionKind.ASTRAL}))
        for name in ("dimension:edit", "dimension:delete")
    },
    "cluster:create": Lever(values={"name": "Near Group", "kind": "poor_cluster", "dimension_id": Where("dimensions", "id")}, setup=rich_heavens),
    **{name: setup_then(heavens, cluster_id=Newest("galaxy_cluster")) for name in ("cluster:edit", "cluster:delete")},
    "galaxy:create": Lever(values={"name": "Near Spiral", "galaxy_type": "ring", "cluster_id": Newest("galaxy_cluster")}, setup=rich_heavens),
    **{name: setup_then(heavens, galaxy_id=Newest("galaxy")) for name in ("galaxy:edit", "galaxy:delete")},
    "galactic_structure:create": Lever(values={"galaxy_id": Newest("galaxy"), "kind": "dark_nebula", "name": "Dark Lane"}, setup=heavens),
    **{name: setup_then(heavens, structure_id=Newest("galactic_structure")) for name in ("galactic_structure:edit", "galactic_structure:delete")},
    "galactic_event:trigger": Lever(values={"galaxy_id": Newest("galaxy"), "kind": "galactic_dimming"}, setup=heavens),
    **{name: setup_then(heavens, event_id=Newest("galactic_event")) for name in ("galactic_event:edit", "galactic_event:delete")},
    "dimensional_event:trigger": Lever(values={"dimension_id": Newest("dimension"), "kind": "planar_alignment"}, setup=heavens),
    **{name: setup_then(heavens, event_id=Newest("dimensional_event")) for name in ("dimensional_event:edit", "dimensional_event:delete")},
    "rift:open": Lever(values={"world_id": Pick("world"), "region_id": Pick(EntityType.REGION), "dimension_id": Newest("dimension")}, setup=heavens),
    **{name: setup_then(heavens, rift_id=Newest("rift")) for name in ("rift:edit", "rift:seal", "rift:delete")},
    "cosmic_being:call": given(kind="cloud_mind", world_id=Pick("world"), region_id=Pick(EntityType.REGION)),
    **{
        name: setup_then(heavens, being_id=Newest(EntityType.COSMIC_BEING))
        for name in ("cosmic_being:edit", "cosmic_being:bind", "cosmic_being:banish", "cosmic_wound:strike")
    },
    "phenomenon:create": given(kind="sounding_ground", region_id=Pick(EntityType.REGION), intensity=40),
    **{name: setup_then(heavens, phenomenon_id=Newest(EntityType.PHENOMENON)) for name in ("phenomenon:edit", "phenomenon:contain")},
    "phenomenon:footprint": setup_then(heavens, phenomenon_id=Newest(EntityType.PHENOMENON), region_id=Pick(EntityType.REGION, 1), intensity=30),
    "star_life:edit": setup_then(heavens, star_id=Pick("star")),
    "world_life:edit": setup_then(heavens, world_id=Pick("world")),
    "route_flow:edit": given(route_id=Pick("route")),
    "gathering:convene": given(host_id=Pick(MORTAL), kind="feast", guests=[Pick(MORTAL, 1)]),
    **{
        name: after(("gathering:convene", {"host_id": Pick(MORTAL), "kind": "feast", "hold_now": False}), gathering_id=Newest("gathering"))
        for name in ("gathering:hold", "gathering:edit", "gathering:delete")
    },
    "gathering_guest:set": after(
        ("gathering:convene", {"host_id": Pick(MORTAL), "kind": "feast", "hold_now": False}), gathering_id=Newest("gathering"), node_id=Pick(MORTAL, 1)
    ),
    "gathering_guest:remove": after(
        ("gathering:convene", {"host_id": Pick(MORTAL), "kind": "feast", "hold_now": False}),
        ("gathering_guest:set", {"gathering_id": Newest("gathering"), "node_id": Pick(MORTAL, 1)}),
        gathering_id=Newest("gathering"),
        node_id=Pick(MORTAL, 1),
    ),
    "collection:create": given(kind="war", name="War of the Fords", members=[{"node_id": Pick(REALM), "role": "leader"}], places=[Pick(TOWN)]),
    **{
        name: after(("collection:create", {"kind": "war", "members": [{"node_id": Pick(REALM)}]}), collection_id=Newest("incident_collection"))
        for name in ("collection:edit", "collection:delete")
    },
    "collection_member:set": after(
        ("collection:create", {"kind": "war", "members": [{"node_id": Pick(REALM)}]}), collection_id=Newest("incident_collection"), node_id=Pick(MORTAL)
    ),
    "collection_member:remove": after(
        ("collection:create", {"kind": "war", "members": [{"node_id": Pick(REALM)}, {"node_id": Pick(MORTAL)}]}),
        collection_id=Newest("incident_collection"),
        node_id=Pick(MORTAL),
    ),
    "collection:place": after(
        ("collection:create", {"kind": "war", "members": [{"node_id": Pick(REALM)}]}), collection_id=Newest("incident_collection"), place_id=Pick(TOWN)
    ),
    "storyteller:set": given(world_id=Pick("world"), profile="steady"),
    "site_room:create": given(site_id=Pick(EntityType.PLACE), kind="vault", challenge="trap", difficulty=40),
    **{
        name: after(("site_room:create", {"site_id": Pick(EntityType.PLACE), "kind": "vault"}), room_id=Newest("site_room"))
        for name in ("site_room:edit", "site_room:delete")
    },
    "room_content:add": after(("site_room:create", {"site_id": Pick(EntityType.PLACE), "kind": "vault"}), room_id=Newest("site_room"), kind="trap"),
    "room_content:remove": after(
        ("site_room:create", {"site_id": Pick(EntityType.PLACE), "kind": "vault"}),
        ("room_content:add", {"room_id": Newest("site_room"), "kind": "trap"}),
        content_id=Newest("room_content"),
    ),
    "site:delve": after(("site_room:create", {"site_id": Pick(EntityType.PLACE), "kind": "hall"}), delver_id=Pick(MORTAL), site_id=Pick(EntityType.PLACE)),
    "site_holder:set": given(site_id=Pick(EntityType.PLACE), holder_id=Pick(REALM)),
    "site_holder:delete": after(("site_holder:set", {"site_id": Pick(EntityType.PLACE), "holder_id": Pick(REALM)}), holder_row_id=Newest("site_holder")),
    "excavation:begin": given(site_id=Pick(EntityType.PLACE), leader_id=Pick(MORTAL), sponsor_id=Pick(REALM)),
    **{
        name: after(("excavation:begin", {"site_id": Pick(EntityType.PLACE), "leader_id": Pick(MORTAL)}), dig_id=Newest("excavation"))
        for name in ("excavation:edit", "excavation:advance", "excavation:delete")
    },
    "excavation_stage:edit": after(("excavation:begin", {"site_id": Pick(EntityType.PLACE), "leader_id": Pick(MORTAL)}), stage_id=Newest("excavation_stage")),
    "battlefield_feature:create": given(place_id=Pick(EntityType.PLACE), feature="mass_grave", strength=60),
    "modifier:edit": given(modifier_id=Pick("modifier"), magnitude=1.5),
    "throne:create": given(place_id=Pick(EntityType.REGION), power=70),
    **{name: after(("throne:create", {"place_id": Pick(EntityType.REGION)}), throne_id=Newest("throne")) for name in ("throne:edit", "throne:delete")},
    **{
        name: after(("intervene", {"entity_id": Pick(TOWN), "action": "miracle", "miracle": "bounty"}), miracle_id=Newest("miracle_record"))
        for name in ("miracle_record:edit", "miracle_record:delete")
    },
    **{name: after(RITE, rite_id=Newest(EntityType.RITE)) for name in ("rite_grammar:edit", "rite_grammar:delete")},
    "lab_text:write": after(RITE, rite_id=Newest(EntityType.RITE), author_id=Pick(MORTAL)),
    **{
        name: after(RITE, ("lab_text:write", {"rite_id": Newest(EntityType.RITE), "author_id": Pick(MORTAL)}), book_id=Where("lab_texts", "book_entity_id"))
        for name in ("lab_text:edit", "lab_text:delete")
    },
    "vis:set": given(holder_id=Pick(TOWN), form="fire", amount=5),
    "vis:delete": after(("vis:set", {"holder_id": Pick(TOWN), "form": "fire", "amount": 5}), holder_id=Pick(TOWN), form="fire"),
    "warping:edit": given(node_id=Pick(MORTAL)),
    "warping:delete": after(("warping:edit", {"node_id": Pick(MORTAL), "values": {"value": 30}}), node_id=Pick(MORTAL)),
    "longevity:begin": given(mortal_id=Pick(MORTAL), form="body"),
    **{name: after(("longevity:begin", {"mortal_id": Pick(MORTAL), "form": "body"}), mortal_id=Pick(MORTAL)) for name in ("longevity:edit", "longevity:end")},
    "enchantment:lay": given(caster_id=Pick("son"), effect="bounty", world_id=Pick("world"), strength=40),
    **{
        name: after(
            ("enchantment:lay", {"caster_id": Pick("son"), "effect": "bounty", "world_id": Pick("world"), "strength": 40}),
            law_id=Where("law_upkeep", "law_entity_id"),
        )
        for name in ("law_upkeep:edit", "law_upkeep:delete", "enchantment:dispel")
    },
    "item_charge:edit": after(
        ("item:enchant", {"item_id": Pick(EntityType.ITEM), "effect": "ward", "strength": 30}), item_id=Pick(EntityType.ITEM), effect="ward"
    ),
    "sound_change:add": given(language_id=Pick(TONGUE), kind="shift", source="a", target="e"),
    **{name: after(SOUND, change_id=Newest("sound_change")) for name in ("sound_change:edit", "sound_change:delete")},
    "grammar:edit": given(language_id=Pick(TONGUE)),
    "grammar:reset": given(language_id=Pick(TONGUE)),
    "tongue:edit": given(language_id=Pick(TONGUE)),
    "word:register": given(lexeme_id=Pick("lexeme"), word_register="poetic"),
    "word:veil": given(language_id=Pick(TONGUE), node_id=Pick(MORTAL)),
    **{name: after(VEIL, shift_id=Newest("meaning_shift")) for name in ("meaning_shift:edit", "meaning_shift:delete")},
    "script:create": given(language_id=Pick(TONGUE), system="alphabet"),
    **{name: after(SCRIPT, script_id=Newest("script")) for name in ("script:edit", "script:delete")},
    "script:assign": after(SCRIPT, language_id=Pick(TONGUE), script_id=Newest("script")),
    "decipherment:start": given(language_id=Pick(TONGUE), scholar_id=Pick(MORTAL)),
    **{name: after(DECIPHER, language_id=Pick(TONGUE)) for name in ("decipherment:edit", "decipherment:delete")},
    "language_policy:set": given(holder_id=Pick(REALM), language_id=Pick(TONGUE), policy="official"),
    **{name: after(POLICY, holder_id=Pick(REALM), language_id=Pick(TONGUE), policy="official") for name in ("language_policy:edit", "language_policy:delete")},
    "divine_tongue:set": given(god_id=Pick("son")),
    **{name: after(TONGUE_GIVEN, god_id=Pick("son")) for name in ("divine_tongue:edit", "divine_tongue:delete")},
    "divine_tongue:teach": after(TONGUE_GIVEN, god_id=Pick("son"), mortal_id=Pick(MORTAL)),
    "pidgin:make": Lever(values={"first_id": Pick(TOWN), "second_id": Pick(TOWN, 1)}, setup=strangers),
    "district_urban:edit": given(district_id=DISTRICT),
    "district:move": given(district_id=DISTRICT, q=40, r=-40),
    "town_urban:edit": given(settlement_id=Pick(TOWN)),
    "structure:place": after(TEMPLE, structure_id=Newest(EntityType.STRUCTURE), district_id=DISTRICT),
    "slums:clear": given(settlement_id=Pick(TOWN)),
    "district_service:set": given(district_id=DISTRICT, service="watch", coverage=60),
    **{name: after(SERVICE_SET, district_id=DISTRICT, service="watch") for name in ("district_service:edit", "district_service:delete")},
    "turf:set": after(CRIME, district_id=DISTRICT, faction_id=Newest(EntityType.FACTION), strength=40),
    **{name: after(CRIME, TURF, district_id=DISTRICT, faction_id=Newest(EntityType.FACTION)) for name in ("turf:edit", "turf:delete")},
    "racket:set": after(CRIME, faction_id=Newest(EntityType.FACTION), settlement_id=Pick(TOWN), racket="gambling"),
    **{
        name: after(CRIME, RACKET, faction_id=Newest(EntityType.FACTION), settlement_id=Pick(TOWN), racket="gambling")
        for name in ("racket:edit", "racket:delete")
    },
    "payroll:add": after(CRIME, faction_id=Newest(EntityType.FACTION), official_id=Pick(MORTAL)),
    **{name: after(CRIME, PAYROLL, faction_id=Newest(EntityType.FACTION), official_id=Pick(MORTAL)) for name in ("payroll:edit", "payroll:delete")},
    "crime_stance:set": after(CRIME, polity_id=Pick(REALM), faction_id=Newest(EntityType.FACTION), stance="suppress"),
    **{name: after(CRIME, STANCE, polity_id=Pick(REALM), faction_id=Newest(EntityType.FACTION)) for name in ("crime_stance:edit", "crime_stance:delete")},
    "order_law:set": after(HOUSE, ORDER, faction_id=Newest(EntityType.FACTION), law="share_discoveries"),
    **{name: after(HOUSE, ORDER, LAW, faction_id=Newest(EntityType.FACTION), law="share_discoveries") for name in ("order_law:edit", "order_law:delete")},
    "tribunal:convene": after(HOUSE, ORDER, LAW, faction_id=Newest(EntityType.FACTION), law="share_discoveries", accused_id=Pick(MORTAL)),
    "tribunal:strike": after(HOUSE, ORDER, LAW, TRIAL, trial_id=Newest("order_tribunal")),
    "trading_post:open": after(HOUSE, owner_id=Newest(EntityType.FACTION), host_id=Pick(TOWN)),
    **{name: after(HOUSE, POST, structure_id=Newest(EntityType.STRUCTURE)) for name in ("trading_post:edit", "trading_post:close")},
    "convoy:send": given(route_id=Pick(EntityType.TRADE_ROUTE)),
    **{name: after(CONVOY, convoy_id=Newest("convoy")) for name in ("convoy:edit", "convoy:delete")},
    "fleet:set": given(owner_id=Pick(TOWN), kind="animal_carts", count=12),
    **{name: after(FLEET, owner_id=Pick(TOWN), kind="animal_carts") for name in ("fleet:edit", "fleet:delete")},
    "market_play:set": after(HOUSE, holder_id=Newest(EntityType.FACTION), settlement_id=Pick(TOWN), commodity="grain", play="corner"),
    **{
        name: after(HOUSE, PLAY, holder_id=Newest(EntityType.FACTION), settlement_id=Pick(TOWN), commodity="grain", play="corner")
        for name in ("market_play:edit", "market_play:delete")
    },
    "legal_system:set": given(holder_id=Pick(REALM), system="precedent"),
    **{name: after(SYSTEM, holder_id=Pick(REALM)) for name in ("legal_system:edit", "legal_system:delete")},
    "precedent:add": given(holder_id=Pick(REALM), crime="theft", verdict="guilty"),
    **{name: after(PRECEDENT, precedent_id=Newest("precedent")) for name in ("precedent:edit", "precedent:delete")},
    "appeal:file": given(case_id=CONVICTION, to_court="provincial", fee=0),
    **{name: after(APPEAL, case_id=Newest("crime_case")) for name in ("appeal:edit", "appeal:hear", "appeal:delete")},
    "oracle:answer": after(CASE, case_id=Newest("crime_case"), verdict="acquitted"),
    "registry:add": given(holder_id=Pick(REALM), kind="debt", owner_id=Pick(MORTAL), counterparty_id=Pick(MORTAL, 1), amount=30),
    **{name: after(DEED, registry_id=Newest("registry")) for name in ("registry:edit", "registry:delete")},
    "jurisdiction:set": given(holder_id=Pick(REALM), claimant_id=Pick(EntityType.CULT), claim="clergy", strength=40),
    **{name: after(CLAIM, holder_id=Pick(REALM), claimant_id=Pick(EntityType.CULT), claim="clergy") for name in ("jurisdiction:edit", "jurisdiction:delete")},
    "pardon:grant": after(OUTLAW, granter_id=Pick(MORTAL), mortal_id=Pick(MORTAL, 2)),
    "amnesty:declare": given(polity_id=Computed(ruled_realm)),
    "polity:depose": given(polity_id=Computed(ruled_realm)),
    "pardon:delete": after(OUTLAW, PARDON, pardon_id=Newest("pardon")),
    "outlaw:declare": given(mortal_id=Pick(MORTAL, 2), polity_id=Pick(REALM), bounty=20),
    **{name: after(OUTLAW, mortal_id=Pick(MORTAL, 2)) for name in ("outlaw:edit", "outlaw:delete")},
    "prison:set": given(structure_id=PRISON, values={"food": 60}),
    **{name: after(PRISON_SET, structure_id=PRISON) for name in ("prison:edit", "prison:delete")},
    "prisoner:jail": given(mortal_id=Pick(MORTAL, 2), prison_id=PRISON, term=3),
    **{name: after(JAIL, mortal_id=Pick(MORTAL, 2)) for name in ("prisoner:edit", "prisoner:free")},
    "spy_cell:add": after(SPY_NET, network_id=Newest("spy_network"), dead_drops=2),
    **{name: after(SPY_NET, CELL, cell_id=Newest("spy_cell")) for name in ("spy_cell:edit", "spy_cell:delete")},
    "mole_hunt:order": given(polity_id=Computed(spied_realm)),
    "mole_hunt:delete": after(DEFECT, HUNT, hunt_id=Computed(any_hunt)),
    "defection:make": given(mortal_id=Pick(MORTAL, 2), to_id=Pick(REALM), protected=True),
    **{name: after(DEFECT, defection_id=Newest("defection")) for name in ("defection:edit", "defection:delete")},
    "killing:add": given(victim_id=Pick(MORTAL, 2), method="poison", recognised=True),
    **{name: after(KILLING, killing_id=Newest("assassination")) for name in ("killing:edit", "killing:delete")},
    "species_trait:set": given(species_id=Pick(EntityType.SPECIES), region_id=Pick(EntityType.REGION), trait="speed", mean=60),
    **{
        name: after(TRAIT, species_id=Pick(EntityType.SPECIES), region_id=Pick(EntityType.REGION), trait="speed")
        for name in ("species_trait:edit", "species_trait:delete")
    },
    "lineage:mark": given(species_id=Pick(EntityType.SPECIES), package="divine_blessing", blessing=True, source_node_id=Pick("son")),
    **{name: after(LINE, species_id=Pick(EntityType.SPECIES), package="divine_blessing") for name in ("lineage:edit", "lineage:delete")},
    "species_ecology:edit": given(species_id=Pick(EntityType.SPECIES)),
    "ecosystem_service:set": given(region_id=Pick(EntityType.REGION), role="pollinator", strength=50, species_id=Pick(EntityType.SPECIES)),
    **{name: after(SERVICE, region_id=Pick(EntityType.REGION), role="pollinator") for name in ("ecosystem_service:edit", "ecosystem_service:delete")},
    "herd:release": after(HERD, community_id=Pick(TOWN), species_id=Pick(EntityType.SPECIES)),
    "carrier:add": after(DISEASE, mortal_id=Pick(MORTAL), disease_id=Newest(EntityType.DISEASE)),
    **{name: after(DISEASE, CARRIER, mortal_id=Pick(MORTAL), disease_id=Newest(EntityType.DISEASE)) for name in ("carrier:edit", "carrier:delete")},
    "plague_response:set": after(DISEASE, community_id=Pick(TOWN), disease_id=Newest(EntityType.DISEASE), response="quarantine"),
    **{
        name: after(DISEASE, RESPONSE, community_id=Pick(TOWN), disease_id=Newest(EntityType.DISEASE), response="prayer")
        for name in ("plague_response:edit", "plague_response:delete")
    },
    "cure_research:start": after(HOSPITAL, DISEASE, institution_id=Newest(EntityType.STRUCTURE), disease_id=Newest(EntityType.DISEASE)),
    **{
        name: after(HOSPITAL, DISEASE, RESEARCH, institution_id=Newest(EntityType.STRUCTURE), disease_id=Newest(EntityType.DISEASE))
        for name in ("cure_research:edit", "cure_research:delete")
    },
    "world_cycle:edit": given(world_id=Pick("world")),
    "world_cycle:reset": after(("world_cycle:edit", {"world_id": Pick("world"), "values": {"carbon": 60}}), world_id=Pick("world")),
    "land:reshape": given(region_id=Pick(EntityType.REGION), act="raise_land"),
    "heroquest:begin": given(quester_id=Pick(MORTAL), legend_id=Pick(EntityType.LEGEND)),
    **{
        name: after(("heroquest:begin", {"quester_id": Pick(MORTAL), "legend_id": Pick(EntityType.LEGEND)}), quest_id=Newest("heroquest"))
        for name in ("heroquest:edit", "heroquest:party", "heroquest:advance", "heroquest:delete")
    },
    "mantling:edit": given(mortal_id=Pick(MORTAL)),
    "mantling:delete": after(("mantling:edit", {"mortal_id": Pick(MORTAL), "values": {"progress": 30}}), mortal_id=Pick(MORTAL)),
    "servitor:make": given(god_id=Pick("son"), name="Watcher", role="guard"),
    **{
        name: after(("servitor:make", {"god_id": Pick("son"), "name": "Watcher", "role": "guard"}), spirit_id=Where("servitors", "spirit_entity_id"))
        for name in ("servitor:edit", "servitor:release")
    },
    "geas:lay": given(bearer_id=Pick(MORTAL), mode="taboo", act="theft"),
    **{
        name: after(("geas:lay", {"bearer_id": Pick(MORTAL), "mode": "taboo", "act": "theft"}), geas_id=Where("geasa", "id"))
        for name in ("geas:edit", "geas:break", "geas:delete")
    },
    "cosmic_office:appoint": given(office="dead", holder_id=Pick("son")),
    "cosmic_office:edit": given(office="dead"),
    "cosmic_office:vacate": after(("cosmic_office:appoint", {"office": "dead", "holder_id": Pick("son")}), office="dead"),
    "divine_creature:raise": given(god_id=Pick("son"), name="Grey Warden", description="A watcher of the hills", home_id=Pick(EntityType.REGION)),
    **{
        name: after(
            ("divine_creature:raise", {"god_id": Pick("son"), "name": "Grey Warden", "home_id": Pick(EntityType.REGION)}),
            creature_id=Where("divine_creatures", "creature_entity_id"),
            **extra,
        )
        for name, extra in (
            ("divine_creature:edit", {}),
            ("divine_creature:teach", {"deed": "tend_fields", "lesson": "reward"}),
            ("divine_creature:weight", {"deed": "heal_sick", "weight": 40}),
            ("divine_creature:release", {}),
        )
    },
    **{
        name: after(("battlefield_feature:create", {"place_id": Pick(EntityType.PLACE), "feature": "salvage_field"}), feature_id=Newest("battlefield_feature"))
        for name in ("battlefield_feature:edit", "battlefield_feature:delete")
    },
    "cosmic_feature:create": given(kind="asteroid_field", name="Near Belt", star_id=Pick("star")),
    **{
        name: after(("cosmic_feature:create", {"kind": "asteroid_field", "name": "Near Belt", "star_id": Pick("star")}), feature_id=Newest("cosmic_feature"))
        for name in ("cosmic_feature:edit", "cosmic_feature:delete")
    },
    **{
        name: after(("impact:call", {"world_id": Pick("world")}), impact_id=Newest("impact_event"))
        for name in ("impact:deflect", "impact:edit", "impact:delete")
    },
    **{
        name: after(("terraform:start", {"world_id": Pick("world"), "aim": "warm"}), project_id=Newest("terraforming"))
        for name in ("terraform:edit", "terraform:stop")
    },
    "survey:set": given(observer_id=Pick(EntityType.PEOPLE), world_id=Pick("world"), level="observed"),
    **{
        name: Lever(
            values={"journey_id": Newest("journey"), **extra},
            before=(GATE_LORE, ("expedition", {"entity_id": Pick(EntityType.PEOPLE), "route_id": Pick("route")})),
            setup=gate_lore,
        )
        for name, extra in (
            (
                "journey:load",
                {
                    "convoy": 3,
                    "escorts": 2,
                    "cargo": [{"commodity": "grain", "amount": 50}],
                    "passengers": [{"social_class": "farmer", "count": 40}],
                    "supplies": 70,
                    "births": 2,
                    "deaths": 1,
                    "arrival": "settlers",
                },
            ),
            ("journey:release", {"fields": ["convoy", "cargo"]}),
        )
    },
    "celestial_reading:set": setup_then(heavens, celestial_id=Newest(EntityType.CELESTIAL), people_id=Pick(EntityType.PEOPLE), reading="evil", visible=False),
    "apocalypse:variant": given(variant="galactic_death"),
    "region_climate:turn": given(region_id=Pick(EntityType.REGION), turn="drier"),
    "body:prosthesis": after(("body:maim", {"bearer_id": Pick(MORTAL), "part": "left_arm", "severity": 5, "lethal": False}), material="wood", quality=40),
}

EDITS: Mapping[str, Mapping[str, Any]] = {
    "crowd_mood:edit": {"anger": 70, "anxiety": 20, "fervour": 10, "deterrence": 30, "agitation": 15, "last_trigger": "famine"},
    "mob:edit": {
        "act": "riot",
        "size": 200,
        "anger": 40,
        "damage": 12,
        "target": "palace",
        "status": "rampaging",
        "target_entity_id": Pick(MORTAL),
        "leader_entity_id": Pick(MORTAL, 1),
    },
    "popular_movement:edit": {
        "act": "riot",
        "trigger": "famine",
        "members": 300,
        "strength": 50,
        "leader_entity_id": Pick(MORTAL),
        "ended_epoch": 9,
    },
    "account:edit": {
        "kind": "folk_memory",
        "fidelity": 40,
        "credence": 70,
        "defaced": True,
        "medium": "inscription",
        "author_node_id": Pick(MORTAL),
        "subject_node_id": Pick(MORTAL, 1),
    },
    "memory_strike:edit": {"active": False},
    "founding_myth:edit": {"credence": 50},
    "commemoration:edit": {"strength": 40, "pride": False},
    "lost_land:edit": {"strength": 30, "claimed_epoch": 4},
    "storylet:edit": {"status": "expired", "due_epoch": 9, "chooser_node_id": Pick(MORTAL)},
    "social_norm:edit": {"stance": "shameful"},
    "learning_bias:edit": {"prestige_pct": 50, "conformity_pct": 30, "content_pct": 20},
    "generation:edit": {"alive": 120},
    "diaspora:edit": {"population": 300, "ties": 40, "remittance": 10, "home_entity_id": Pick(TOWN, 1)},
    "transition:edit": {"fertility_pct": 80, "elder_share": 20, "urban_share": 40, "literacy": 30},
    "sex_ratio:edit": {"males_per_hundred": 90, "widows": 10},
    "role_norm:edit": {"eligibility": "female_preferred", "min_age": 18, "stance": "frowned_upon", "classes": ["noble", "priest"]},
    "dating_system:edit": {
        "kind": "regnal",
        "anchor_year": 12,
        "cycle_years": 30,
        "anchor_node_id": Pick(MORTAL),
        "label_node_id": Pick(REALM),
    },
    "arms:edit": {
        "shape": "kite",
        "field": "red",
        "division": "bend_sinister",
        "line": "engrailed",
        "second": "ermine",
        "charge": "tower",
        "charge_tincture": "gold",
        "charge_two": "fleur_de_lis",
        "charge_two_tincture": "silver",
        "charge_three": "rose",
        "charge_three_tincture": "gold",
        "arrangement": "one_and_two",
        "rim": "beaded",
        "rim_line": "wavy",
        "rim_tincture": "gold",
        "supporter": "column",
        "supporter_pose": "flanking",
        "supporter_tincture": "silver",
        "crest": "crown",
        "crest_tincture": "gold",
        "motto": "Steady",
    },
    "design:edit": {
        "name": "The Swift",
        "frame": "carrack",
        "speed": 40,
        "range": 30,
        "seaworthiness": 60,
        "cargo": 80,
        "armament": 20,
        "crew": 30,
        "obsolete": False,
        "designer_entity_id": Pick(MORTAL),
    },
    "component_wear:edit": {"wear": 30},
    "trade_route:edit": {"danger_bandits": 30, "capacity": 50, "length": 3, "chokepoint": True},
    "structure:edit": {"condition": 80, "anchor": True, "splendor": 60},
    "structure_design:edit": {"cost_pct": 110, "form": "dome", "storeys": 3, "material": "stone"},
    "species:edit": {"litter_size": 2},
    "species:range": {"abundance": 40},
    "herd:edit": {"head": 40},
    "beast:edit": {"age": 10},
    "use_kind:edit": {"output_pct": 120},
    "anatomy:edit": {"limbs": 4},
    "plant:edit": {"soil_need": 40, "growing_seasons": 2},
    "lore:edit": {"credence": 40, "distortion": 10},
    "research:institution": {"embraced": True},
    "research:boost_edit": {"progress": 40, "epoch": 2},
    "research:holder": {"level": 2},
    "kind:edit": {"name": "Plain kind", "description": "A kind set by hand."},
    "faction:edit": {"cohesion": 60, "treasury": 40},
    "event:edit": {"severity": 40},
    "ley:work": {"attuned": True},
    "material:create": {"hardness": 50},
    "workshop_design:create": {"output_pct": 110},
    "workshop_design:edit": {"output_pct": 110},
    "people:edit": {"cohesion": 60},
    "people:found": {"cohesion": 60},
    "class:standing": {"fed_pct": 70, "wealth": 30},
    "disease:edit": {"lethality": 20, "incubation": 2},
    "disease:create": {"lethality": 20},
    "outbreak:edit": {"severity": 30},
    "settlement:edit": {"crime": 20, "sewers": True},
    "district:design": {"housing": 10},
    "district:design_edit": {"housing": 10},
    "polity:edit": {"legitimacy": 60, "stability": 55},
    "house:edit": {"prestige": 40},
    "army:edit": {"cohesion": 60, "loot": 5},
    "army:edit_stack": {"morale": 60, "experience": 30},
    "siege:edit": {"disease_inside": 10},
    "war:edit_side": {"support": 70, "weariness": 20},
    "spy:edit_network": {"intel": 40, "exposure": 10},
    "military:edit": {"name": "Shieldwall"},
    "cult:doctrine": {"orthodoxy": 60, "treasury": 10},
    "cult:edit_heresy": {"distance": 30},
    "relic:edit": {"sanctity": 60},
    "soul:edit": {"veneration": 30},
    "soul:possession": {"stress": 20},
    "mind:values": {"honour": 40},
    "mind:attributes": {"strength": 60},
    "mind:facets": {"anxiety": 30},
    "god_goal:edit": {"progress": 40},
    "divine_standing:set": {"love": 40, "fear": 10},
    "divine_wound:edit": {"healed": 30, "prior_mode": "concrete"},
    "avatar:edit": {"deeds": 2},
    "attention:set": {"attention": 40, "watched": True},
    "ruling:edit": {"until_epoch": 9},
    "law_profile:edit": {"strength": 70, "scope": "cosmos", "effect": "bounty"},
    "outer_profile:edit": {"reach": 2, "hunger": "light", "fed": 3},
    "breach:edit": {"strength": 40},
    "dimension:edit": {"veil": 30, "time_factor": 2.0, "causality": "loose"},
    "cluster:edit": {"medium_heat": 40, "radius": 2000.0},
    "galaxy:edit": {"star_formation": 60, "arm_count": 3, "nucleus": "active"},
    "galactic_structure:edit": {"intensity": 70, "radius": 80.0},
    "galactic_event:edit": {"intensity": 60},
    "dimensional_event:edit": {"intensity": 40},
    "rift:edit": {"size": 40, "stability": 70},
    "cosmic_being:edit": {"might": 70, "agenda": "guard"},
    "phenomenon:edit": {"intensity": 60, "growth": 2},
    "star_life:edit": {"stability": 50, "age_stage": "old", "radiation": 30},
    "world_life:edit": {"magnetism": 20, "biosphere_health": 60, "mood": -10},
    "route_flow:edit": {"toll_pct": 10, "piracy": 20, "window_every": 2},
    "star_physics:edit": {"mass": 1.2, "metallicity": 40},
    "star_system:edit": {"name": "Twin Lights", "separation": 2.0},
    "world_physics:edit": {"albedo": 35, "pressure": 1.2},
    "life_class:edit": {"complexity": "complex", "environments": ["marine", "terrestrial"]},
    "gathering:edit": {"prestige": 40, "cost": 12, "note": "held by order of the gods"},
    "collection:edit": {"name": "War of the Two Fords", "start_epoch": 1, "note": "a long war"},
    "storyteller:set": {"tension": 40, "boost_pct": 10, "cycle_offset": 2},
    "site_room:edit": {"difficulty": 55, "challenge": "guardian"},
    "excavation:edit": {"progress": 30, "stage": "clearing"},
    "god_design:edit": {"dominion_strength": 40, "rank": 1},
    "god_image:edit": {"stance": "resist", "believed_wrath": 30},
    "miracle_record:edit": {"belief": 12, "need": 40},
    "magic_site:edit": {"strength": 70, "output": 5},
    "throne:edit": {"power": 80},
    "divine_creature:edit": {"hunger": 20, "neglect_epochs": 1},
    "rite_grammar:edit": {"technique": "ward", "range": "region"},
    "lab_text:edit": {"fidelity": 60},
    "warping:edit": {"value": 60},
    "longevity:edit": {"dose": 2, "dependence": 30},
    "law_upkeep:edit": {"essence_upkeep": 3, "dispel_resistance": 70},
    "item_charge:edit": {"charges": 2, "capacity": 4},
    "sound_change:edit": {"target": "o"},
    "grammar:edit": {"cases": 3, "word_order": "svo"},
    "tongue:edit": {"modality": "sign"},
    "meaning_shift:edit": {"new_meaning": "a newer sense"},
    "script:edit": {"signs": 30},
    "decipherment:edit": {"progress": 40},
    "language_policy:edit": {"strength": 70},
    "divine_tongue:edit": {"language_entity_id": Pick(TONGUE, 1)},
    "species_trait:edit": {"mean": 70, "variance": 20},
    "lineage:edit": {"blessing": False, "source_node_id": Pick("son")},
    "species_ecology:edit": {"keystone": "pollinator", "feral_epoch": 2},
    "ecosystem_service:edit": {"strength": 70, "species_entity_id": Pick(EntityType.SPECIES)},
    "carrier:edit": {"identified": True, "seeded": 2},
    "plague_response:edit": {"strength": 80, "until_epoch": 9},
    "cure_research:edit": {"points": 40, "specimens": 3},
    "world_cycle:edit": {"carbon": 60, "water": 40, "nutrients": 55},
    "district_urban:edit": {"housing": "townhouse", "desirability": 70, "land_value": 60},
    "town_urban:edit": {"morphology": "planned", "homeless": 40},
    "district_service:edit": {"coverage": 80},
    "turf:edit": {"strength": 70},
    "racket:edit": {"income": 25},
    "payroll:edit": {"bribe": 15},
    "crime_stance:edit": {"strength": 80, "stance": "co_opt"},
    "order_law:edit": {"strength": 90},
    "trading_post:edit": {"informants": 3, "goods": 50},
    "convoy:edit": {"guards": 6, "status": "delayed", "capacity": 40},
    "fleet:edit": {"count": 20, "age": 3, "condition": 70},
    "market_play:edit": {"strength": 70, "until_epoch": 9},
    "legal_system:edit": {"system": "codified"},
    "precedent:edit": {"authority": 70, "verdict": "acquitted", "overturned": True},
    "appeal:edit": {"to_court": "high", "fee": 40, "reversed": True},
    "registry:edit": {"amount": 60},
    "jurisdiction:edit": {"strength": 75},
    "outlaw:edit": {"bounty": 50, "private_bounty": 20, "renown": 30},
    "prison:edit": {"food": 40, "crowding": 50, "cruelty": 60, "gang_strength": 20},
    "prisoner:edit": {"term": 5, "gang_rank": 40},
    "spy_cell:edit": {"dead_drops": 4},
    "defection:edit": {"secrets": 2, "protected": False},
    "killing:edit": {"method": "accident", "recognised": False},
    "heroquest:edit": {"steps": 4, "fidelity": 80},
    "mantling:edit": {"progress": 40, "deeds": 3},
    "servitor:edit": {"loyalty": 60, "role": "judge"},
    "geas:edit": {"favour": 10},
    "cosmic_office:edit": {"neglect": 20, "duty": 40},
    "excavation_stage:edit": {"difficulty": 45, "risk": "collapse", "find": "book"},
    "battlefield_feature:edit": {"strength": 70},
    "cosmic_feature:edit": {"density": 40, "richness": 60},
    "impact:edit": {"size": 30, "winter_epochs": 1},
    "terraform:edit": {"step": 5, "epochs_left": 3},
}
TOWN_MOOD = Computed(profiled_town)
EVENT = Computed(any_collection)
VESSEL = Computed(any_vessel)
PEOPLE = EntityType.PEOPLE
MOOD = ("crowd_mood:set", {"town_id": TOWN_MOOD, "anger": 60})
SPARK = ("cascade:spark", {"town_id": TOWN_MOOD, "trigger": "famine"})
MOB = ("mob:raise", {"town_id": TOWN_MOOD, "act": "riot", "target": "district", "size": 100, "anger": 60})
MOVEMENT = ("popular_movement:found", {"town_id": TOWN_MOOD})
ACCOUNT = ("account:write", {"holder_id": Pick(REALM), "subject_id": Pick(MORTAL)})
REVISION = ("account:revise", {"account_id": Newest("account"), "ousted_ids": [Pick(MORTAL)]})
STANCE = ("account_stance:set", {"account_id": Newest("account"), "node_id": Pick(MORTAL), "stance": "glorify"})
STRIKE = ("memory_strike:set", {"by_id": Pick(REALM), "node_id": Pick(MORTAL)})
MYTH = ("founding_myth:set", {"holder_id": Pick(REALM), "credence": 80})
KEPT = ("commemoration:set", {"holder_id": Pick(REALM), "collection_id": EVENT})
LOST = ("lost_land:set", {"claimant_id": Pick(REALM), "region_id": Pick(EntityType.REGION)})
STORYLET = ("storylet:open", {"storylet": "lost_heir", "world_id": Pick("world")})
NORM = ("social_norm:set", {"holder_id": Pick(PEOPLE), "situation": "feast", "behaviour": "jest", "stance": "admirable"})
BIAS = ("learning_bias:set", {"holder_id": Pick(PEOPLE)})
GENERATION = ("generation:set", {"community_id": Pick(TOWN), "generation_epoch": 0})
DIASPORA = ("diaspora:set", {"people_id": Pick(PEOPLE), "host_id": Pick(TOWN)})
TRANSITION = ("transition:set", {"community_id": Pick(TOWN)})
RATIO = ("sex_ratio:set", {"community_id": Pick(TOWN)})
ROLE = ("role_norm:set", {"holder_id": Pick(PEOPLE), "role": "office"})
DATING = ("dating_system:set", {"holder_id": Pick(REALM), "kind": "founding", "anchor_year": 10})
ARMS = (
    "arms:set",
    {
        "holder_id": Pick(REALM),
        "holder_kind": "polity",
        "shape": "french",
        "field": "gold",
        "division": "chevron",
        "line": "indented",
        "second": "blue",
        "charge": "star",
        "charge_tincture": "black",
        "charge_two": "star",
        "charge_two_tincture": "black",
        "arrangement": "in_fess",
        "rim": "rope",
        "supporter": "sword",
        "supporter_pose": "crossed",
        "supporter_tincture": "silver",
        "crest": "sun",
    },
)
OTHER_ARMS = ("arms:set", {"holder_id": Pick(REALM, 1), "holder_kind": "polity", "field": "blue"})
DESIGN = ("design:draw", {"owner_id": Pick(REALM), "frame": "carrack"})
WEAR = ("component_wear:set", {"vessel_id": VESSEL, "component": "hull", "wear": 20})
LEVERS.update(
    {
        "crowd_mood:set": given(town_id=TOWN_MOOD, anger=60),
        **{name: after(MOOD, town_id=TOWN_MOOD) for name in ("crowd_mood:edit", "crowd_mood:delete")},
        "cascade:spark": given(town_id=TOWN_MOOD, trigger="famine"),
        "cascade:delete": after(SPARK, cascade_id=Newest("cascade")),
        "mob:raise": given(town_id=TOWN_MOOD, act="riot", target="district", size=100, anger=60),
        **{name: after(MOB, mob_id=Newest("mob")) for name in ("mob:edit", "mob:disperse", "mob:delete")},
        "popular_movement:found": given(town_id=TOWN_MOOD),
        **{name: after(MOVEMENT, movement_id=Newest("movement")) for name in ("popular_movement:edit", "popular_movement:delete")},
        "account:write": given(holder_id=Pick(REALM), subject_id=Pick(MORTAL)),
        **{name: after(ACCOUNT, account_id=Newest("account")) for name in ("account:edit", "account:delete")},
        "account:revise": after(ACCOUNT, account_id=Newest("account"), ousted_ids=[Pick(MORTAL)]),
        "account:expose": after(ACCOUNT, REVISION, account_id=Newest("account")),
        "account_stance:set": after(ACCOUNT, account_id=Newest("account"), node_id=Pick(MORTAL), stance="vilify"),
        "account_stance:delete": after(ACCOUNT, STANCE, account_id=Newest("account"), node_id=Pick(MORTAL)),
        "memory_strike:set": given(by_id=Pick(REALM), node_id=Pick(MORTAL)),
        **{name: after(STRIKE, by_id=Pick(REALM), node_id=Pick(MORTAL)) for name in ("memory_strike:edit", "memory_strike:delete")},
        "founding_myth:set": given(holder_id=Pick(REALM), credence=80),
        **{name: after(MYTH, holder_id=Pick(REALM)) for name in ("founding_myth:edit", "founding_myth:debunk", "founding_myth:delete")},
        "commemoration:set": given(holder_id=Pick(REALM), collection_id=EVENT),
        **{name: after(KEPT, holder_id=Pick(REALM), collection_id=EVENT) for name in ("commemoration:edit", "commemoration:relive", "commemoration:delete")},
        "lost_land:set": given(claimant_id=Pick(REALM), region_id=Pick(EntityType.REGION)),
        **{name: after(LOST, claimant_id=Pick(REALM), region_id=Pick(EntityType.REGION)) for name in ("lost_land:edit", "lost_land:delete")},
        "storylet:open": Lever(values={"storylet": "lost_heir", "world_id": Pick("world")}, setup=heir_at_court),
        **{name: setup_then(heir_at_court, STORYLET, run_id=Newest("storylet_run")) for name in ("storylet:edit", "storylet:delete")},
        "storylet:choose": setup_then(heir_at_court, STORYLET, run_id=Newest("storylet_run"), choice=0),
        "social_norm:set": given(holder_id=Pick(PEOPLE), situation="feast", behaviour="jest", stance="admirable"),
        **{name: after(NORM, holder_id=Pick(PEOPLE), situation="feast", behaviour="jest") for name in ("social_norm:edit", "social_norm:delete")},
        "norm_change:delete": after(NORM, change_id=Newest("norm_change")),
        "learning_bias:set": given(holder_id=Pick(PEOPLE)),
        **{name: after(BIAS, holder_id=Pick(PEOPLE)) for name in ("learning_bias:edit", "learning_bias:delete")},
        "learning_event:delete": Lever(values={"event_id": Newest("learning_event")}, setup=a_lesson),
        "generation:set": given(community_id=Pick(TOWN), generation_epoch=0),
        "generation:shape": given(community_id=Pick(TOWN), generation_epoch=0, formative=["plague"], axis="piety", shift=10),
        **{name: after(GENERATION, community_id=Pick(TOWN), generation_epoch=0) for name in ("generation:edit", "generation:delete")},
        "diaspora:set": given(people_id=Pick(PEOPLE), host_id=Pick(TOWN)),
        **{name: after(DIASPORA, people_id=Pick(PEOPLE), host_id=Pick(TOWN)) for name in ("diaspora:edit", "diaspora:delete")},
        "transition:set": given(community_id=Pick(TOWN)),
        **{name: after(TRANSITION, community_id=Pick(TOWN)) for name in ("transition:edit", "transition:delete")},
        "sex_ratio:set": given(community_id=Pick(TOWN)),
        **{name: after(RATIO, community_id=Pick(TOWN)) for name in ("sex_ratio:edit", "sex_ratio:delete")},
        "role_norm:set": given(holder_id=Pick(PEOPLE), role="office", classes=["noble"]),
        **{name: after(ROLE, holder_id=Pick(PEOPLE), role="office") for name in ("role_norm:edit", "role_norm:delete")},
        "dating_system:set": given(holder_id=Pick(REALM), kind="founding", anchor_year=10),
        **{name: after(DATING, holder_id=Pick(REALM)) for name in ("dating_system:edit", "dating_system:delete")},
        "arms:set": given(**ARMS[1]),
        **{name: after(ARMS, holder_id=Pick(REALM)) for name in ("arms:edit", "arms:delete")},
        "arms:quarter": after(ARMS, OTHER_ARMS, holder_id=Pick(REALM), other_id=Pick(REALM, 1)),
        "arms:difference": after(ARMS, holder_id=Pick(REALM, 1), parent_id=Pick(REALM), border="vair", line="nebuly"),
        "design:draw": given(owner_id=Pick(REALM), frame="carrack"),
        **{name: after(DESIGN, design_id=Newest("design")) for name in ("design:edit", "design:refit", "design:delete")},
        "design_component:set": after(DESIGN, design_id=Newest("design"), component="hull", size=5, quality=60),
        "design_component:delete": after(DESIGN, design_id=Newest("design"), component="hull"),
        "design:fit": after(DESIGN, vessel_id=VESSEL, design_id=Newest("design")),
        "component_wear:set": given(vessel_id=VESSEL, component="hull", wear=20),
        **{name: after(WEAR, vessel_id=VESSEL, component="hull") for name in ("component_wear:edit", "component_wear:delete")},
    }
)


async def full_treasuries(session: AsyncSession) -> None:
    await session.execute(update(PolityProfileRow).values(treasury=10_000))
    await session.flush()


async def freed_row(session: AsyncSession) -> None:
    town = await canon(session, TOWN, 0)
    assert town is not None
    session.add(ManumissionRow(community_entity_id=town, count=5, path=ManumissionPath.LAW, epoch=0))
    await session.flush()


STRESS = ("stress:set", {"polity_id": Pick(REALM)})
READING = ("stress_reading:set", {"polity_id": Pick(REALM), "epoch": 0})
SOLIDARITY = ("asabiyya:set", {"holder_id": Pick(PEOPLE)})
CHALLENGE = ("challenge:strike", {"polity_id": Pick(REALM)})
PLAN = ("plan:create", {"holder_id": Pick(REALM), "kind": "wonder", "name": "The Long Work", "target_id": Pick(TOWN)})
GIFT = ("gift:give", {"giver_id": Pick(REALM), "receiver_id": Pick(REALM, 1), "value": 10})
CIRCUIT = ("circuit:create", {"name": "The First Round", "stops": [Pick(TOWN), Pick(TOWN, 1)]})
DEBT = ("debt:set", {"god_id": Pick("son"), "community_id": Pick(TOWN)})
KIN = ("kinship:set", {"people_id": Pick(PEOPLE), "first_side": "male"})
ALLIANCE = ("alliance:set", {"giver_id": Pick(EntityType.HOUSE), "taker_id": Pick(EntityType.HOUSE, 1)})
BIRTHS = ("reproduction:set", {"people_id": Pick(PEOPLE)})
CASTE = ("caste:set", {"mortal_id": Pick(MORTAL), "caste": "soldier"})
CAMP = ("camp:set", {"town_id": Pick(TOWN)})
OTHER_CAMP = ("camp:set", {"town_id": Pick(TOWN, 1)})
LEAGUE = ("confederation:create", {"name": "The Joined Camps", "leader_id": Pick(MORTAL), "members": [Pick(TOWN), Pick(TOWN, 1)]})
LEGACY = ("legacy:set", {"people_id": Pick(PEOPLE), "kind": "martial_style", "key": "phalanx", "predecessor_id": Pick(PEOPLE, 1)})
BOND = ("indenture:create", {"community_id": Pick(TOWN)})
MARKET = ("slave_market:set", {"town_id": Pick(TOWN)})
GIFT_ID = Newest("gift")
LEGACY_KEY = {"people_id": Pick(PEOPLE), "kind": "martial_style", "key": "phalanx"}
CYCLE_EDITS: Mapping[str, Mapping[str, Any]] = {
    "stress:edit": {
        "pressure": 40,
        "immiseration": 30,
        "elite_overproduction": 50,
        "fiscal_distress": 20,
        "aspirants": 100,
        "positions": 80,
        "challenge": 10,
        "phase": "stagflation",
    },
    "stress_reading:edit": {"pressure": 30, "immiseration": 20, "elite_overproduction": 40, "fiscal_distress": 10, "psi": 25, "phase": "crisis"},
    "asabiyya:edit": {"value": 70, "frontier": 2, "luxury_generations": 1, "conflict": 30},
    "challenge:edit": {"kind": "plague", "severity": 40, "response": "collapse", "source_node_id": Pick(TOWN)},
    "plan:edit": {
        "name": "The Second Work",
        "kind": "conversion",
        "target_node_id": Pick(TOWN),
        "carrier_node_id": Pick(MORTAL),
        "steps": 20,
        "progress": 3,
        "step_cost": 5,
        "secrecy": 70,
        "exposed": True,
        "status": "active",
    },
    "gift:edit": {"value": 25, "occasion": "feast", "item_entity_id": Pick(EntityType.ITEM), "state": "returned", "due_epoch": 5},
    "circuit:edit": {"name": "The Second Round", "item_entity_id": Pick(EntityType.ITEM), "position": 1, "passes": 3},
    "debt:edit": {"offered": 50, "answered": 20},
    "union:edit": {
        "form": "plural",
        "plural_side": "second",
        "purpose": "alliance",
        "residence": "with_second_family",
        "exchange": "service",
        "exchange_value": 20,
        "dissolution": "none",
        "endogamy": "faith",
        "exogamy": "moiety",
        "kin_match": "parallel_cousin",
        "term_epochs": 6,
    },
    "kinship:edit": {
        "descent": "through_second_line",
        "residence": "with_second_family",
        "descent_group": "clan",
        "kin_terms": "bifurcate_merging",
        "adoption": "chosen_kin",
        "first_side": "female",
        "sibling_union_first": True,
        "sibling_union_second": True,
    },
    "alliance:edit": {"marriages": 4},
    "reproduction:edit": {"system": "caste", "change_age": 25, "breeder_pct": 15, "soldier_pct": 25, "worker_pct": 60},
    "caste:edit": {"caste": "breeder"},
    "camp:edit": {"mode": "transhumant", "season_index": 0, "herd": 300, "grazing": 60, "water": 40},
    "confederation:edit": {"name": "The Bound Camps", "leader_entity_id": Pick(MORTAL, 1), "dissolved_epoch": 1},
    "legacy:edit": {"predecessor_entity_id": Pick(PEOPLE, 1)},
    "indenture:edit": {
        "employer_node_id": Pick(TOWN, 1),
        "regime": "peonage",
        "count": 20,
        "term_epochs": 4,
        "debt": 80,
        "exploitation": 60,
        "origin_entity_id": Pick(PEOPLE),
    },
    "slave_market:edit": {"price": 35, "stock": 10, "sold": 2, "open": False},
    "manumission:edit": {"count": 7, "path": "purchase", "standing": 65, "origin_entity_id": Pick(PEOPLE)},
}
EDITS = {**EDITS, **CYCLE_EDITS}
LEVERS.update(
    {
        "stress:set": given(polity_id=Pick(REALM)),
        **{name: after(STRESS, polity_id=Pick(REALM)) for name in ("stress:edit", "stress:delete")},
        "stress_reading:set": given(polity_id=Pick(REALM), epoch=0),
        **{name: after(READING, polity_id=Pick(REALM), epoch=0) for name in ("stress_reading:edit", "stress_reading:delete")},
        "asabiyya:set": given(holder_id=Pick(PEOPLE)),
        **{name: after(SOLIDARITY, holder_id=Pick(PEOPLE)) for name in ("asabiyya:edit", "asabiyya:delete")},
        "challenge:strike": given(polity_id=Pick(REALM)),
        **{name: after(CHALLENGE, challenge_id=Newest("challenge")) for name in ("challenge:edit", "challenge:delete")},
        "plan:create": given(holder_id=Pick(REALM), kind="wonder", name="The Long Work", target_id=Pick(TOWN)),
        **{name: after(PLAN, plan_id=Newest("long_plan")) for name in ("plan:edit", "plan:advance", "plan:expose", "plan:delete")},
        "gift:give": setup_then(full_treasuries, giver_id=Pick(REALM), receiver_id=Pick(REALM, 1), value=10),
        **{name: setup_then(full_treasuries, GIFT, gift_id=GIFT_ID) for name in ("gift:return", "gift:refuse", "gift:edit", "gift:delete")},
        "circuit:create": given(name="The First Round", stops=[Pick(TOWN), Pick(TOWN, 1)]),
        "circuit:route": after(CIRCUIT, circuit_id=Newest("circuit"), stops=[Pick(TOWN, 1), Pick(TOWN, 2)]),
        **{name: after(CIRCUIT, circuit_id=Newest("circuit")) for name in ("circuit:edit", "circuit:pass", "circuit:delete")},
        "debt:set": given(god_id=Pick("son"), community_id=Pick(TOWN)),
        **{name: after(DEBT, god_id=Pick("son"), community_id=Pick(TOWN)) for name in ("debt:edit", "debt:delete")},
        "kinship:set": given(people_id=Pick(PEOPLE), first_side="female"),
        "union:set": given(people_id=Pick(PEOPLE), form="contract", purpose="love", descent="by_house_rule", exchange="mutual", exogamy="house"),
        **{name: after(("union:set", {"people_id": Pick(PEOPLE)}), people_id=Pick(PEOPLE)) for name in ("union:edit", "union:delete")},
        **{name: after(KIN, people_id=Pick(PEOPLE)) for name in ("kinship:edit", "kinship:delete")},
        "alliance:set": given(giver_id=Pick(EntityType.HOUSE), taker_id=Pick(EntityType.HOUSE, 1)),
        **{name: after(ALLIANCE, giver_id=Pick(EntityType.HOUSE), taker_id=Pick(EntityType.HOUSE, 1)) for name in ("alliance:edit", "alliance:delete")},
        "reproduction:set": given(people_id=Pick(PEOPLE)),
        **{name: after(BIRTHS, people_id=Pick(PEOPLE)) for name in ("reproduction:edit", "reproduction:delete")},
        "caste:set": given(mortal_id=Pick(MORTAL), caste="soldier"),
        **{name: after(CASTE, mortal_id=Pick(MORTAL)) for name in ("caste:edit", "caste:delete")},
        "camp:set": given(town_id=Pick(TOWN)),
        "camp:route": after(CAMP, town_id=Pick(TOWN), regions=[Pick(EntityType.REGION)]),
        **{name: after(CAMP, town_id=Pick(TOWN)) for name in ("camp:edit", "camp:move", "camp:delete")},
        "confederation:create": after(CAMP, OTHER_CAMP, name="The Joined Camps", leader_id=Pick(MORTAL), members=[Pick(TOWN), Pick(TOWN, 1)]),
        "confederation:members": after(CAMP, OTHER_CAMP, LEAGUE, confederation_id=Newest("confederation"), members=[Pick(TOWN, 1), Pick(TOWN)]),
        **{
            name: after(CAMP, OTHER_CAMP, LEAGUE, confederation_id=Newest("confederation"))
            for name in ("confederation:edit", "confederation:dissolve", "confederation:delete")
        },
        "legacy:set": given(people_id=Pick(PEOPLE), kind="martial_style", key="phalanx", predecessor_id=Pick(PEOPLE, 1)),
        **{name: after(LEGACY, **LEGACY_KEY) for name in ("legacy:edit", "legacy:delete")},
        "indenture:create": given(community_id=Pick(TOWN), origin_id=Pick(PEOPLE)),
        **{name: after(BOND, indenture_id=Newest("indenture")) for name in ("indenture:edit", "indenture:release", "indenture:delete")},
        "slave_market:set": given(town_id=Pick(TOWN)),
        **{name: after(MARKET, town_id=Pick(TOWN)) for name in ("slave_market:edit", "slave_market:delete")},
        "manumission:free": given(community_id=Pick(TOWN), share_pct=50, path="law"),
        **{name: Lever(values={"manumission_id": Newest("manumission")}, setup=freed_row) for name in ("manumission:edit", "manumission:delete")},
    }
)


async def empty_seat(session: AsyncSession) -> int:
    realm = await canon(session, EntityType.POLITY, 0)
    assert realm is not None
    seat = await session.scalar(
        select(OfficeRow.id).where(OfficeRow.polity_entity_id == realm, OfficeRow.kind == OfficeKind.CHANCELLOR, OfficeRow.holder_entity_id.is_(None)).limit(1)
    )
    if seat is None:
        office = OfficeRow(polity_entity_id=realm, kind=OfficeKind.CHANCELLOR, holder_entity_id=None, powers=[], locked=[])
        session.add(office)
        await session.flush()
        seat = office.id
    buyer = await canon(session, EntityType.MORTAL, 0)
    assert buyer is not None
    profile = await session.get(MortalProfileRow, buyer)
    if profile is None:
        session.add(MortalProfileRow(entity_id=buyer, wealth=100, locked=[]))
    else:
        profile.wealth = 100
    await session.flush()
    return int(seat)


async def seat_ready(session: AsyncSession) -> None:
    await empty_seat(session)


SEAT = Computed(empty_seat)
BOUGHT = Where("venal_offices", "office_id")
RULE = ("regime:set", {"polity_id": Pick(REALM)})
CIRCLE = ("coalition:enrol", {"polity_id": Pick(REALM), "mortal_id": Pick(MORTAL)})
TIE = ("patronage:bind", {"patron_id": Pick(MORTAL, 1), "client_id": Pick(MORTAL)})
SALE = ("venal_office:sell", {"office_id": SEAT, "buyer_id": Pick(MORTAL), "price": 10})
POWER = ("power_base:set", {"mortal_id": Pick(MORTAL), "polity_id": Pick(REALM), "threat": 40})
SEGMENT = ("kin_segment:set", {"house_id": Pick(EntityType.HOUSE), "level": "clan", "tribe_id": Pick(PEOPLE)})
DESIGN = (
    "breeding:create",
    {"holder_id": Pick(EntityType.HOUSE), "house_id": Pick(EntityType.HOUSE), "name": "The Long Match", "claim_polity_id": Pick(REALM)},
)
EXAMS = ("examination:set", {"polity_id": Pick(REALM)})
SITTING = ("examination:sit", {"polity_id": Pick(REALM)})
DEGREE = ("credential:grant", {"mortal_id": Pick(MORTAL), "kind": "master", "granter_id": Pick(REALM), "skill": "lore"})
FREEDOM = ("academic_freedom:set", {"structure_id": Pick(EntityType.STRUCTURE), "level": 40})
SCHOOL = ("school:found", {"founder_id": Pick(MORTAL), "name": "The First School"})
DISCIPLE = ("disciple:admit", {"school_id": Newest("school_lineage"), "mortal_id": Pick(MORTAL, 1), "master_id": Pick(MORTAL)})
REGIME_EDITS: Mapping[str, Mapping[str, Any]] = {
    "regime:edit": {
        "selectorate": "council",
        "selectorate_size": 100,
        "coalition_size": 20,
        "coalition_loyalty": 60,
        "public_share": 60,
        "traditional": 50,
        "charismatic": 30,
        "rational": 20,
        "founder_entity_id": Pick(MORTAL),
        "routinisation": "dynasty",
        "horizon": 70,
        "extraction": 90,
        "institutions": 40,
        "leadership": "ascribed",
        "rotation": True,
        "parallel_guard": True,
        "loyalty_promotion": True,
        "hostages": True,
    },
    "coalition:edit": {"reward": 30, "loyalty": 70},
    "patronage:edit": {"role": "official", "strength": 55},
    "venal_office:edit": {"price": 50, "buyer_entity_id": Pick(MORTAL), "sinecure": True, "recouped": 10},
    "power_base:edit": {"holdings": 2, "troops": 3, "offices": 1, "wealth": 20, "popularity": 30, "threat": 45, "stance": "defiant"},
    "kin_segment:edit": {"level": "tribe", "tribe_entity_id": Pick(PEOPLE), "backs_entity_id": Pick(EntityType.HOUSE, 1)},
    "breeding:edit": {
        "locus": "height",
        "allele": "tall",
        "target_share": 50,
        "claim_polity_id": Pick(REALM),
        "matches": 1,
        "love_matches": 1,
        "barren": 1,
        "concealed": 1,
    },
    "examination:edit": {"interval": 3, "quota": 30, "pass_mark": 60, "demand": 20, "last_epoch": 0},
    "exam_sitting:edit": {"candidates": 40, "passed": 10, "mark": 55},
    "credential:edit": {"kind": "doctor", "granter_node_id": Pick(REALM), "skill": "law"},
    "academic_freedom:edit": {"level": 30, "orthodoxy_node_id": Pick(REALM), "suppressed": True},
    "school:edit": {"name": "The Second School", "founder_entity_id": Pick(MORTAL), "persecuted": True},
    "disciple:edit": {"master_entity_id": Pick(MORTAL), "generation": 2},
}
EDITS = {**EDITS, **REGIME_EDITS}
LEVERS.update(
    {
        "regime:set": given(polity_id=Pick(REALM)),
        **{name: after(RULE, polity_id=Pick(REALM)) for name in ("regime:edit", "regime:delete")},
        "coalition:enrol": given(polity_id=Pick(REALM), mortal_id=Pick(MORTAL)),
        **{name: after(CIRCLE, polity_id=Pick(REALM), mortal_id=Pick(MORTAL)) for name in ("coalition:edit", "coalition:purge", "coalition:delete")},
        "patronage:bind": given(patron_id=Pick(MORTAL, 1), client_id=Pick(MORTAL)),
        **{name: after(TIE, tie_id=Newest("patronage_tie")) for name in ("patronage:edit", "patronage:delete")},
        "venal_office:sell": Lever(values={"office_id": SEAT, "buyer_id": Pick(MORTAL), "price": 10}, setup=seat_ready),
        "venal_office:sinecure": Lever(values={"office_id": SEAT, "holder_id": Pick(MORTAL)}, setup=seat_ready),
        **{name: setup_then(seat_ready, SALE, office_id=BOUGHT) for name in ("venal_office:edit", "venal_office:delete")},
        "power_base:measure": given(polity_id=Pick(REALM)),
        "power_base:set": given(mortal_id=Pick(MORTAL), polity_id=Pick(REALM), threat=40),
        **{name: after(POWER, mortal_id=Pick(MORTAL)) for name in ("power_base:edit", "power_base:delete")},
        "kin_segment:set": given(house_id=Pick(EntityType.HOUSE), level="clan", tribe_id=Pick(PEOPLE)),
        **{name: after(SEGMENT, house_id=Pick(EntityType.HOUSE)) for name in ("kin_segment:edit", "kin_segment:delete")},
        "breeding:create": given(holder_id=Pick(EntityType.HOUSE), house_id=Pick(EntityType.HOUSE), name="The Long Match", claim_polity_id=Pick(REALM)),
        **{name: after(DESIGN, plan_id=Where("breeding_plans", "plan_id")) for name in ("breeding:edit", "breeding:delete")},
        "examination:set": given(polity_id=Pick(REALM)),
        "examination:sit": given(polity_id=Pick(REALM)),
        **{name: after(EXAMS, polity_id=Pick(REALM)) for name in ("examination:edit", "examination:delete")},
        **{name: after(SITTING, sitting_id=Newest("exam_sitting")) for name in ("exam_sitting:edit", "exam_sitting:delete")},
        "credential:grant": given(mortal_id=Pick(MORTAL), kind="master", granter_id=Pick(REALM), skill="lore"),
        **{name: after(DEGREE, credential_id=Newest("credential")) for name in ("credential:edit", "credential:delete")},
        "academic_freedom:set": given(structure_id=Pick(EntityType.STRUCTURE), level=40),
        **{name: after(FREEDOM, structure_id=Pick(EntityType.STRUCTURE)) for name in ("academic_freedom:edit", "academic_freedom:delete")},
        "school:found": given(founder_id=Pick(MORTAL), name="The First School"),
        **{name: after(SCHOOL, school_id=Newest("school_lineage")) for name in ("school:edit", "school:delete")},
        "disciple:admit": after(SCHOOL, school_id=Newest("school_lineage"), mortal_id=Pick(MORTAL, 1), master_id=Pick(MORTAL)),
        **{name: after(SCHOOL, DISCIPLE, school_id=Newest("school_lineage"), mortal_id=Pick(MORTAL, 1)) for name in ("disciple:edit", "disciple:delete")},
    }
)


async def free_workshop(session: AsyncSession) -> int:
    town = await canon(session, EntityType.SETTLEMENT, 0)
    assert town is not None
    branded = select(BrandRow.workshop_id)
    found = await session.scalar(
        select(WorkshopRow.id).where(WorkshopRow.community_entity_id == town, WorkshopRow.id.not_in(branded)).order_by(WorkshopRow.id).limit(1)
    )
    if found is not None:
        return int(found)
    taken = set(await session.scalars(select(WorkshopRow.kind).where(WorkshopRow.community_entity_id == town)))
    kind = next(item for item in WorkshopKind if item not in taken)
    row = WorkshopRow(community_entity_id=town, kind=kind, level=2, built_epoch=0)
    session.add(row)
    await session.flush()
    return row.id


async def open_land(session: AsyncSession) -> int:
    woods = select(CommonsRow.region_entity_id).where(CommonsRow.kind == CommonsKind.WOODS)
    found = await session.scalar(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.REGION, EntityRow.id.not_in(woods)).order_by(EntityRow.id).limit(1)
    )
    assert found is not None
    return int(found)


LAND = EntityType.REGION
WORKSHOP = Computed(free_workshop)
OPEN_LAND = Computed(open_land)
RING = ("land_ring:set", {"region_id": Pick(LAND), "ring": "grain", "market_id": Pick(TOWN)})
CENTRAL = ("central_place:set", {"settlement_id": Pick(TOWN)})
NUTRIENT = ("soil_nutrient:set", {"region_id": Pick(LAND), "nutrient": "fixed", "stock": 40})
PRESSURE = ("intensification:set", {"region_id": Pick(LAND)})
PLANTING = ("perennial:plant", {"region_id": Pick(LAND), "kind": "orchard", "owner_id": Pick(MORTAL)})
COMMON = ("commons:create", {"region_id": OPEN_LAND, "kind": "woods", "steward_id": Pick(TOWN)})
RESERVE = ("game_reserve:declare", {"region_id": Pick(LAND), "holder_id": Pick(MORTAL), "strictness": 60})
HUNGER = ("famine_lore:set", {"people_id": Pick(PEOPLE)})
WORK = ("preparedness:build", {"settlement_id": Pick(TOWN), "kind": "levee", "level": 2})
AID = ("relief:send", {"giver_id": Pick(REALM), "settlement_id": Pick(TOWN), "kind": "goods", "amount": 50})
REBUILD = ("reconstruction:begin", {"settlement_id": Pick(TOWN), "cause": "fire", "plan": "planned"})
KEYSTONE = (
    "keystone:designate",
    {
        "world_id": Pick("world"),
        "name": "The First Yield",
        "use": "rite",
        "producer_id": Pick(EntityType.SPECIES),
        "source_region_id": Pick(LAND),
        "cult_id": Pick(EntityType.CULT),
    },
)
BRAND = ("brand:found", {"workshop_id": WORKSHOP, "name": "The First Brand"})
AGRARIAN_EDITS: Mapping[str, Mapping[str, Any]] = {
    "land_ring:edit": {"market_entity_id": Pick(TOWN), "ring": "ranching", "distance": 200, "by_water": True, "gap": 30},
    "central_place:edit": {"catchment": 9000, "served_by_entity_id": Pick(TOWN, 1), "centrality": 80},
    "soil_nutrient:edit": {"stock": 35, "trend": -2},
    "intensification:edit": {"pressure": 120, "intensity": 50, "research_boost": 30},
    "perennial:edit": {
        "kind": "vineyard",
        "species_entity_id": Pick(EntityType.SPECIES),
        "owner_node_id": Pick(MORTAL),
        "area": 8,
        "maturity": 60,
        "mature_epochs": 4,
        "condition": 80,
    },
    "commons:edit": {
        "kind": "woods",
        "rule": "council",
        "condition": 50,
        "use": 70,
        "steward_entity_id": Pick(TOWN),
        "encloser_node_id": Pick(MORTAL),
        "dispossessed": 3,
    },
    "game_reserve:edit": {"holder_node_id": Pick(MORTAL, 1), "species_entity_id": Pick(EntityType.SPECIES), "strictness": 40, "poaching": 20, "resentment": 10},
    "famine_lore:edit": {"memory": 60, "famine_foods": False, "storage": 30},
    "preparedness:edit": {"level": 3, "condition": 70, "averted": 1},
    "relief:edit": {"kind": "labour", "amount": 30, "god_node_id": Pick("son"), "refused": True},
    "reconstruction:edit": {
        "cause": "flood",
        "plan": "opportunistic",
        "cost": 400,
        "paid": 100,
        "progress": 40,
        "planner_entity_id": Pick(MORTAL),
        "seized_by_node_id": Pick(MORTAL, 1),
        "seized": 5,
    },
    "keystone:edit": {
        "name": "The Second Yield",
        "producer_entity_id": Pick(EntityType.SPECIES),
        "source_region_entity_id": Pick(LAND),
        "commodity": "herbs",
        "use": "navigation",
        "cult_entity_id": Pick(EntityType.CULT),
        "controller_entity_id": Pick(REALM),
        "harvest": 30,
        "supply": 40,
        "price": 150,
    },
    "brand:edit": {"name": "The Second Brand", "owner_node_id": Pick(MORTAL), "reputation": 50, "quality": 70, "renowned": 2, "counterfeits": 10},
}
EDITS = {**EDITS, **AGRARIAN_EDITS}
LEVERS.update(
    {
        "land_ring:set": given(region_id=Pick(LAND), ring="grain", market_id=Pick(TOWN)),
        **{name: after(RING, region_id=Pick(LAND)) for name in ("land_ring:edit", "land_ring:delete")},
        "central_place:set": given(settlement_id=Pick(TOWN)),
        **{name: after(CENTRAL, settlement_id=Pick(TOWN)) for name in ("central_place:edit", "central_place:delete")},
        "soil_nutrient:set": given(region_id=Pick(LAND), nutrient="fixed", stock=40),
        **{name: after(NUTRIENT, region_id=Pick(LAND), nutrient="fixed") for name in ("soil_nutrient:edit", "soil_nutrient:delete")},
        "intensification:set": given(region_id=Pick(LAND)),
        **{name: after(PRESSURE, region_id=Pick(LAND)) for name in ("intensification:edit", "intensification:delete")},
        "perennial:plant": given(region_id=Pick(LAND), kind="orchard", owner_id=Pick(MORTAL)),
        **{name: after(PLANTING, perennial_id=Newest("perennial")) for name in ("perennial:edit", "perennial:fell", "perennial:delete")},
        "commons:create": given(region_id=OPEN_LAND, kind="woods", steward_id=Pick(TOWN)),
        **{name: after(COMMON, commons_id=Newest("commons")) for name in ("commons:edit", "commons:delete")},
        "commons:enclose": after(COMMON, commons_id=Newest("commons"), encloser_id=Pick(MORTAL)),
        "game_reserve:declare": given(region_id=Pick(LAND), holder_id=Pick(MORTAL), strictness=60),
        **{name: after(RESERVE, reserve_id=Newest("game_reserve")) for name in ("game_reserve:edit", "game_reserve:delete")},
        "famine_lore:set": given(people_id=Pick(PEOPLE)),
        **{name: after(HUNGER, people_id=Pick(PEOPLE)) for name in ("famine_lore:edit", "famine_lore:delete")},
        "preparedness:build": given(settlement_id=Pick(TOWN), kind="levee", level=2),
        **{name: after(WORK, settlement_id=Pick(TOWN), kind="levee") for name in ("preparedness:edit", "preparedness:delete")},
        "relief:send": given(giver_id=Pick(REALM), settlement_id=Pick(TOWN), kind="goods", amount=50),
        **{name: after(AID, aid_id=Newest("relief_aid")) for name in ("relief:edit", "relief:delete")},
        "reconstruction:begin": given(settlement_id=Pick(TOWN), cause="fire", plan="planned"),
        **{name: after(REBUILD, rebuild_id=Newest("reconstruction")) for name in ("reconstruction:edit", "reconstruction:finish", "reconstruction:delete")},
        "keystone:designate": given(
            world_id=Pick("world"),
            name="The First Yield",
            use="rite",
            producer_id=Pick(EntityType.SPECIES),
            source_region_id=Pick(LAND),
            cult_id=Pick(EntityType.CULT),
        ),
        **{name: after(KEYSTONE, keystone_id=Newest("keystone_resource")) for name in ("keystone:edit", "keystone:delete")},
        "brand:found": Lever(values={"workshop_id": WORKSHOP, "name": "The First Brand"}),
        **{name: after(BRAND, brand_id=Newest("brand")) for name in ("brand:edit", "brand:delete")},
    }
)


VTYPE = ("design:draw", {"owner_id": Pick(REALM), "frame": "wagon"})
VTYPE_ID = Newest("design")
SECTION_SET = ("design_section:set", {"design_id": VTYPE_ID, "section": "tracks", "values": {"share": 10}})
MOUNT_ADD = ("design_mount:add", {"design_id": VTYPE_ID, "mount": "deck"})
LAST_TECHNIQUE = "drainage"
DESIGN_TECHNIQUE = ("design_technique:add", {"design_id": VTYPE_ID, "technique": LAST_TECHNIQUE})
GROUP = ("vehicle_group:create", {"holder_id": Pick(REALM), "design_id": VTYPE_ID, "count": 4})
GROUP_ID = Newest("vehicle_group")
GROUP_SECTION = ("vehicle_group_section:set", {"group_id": GROUP_ID, "section": "wheels", "values": {"damaged": 1}})
VESSEL_SECTION = ("vessel_section:set", {"vessel_id": VESSEL, "section": "hull", "values": {"condition": 60}})
MODEL = ("equipment_model:create", {"origin_id": Pick(REALM), "family": "spear"})
MODEL_ID = Newest("equipment_model")
STORE = ("equipment_store:set", {"holder_id": Pick(TOWN), "model_id": MODEL_ID, "count": 20})
HOST = ("army:raise", {"community_id": Pick(TOWN), "size": 200})
STACK_ID = Newest("army_unit")
CARRIED = ("army_equipment:set", {"unit_id": STACK_ID, "model_id": MODEL_ID, "count": 50})
UNIT_TYPE = ("unit_type:create", {"owner_id": Pick(REALM), "role": "line_infantry"})
UNIT_TYPE_ID = Newest("unit_design")
LOADOUT = ("unit_loadout:set", {"design_id": UNIT_TYPE_ID, "model_id": MODEL_ID, "count": 2})
UNIT_TECHNIQUE = ("unit_technique:add", {"design_id": UNIT_TYPE_ID, "technique": LAST_TECHNIQUE})
GRANARY = Computed(town_granary)
BEACON_WORK = Computed(town_beacon)
STRUCTURE_SECTION = ("structure_section:edit", {"structure_id": GRANARY, "section": "roof", "values": {"condition": 70}})
TEMPLE_TYPE = ("structure_design:create", {"world_id": Pick("world"), "values": {"name": "Long Hall", "base_kind": "temple"}})
TEMPLE_TYPE_ID = Newest("structure_design")
TYPE_SECTION = ("structure_design_section:set", {"design_id": TEMPLE_TYPE_ID, "section": "dome", "values": {"share": 20}})
MEGA = ("megastructure:edit", {"structure_id": BEACON_WORK, "values": {"output": 40}})
DISH = ("dish:create", {"origin_id": Pick(PEOPLE), "method": "baked", "course": "festive", "ingredients": ["grain", "eggs"]})
DISH_ID = Newest("dish")
COOKED = ("community_dish:set", {"community_id": Pick(TOWN), "dish_id": DISH_ID, "popularity": 70})
MADE_KIND_EDITS: Mapping[str, Mapping[str, Any]] = {
    "design_section:set": {"criticality": "major", "share": 20, "exposure": 30, "armour": 40, "hazard": "fire", "size": 4, "quality": 60},
    "design_mount:add": {"count": 2, "arc": "forward", "section": "chassis"},
    "design_mount:edit": {"count": 3, "arc": "side", "slot": 1},
    "vehicle_group:edit": {"count": 5, "crewed": 3, "condition": 80, "fuel": 50, "status": "laid_up"},
    "vehicle_group_section:set": {"damaged": 2, "disabled": 1, "destroyed": 0},
    "vessel_section:set": {"state": "damaged", "condition": 60},
    "equipment_model:edit": {"name": "The Second Spear", "quality": 70, "damage": 30, "piercing": 20, "reach": 1, "weight": 3, "cost": 5},
    "unit_type:edit": {"name": "The Watch", "melee": 50, "defence": 50, "discipline": 60, "formation": "column", "doctrine": "shock", "training_epochs": 2},
    "structure_section:edit": {"condition": 60, "role": "storage", "criticality": "major", "share": 30, "exposure": 40, "flammability": 50},
    "structure_design_section:set": {"criticality": "critical", "share": 25, "material": "stone"},
    "megastructure:edit": {"output": 60, "target_orbit": 2},
    "dish:edit": {
        "name": "Second Loaf",
        "nourishment": 50,
        "delight": 40,
        "keeps": 2,
        "prestige": 20,
        "course": "side",
        "category": "feast",
        "prep_skill": 30,
        "sweet": 40,
        "smoky": 10,
    },
    "community_dish:edit": {"popularity": 70, "cooked": 3, "short_epochs": 1},
    "dish_step:edit": {"method": "aged", "duration": 4},
}
EDITS = {**EDITS, **MADE_KIND_EDITS}
LEVERS.update(
    {
        "mortal:attraction": given(mortal_id=Pick(MORTAL), drawn_to=["female", "other"], attraction=60),
        "design_section:set": after(VTYPE, design_id=VTYPE_ID, section="tracks"),
        "design_section:delete": after(VTYPE, SECTION_SET, design_id=VTYPE_ID, section="tracks"),
        "design_mount:add": after(VTYPE, design_id=VTYPE_ID, mount="deck"),
        **{name: after(VTYPE, MOUNT_ADD, record_id=Newest("design_mount")) for name in ("design_mount:edit", "design_mount:delete")},
        "design_technique:add": after(VTYPE, design_id=VTYPE_ID, technique=LAST_TECHNIQUE),
        "design_technique:delete": after(VTYPE, DESIGN_TECHNIQUE, design_id=VTYPE_ID, technique=LAST_TECHNIQUE),
        "vehicle_group:create": after(VTYPE, holder_id=Pick(REALM), design_id=VTYPE_ID, count=4, crewed=2),
        **{name: after(VTYPE, GROUP, record_id=GROUP_ID) for name in ("vehicle_group:edit", "vehicle_group:delete")},
        "vehicle_group:move": after(VTYPE, GROUP, group_id=GROUP_ID, holder_id=Pick(TOWN), count=2),
        "vehicle_group:repair": after(VTYPE, GROUP, GROUP_SECTION, group_id=GROUP_ID, points=20),
        "vehicle_group_section:set": after(VTYPE, GROUP, group_id=GROUP_ID, section="wheels"),
        "vehicle_group_section:delete": after(VTYPE, GROUP, GROUP_SECTION, group_id=GROUP_ID, section="wheels"),
        "vessel_section:set": given(vessel_id=VESSEL, section="hull"),
        "vessel_section:delete": after(VESSEL_SECTION, vessel_id=VESSEL, section="hull"),
        "equipment_model:create": given(origin_id=Pick(REALM), family="spear", quality=60),
        **{name: after(MODEL, record_id=MODEL_ID) for name in ("equipment_model:edit", "equipment_model:delete")},
        "equipment_store:set": after(MODEL, holder_id=Pick(TOWN), model_id=MODEL_ID, count=20),
        "equipment_store:delete": after(MODEL, STORE, holder_id=Pick(TOWN), model_id=MODEL_ID),
        "army_equipment:set": after(HOST, MODEL, unit_id=STACK_ID, model_id=MODEL_ID, count=50, condition=90),
        "army_equipment:delete": after(HOST, MODEL, CARRIED, unit_id=STACK_ID, model_id=MODEL_ID),
        "unit_type:create": given(owner_id=Pick(REALM), role="line_infantry", name="The Line"),
        **{name: after(UNIT_TYPE, record_id=UNIT_TYPE_ID) for name in ("unit_type:edit", "unit_type:delete")},
        "unit_loadout:set": after(UNIT_TYPE, MODEL, design_id=UNIT_TYPE_ID, model_id=MODEL_ID, count=2),
        "unit_loadout:delete": after(UNIT_TYPE, MODEL, LOADOUT, design_id=UNIT_TYPE_ID, model_id=MODEL_ID),
        "unit_technique:add": after(UNIT_TYPE, design_id=UNIT_TYPE_ID, technique=LAST_TECHNIQUE),
        "unit_technique:delete": after(UNIT_TYPE, UNIT_TECHNIQUE, design_id=UNIT_TYPE_ID, technique=LAST_TECHNIQUE),
        "structure_section:edit": given(structure_id=GRANARY, section="roof"),
        **{name: given(structure_id=GRANARY, section="stores") for name in ("structure_section:repair", "structure_section:strike")},
        "structure_section:delete": after(STRUCTURE_SECTION, structure_id=GRANARY, section="roof"),
        "structure_design_section:set": after(TEMPLE_TYPE, design_id=TEMPLE_TYPE_ID, section="dome"),
        "structure_design_section:delete": after(TEMPLE_TYPE, TYPE_SECTION, design_id=TEMPLE_TYPE_ID, section="dome"),
        "megastructure:edit": given(structure_id=BEACON_WORK),
        "megastructure:delete": after(MEGA, structure_id=BEACON_WORK),
        "dish:create": given(origin_id=Pick(PEOPLE), method="baked", course="festive", ingredients=["grain", "eggs"]),
        **{name: after(DISH, record_id=DISH_ID) for name in ("dish:edit", "dish:delete")},
        "dish_ingredient:set": after(DISH, dish_id=DISH_ID, commodity="herbs", share=20, role="seasoning"),
        "dish_ingredient:delete": after(DISH, dish_id=DISH_ID, commodity="grain"),
        "dish_step:set": after(DISH, dish_id=DISH_ID, step=2, method="aged", duration=6),
        **{name: after(DISH, record_id=Newest("dish_step")) for name in ("dish_step:edit", "dish_step:delete")},
        "community_dish:set": after(DISH, community_id=Pick(TOWN), dish_id=DISH_ID, popularity=70),
        **{name: after(DISH, COOKED, community_id=Pick(TOWN), dish_id=DISH_ID) for name in ("community_dish:edit", "community_dish:delete")},
    }
)


async def hidden_route(session: AsyncSession) -> None:
    route = await session.scalar(select(RouteRow).order_by(RouteRow.id).limit(1))
    assert route is not None
    route.known = False


BRANCH_LEVERS: Mapping[tuple[str, str], Lever] = {
    ("intervene", "disaster"): given(entity_id=Pick(TOWN), disaster="flood"),
    ("intervene", "teach_knowledge"): after(
        ("knowledge:set", {"entity_id": Pick(EntityType.PEOPLE), "knowledge_id": Pick(EntityType.KNOWLEDGE), "known": False}),
        entity_id=Pick(EntityType.PEOPLE),
        knowledge_id=Pick(EntityType.KNOWLEDGE),
    ),
    ("route", "reveal"): Lever(values={"route_id": Pick("route")}, setup=hidden_route),
    ("route", "reopen"): after(("route", {"route_id": Pick("route"), "action": "sever", "duration": 3}), route_id=Pick("route")),
}


ART_FORM = ("lore:create", {"entity_type": "art_form", "name": "Reed Song", "world_id": Pick("world"), "values": {"discipline": "musical"}})
LORE_LEVERS: Mapping[str, Lever] = {
    kind.value: after(step, entity_id=Newest(kind))
    for kind, step in (
        (EntityType.ART_FORM, ART_FORM),
        (EntityType.ARTWORK, ARTWORK),
        (EntityType.IDEOLOGY, IDEOLOGY),
        (EntityType.PROPHECY, PROPHECY),
        (EntityType.RITE, RITE),
        (EntityType.THEORY, THEORY),
    )
}


async def supply_flow(session: AsyncSession) -> None:
    army = await session.scalar(select(ArmyRow).order_by(ArmyRow.entity_id.desc()).limit(1))
    assert army is not None
    session.add(
        SupplyFlowRow(owner_entity_id=army.owner_entity_id, army_entity_id=army.entity_id, produced=40, shipped=30, lost=5, delivered=25, need=30, locked=[])
    )
    await session.flush()


ARMY_UP = ("army:raise", {"community_id": Pick(TOWN), "size": 200, "war_id": Newest("war")})
ECHELON = ("echelon:create", {"owner_id": Pick(TOWN), "level": "brigade", "name": "Brigade 1", "army_id": Newest(EntityType.ARMY)})
DEPOT = ("depot:create", {"owner_id": Pick(TOWN), "region_id": Pick(LAND)})
TRANSPORT = ("transport:create", {"owner_id": Pick(TOWN), "kind": "animal_carts", "count": 5})
THEATRE = ("theatre:set", {"owner_id": Pick(TOWN), "war_id": Newest("war"), "priority": 60})
OPERATION = ("army_operation:set", {"army_id": Newest(EntityType.ARMY)})
SHIP = ("ship_state:set", {"vessel_id": VESSEL})
CREW = ("ship_crew:set", {"vessel_id": VESSEL, "station": "gunners"})
ADMIRALTY = ("admiralty:set", {"polity_id": Pick(REALM)})
EXPEDITION = ("expedition:create", {"leader_id": Pick(MORTAL), "target_id": Pick(LAND)})
QUIRK = ("quirk:create", {"mortal_id": Pick(MORTAL), "kind": "hardy"})
OPERATIONS_EDITS: Mapping[str, Mapping[str, Any]] = {
    "echelon:edit": {
        "name": "Brigade 2",
        "level": "division",
        "commander_entity_id": Pick(MORTAL),
        "hq_region_entity_id": Pick(LAND),
        "staff": 55,
        "command_range": 3,
        "command_points": 6,
        "points_spent": 1,
        "order": "hold",
        "in_range": False,
    },
    "depot:edit": {"region_entity_id": Pick(LAND), "supplies": 120, "capacity": 400, "field": True, "cut": True},
    "transport:edit": {"kind": "pack_animals", "count": 12, "capacity": 6, "condition": 70},
    "supply_flow:edit": {"produced": 50, "shipped": 40, "lost": 4, "delivered": 36, "need": 45, "throughput": 60},
    "army_operation:edit": {
        "offensive_seasons": 3,
        "need": 40,
        "delivered": 12,
        "organisation": 35,
        "culminated": True,
        "pause_seasons": 2,
        "foresight": 1,
        "standing": True,
    },
    "theatre:edit": {
        "front_region_entity_id": Pick(LAND),
        "marshal_entity_id": Pick(MORTAL),
        "priority": 70,
        "believed_threat": 40,
        "true_threat": 60,
        "reserves": 80,
        "levies": 30,
        "transport": 4,
        "misjudged": True,
    },
    "ship_state:edit": {
        "heading": 2,
        "wind_from": 6,
        "point_of_sail": "running",
        "tacks": 1,
        "shot": "chain",
        "leak": 20,
        "fire": 10,
        "magazine": True,
        "rate_of_fire": 60,
        "rower_fatigue": 5,
        "raked": 1,
        "struck": False,
        "prize_of_entity_id": Pick(TOWN),
        "prize_crew": 4,
        "prize_money": 90,
    },
    "ship_crew:edit": {"count": 30, "skill": 65},
    "admiralty:edit": {
        "admiral_entity_id": Pick(MORTAL),
        "budget_share": 40,
        "requested": 45,
        "influence": 55,
        "tonnage": 300,
        "limit_tonnage": 400,
        "concealed": 20,
        "commissioned": 3,
    },
    "expedition:edit": {
        "name": "The Second Venture",
        "leader_entity_id": Pick(MORTAL),
        "target_entity_id": Pick(LAND),
        "ground": "wilds",
        "status": "camped",
        "legs_done": 1,
        "legs_total": 5,
        "provisions": 8,
        "light": 3,
        "tools": 1,
        "medicine": 2,
        "darkness": 20,
        "danger": 30,
        "found": 1,
    },
    "expedition_member:edit": {"role": "scout", "stress": 80, "resolve": "focused", "cold": 10, "wet": 5, "hunger": 15, "fatigue": 20, "fallen": False},
    "expedition_log:edit": {"event": "camp", "leg": 1, "provisions_used": 2, "light_used": 1, "stress": 10, "resolve": "steady", "quirk": "hardy"},
    "quirk:edit": {"kind": "keen_eyed", "source_entity_id": Pick(LAND), "strength": 2},
}
EDITS = {**EDITS, **OPERATIONS_EDITS}
LEVERS.update(
    {
        "echelon:create": after(WAR, ARMY_UP, owner_id=Pick(TOWN), level="brigade", name="Brigade 1", army_id=Newest(EntityType.ARMY)),
        **{name: after(WAR, ARMY_UP, ECHELON, echelon_id=Newest("echelon")) for name in ("echelon:edit", "echelon:delete")},
        "echelon:assign": after(WAR, ARMY_UP, ECHELON, stack_id=Newest("army_unit"), echelon_id=Newest("echelon")),
        "depot:create": given(owner_id=Pick(TOWN), region_id=Pick(LAND)),
        **{name: after(DEPOT, depot_id=Newest("depot")) for name in ("depot:edit", "depot:delete")},
        "transport:create": given(owner_id=Pick(TOWN), kind="animal_carts", count=5),
        **{name: after(TRANSPORT, transport_id=Newest("transport_asset")) for name in ("transport:edit", "transport:delete")},
        **{
            name: Lever(values={"flow_id": Newest("supply_flow")}, before=(WAR, ARMY_UP), then=supply_flow)
            for name in ("supply_flow:edit", "supply_flow:delete")
        },
        "army_operation:set": after(WAR, ARMY_UP, army_id=Newest(EntityType.ARMY), culminated=True, pause_seasons=1),
        **{name: after(WAR, ARMY_UP, OPERATION, army_id=Newest(EntityType.ARMY)) for name in ("army_operation:edit", "army_operation:delete")},
        "theatre:set": after(WAR, owner_id=Pick(TOWN), war_id=Newest("war"), priority=60),
        **{name: after(WAR, THEATRE, theatre_id=Newest("theatre")) for name in ("theatre:edit", "theatre:delete")},
        "ship_state:set": given(vessel_id=VESSEL, shot="grape", point_of_sail="close_hauled"),
        **{name: after(SHIP, vessel_id=VESSEL) for name in ("ship_state:edit", "ship_state:delete")},
        "ship_crew:set": given(vessel_id=VESSEL, station="riggers", count=12, skill=50),
        **{name: after(CREW, vessel_id=VESSEL, station="gunners") for name in ("ship_crew:edit", "ship_crew:delete")},
        "admiralty:set": given(polity_id=Pick(REALM), budget_share=35),
        **{name: after(ADMIRALTY, polity_id=Pick(REALM)) for name in ("admiralty:edit", "admiralty:delete")},
        "expedition:create": given(leader_id=Pick(MORTAL), target_id=Pick(LAND), companion_ids=[]),
        **{name: after(EXPEDITION, expedition_id=Newest("expedition")) for name in ("expedition:edit", "expedition:recall", "expedition:delete")},
        "expedition:advance": after(EXPEDITION, expedition_id=Newest("expedition"), legs=1),
        "expedition_member:create": after(EXPEDITION, expedition_id=Newest("expedition"), mortal_id=Pick(MORTAL, 1), role="healer"),
        **{name: after(EXPEDITION, member_id=Newest("expedition_member")) for name in ("expedition_member:edit", "expedition_member:delete")},
        **{name: after(EXPEDITION, log_id=Newest("expedition_log")) for name in ("expedition_log:edit", "expedition_log:delete")},
        "quirk:create": given(mortal_id=Pick(MORTAL), kind="hardy"),
        **{name: after(QUIRK, quirk_id=Newest("quirk")) for name in ("quirk:edit", "quirk:delete")},
    }
)


async def unspirited_place(session: AsyncSession) -> int | None:
    bound = select(GeniusLocusRow.place_entity_id).where(GeniusLocusRow.place_entity_id.is_not(None))
    return await session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.PLACE, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(bound))
        .order_by(EntityRow.id)
        .limit(1)
    )


async def newest_spirit(session: AsyncSession) -> int | None:
    return await session.scalar(select(GeniusLocusRow.spirit_entity_id).order_by(GeniusLocusRow.spirit_entity_id.desc()).limit(1))


async def churched_town(session: AsyncSession) -> None:
    town = await session.scalar(select(EntityRow).where(EntityRow.entity_type == TOWN, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1))
    cult = await session.scalar(
        select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )
    assert town is not None and cult is not None
    cult.location_id = town.id
    doctrine = await session.get(CultDoctrineRow, cult.id)
    if doctrine is None:
        session.add(CultDoctrineRow(cult_entity_id=cult.id, clergy_count=5, locked=[]))
    else:
        doctrine.clergy_count = max(doctrine.clergy_count, 5)
    if await session.get(DoctrineSacramentRow, (cult.id, SacramentKind.BIRTH_BLESSING)) is None:
        session.add(DoctrineSacramentRow(cult_entity_id=cult.id, kind=SacramentKind.BIRTH_BLESSING, protection=SacramentProtection.POSSESSION, locked=[]))
    mortal = await session.scalar(
        select(EntityRow).where(EntityRow.entity_type == MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )
    assert mortal is not None
    mortal.location_id = town.id
    await session.flush()


async def church_town(session: AsyncSession) -> int | None:
    return await session.scalar(
        select(EntityRow.location_id).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )


async def church(session: AsyncSession) -> int | None:
    return await session.scalar(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )


async def unkept_divination(session: AsyncSession) -> str:
    people = await pick(session, EntityType.PEOPLE, 0)
    kept = set(await session.scalars(select(DivinationSystemRow.kind).where(DivinationSystemRow.people_entity_id == people)))
    return next(kind.value for kind in DivinationKind if kind not in kept)


async def drained_sons(session: AsyncSession) -> None:
    for son in await session.scalars(select(SonRow)):
        son.essence = 0
    await session.flush()


FREE_PLACE = Computed(unspirited_place)
NEW_SPIRIT = Computed(newest_spirit)
CHURCH_TOWN = Computed(church_town)
CHURCH = Computed(church)
RULED = Computed(ruled_realm)
SPIRIT_UP = ("genius_locus:create", {"place_id": FREE_PLACE})
OFFICE_UP = ("spirit_office:set", {"spirit_id": NEW_SPIRIT, "rank": "local"})
PETITION_UP = ("petition:create", {"petitioner_id": Pick(MORTAL), "office_id": NEW_SPIRIT, "kind": "healing"})
MYSTIC_UP = ("mystic:create", {"mortal_id": Pick(MORTAL)})
MOVEMENT_UP = ("millenarian:create", {"town_id": Pick(TOWN)})
CRISIS_UP = ("theodicy:create", {"town_id": CHURCH_TOWN, "cause": "famine", "suffering": 60})
TEACHING_UP = ("doctrine_sacrament:set", {"cult_id": CHURCH, "kind": "initiation", "protection": "unrest", "strength": 55})
SACRAMENT_UP = ("sacrament:create", {"mortal_id": Pick(MORTAL), "kind": "birth_blessing"})
AFTERLIFE_UP = ("doctrine_afterlife:set", {"cult_id": CHURCH, "model": "rebirth"})
CLIMATE_UP = ("faith_climate:set", {"town_id": Pick(TOWN)})
SYSTEM_UP = ("divination_system:create", {"people_id": Pick(EntityType.PEOPLE), "kind": Computed(unkept_divination)})
READING_UP = ("divination:create", {"realm_id": RULED, "question": "harvest", "system_id": Newest("divination_system")})
FORESIGHT_UP = ("foresight:create", {"seer_id": Pick(MORTAL), "subject_id": Pick(MORTAL, 1), "predicate": "dies", "certainty": 60})
MODEL_UP = ("forecast_model:create", {"order_id": Pick(EntityType.FACTION), "realm_id": Pick(REALM)})
FEEDING_UP = ("god_feeding:set", {"god_id": Pick("son"), "emotion": "joy", "weight": 40})
SACRED_EDITS: Mapping[str, Mapping[str, Any]] = {
    "genius_locus:edit": {
        "place_entity_id": Pick(EntityType.PLACE),
        "community_entity_id": Pick(TOWN),
        "kind": "spring",
        "temperament": 70,
        "contentment": 40,
        "offerings": 6,
        "owed": 2,
        "favour": 30,
        "offended": "pollution",
    },
    "spirit_office:edit": {
        "rank": "city",
        "superior_spirit_id": None,
        "overseer_node_id": Pick("son"),
        "jurisdiction_entity_id": Pick(TOWN),
        "merit": 12,
        "corruption": 25,
        "resolved": 3,
        "neglected": 1,
        "dismissed": False,
    },
    "petition:edit": {"kind": "harvest", "bribe": 3, "status": "delayed", "due_epoch": 9, "defendant_spirit_id": None, "appealed_to_id": None},
    "mystic:edit": {
        "state": "revered",
        "visions": 4,
        "genuine_visions": 1,
        "followers": 30,
        "answered_by_node_id": Pick("son"),
        "cult_entity_id": CHURCH,
        "founded_entity_id": None,
        "reverence": 60,
        "persecution": 10,
    },
    "vision:edit": {"kind": "union", "sender_node_id": Pick("son"), "genuine": True, "awe": 70},
    "millenarian:edit": {
        "cult_entity_id": CHURCH,
        "prophet_entity_id": Pick(MORTAL),
        "prophecy_entity_id": None,
        "stage": "vigil",
        "end_epoch": 12,
        "members": 40,
        "conviction": 80,
        "given_up": 5,
        "idle_share": 30,
        "attacks": 1,
        "dates_set": 2,
        "sect_entity_id": None,
    },
    "theodicy:edit": {
        "god_node_id": Pick("son"),
        "cause": "defeat",
        "suffering": 70,
        "answered": False,
        "resolution": "argued",
        "theologian_entity_id": Pick(MORTAL),
    },
    "doctrine_sacrament:edit": {"protection": "routing", "strength": 70},
    "sacrament:edit": {"kind": "marriage", "cult_entity_id": CHURCH, "priest_entity_id": Pick(MORTAL, 1), "missed": True},
    "doctrine_afterlife:edit": {"model": "realm_by_death", "aligned": True, "aligned_by_node_id": Pick("son"), "shocks": 2, "testimonies": 1, "doubt": 20},
    "faith_climate:edit": {
        "piety_drift": -3,
        "literacy_pull": -10,
        "science_pull": -4,
        "prosperity_pull": -2,
        "city_pull": -1,
        "silence_pull": -6,
        "disaster_push": 5,
        "miracle_push": 15,
        "war_push": 10,
        "dominion_push": 8,
        "silent_epochs": 2,
        "godless": False,
    },
    "divination_system:edit": {"kind": "lots", "validity": "seer_gift", "trust": 65, "diviners": 3},
    "divination:edit": {
        "diviner_entity_id": Pick(MORTAL),
        "client_entity_id": Pick(MORTAL, 1),
        "question": "battle",
        "verdict": "auspicious",
        "true_verdict": "inauspicious",
        "heeded": True,
        "swayed_by_node_id": Pick("son"),
    },
    "foresight:edit": {
        "subject_node_id": Pick(MORTAL, 2),
        "predicate": "dies",
        "horizon": 20,
        "due_epoch": 15,
        "certainty": 75,
        "source": "god",
        "status": "pending",
    },
    "forecast_model:edit": {
        "subject_entity_id": Pick(REALM),
        "archive": 9,
        "accuracy": 60,
        "forecast_psi": 40,
        "actual_psi": 45,
        "plan_id": None,
        "disruption": 10,
        "disrupted_by_node_id": Pick("son"),
        "horizon": 6,
    },
    "god_feeding:edit": {"weight": 80},
}
EDITS = {**EDITS, **SACRED_EDITS}
LEVERS.update(
    {
        "bless": Lever(setup=drained_sons),
        "genius_locus:create": given(place_id=FREE_PLACE, kind="grove"),
        **{name: after(SPIRIT_UP, spirit_id=NEW_SPIRIT) for name in ("genius_locus:edit", "genius_locus:delete")},
        "spirit_office:set": after(SPIRIT_UP, spirit_id=NEW_SPIRIT, overseer_id=Pick("son"), jurisdiction_id=Pick(TOWN)),
        **{name: after(SPIRIT_UP, OFFICE_UP, spirit_id=NEW_SPIRIT) for name in ("spirit_office:edit", "spirit_office:delete")},
        "petition:create": after(SPIRIT_UP, petitioner_id=Pick(MORTAL), office_id=NEW_SPIRIT, kind="prosperity", bribe=2),
        **{name: after(SPIRIT_UP, PETITION_UP, petition_id=Newest("petition")) for name in ("petition:edit", "petition:delete")},
        "petition:judge": after(SPIRIT_UP, PETITION_UP, petition_id=Newest("petition"), granted=True),
        "mystic:create": given(mortal_id=Pick(MORTAL), sender_id=Pick("son")),
        **{name: after(MYSTIC_UP, mortal_id=Pick(MORTAL)) for name in ("mystic:edit", "mystic:delete")},
        "vision:create": after(MYSTIC_UP, mystic_id=Pick(MORTAL), sender_id=Pick("son")),
        **{name: after(MYSTIC_UP, vision_id=Newest("vision")) for name in ("vision:edit", "vision:delete")},
        "millenarian:create": given(town_id=Pick(TOWN), prophet_id=Pick(MORTAL)),
        **{name: after(MOVEMENT_UP, movement_id=Newest("millenarian_movement")) for name in ("millenarian:edit", "millenarian:delete")},
        "theodicy:create": setup_then(churched_town, town_id=CHURCH_TOWN, cause="plague", suffering=70),
        **{name: setup_then(churched_town, CRISIS_UP, crisis_id=Newest("theodicy_crisis")) for name in ("theodicy:edit", "theodicy:delete")},
        "theodicy:answer": setup_then(churched_town, CRISIS_UP, crisis_id=Newest("theodicy_crisis"), god_id=Pick("son")),
        "doctrine_sacrament:set": setup_then(churched_town, cult_id=CHURCH, kind="last_rites", protection="routing", strength=65),
        **{
            name: setup_then(churched_town, TEACHING_UP, cult_id=CHURCH, kind="initiation") for name in ("doctrine_sacrament:edit", "doctrine_sacrament:delete")
        },
        "sacrament:create": setup_then(churched_town, mortal_id=Pick(MORTAL), kind="birth_blessing", priest_id=Pick(MORTAL, 1)),
        **{name: setup_then(churched_town, SACRAMENT_UP, sacrament_id=Newest("sacrament")) for name in ("sacrament:edit", "sacrament:delete")},
        "doctrine_afterlife:set": setup_then(churched_town, cult_id=CHURCH, model="realm_of_line"),
        **{name: setup_then(churched_town, AFTERLIFE_UP, cult_id=CHURCH) for name in ("doctrine_afterlife:edit", "doctrine_afterlife:delete")},
        "doctrine_afterlife:align": setup_then(churched_town, AFTERLIFE_UP, cult_id=CHURCH, god_id=Pick("son")),
        "faith_climate:set": given(town_id=Pick(TOWN)),
        **{name: after(CLIMATE_UP, town_id=Pick(TOWN)) for name in ("faith_climate:edit", "faith_climate:delete")},
        "divination_system:create": given(people_id=Pick(EntityType.PEOPLE), kind=Computed(unkept_divination)),
        **{
            name: after(SYSTEM_UP, system_id=Newest("divination_system"))
            for name in ("divination_system:edit", "divination_system:delete", "divination_system:read")
        },
        "divination:create": after(SYSTEM_UP, realm_id=RULED, question="coronation", system_id=Newest("divination_system")),
        **{name: after(SYSTEM_UP, READING_UP, reading_id=Newest("divination")) for name in ("divination:edit", "divination:delete")},
        "foresight:create": given(seer_id=Pick(MORTAL), subject_id=Pick(MORTAL, 1), predicate="dies", certainty=80, proclaimed=True),
        **{name: after(FORESIGHT_UP, foresight_id=Newest("foresight")) for name in ("foresight:edit", "foresight:delete")},
        "forecast_model:create": given(order_id=Pick(EntityType.FACTION), realm_id=Pick(REALM)),
        **{name: after(MODEL_UP, model_id=Newest("forecast_model")) for name in ("forecast_model:edit", "forecast_model:delete")},
        "god_feeding:set": given(god_id=Pick("son"), emotion="grief", weight=60),
        **{name: after(FEEDING_UP, god_id=Pick("son"), emotion="joy") for name in ("god_feeding:edit", "god_feeding:delete")},
    }
)


async def maker_town(session: AsyncSession) -> int | None:
    author = await session.scalar(
        select(EntityRow)
        .join(ArtworkProfileRow, ArtworkProfileRow.author_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    town = await town_of(session, author) if author is not None else None
    return town.id if town is not None else None


async def authored_town(session: AsyncSession) -> None:
    work = await session.scalar(select(ArtworkProfileRow).order_by(ArtworkProfileRow.artwork_entity_id.desc()).limit(1))
    mortal = await session.scalar(
        select(EntityRow).where(EntityRow.entity_type == MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )
    town = await session.scalar(select(EntityRow).where(EntityRow.entity_type == TOWN, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1))
    assert work is not None and mortal is not None and town is not None
    work.author_entity_id = mortal.id
    mortal.location_id = town.id
    await session.flush()


async def authored_school(session: AsyncSession) -> None:
    await authored_town(session)
    town_id = await maker_town(session)
    town = await session.get(EntityRow, town_id) if town_id is not None else None
    assert town is not None
    ctx = await manual_context(session, "lever_school", Rules())
    await found_movement(ctx, town, list((await makers_by_town(ctx)).get(town.id, [])))


async def newest_club(session: AsyncSession) -> int | None:
    return await session.scalar(select(ClubRow.faction_entity_id).order_by(ClubRow.faction_entity_id.desc()).limit(1))


async def older_club(session: AsyncSession) -> int | None:
    rows = list(await session.scalars(select(ClubRow.faction_entity_id).order_by(ClubRow.faction_entity_id.desc()).limit(2)))
    return rows[-1] if rows else None


async def newest_league(session: AsyncSession) -> int | None:
    return await session.scalar(select(LeagueRow.faction_entity_id).order_by(LeagueRow.faction_entity_id.desc()).limit(1))


async def newest_movement(session: AsyncSession) -> int | None:
    return await session.scalar(select(ArtMovementRow.faction_entity_id).order_by(ArtMovementRow.faction_entity_id.desc()).limit(1))


async def newest_construct(session: AsyncSession) -> int | None:
    return await session.scalar(select(ConstructRow.entity_id).order_by(ConstructRow.entity_id.desc()).limit(1))


async def unleagued_realm(session: AsyncSession) -> int | None:
    leagued = select(LeagueRow.polity_entity_id).where(LeagueRow.polity_entity_id.is_not(None))
    return await session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == REALM, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(leagued))
        .order_by(EntityRow.id)
        .limit(1)
    )


ART_WORK = Newest(EntityType.ARTWORK)
MAKER_TOWN = Computed(maker_town)
CLUB = Computed(newest_club)
OTHER_CLUB = Computed(older_club)
CLUB_LEAGUE = Computed(newest_league)
ART_SCHOOL = Computed(newest_movement)
CONSTRUCT = Computed(newest_construct)
FREE_REALM = Computed(unleagued_realm)
PRICE_UP = ("art_price:set", {"artwork_id": ART_WORK, "price": 20})
SALE_UP = ("art_sale:create", {"artwork_id": ART_WORK, "buyer_id": Pick(MORTAL, 1), "price": 0})
COLLECTOR_UP = ("collector:create", {"holder_id": Pick(MORTAL, 2), "role": "dealer"})
FORGERY_UP = ("forgery:create", {"original_id": ART_WORK, "forger_id": Pick(MORTAL)})
CANON_UP = ("canon_work:create", {"people_id": Pick(EntityType.PEOPLE), "artwork_id": ART_WORK, "path": "renown"})
SCHOOL_UP = ("art_movement:create", {"town_id": MAKER_TOWN})
CLUB_UP = ("club:create", {"town_id": Pick(TOWN), "kind": "racing"})
CLUB_TOO = ("club:create", {"town_id": Pick(TOWN, 1), "kind": "combat"})
LEAGUE_UP = ("league:create", {"realm_id": FREE_REALM})
MATCH_UP = ("match:create", {"home_id": CLUB, "away_id": OTHER_CLUB})
BET_UP = ("bet:create", {"match_id": Newest("match"), "town_id": Pick(TOWN), "club_id": CLUB, "stake": 5})
CONSTRUCT_UP = ("construct:create", {"maker_id": Pick(MORTAL), "material": "stone", "source": "ley", "token": "word"})
RULES_UP = ("instruction_set:create", {"owner_id": CONSTRUCT, "token": "word", "holder_id": Pick(MORTAL)})
ORDER_UP = ("instruction_order:create", {"set_id": Newest("instruction_set"), "kind": "guard", "target_id": Pick(TOWN)})
REMADE_UP = ("remade:create", {"mortal_id": Pick(MORTAL, 3)})
CONTRACT_UP = ("monster_contract:create", {"town_id": Pick(TOWN), "beast_id": Newest(EntityType.BEAST), "bounty": 30})
SIGN_UP = ("birth_sign:create", {"mortal_id": Pick(MORTAL, 4)})
ARTS_EDITS: Mapping[str, Mapping[str, Any]] = {
    "art_price:edit": {"price": 90, "provenance": 3, "interest": 40, "last_buyer_node_id": Pick(MORTAL, 1)},
    "art_sale:edit": {"seller_node_id": Pick(MORTAL), "buyer_node_id": Pick(MORTAL, 1), "price": 12, "fair_place_entity_id": Pick(TOWN)},
    "collector:edit": {"role": "connoisseur", "taste_form_entity_id": None, "connoisseurship": 80},
    "forgery:edit": {
        "kind": "artwork",
        "forger_entity_id": Pick(MORTAL),
        "original_entity_id": ART_WORK,
        "skill": 70,
        "status": "hidden",
        "exposed_by_entity_id": None,
    },
    "canon_work:edit": {"path": "teaching", "weight": 65, "contested": True},
    "art_movement:edit": {"art_form_entity_id": None, "orthodoxy": True, "scandals": 2, "patrons": 4},
    "club:edit": {
        "kind": "athletics",
        "league_entity_id": None,
        "arena_entity_id": None,
        "wins": 3,
        "losses": 1,
        "rating": 60,
        "fandom": 70,
        "line": "district",
        "line_entity_id": Pick(TOWN),
        "leverage": 45,
        "bought_by_entity_id": Pick(REALM),
    },
    "league:edit": {"polity_entity_id": Pick(REALM), "champion_entity_id": CLUB, "season_epoch": 2},
    "match:edit": {"home_entity_id": CLUB, "away_entity_id": OTHER_CLUB, "winner_entity_id": OTHER_CLUB, "stake": 9, "riot": True},
    "bet:edit": {"club_entity_id": CLUB, "stake": 4, "won": False},
    "construct:edit": {
        "material": "iron",
        "power_source": "divine",
        "power": 60,
        "upkeep": 4,
        "maker_entity_id": Pick(MORTAL),
        "decay": 20,
        "soul_entity_id": None,
        "will": "emergent",
    },
    "instruction_set:edit": {
        "binding": "oath",
        "command_token": "bloodline",
        "token_entity_id": None,
        "holder_node_id": Pick(MORTAL),
        "kill_switch": True,
        "kill_token_entity_id": None,
        "literalness": 30,
    },
    "instruction_order:edit": {"kind": "serve", "target_node_id": Pick(TOWN), "priority": 2, "condition": "until_date", "until_epoch": 9, "lapsed": False},
    "remade:edit": {
        "lost_function": "speech",
        "forced_function": "grasp",
        "sentenced_by_entity_id": Pick(REALM),
        "grievance": 55,
        "bound_to_entity_id": Pick(TOWN),
    },
    "monster_contract:edit": {
        "community_entity_id": Pick(TOWN),
        "beast_entity_id": Newest(EntityType.BEAST),
        "bounty": 50,
        "hunter_entity_id": Pick(MORTAL),
        "status": "taken",
        "study": 30,
    },
    "birth_sign:edit": {"season": 2, "ruling_celestial_entity_id": None, "dreaded": True, "influence": "real", "fortune": -5, "exposed": False},
}
EDITS = {**EDITS, **ARTS_EDITS}
LEVERS.update(
    {
        "art_price:set": after(ARTWORK, artwork_id=ART_WORK, price=30),
        **{name: after(ARTWORK, PRICE_UP, artwork_id=ART_WORK) for name in ("art_price:edit", "art_price:delete")},
        "art_sale:create": after(ARTWORK, artwork_id=ART_WORK, buyer_id=Pick(MORTAL, 1), price=0),
        **{name: after(ARTWORK, SALE_UP, sale_id=Newest("art_sale")) for name in ("art_sale:edit", "art_sale:delete")},
        "collector:create": given(holder_id=Pick(MORTAL, 2), role="patron"),
        **{name: after(COLLECTOR_UP, holder_id=Pick(MORTAL, 2)) for name in ("collector:edit", "collector:delete")},
        "forgery:create": after(ARTWORK, original_id=ART_WORK, forger_id=Pick(MORTAL)),
        **{name: after(ARTWORK, FORGERY_UP, forgery_id=Newest("forgery")) for name in ("forgery:edit", "forgery:delete")},
        "forgery:expose": after(ARTWORK, FORGERY_UP, forgery_id=Newest("forgery"), expert_id=Pick(MORTAL, 1)),
        "canon_work:create": after(ARTWORK, people_id=Pick(EntityType.PEOPLE), artwork_id=ART_WORK, path="copying"),
        **{name: after(ARTWORK, CANON_UP, people_id=Pick(EntityType.PEOPLE), artwork_id=ART_WORK) for name in ("canon_work:edit", "canon_work:delete")},
        "art_movement:create": Lever(values={"town_id": MAKER_TOWN}, before=(ARTWORK,), then=authored_town),
        **{name: Lever(values={"faction_id": ART_SCHOOL}, before=(ARTWORK,), then=authored_school) for name in ("art_movement:edit", "art_movement:delete")},
        "art_movement:manifesto": Lever(values={"faction_id": ART_SCHOOL, "axis": "honour", "value": 60}, before=(ARTWORK,), then=authored_school),
        "club:create": given(town_id=Pick(TOWN), kind="team_game"),
        **{name: after(CLUB_UP, faction_id=CLUB) for name in ("club:edit", "club:delete")},
        "league:create": given(realm_id=FREE_REALM, town_id=Pick(TOWN)),
        **{name: after(LEAGUE_UP, faction_id=CLUB_LEAGUE) for name in ("league:edit", "league:delete")},
        "match:create": after(CLUB_UP, CLUB_TOO, home_id=CLUB, away_id=OTHER_CLUB, winner_id=CLUB),
        **{name: after(CLUB_UP, CLUB_TOO, MATCH_UP, match_id=Newest("match")) for name in ("match:edit", "match:delete")},
        "bet:create": after(CLUB_UP, CLUB_TOO, MATCH_UP, match_id=Newest("match"), town_id=Pick(TOWN, 1), club_id=OTHER_CLUB, stake=6),
        **{name: after(CLUB_UP, CLUB_TOO, MATCH_UP, BET_UP, bet_id=Newest("bet")) for name in ("bet:edit", "bet:delete")},
        "construct:create": given(maker_id=Pick(MORTAL), material="clay", source="reagent", token="item", name="The Clay Warden"),
        **{name: after(CONSTRUCT_UP, construct_id=CONSTRUCT) for name in ("construct:edit", "construct:delete", "construct:unmake")},
        "construct:ensoul": after(CONSTRUCT_UP, construct_id=CONSTRUCT, spirit_id=Pick(EntityType.SPIRIT)),
        "instruction_set:create": after(CONSTRUCT_UP, owner_id=CONSTRUCT, token="office", token_id=Pick(REALM), holder_id=None),
        **{
            name: after(CONSTRUCT_UP, RULES_UP, set_id=Newest("instruction_set"))
            for name in ("instruction_set:edit", "instruction_set:delete", "instruction_set:resolve")
        },
        "instruction_order:create": after(CONSTRUCT_UP, set_id=Newest("instruction_set"), kind="report", target_id=Pick(MORTAL), condition="always"),
        **{name: after(CONSTRUCT_UP, ORDER_UP, order_id=Newest("instruction_order")) for name in ("instruction_order:edit", "instruction_order:delete")},
        "remade:create": given(mortal_id=Pick(MORTAL, 3)),
        **{name: after(REMADE_UP, mortal_id=Pick(MORTAL, 3)) for name in ("remade:edit", "remade:delete")},
        "monster_contract:create": after(BEAST, town_id=Pick(TOWN), beast_id=Newest(EntityType.BEAST), bounty=40),
        **{name: after(BEAST, CONTRACT_UP, contract_id=Newest("monster_contract")) for name in ("monster_contract:edit", "monster_contract:delete")},
        "monster_contract:assign": after(BEAST, CONTRACT_UP, contract_id=Newest("monster_contract"), hunter_id=Pick(MORTAL)),
        "birth_sign:create": given(mortal_id=Pick(MORTAL, 4)),
        **{name: after(SIGN_UP, mortal_id=Pick(MORTAL, 4)) for name in ("birth_sign:edit", "birth_sign:delete")},
    }
)


async def cyclic_cosmos(session: AsyncSession) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.age_cycle = AgeCycle.CYCLIC
    await session.flush()


async def newest_eco_plan(session: AsyncSession) -> int | None:
    return await session.scalar(select(EcoTransformationRow.plan_id).order_by(EcoTransformationRow.plan_id.desc()).limit(1))


WORLD = Pick("world")
ECO_PLAN = ("plan:create", {"holder_id": Pick(REALM), "kind": "ecological_transformation", "name": "The Green Work", "target_id": Pick(EntityType.REGION)})
ECO_UP = ("eco_transformation:set", {"plan_id": Newest("long_plan"), "target_moisture": 70})
SEASON_UP = ("irregular_season:create", {"world_id": WORLD})
FORMATION_UP = ("formation:read", {"world_id": WORLD, "reshape": False})
FORECAST_UP = ("winter_forecast:set", {"world_id": WORLD, "people_id": Pick(EntityType.PEOPLE), "predicted_end_epoch": 9})
CYCLE_UP = ("age:cycle", {"cycle": "cyclic"})
TURN_UP: tuple[str, dict[str, Any]] = ("age:turn", {})
ECHO_UP = ("age_echo:create", {"age_id": Newest("age"), "template": "quest", "source_id": Pick(MORTAL), "weight": 50})
ARC_UP = ("arc:create", {"subject_id": Pick(MORTAL), "template": "rivalry", "figure_id": Pick(MORTAL, 1), "role": "rival"})
BEAT_UP = ("arc_beat:create", {"arc_id": Newest("arc"), "stage": "crisis", "text": "They met at the ford."})
SETUP_UP = ("setup:create", {"kind": "omen", "source_id": 0, "subject_id": Pick(MORTAL)})
AGES_EDITS: Mapping[str, Mapping[str, Any]] = {
    "formation:edit": {
        "zone": "outer",
        "migration": "inward",
        "bombardment": 50,
        "craters": 3,
        "core_share": 20,
        "mantle_heat": 45,
        "water_delivered": 70,
        "exotic_delivered": 10,
    },
    "irregular_season:edit": {"cause": "divine", "spell": "winter", "spell_started_epoch": 2, "spell_length": 4, "severity": 80},
    "winter_forecast:edit": {"scholar_entity_id": Pick(MORTAL), "predicted_end_epoch": 12, "heeded": False},
    "eco_transformation:edit": {"target_moisture": 40, "target_forest": 30, "target_fertility": 50, "regions_changed": 2, "resistance": 20, "sabotage": 1},
    "age:edit": {"number": 3, "began_epoch": 1, "ended_epoch": 4, "variant": "ruin", "carried": 25},
    "age_echo:edit": {"template": "revenge", "role": "foe", "source_node_id": Pick(MORTAL), "echo_node_id": Pick(MORTAL, 1), "weight": 70},
    "arc:edit": {"template": "tragedy", "stage": "climax", "outcome": "open", "beats": 3, "drama": 60, "ended_epoch": None},
    "arc_figure:edit": {"role": "betrayer"},
    "arc_beat:edit": {"stage": "climax", "text": "The ford ran red."},
    "setup:edit": {"kind": "dream", "subject_node_id": Pick(MORTAL), "payoff": "fulfilled", "paid_epoch": 5, "payoff_text": "It came true."},
}
EDITS = {**EDITS, **AGES_EDITS}
LEVERS.update(
    {
        "formation:read": given(world_id=WORLD, reshape=True),
        **{name: after(FORMATION_UP, world_id=WORLD) for name in ("formation:reshape", "formation:edit", "formation:delete")},
        "irregular_season:create": given(world_id=WORLD),
        **{name: after(SEASON_UP, world_id=WORLD) for name in ("irregular_season:forecast", "irregular_season:edit", "irregular_season:delete")},
        "winter_forecast:set": given(world_id=WORLD, people_id=Pick(EntityType.PEOPLE), predicted_end_epoch=8, heeded=True),
        **{name: after(FORECAST_UP, forecast_id=Newest("winter_forecast")) for name in ("winter_forecast:edit", "winter_forecast:delete")},
        "eco_transformation:set": after(ECO_PLAN, plan_id=Newest("long_plan"), target_moisture=80, target_forest=60, target_fertility=70),
        **{name: after(ECO_PLAN, ECO_UP, plan_id=Computed(newest_eco_plan)) for name in ("eco_transformation:edit", "eco_transformation:delete")},
        "age:cycle": given(cycle="cyclic"),
        "age:turn": setup_then(cyclic_cosmos),
        **{name: after(CYCLE_UP, TURN_UP, age_id=Newest("age")) for name in ("age:edit", "age:delete")},
        "age_echo:create": after(CYCLE_UP, TURN_UP, age_id=Newest("age"), template="redemption", source_id=Pick(MORTAL), weight=40),
        **{name: after(CYCLE_UP, TURN_UP, ECHO_UP, echo_id=Newest("age_echo")) for name in ("age_echo:edit", "age_echo:delete")},
        "arc:create": given(subject_id=Pick(MORTAL), template="quest", figure_id=Pick(MORTAL, 2), role="ally"),
        **{name: after(ARC_UP, arc_id=Newest("arc")) for name in ("arc:press", "arc:edit", "arc:delete")},
        "arc_figure:create": after(ARC_UP, arc_id=Newest("arc"), node_id=Pick(MORTAL, 3), role="mentor"),
        **{name: after(ARC_UP, arc_id=Newest("arc"), node_id=Pick(MORTAL, 1)) for name in ("arc_figure:edit", "arc_figure:delete")},
        "arc_beat:create": after(ARC_UP, arc_id=Newest("arc"), stage="rising", text="A first meeting."),
        **{name: after(ARC_UP, BEAT_UP, beat_id=Newest("arc_beat")) for name in ("arc_beat:edit", "arc_beat:delete")},
        "setup:create": given(kind="prophecy", source_id=0, subject_id=Pick(MORTAL)),
        **{name: after(SETUP_UP, setup_id=Newest("setup")) for name in ("setup:edit", "setup:delete")},
    }
)

LEVERS.update({name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in EDITS.items()})


ITEM = EntityType.ITEM
PEOPLE = EntityType.PEOPLE
DIET_UP = ("diet:set", {"holder_id": Pick(TOWN), "values": {"staple": 50}})
NEED_UP = ("nutrient_need:set", {"people_id": Pick(PEOPLE), "nutrient": "fresh", "weight": 60})
SCORE_UP = ("nutrition_score:set", {"holder_id": Pick(MORTAL), "values": {"score": 55}})
BIAS_UP = ("bias_weight:set", {"holder_id": Pick(MORTAL), "bias": "optimism", "weight": 70})
PURITY_UP = ("purity:set", {"mortal_id": Pick(MORTAL), "values": {"state": "impure", "source": "the_dead"}})
SOURCE_UP = ("impurity_source:set", {"people_id": Pick(PEOPLE), "source": "birth", "weight": 40, "lasts": 2})
METHOD_UP = ("purification:set", {"people_id": Pick(PEOPLE), "method": "fasting", "epochs": 1, "cost": 0, "success": 90})
RANK_UP = ("purity_rank:create", {"people_id": Pick(PEOPLE), "name": "The First Rank", "standing": 80, "professions": ["priest"]})
MISHAP_UP = ("mishap:create", {"town_id": Pick(TOWN), "kind": "illness", "victim_id": Pick(MORTAL)})
BELIEF_UP = ("luck_belief:create", {"people_id": Pick(PEOPLE), "sign": "number", "reach": "battle", "lucky": True, "name": "A lucky number of the folk"})
CHARM_UP = ("charm:set", {"item_id": Pick(ITEM), "power": "luck", "strength": 40})
ACCUSE_UP: tuple[str, dict[str, Any]] = ("accusation:create", {"town_id": Computed(peopled_town), "accuser_id": None, "mishap_id": None})
HUNT_UP = ("witch_hunt:create", {"town_id": Pick(TOWN), "fervour": 50})
FOLKWAYS_EDITS: Mapping[str, Mapping[str, Any]] = {
    "diet:edit": {"staple": 40, "protein": 20, "fat": 10, "fresh": 15, "mineral": 5, "preserved": 5, "special": 5, "energy": 80},
    "nutrient_need:edit": {"weight": 70},
    "nutrition_score:edit": {"energy": 70, "balance": 60, "score": 65, "deficiency": "mineral", "childhood": 50},
    "bias_weight:edit": {"weight": 30},
    "purity:edit": {"state": "defiled", "source": "act", "until_epoch": 6, "rank_id": None},
    "impurity_source:edit": {"weight": 70, "lasts": 3},
    "purification:edit": {"epochs": 2, "cost": 5, "success": 60},
    "purity_rank:edit": {"name": "The High Rank", "standing": 90, "endogamous": False, "commensal": True},
    "mishap:edit": {
        "kind": "accident",
        "true_cause": "a fall",
        "explained": True,
        "attribution": "omen",
        "response": "rite",
        "victim_node_id": Pick(MORTAL, 1),
        "cause_node_id": None,
    },
    "luck_belief:edit": {"name": "An unlucky gesture of the folk", "sign": "gesture", "reach": "journey", "lucky": False},
    "charm:edit": {"power": "healing", "real": True, "strength": 70},
    "accusation:edit": {"accuser_node_id": Pick(MORTAL, 2), "outcome": "cleared", "guilty_in_truth": False},
    "witch_hunt:edit": {"fervour": 30, "accused": 2, "killed": 1, "ended_epoch": None},
}
EDITS = {**EDITS, **FOLKWAYS_EDITS}
LEVERS.update(
    {
        "diet:set": given(holder_id=Pick(TOWN), values={"energy": 90}),
        **{name: after(DIET_UP, holder_id=Pick(TOWN)) for name in ("diet:edit", "diet:delete")},
        "nutrient_need:set": given(people_id=Pick(PEOPLE), nutrient="protein", weight=55),
        **{name: after(NEED_UP, people_id=Pick(PEOPLE), nutrient="fresh") for name in ("nutrient_need:edit", "nutrient_need:delete")},
        "nutrition_score:set": given(holder_id=Pick(MORTAL), values={"score": 40}),
        **{name: after(SCORE_UP, holder_id=Pick(MORTAL)) for name in ("nutrition_score:edit", "nutrition_score:delete")},
        "nutrition:feed": given(),
        "bias_weight:set": given(holder_id=Pick(MORTAL), bias="sunk_cost", weight=80),
        **{name: after(BIAS_UP, holder_id=Pick(MORTAL), bias="optimism") for name in ("bias_weight:edit", "bias_weight:delete")},
        "bias:read": given(holder_id=Pick(MORTAL)),
        "purity:set": given(mortal_id=Pick(MORTAL), values={"state": "impure"}),
        **{name: after(PURITY_UP, mortal_id=Pick(MORTAL)) for name in ("purity:edit", "purity:delete", "purity:cleanse")},
        "impurity_source:set": given(people_id=Pick(PEOPLE), source="wound", weight=30, lasts=1),
        **{name: after(SOURCE_UP, people_id=Pick(PEOPLE), source="birth") for name in ("impurity_source:edit", "impurity_source:delete")},
        "purification:set": given(people_id=Pick(PEOPLE), method="rite", epochs=0, cost=3, success=70),
        **{name: after(METHOD_UP, people_id=Pick(PEOPLE), method="fasting") for name in ("purification:edit", "purification:delete")},
        "purity_rank:create": given(people_id=Pick(PEOPLE), name="The Low Rank", standing=20, professions=["farmer"]),
        **{name: after(RANK_UP, rank_id=Newest("purity_rank")) for name in ("purity_rank:edit", "purity_rank:delete")},
        "purity_rank:profession": after(RANK_UP, rank_id=Newest("purity_rank"), profession="smith", member=True),
        "mishap:create": given(town_id=Pick(TOWN), kind="bad_luck", victim_id=None, cause_id=None),
        **{name: after(MISHAP_UP, mishap_id=Newest("mishap")) for name in ("mishap:edit", "mishap:delete")},
        "luck_belief:create": given(people_id=Pick(PEOPLE), sign="day", reach="harvest", lucky=False, name="An unlucky day of the folk"),
        **{name: after(BELIEF_UP, belief_id=Newest("luck_belief")) for name in ("luck_belief:edit", "luck_belief:delete")},
        "charm:set": given(item_id=Pick(ITEM), power="protection", strength=60),
        **{name: after(CHARM_UP, item_id=Pick(ITEM)) for name in ("charm:edit", "charm:delete")},
        "accusation:create": given(town_id=Computed(peopled_town), accuser_id=None, mishap_id=None),
        **{name: after(ACCUSE_UP, accusation_id=Newest("accusation")) for name in ("accusation:edit", "accusation:delete")},
        "witch_hunt:create": given(town_id=Pick(TOWN), fervour=70),
        **{name: after(HUNT_UP, hunt_id=Newest("witch_hunt")) for name in ("witch_hunt:edit", "witch_hunt:delete")},
    }
)

LEVERS.update(
    {name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in FOLKWAYS_EDITS.items()}
)


STRUCTURE = EntityType.STRUCTURE
FACTION = EntityType.FACTION
REVIVAL_UP = ("revival:create", {"people_entity_id": Pick(PEOPLE), "aim": "restore", "goal": "revive_language"})
INTOX_UP = ("intoxicant_custom:set", {"people_id": Pick(PEOPLE), "intoxicant": "wine", "use": "feast", "acceptance": 40})
MARKC_UP = ("mark_custom:set", {"people_id": Pick(PEOPLE), "kind": "scar", "meaning": "deed"})
MARK_UP = ("body_mark:create", {"holder_node_id": Pick(MORTAL), "kind": "tattoo", "meaning": "clan"})
BUDGET_UP = (
    "time_budget:set",
    {"people_id": Pick(PEOPLE), "social_class": "farmer", "work": 60, "rest": 20, "worship": 10, "leisure": 5, "travel": 3, "service": 2},
)
NAMING_UP = ("naming_custom:set", {"people_id": Pick(PEOPLE), "pattern": "clan", "secret_names": True, "taboo_epochs": 1})
NAME_UP = ("name_form:set", {"holder_id": Pick(MORTAL), "form": "deed", "name": "The Unbowed"})
SET_UP = ("age_set:create", {"people_entity_id": Pick(PEOPLE), "name": "The First Set", "grade": "youths"})
MEMBER_SET_UP = ("age_set_member:set", {"mortal_id": Pick(MORTAL), "age_set_id": Newest("age_set")})
TAVERN_UP = ("tavern:set", {"structure_id": Pick(STRUCTURE), "keeper_node_id": None})
HOUSE_UP = ("welfare_house:set", {"structure_id": Pick(STRUCTURE, 1), "patron_node_id": None})
COMMUTE_UP = ("commute:set", {"settlement_id": Pick(TOWN), "distance": 20})
COOP_UP = ("cooperative:set", {"faction_id": Pick(FACTION), "purpose": "boats"})
EVIDENCE_UP = ("evidence:create", {"case_id": Newest("crime_case"), "kind": "trace", "points_to_node_id": None, "reliability": 40})
CATEGORY_UP = ("membership_category:set", {"polity_id": Pick(REALM), "category": "subject"})
MEMBERSHIP_UP = ("membership:set", {"mortal_id": Pick(MORTAL), "polity_entity_id": Pick(REALM), "category": "resident_foreigner", "path": "birthplace"})
BORDER_UP = ("border_control:set", {"polity_id": Pick(REALM), "fee": 40, "delay": 1, "enforcement": 50})
RELIEF_UP = ("poor_relief:set", {"polity_id": Pick(REALM), "kind": "granary", "budget": 30, "reach": 30})
MEASURE_UP = ("measure_standard:set", {"polity_id": Pick(REALM), "standard": True, "fraud": 5})
CUSTOMS_EDITS: Mapping[str, Mapping[str, Any]] = {
    "revival:edit": {
        "aim": "synthesise",
        "stage": "revitalisation",
        "goal": "restore_god",
        "strength": 40,
        "prophet_node_id": Pick(MORTAL),
        "ended_epoch": None,
    },
    "intoxicant_custom:edit": {"use": "rite", "acceptance": 70},
    "mark_custom:edit": {"meaning": "mourning"},
    "body_mark:edit": {"kind": "scar", "meaning": "deed", "placed_epoch": 2},
    "time_budget:edit": {"work": 50, "rest": 25, "worship": 10, "leisure": 10, "travel": 3, "service": 2},
    "naming_custom:edit": {
        "pattern": "parent",
        "secret_names": False,
        "taboo_epochs": 2,
        "rename_on_initiation": True,
        "rename_on_marriage": True,
        "rename_on_vow": False,
    },
    "name_form:edit": {"name": "The Steadfast", "given_epoch": 3},
    "age_set:edit": {"name": "The Bold Set", "initiated_from": 1, "initiated_to": 3, "grade": "warriors", "promoted_epoch": 3},
    "age_set_member:edit": {"age_set_id": Newest("age_set")},
    "tavern:edit": {"keeper_node_id": Pick(MORTAL), "patrons": 30, "brawls": 2, "lodging": 10, "rumours": 4},
    "welfare_house:edit": {"patron_node_id": Pick(MORTAL), "inmates": 12, "upkeep": 6},
    "commute:edit": {"distance": 30, "labour_lost": 12, "worker_camp": True},
    "cooperative:edit": {"purpose": "credit", "pool": 20, "members": 5},
    "evidence:edit": {"kind": "witness", "points_to_node_id": Pick(MORTAL), "reliability": 60, "forged": True, "found_epoch": 2},
    "membership_category:edit": {"office": True, "courts": True, "arms": False},
    "membership:edit": {"polity_entity_id": Pick(REALM), "category": "citizen", "path": "residence"},
    "border_control:edit": {"fee": 60, "delay": 2, "enforcement": 70, "corruption": 10},
    "poor_relief:edit": {"kind": "parish", "budget": 40, "reach": 50},
    "measure_standard:edit": {"standard": False, "adopted_epoch": 1, "fraud": 30},
}
EDITS = {**EDITS, **CUSTOMS_EDITS}
LEVERS.update(
    {
        **{name: after(REVIVAL_UP, record_id=Newest("revival")) for name in ("revival:edit", "revival:delete")},
        **{name: after(INTOX_UP, people_id=Pick(PEOPLE), intoxicant="wine") for name in ("intoxicant_custom:edit", "intoxicant_custom:delete")},
        **{name: after(MARKC_UP, people_id=Pick(PEOPLE), kind="scar") for name in ("mark_custom:edit", "mark_custom:delete")},
        **{name: after(MARK_UP, record_id=Newest("body_mark")) for name in ("body_mark:edit", "body_mark:delete")},
        **{name: after(BUDGET_UP, people_id=Pick(PEOPLE), social_class="farmer") for name in ("time_budget:edit", "time_budget:delete")},
        **{name: after(NAMING_UP, people_id=Pick(PEOPLE)) for name in ("naming_custom:edit", "naming_custom:delete")},
        **{name: after(NAME_UP, holder_id=Pick(MORTAL), form="deed") for name in ("name_form:edit", "name_form:delete")},
        **{name: after(SET_UP, record_id=Newest("age_set")) for name in ("age_set:edit", "age_set:delete")},
        "age_set_member:set": after(SET_UP, mortal_id=Pick(MORTAL), age_set_id=Newest("age_set")),
        **{name: after(SET_UP, MEMBER_SET_UP, mortal_id=Pick(MORTAL)) for name in ("age_set_member:edit", "age_set_member:delete")},
        **{name: after(TAVERN_UP, structure_id=Pick(STRUCTURE)) for name in ("tavern:edit", "tavern:delete")},
        **{name: after(HOUSE_UP, structure_id=Pick(STRUCTURE, 1)) for name in ("welfare_house:edit", "welfare_house:delete")},
        **{name: after(COMMUTE_UP, settlement_id=Pick(TOWN)) for name in ("commute:edit", "commute:delete")},
        **{name: after(COOP_UP, faction_id=Pick(FACTION)) for name in ("cooperative:edit", "cooperative:delete")},
        "evidence:create": after(ACCUSE_UP, case_id=Newest("crime_case"), kind="document", points_to_node_id=None, reliability=50),
        **{name: after(ACCUSE_UP, EVIDENCE_UP, record_id=Newest("evidence")) for name in ("evidence:edit", "evidence:delete")},
        **{name: after(CATEGORY_UP, polity_id=Pick(REALM), category="subject") for name in ("membership_category:edit", "membership_category:delete")},
        "membership_category:right": given(polity_id=Pick(REALM), category="resident_foreigner", right="arms", granted=True),
        **{name: after(MEMBERSHIP_UP, mortal_id=Pick(MORTAL)) for name in ("membership:edit", "membership:delete")},
        **{name: after(BORDER_UP, polity_id=Pick(REALM)) for name in ("border_control:edit", "border_control:delete")},
        **{name: after(RELIEF_UP, polity_id=Pick(REALM)) for name in ("poor_relief:edit", "poor_relief:delete")},
        **{name: after(MEASURE_UP, polity_id=Pick(REALM)) for name in ("measure_standard:edit", "measure_standard:delete")},
    }
)

LEVERS.update(
    {name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in CUSTOMS_EDITS.items()}
)


RESOURCE = EntityType.RESOURCE
GROUND_UP = (
    "catch_ground:set",
    {"source_id": Pick(RESOURCE), "region_id": Pick(EntityType.REGION), "ground": "fishery", "gear": "nets", "right": "commons", "effort": 50},
)
WORKS_UP = ("chemical_works:set", {"settlement_id": Pick(TOWN), "product": "soap", "output": 20, "hazard": 5, "pollution": 5})
INSURER_UP = ("insurer:set", {"insurer_id": Pick(FACTION), "pool": 30, "risk_belief": 20, "premium_pct": 5})
POLICY_UP = (
    "insurance_policy:create",
    {"insurer_entity_id": Pick(FACTION), "holder_node_id": Pick(MORTAL), "cover": "life", "premium": 1, "sum_insured": 20},
)
RIGHT_UP = (
    "incorporeal_right:create",
    {"holder_node_id": Pick(MORTAL), "kind": "song", "subject_node_id": None, "name": "The Long Air", "acquired": "granted"},
)
AID_UP = ("assistive_aid:set", {"holder_id": Pick(MORTAL), "kind": "spectacles", "quality": 60})
CLOCK_UP = ("public_clock:set", {"settlement_id": Pick(TOWN), "kind": "water_clock", "precision": 35})
NUMBERS_UP = ("number_system:set", {"people_id": Pick(PEOPLE), "base": 12, "notation": "additive", "zero": False, "numeracy": 20})
MATERIAL_UP = ("material:edit", {"world_id": Pick("world"), "material": "iron", "values": {"hardness": 60}})
AFFINITY_UP = ("material_affinity:set", {"material_id": Newest("world_material"), "school": "earth", "mode": "worn", "power": 30})
LINK_UP = ("sympathetic_link:create", {"holder_node_id": Pick(MORTAL), "target_node_id": Pick(MORTAL, 1), "token": "hair", "strength": 50})
MOOD_SPIRIT_UP = (
    "emotion_spirit:create",
    {"region_entity_id": Pick(EntityType.REGION), "emotion": "joy", "strength": 30, "lifetime": 3, "bound_by_node_id": None},
)
CRAFTS_EDITS: Mapping[str, Mapping[str, Any]] = {
    "catch_ground:edit": {
        "ground": "trapping",
        "gear": "traps",
        "right": "owned",
        "owner_node_id": Pick(TOWN),
        "effort": 70,
        "collapse_at": 25,
        "collapsed": False,
        "last_catch": 4,
        "first_stock": 80,
    },
    "chemical_works:edit": {"output": 60, "hazard": 15, "pollution": 20, "accidents": 1},
    "insurer:edit": {"pool": 50, "risk_belief": 30, "premium_pct": 8, "ruined": False, "claims_seen": 2},
    "insurance_policy:edit": {"insurer_entity_id": Pick(FACTION), "cover": "house", "premium": 2, "sum_insured": 30, "active": True, "claims": 1},
    "incorporeal_right:edit": {
        "holder_node_id": Pick(MORTAL),
        "kind": "design",
        "subject_node_id": None,
        "name": "The Knotted Border",
        "acquired": "bought",
        "licensed_to_node_id": Pick(MORTAL, 1),
    },
    "assistive_aid:edit": {"quality": 80},
    "public_clock:edit": {"kind": "mechanical", "precision": 70, "built_epoch": 1},
    "number_system:edit": {"base": 20, "notation": "positional", "zero": True, "numeracy": 40},
    "material_affinity:edit": {"mode": "consumed", "power": 60},
    "sympathetic_link:edit": {"token": "blood", "strength": 70, "obtained_epoch": 1},
    "emotion_spirit:edit": {"emotion": "grief", "strength": 50, "lifetime": 4, "bound_by_node_id": Pick(MORTAL)},
}
EDITS = {**EDITS, **CRAFTS_EDITS}
LEVERS.update(
    {
        "catch_ground:set": given(**GROUND_UP[1]),
        **{name: after(GROUND_UP, source_id=Pick(RESOURCE), region_id=Pick(EntityType.REGION)) for name in ("catch_ground:edit", "catch_ground:delete")},
        "chemical_works:set": given(**WORKS_UP[1]),
        **{name: after(WORKS_UP, settlement_id=Pick(TOWN), product="soap") for name in ("chemical_works:edit", "chemical_works:delete")},
        "insurer:set": given(**INSURER_UP[1]),
        **{name: after(INSURER_UP, insurer_id=Pick(FACTION)) for name in ("insurer:edit", "insurer:delete")},
        "insurance_policy:create": given(**POLICY_UP[1]),
        **{name: after(POLICY_UP, record_id=Newest("insurance_policy")) for name in ("insurance_policy:edit", "insurance_policy:delete")},
        "incorporeal_right:create": given(**RIGHT_UP[1]),
        **{name: after(RIGHT_UP, record_id=Newest("incorporeal_right")) for name in ("incorporeal_right:edit", "incorporeal_right:delete")},
        "assistive_aid:set": given(**AID_UP[1]),
        **{name: after(AID_UP, holder_id=Pick(MORTAL), kind="spectacles") for name in ("assistive_aid:edit", "assistive_aid:delete")},
        "public_clock:set": given(**CLOCK_UP[1]),
        **{name: after(CLOCK_UP, settlement_id=Pick(TOWN)) for name in ("public_clock:edit", "public_clock:delete")},
        "number_system:set": given(**NUMBERS_UP[1]),
        **{name: after(NUMBERS_UP, people_id=Pick(PEOPLE)) for name in ("number_system:edit", "number_system:delete")},
        "number_system:read": after(NUMBERS_UP, people_id=Pick(PEOPLE), number=7, reading="sacred"),
        "material_affinity:set": after(MATERIAL_UP, **AFFINITY_UP[1]),
        **{
            name: after(MATERIAL_UP, AFFINITY_UP, material_id=Newest("world_material"), school="earth")
            for name in ("material_affinity:edit", "material_affinity:delete")
        },
        "sympathetic_link:create": given(**LINK_UP[1]),
        **{name: after(LINK_UP, record_id=Newest("sympathetic_link")) for name in ("sympathetic_link:edit", "sympathetic_link:delete")},
        "emotion_spirit:create": given(**MOOD_SPIRIT_UP[1]),
        **{name: after(MOOD_SPIRIT_UP, record_id=Newest("emotion_spirit")) for name in ("emotion_spirit:edit", "emotion_spirit:delete")},
    }
)

LEVERS.update(
    {name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in CRAFTS_EDITS.items()}
)


REGION = EntityType.REGION
WIND_UP = ("region_wind:set", {"region_id": Pick(REGION), "band": "westerly", "wind_from": 6, "strength": 50})
MONSOON_UP = ("monsoon_season:set", {"world_id": Pick("world"), "epoch": 1, "strength": 120, "failed": False})
SWING_UP = ("climate_oscillation:set", {"world_id": Pick("world"), "phase": "warm", "period": 6, "strength": 10})
WINDOW_UP = ("launch_window:set", {"from_world_id": Pick("world", 1), "to_world_id": Pick("world"), "synodic": 4, "offset": 1, "open": False})
ROAD_UP = ("cosmopolitan_culture:create", {"route_id": Pick("route"), "name": "The Folk of the Long Road", "lingua_franca_entity_id": None, "strength": 20})
ROAD_MEMBER_UP = ("cosmopolitan_member:set", {"culture_id": Newest("cosmopolitan_culture"), "community_id": Pick(TOWN), "share": 30})
CLIMES_EDITS: Mapping[str, Mapping[str, Any]] = {
    "region_wind:edit": {"band": "polar", "wind_from": 2, "strength": 40, "windward": True, "shadow": 10, "monsoon": 20, "upwelling": True},
    "monsoon_season:edit": {"strength": 40, "failed": True},
    "climate_oscillation:edit": {"phase": "cold", "period": 8, "step": 2, "strength": 15},
    "launch_window:edit": {"synodic": 6, "offset": 2, "open": True},
    "cosmopolitan_culture:edit": {"name": "The Folk of the Far Crossing", "lingua_franca_entity_id": Pick(EntityType.LANGUAGE), "strength": 40},
    "cosmopolitan_member:edit": {"share": 60},
}
EDITS = {**EDITS, **CLIMES_EDITS}
LEVERS.update(
    {
        "region_wind:set": given(**WIND_UP[1]),
        **{name: after(WIND_UP, region_id=Pick(REGION)) for name in ("region_wind:edit", "region_wind:delete")},
        "monsoon_season:set": given(**MONSOON_UP[1]),
        **{name: after(MONSOON_UP, world_id=Pick("world"), epoch=1) for name in ("monsoon_season:edit", "monsoon_season:delete")},
        "climate_oscillation:set": given(**SWING_UP[1]),
        **{name: after(SWING_UP, world_id=Pick("world")) for name in ("climate_oscillation:edit", "climate_oscillation:delete")},
        "launch_window:set": given(**WINDOW_UP[1]),
        **{name: after(WINDOW_UP, from_world_id=Pick("world"), to_world_id=Pick("world", 1)) for name in ("launch_window:edit", "launch_window:delete")},
        "cosmopolitan_culture:create": given(**ROAD_UP[1]),
        **{name: after(ROAD_UP, record_id=Newest("cosmopolitan_culture")) for name in ("cosmopolitan_culture:edit", "cosmopolitan_culture:delete")},
        "cosmopolitan_culture:value": after(ROAD_UP, culture_id=Newest("cosmopolitan_culture"), axis="tradition", value=30),
        "cosmopolitan_member:set": after(ROAD_UP, **ROAD_MEMBER_UP[1]),
        **{
            name: after(ROAD_UP, ROAD_MEMBER_UP, culture_id=Newest("cosmopolitan_culture"), community_id=Pick(TOWN))
            for name in ("cosmopolitan_member:edit", "cosmopolitan_member:delete")
        },
    }
)

LEVERS.update(
    {name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in CLIMES_EDITS.items()}
)


IDENTITY_UP = ("held_identity:set", {"holder_id": Pick(TOWN), "layer": "faith", "salience": 60})
PEER_UP = ("peer_group:create", {"settlement_entity_id": Pick(TOWN), "social_class": "farmer", "play": "games"})
PEER_MEMBER_UP = ("peer_member:set", {"group_id": Newest("peer_group"), "mortal_id": Pick(MORTAL), "deprived_epochs": 0})
SANCTUARY_UP = (
    "sanctuary:create",
    {
        "fugitive_entity_id": Pick(MORTAL),
        "host_entity_id": Pick(TOWN),
        "kind": "hospitality",
        "fugitive_kind": "accused",
        "pursuer_entity_id": Pick(REALM),
    },
)
LAW_UP = ("sanctuary_law:set", {"polity_id": Pick(REALM), "restricted": True, "fee_pct": 10})
SATIRE_UP = ("satire:create", {"satirist_entity_id": Pick(MORTAL), "target_entity_id": Pick(MORTAL, 1), "polity_entity_id": Pick(REALM), "bite": 30})
BELONGING_EDITS: Mapping[str, Mapping[str, Any]] = {
    "held_identity:edit": {"value_node_id": Pick(PEOPLE), "value_label": None, "strength": 70, "salience": 40, "driver": "rhetoric"},
    "peer_group:edit": {
        "settlement_entity_id": Pick(TOWN),
        "social_class": "artisan",
        "play": "songs",
        "children": 4,
        "cohesion": 50,
        "deprived": False,
        "dissolved_epoch": 2,
    },
    "peer_member:edit": {"deprived_epochs": 1},
    "sanctuary:edit": {
        "host_entity_id": Pick(TOWN),
        "kind": "temple",
        "fugitive_kind": "outlaw",
        "pursuer_entity_id": Pick(REALM),
        "state": "besieged",
        "fee": 3,
        "siege_epochs": 1,
    },
    "sanctuary_law:edit": {"restricted": False, "fee_pct": 20},
    "satire:edit": {
        "satirist_entity_id": Pick(MORTAL),
        "target_entity_id": Pick(MORTAL, 1),
        "polity_entity_id": Pick(REALM),
        "work_entity_id": None,
        "source": "artwork",
        "bite": 40,
        "tolerated": False,
        "punished": True,
        "judged": True,
    },
}
EDITS = {**EDITS, **BELONGING_EDITS}
LEVERS.update(
    {
        "held_identity:set": given(**IDENTITY_UP[1]),
        **{name: after(IDENTITY_UP, holder_id=Pick(TOWN), layer="faith") for name in ("held_identity:edit", "held_identity:delete")},
        "peer_group:create": given(**PEER_UP[1]),
        **{name: after(PEER_UP, record_id=Newest("peer_group")) for name in ("peer_group:edit", "peer_group:delete")},
        "peer_member:set": after(PEER_UP, **PEER_MEMBER_UP[1]),
        **{name: after(PEER_UP, PEER_MEMBER_UP, group_id=Newest("peer_group"), mortal_id=Pick(MORTAL)) for name in ("peer_member:edit", "peer_member:delete")},
        "sanctuary:create": given(**SANCTUARY_UP[1]),
        **{name: after(SANCTUARY_UP, record_id=Newest("sanctuary")) for name in ("sanctuary:edit", "sanctuary:delete")},
        "sanctuary_law:set": given(**LAW_UP[1]),
        **{name: after(LAW_UP, polity_id=Pick(REALM)) for name in ("sanctuary_law:edit", "sanctuary_law:delete")},
        "satire:create": given(**SATIRE_UP[1]),
        **{name: after(SATIRE_UP, record_id=Newest("satire")) for name in ("satire:edit", "satire:delete")},
    }
)

LEVERS.update(
    {name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in BELONGING_EDITS.items()}
)

PROGRAMME_UP = ("tech_programme:create", {"polity_id": Pick(REALM), "technique": "rocketry", "progress": 20, "stage": "planning", "visibility": 10})
ERA_EDITS: Mapping[str, Mapping[str, Any]] = {
    "tech_programme:edit": {"technique": "nuclear_power", "progress": 75, "stage": "testing", "visibility": 60, "sabotaged": 1, "finished_epoch": None},
}
EDITS = {**EDITS, **ERA_EDITS}
LEVERS.update(
    {
        "tech_programme:create": given(**PROGRAMME_UP[1]),
        **{name: after(PROGRAMME_UP, record_id=Newest("tech_programme")) for name in ("tech_programme:edit", "tech_programme:delete")},
    }
)
LEVERS.update({name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in ERA_EDITS.items()})

SOIL_UP = ("soil_microbiota:set", {"region_id": Pick(EntityType.REGION), "life": 40, "sterile_epochs": 0})
CULTURE_UP = ("ferment_culture:create", {"holder_entity_id": Pick(TOWN), "kind": "yeast", "quality": 30})
BOND_UP = (
    "species_relation:create",
    {"first_species_id": Pick(EntityType.SPECIES), "second_species_id": Pick(EntityType.SPECIES, 1), "kind": "mutualism", "strength": 40},
)
SENSE_UP = ("sense:set", {"holder_id": Pick(EntityType.PEOPLE), "sense": "smell", "acuity": 60})
NATURE_EDITS: Mapping[str, Mapping[str, Any]] = {
    "soil_microbiota:edit": {"life": 30, "sterile_epochs": 1},
    "ferment_culture:edit": {"holder_entity_id": Pick(TOWN), "kind": "mould", "quality": 50, "lost_epoch": None},
    "species_relation:edit": {
        "first_species_id": Pick(EntityType.SPECIES),
        "second_species_id": Pick(EntityType.SPECIES, 1),
        "kind": "parasitism",
        "strength": 60,
    },
    "sense:edit": {"acuity": 80},
}
EDITS = {**EDITS, **NATURE_EDITS}
LEVERS.update(
    {
        "soil_microbiota:set": given(**SOIL_UP[1]),
        **{name: after(SOIL_UP, region_id=Pick(EntityType.REGION)) for name in ("soil_microbiota:edit", "soil_microbiota:delete")},
        "ferment_culture:create": given(**CULTURE_UP[1]),
        **{name: after(CULTURE_UP, record_id=Newest("ferment_culture")) for name in ("ferment_culture:edit", "ferment_culture:delete")},
        "species_relation:create": given(**BOND_UP[1]),
        **{name: after(BOND_UP, record_id=Newest("species_relation")) for name in ("species_relation:edit", "species_relation:delete")},
        "sense:set": given(**SENSE_UP[1]),
        **{name: after(SENSE_UP, holder_id=Pick(EntityType.PEOPLE), sense="smell") for name in ("sense:edit", "sense:delete")},
    }
)
LEVERS.update(
    {name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in NATURE_EDITS.items()}
)


async def means_ground(session: AsyncSession) -> None:
    town = await canon(session, TOWN, 0)
    item = await canon(session, EntityType.ITEM, 0)
    lore = await canon(session, EntityType.KNOWLEDGE, 0)
    if item is not None and lore is not None and await session.get(BookContentRow, (item, lore)) is None:
        session.add(BookContentRow(book_entity_id=item, knowledge_entity_id=lore, fidelity=80))
    if town is not None and await session.scalar(select(HouseholdRow.id).limit(1)) is None:
        session.add(HouseholdRow(name="House of the Harness", settlement_node_id=town, wealth=100, income=20, expenses=5, locked=[]))
    coins = list(await session.scalars(select(CurrencyRow.id)))
    realm = await canon(session, REALM, 0)
    for index in range(len(coins), 2):
        issuer = realm if realm is not None else town
        if issuer is not None:
            session.add(
                CurrencyRow(issuer_entity_id=issuer, name=f"Harness Coin {index}", metal=MaterialKind.SILVER, purity=80, supply=100, trust=70, minted_epoch=1)
            )
    await session.flush()


BOOK = Computed(lambda session: session.scalar(select(BookContentRow.book_entity_id).order_by(BookContentRow.book_entity_id).limit(1)))
BILL = Computed(lambda session: session.scalar(select(BillOfExchangeRow.id).order_by(BillOfExchangeRow.id.desc()).limit(1)))
FREE_UNIT = Computed(
    lambda session: session.scalar(
        select(ArmyUnitRow.id)
        .where(ArmyUnitRow.id.not_in(select(NamedUnitRow.unit_id).where(NamedUnitRow.unit_id.is_not(None))))
        .order_by(ArmyUnitRow.id)
        .limit(1)
    )
)
HOUSEHOLD = Computed(lambda session: session.scalar(select(HouseholdRow.id).order_by(HouseholdRow.id).limit(1)))
CUSTOM_UP = ("writing_custom:set", {"people_id": Pick(EntityType.PEOPLE), "medium": "papyrus"})
WORK_UP = ("written_work:set", {"work_id": BOOK, "medium": "parchment", "condition": 90, "copies": 1})
VAULT_UP = ("security:set", {"holder_id": Pick(TOWN), "lock": "warded", "lock_quality": 40, "sealed": False, "guards": 1, "traps": False})
LIFT_UP = ("water_lift:set", {"settlement_id": Pick(TOWN), "device": "noria", "count": 2})
KIT_UP = ("navigation_kit:set", {"holder_id": Pick(TOWN), "aid": "astrolabe", "quality": 40})
STOCK_UP = ("container_stock:set", {"community_id": Pick(TOWN), "kind": "barrel", "count": 12, "broken": 0})
SAVING_UP = ("saving:set", {"household_id": HOUSEHOLD, "share_pct": 15, "form": "deposit", "saved": 0})
HOARD_UP = ("hoard:create", {"place_id": Pick(TOWN), "amount": 30, "state": "hidden"})
RATE_UP = ("exchange_rate:create", {"base_currency_id": Pick("currency"), "quote_currency_id": Pick("currency", 1), "market_id": Pick(TOWN), "rate": 120})
BILL_UP = ("bill_of_exchange:create", {"drawer_id": Pick(TOWN), "payee_id": Pick(TOWN, 1), "from_id": Pick(TOWN), "to_id": Pick(TOWN, 1), "amount": 25})
ORDER_UP = ("economic_order:create", {"polity_id": Pick(REALM), "sector": "cloth", "allocation": "command", "planning_capacity": 40})
ORDER_KIND_UP = ("economic_order_kind:create", {"name": "Harness Order", "ownership": "common", "allocation": "need", "labour": "kin", "distribution": "equal"})
TRANSITION_UP = ("order_transition:create", {"polity_id": Pick(REALM), "kind": "land_reform", "compensation": "partial"})
PUT_OUT_UP = ("putting_out:create", {"merchant_id": Pick(EntityType.FACTION), "town_id": Pick(TOWN), "raw": "wool", "product": "cloth", "volume": 8})
CHAIN_UP = ("chain_holding:set", {"holder_id": Pick(EntityType.FACTION), "town_id": Pick(TOWN), "product": "cloth", "share_pct": 25})
FLOW_UP = ("tourist_flow:create", {"origin_id": Pick(TOWN), "sight_id": Pick(TOWN, 1), "sight": "city", "visitors": 15, "income": 30})
UNIT_UP = ("named_unit:create", {"name": "The Harness Guard", "unit_id": FREE_UNIT, "owner_id": Pick(REALM), "esprit": 45})
HONOUR_UP = ("unit_honour:create", {"named_unit_id": Newest("named_unit"), "kind": "victory", "note": "the harness field"})
GRANT_UP = ("veteran_grant:create", {"polity_id": Pick(REALM), "kind": "pension", "veterans": 12})
MEANS_EDITS: Mapping[str, Mapping[str, Any]] = {
    "writing_custom:edit": {"medium": "paper"},
    "written_work:edit": {"medium": "paper", "condition": 70, "copies": 3},
    "security:edit": {"lock": "tumbler", "lock_quality": 55, "sealed": True, "guards": 2, "traps": True, "thwarted": 1},
    "water_lift:edit": {"count": 3},
    "navigation_kit:edit": {"quality": 60},
    "container_stock:edit": {"count": 20, "broken": 2},
    "saving:edit": {"share_pct": 20, "form": "investment", "saved": 10},
    "hoard:edit": {
        "holder_node_id": Pick(MORTAL),
        "place_entity_id": Pick(TOWN),
        "amount": 40,
        "state": "lost",
        "found_by_node_id": None,
        "hidden_epoch": 1,
        "found_epoch": None,
    },
    "exchange_rate:edit": {"rate": 140, "spread_pct": 6, "changer_node_id": Pick(MORTAL), "convertible": False, "volume": 5},
    "bill_of_exchange:edit": {
        "drawer_node_id": Pick(TOWN),
        "payee_node_id": Pick(TOWN, 1),
        "from_entity_id": Pick(TOWN),
        "to_entity_id": Pick(TOWN, 1),
        "amount": 30,
        "settled": True,
    },
    "economic_order:edit": {
        "sector": "grain",
        "ownership": "state",
        "allocation": "redistribution",
        "labour": "corvee",
        "distribution": "by_office",
        "planning_capacity": 55,
        "kind_id": None,
    },
    "economic_order_kind:edit": {"name": "Harness Order Renamed", "ownership": "private", "allocation": "market", "labour": "free", "distribution": "by_share"},
    "order_transition:edit": {"kind": "emancipation", "stage": "transferring", "compensation": "full", "resistance": 10, "transferred": 1, "ended_epoch": None},
    "putting_out:edit": {"town_entity_id": Pick(TOWN), "raw": "fibre", "product": "cloth", "volume": 12, "active": True},
    "chain_holding:edit": {"share_pct": 30},
    "tourist_flow:edit": {"sight": "wonder", "visitors": 25, "income": 50},
    "named_unit:edit": {
        "name": "The Harness Guard of Old",
        "nickname": "the Steady",
        "esprit": 60,
        "battles": 2,
        "unit_id": FREE_UNIT,
        "owner_entity_id": Pick(REALM),
        "raised_from_entity_id": Pick(TOWN),
        "disbanded_epoch": None,
    },
    "unit_honour:edit": {"kind": "stand", "note": "the harness ford"},
    "veteran_grant:edit": {"kind": "land", "veterans": 20, "settlement_entity_id": Pick(TOWN)},
}
EDITS = {**EDITS, **MEANS_EDITS}
LEVERS.update(
    {
        "writing_custom:set": given(**CUSTOM_UP[1]),
        **{name: after(CUSTOM_UP, people_id=Pick(EntityType.PEOPLE)) for name in ("writing_custom:edit", "writing_custom:delete")},
        "written_work:set": setup_then(means_ground, **WORK_UP[1]),
        **{name: setup_then(means_ground, WORK_UP, work_id=BOOK) for name in ("written_work:edit", "written_work:delete")},
        "security:set": given(**VAULT_UP[1]),
        **{name: after(VAULT_UP, holder_id=Pick(TOWN)) for name in ("security:edit", "security:delete")},
        "water_lift:set": given(**LIFT_UP[1]),
        **{name: after(LIFT_UP, settlement_id=Pick(TOWN), device="noria") for name in ("water_lift:edit", "water_lift:delete")},
        "navigation_kit:set": given(**KIT_UP[1]),
        **{name: after(KIT_UP, holder_id=Pick(TOWN), aid="astrolabe") for name in ("navigation_kit:edit", "navigation_kit:delete")},
        "container_stock:set": given(**STOCK_UP[1]),
        **{name: after(STOCK_UP, community_id=Pick(TOWN), kind="barrel") for name in ("container_stock:edit", "container_stock:delete")},
        "saving:set": setup_then(means_ground, **SAVING_UP[1]),
        **{name: setup_then(means_ground, SAVING_UP, household_id=HOUSEHOLD) for name in ("saving:edit", "saving:delete")},
        "hoard:create": given(**HOARD_UP[1]),
        **{name: after(HOARD_UP, record_id=Newest("hoard")) for name in ("hoard:edit", "hoard:delete")},
        "exchange_rate:create": setup_then(means_ground, **RATE_UP[1]),
        **{name: setup_then(means_ground, RATE_UP, record_id=Newest("exchange_rate")) for name in ("exchange_rate:edit", "exchange_rate:delete")},
        "bill_of_exchange:create": given(**BILL_UP[1]),
        **{name: after(BILL_UP, record_id=BILL) for name in ("bill_of_exchange:edit", "bill_of_exchange:delete")},
        "economic_order:create": given(**ORDER_UP[1]),
        **{name: after(ORDER_UP, record_id=Newest("economic_order")) for name in ("economic_order:edit", "economic_order:delete")},
        "economic_order_kind:create": given(**ORDER_KIND_UP[1]),
        **{name: after(ORDER_KIND_UP, record_id=Newest("economic_order_kind")) for name in ("economic_order_kind:edit", "economic_order_kind:delete")},
        "order_transition:create": given(**TRANSITION_UP[1]),
        **{
            name: after(TRANSITION_UP, record_id=Newest("order_transition"))
            for name in ("order_transition:edit", "order_transition:delete", "order_transition:advance")
        },
        "putting_out:create": given(**PUT_OUT_UP[1]),
        **{name: after(PUT_OUT_UP, record_id=Newest("putting_out")) for name in ("putting_out:edit", "putting_out:delete")},
        "chain_holding:set": given(**CHAIN_UP[1]),
        **{
            name: after(CHAIN_UP, holder_id=Pick(EntityType.FACTION), town_id=Pick(TOWN), product="cloth")
            for name in ("chain_holding:edit", "chain_holding:delete")
        },
        "tourist_flow:create": given(**FLOW_UP[1]),
        **{name: after(FLOW_UP, record_id=Newest("tourist_flow")) for name in ("tourist_flow:edit", "tourist_flow:delete")},
        "named_unit:create": given(**UNIT_UP[1]),
        **{name: after(UNIT_UP, record_id=Newest("named_unit")) for name in ("named_unit:edit", "named_unit:delete")},
        "unit_honour:create": after(UNIT_UP, **HONOUR_UP[1]),
        **{name: after(UNIT_UP, HONOUR_UP, record_id=Newest("unit_honour")) for name in ("unit_honour:edit", "unit_honour:delete")},
        "veteran_grant:create": given(**GRANT_UP[1]),
        **{name: after(GRANT_UP, record_id=Newest("veteran_grant")) for name in ("veteran_grant:edit", "veteran_grant:delete")},
    }
)
LEVERS.update({name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in MEANS_EDITS.items()})
LEVERS.update(
    {
        "world_view:edit": given(world_id=WORLD, values={"storm_pct": 150, "need": "heat", "fire": False, "light": "magic"}, release=[]),
        "world_view:reset": given(world_id=WORLD),
    }
)
LEVERS.update(
    {
        "biology:edit": given(holder_id=Pick(EntityType.PEOPLE), values={"food_need_pct": 80, "breathes": False, "storm_harm_pct": 150}, release=[]),
        "biology_variant:add": given(holder_id=Pick(EntityType.PEOPLE), variant="aquatic"),
        "biology_variant:remove": given(holder_id=Pick(EntityType.PEOPLE), variant="aquatic"),
        "biology:reset": given(holder_id=Pick(EntityType.PEOPLE)),
    }
)


async def lore_and_outer(session: AsyncSession) -> None:
    world = await session.scalar(select(EntityRow.world_id).where(EntityRow.entity_type == EntityType.SETTLEMENT).order_by(EntityRow.id).limit(1))
    for kind, name, stats in (
        (EntityType.IDEOLOGY, "The Plain Way", IdeologyStats()),
        (EntityType.OUTER_BEING, "The Hollow Reach", OuterBeingStats(interest=0)),
    ):
        await open_record(session, 1, RecordSpec(entity_type=kind, name=name, body="", stats=stats, power=1, world_id=world))
    await rich_creator(session)


async def looted_piece(session: AsyncSession) -> None:
    piece = await session.scalar(select(MuseumPieceRow).order_by(MuseumPieceRow.id.desc()).limit(1))
    victim = await canon(session, EntityType.SETTLEMENT, 1)
    assert piece is not None and victim is not None
    piece.looted_from_entity_id = victim
    await session.flush()


MUSEUM = ("museum:found", {"keeper_id": Pick(TOWN), "kind": "museum"})
PIECE = ("museum_piece:add", {"collection_id": Newest("museum_collections"), "kind": "specimen", "item_id": Pick(EntityType.SPECIES)})
FOSSIL_BED = ("fossil_bed:create", {"region_id": Pick(REGION), "source": "megafauna", "richness": 50})
GARDEN = ("garden:found", {"town_id": Pick(TOWN), "kind": "physic"})
ENDED = ("world_end:declare", {"world_id": WORLD, "state": "transfigured", "cause": "belief_drift", "new_type": "hollow"})
LEVERS.update(
    {
        "lifecycle:edit": setup_then(lore_and_outer, holder_id=Newest(EntityType.IDEOLOGY), values={"state": "dormant", "idle_epochs": 2}, release=[]),
        "lifecycle:reset": setup_then(lore_and_outer, holder_id=Newest(EntityType.IDEOLOGY)),
        "lifecycle:destroy": setup_then(lore_and_outer, holder_id=Newest(EntityType.OUTER_BEING)),
        "world_end:declare": Lever(values={"world_id": WORLD, "state": "transfigured", "cause": "belief_drift", "new_type": "hollow"}, setup=rich_creator),
        "world_end:edit": setup_then(rich_creator, ENDED, world_id=WORLD, values={"cause": "divine_wrath", "state": "transfigured"}, release=[]),
        "world_end:remove": setup_then(rich_creator, ENDED, world_id=WORLD),
        "fossil_bed:create": given(region_id=Pick(REGION), source="megafauna", richness=50),
        "fossil_bed:edit": after(FOSSIL_BED, bed_id=Newest("fossil_beds"), values={"richness": 70, "reading": "deep_time", "frozen": True}, release=[]),
        "fossil_bed:delete": after(FOSSIL_BED, bed_id=Newest("fossil_beds")),
        "fossil_bed:reveal": after(FOSSIL_BED, bed_id=Newest("fossil_beds")),
        "museum:found": given(keeper_id=Pick(TOWN), kind="museum"),
        "museum:edit": after(MUSEUM, collection_id=Newest("museum_collections"), values={"prestige": 40, "kind": "cabinet"}, release=[]),
        "museum:delete": after(MUSEUM, collection_id=Newest("museum_collections")),
        "museum_piece:add": after(MUSEUM, collection_id=Newest("museum_collections"), kind="specimen", item_id=Pick(EntityType.SPECIES)),
        "museum_piece:edit": after(MUSEUM, PIECE, piece_id=Newest("museum_pieces"), values={"kind": "relic"}, release=[]),
        "museum_piece:remove": after(MUSEUM, PIECE, piece_id=Newest("museum_pieces")),
        "museum_piece:restitute": Lever(values={"piece_id": Newest("museum_pieces")}, before=(MUSEUM, PIECE), then=looted_piece),
        "garden:found": given(town_id=Pick(TOWN), kind="physic"),
        "garden:edit": after(GARDEN, garden_id=Newest("gardens"), values={"condition": 80, "upkeep": 12, "kind": "park"}, release=[]),
        "garden:delete": after(GARDEN, garden_id=Newest("gardens")),
        "garden:plant": after(GARDEN, garden_id=Newest("gardens"), species_id=Pick(EntityType.SPECIES)),
        "garden:uproot": after(GARDEN, garden_id=Newest("gardens"), species_id=Pick(EntityType.SPECIES)),
    }
)


async def first_world(session: AsyncSession) -> int:
    found = await session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    assert found is not None
    return found


async def running_prehistory(session: AsyncSession) -> None:
    row = await session.get(PrehistoryRow, await first_world(session))
    assert row is not None
    row.state = PrehistoryState.RUNNING
    await session.flush()


async def prehistory_happening(session: AsyncSession) -> None:
    world_id = await first_world(session)
    if await session.get(PrehistoryRow, world_id) is None:
        session.add(PrehistoryRow(world_id=world_id, kind=PrehistoryKind.FULL, state=PrehistoryState.DONE, epochs=1, rounds_done=1, locked=[]))
    session.add(PrehistoryEventRow(world_id=world_id, round=0, magnitude=40, source=PrehistorySource.BACKFILLED, subject_node_id=world_id, locked=[]))
    await session.flush()


async def deep_time_run(session: AsyncSession, state: DeepTimeState) -> None:
    run = DeepTimeRunRow(epochs=2, ran=1, from_epoch=1, to_epoch=1, state=state, locked=[])
    session.add(run)
    await session.flush()
    session.add(DeepTimeEventRow(run_id=run.id, epoch=1, magnitude=30, locked=[]))
    await session.flush()


async def running_deep_time(session: AsyncSession) -> None:
    await deep_time_run(session, DeepTimeState.RUNNING)


async def finished_deep_time(session: AsyncSession) -> None:
    await deep_time_run(session, DeepTimeState.DONE)


PLANNED = ("prehistory:configure", {"world_id": WORLD, "epochs": 2, "resolution": 1})
LEVERS.update(
    {
        "prehistory:configure": given(world_id=WORLD, epochs=2, resolution=1),
        "prehistory:edit": after(PLANNED, world_id=WORLD, values={"epochs": 3, "resolution": 2, "kind": "living", "state": "planned"}, release=[]),
        "prehistory:remove": after(PLANNED, world_id=WORLD),
        "prehistory:abort": Lever(values={"world_id": WORLD}, before=(PLANNED,), then=running_prehistory),
        "prehistory_event:edit": Lever(
            values={"event_id": Newest("prehistory_events"), "values": {"magnitude": 60, "round": 2, "mirrored": True}, "release": []},
            setup=prehistory_happening,
        ),
        "prehistory_event:remove": Lever(values={"event_id": Newest("prehistory_events")}, setup=prehistory_happening),
        "deep_time:stop": Lever(values={"run_id": Newest("deep_time_runs")}, setup=running_deep_time),
        "deep_time:edit": Lever(values={"run_id": Newest("deep_time_runs"), "values": {"state": "stopped"}, "release": []}, setup=finished_deep_time),
        "deep_time:remove": Lever(values={"run_id": Newest("deep_time_runs")}, setup=finished_deep_time),
        "deep_time_event:edit": Lever(values={"event_id": Newest("deep_time_events"), "values": {"magnitude": 55}, "release": []}, setup=finished_deep_time),
        "deep_time_event:remove": Lever(values={"event_id": Newest("deep_time_events")}, setup=finished_deep_time),
    }
)


async def planned_prehistory(session: AsyncSession) -> None:
    world_id = await first_world(session)
    known = await session.get(PrehistoryRow, world_id)
    if known is not None:
        await session.delete(known)
        await session.flush()
    session.add(PrehistoryRow(world_id=world_id, kind=PrehistoryKind.FULL, state=PrehistoryState.PLANNED, epochs=1, resolution=1, locked=[]))
    await session.flush()


async def lore_free_world(session: AsyncSession) -> None:
    await rich_creator(session)
    home = await session.get(WorldRow, await first_world(session))
    assert home is not None
    await WorldRepository(session).create_world(
        WorldDraft(
            name="Quiet Shore",
            world_type=WorldType.ORDINARY,
            orbit=home.orbit + 1,
            terrain_seed="quiet",
            terrain_sea=0.3,
            terrain_mountains=0.3,
            terrain_humidity=0.5,
            danger=10,
            created_epoch=1,
            star_id=home.star_id,
        )
    )


FALLEN = ("transform:force", {"kind": "fall", "subject_id": Pick("son")})
BLOCKED_FALL = ("transform:block", {"kind": "fall", "subject_id": Pick("son")})
DIMMED = ("star_modifier:create", {"star_id": Pick("star"), "luminosity_pct": -20, "age_epochs": 5, "decay": 2})
LEVERS.update(
    {
        "transform:force": given(kind="fall", subject_id=Pick("son")),
        "transform:block": given(kind="fall", subject_id=Pick("son")),
        "transform:release": after(BLOCKED_FALL, kind="fall", subject_id=Pick("son")),
        "transform:revert": after(FALLEN, transformation_id=Newest("transformations")),
        "transformation:edit": after(
            FALLEN, transformation_id=Newest("transformations"), values={"trigger": "forced", "subject_name": "Old", "result_name": "New"}, release=[]
        ),
        "transformation:delete": after(FALLEN, transformation_id=Newest("transformations")),
        "transform_prospect:edit": after(
            BLOCKED_FALL,
            prospect_id=Newest("transform_prospects"),
            values={"progress": 40, "stance": "open", "trigger": "engine", "warned_epoch": 1, "due_epoch": 2},
            release=[],
        ),
        "transform_prospect:delete": after(BLOCKED_FALL, prospect_id=Newest("transform_prospects")),
        "star_modifier:create": given(star_id=Pick("star"), luminosity_pct=-20, age_epochs=5, decay=2),
        "star_modifier:edit": after(
            DIMMED, modifier_id=Newest("star_modifiers"), values={"luminosity_pct": -10, "age_epochs": 3, "decay": 1, "source": "divine_act"}, release=[]
        ),
        "star_modifier:delete": after(DIMMED, modifier_id=Newest("star_modifiers")),
    }
)


async def earlier_sociolect(session: AsyncSession) -> int | None:
    return await session.scalar(select(SociolectRow.id).order_by(SociolectRow.id.desc()).offset(1).limit(1))


FOLK = EntityType.PEOPLE
TALKERS = ("sociolect:create", {"holder_id": Pick(FOLK), "kind": "guild"})
COURTLY = ("sociolect:create", {"holder_id": Pick(FOLK), "kind": "court"})
SIGNERS = ("sign_language:create", {"community_id": Pick(FOLK), "cause": "deafness"})
UNBURIED = ("carrion:keep", {"region_id": Pick(EntityType.REGION), "kept": True})
HAPPENING = ("collection:create", {"kind": "war", "members": [{"node_id": Pick(REALM)}]})
REMEMBERED = ("beast_lore:grant", {"beast_id": Newest(EntityType.BEAST), "collection_id": Newest("incident_collection")})
TAUGHT = ("teaching:grant", {"teacher_id": Newest(EntityType.BEAST), "learner_id": Pick(FOLK), "kind": "account"})
TRUCE = ("field_agreement:force", {"kind": "truce", "place_id": Pick(TOWN)})
SEALED = ("deep_seal:seal", {"place_id": Pick(TOWN)})
FORM = ("lore:create", {"entity_type": "art_form", "name": "Reed Song", "world_id": Pick("world"), "values": {"discipline": "musical"}})
FASHION = {"novelty": 40, "adoption": 30, "revivals": 1}
FASHIONED = ("novelty:set", {"holder_id": Newest(EntityType.ART_FORM), "values": FASHION, "release": []})
COUPLING_EDITS: Mapping[str, Mapping[str, Any]] = {
    "sociolect:edit": {"kind": "court", "prestige": 20, "secret": True, "salience": 50, "faded_epoch": 3},
    "sign_origin:edit": {"cause": "silence_vow"},
    "carrion:edit": {"carrion": 40, "scavenged": 10, "preserved": True, "rest": "frozen", "kept": False},
    "teaching:edit": {"kind": "account", "fidelity": 50, "state": "sold", "price": 5},
    "field_agreement:edit": {"kind": "truce", "state": "ended", "term_epoch": 9, "honour": 10},
    "deep_seal:edit": {"kind": "rite", "strength": 60, "decay": 2},
    "novelty:set": FASHION,
}
EDITS = {**EDITS, **COUPLING_EDITS}
LEVERS.update(
    {
        "rite_component:set": after(RITE, rite_id=Newest(EntityType.RITE), component="sung", present=True),
        "restraint:set": after(
            ("captive:take", {"captor_id": Pick(TOWN), "mortal_id": Pick(MORTAL, 1)}), captive_id=Newest("captives"), restraint="gag", present=True
        ),
        "sociolect:create": given(holder_id=Pick(FOLK), kind="guild"),
        "sociolect:merge": after(TALKERS, COURTLY, kept_id=Computed(earlier_sociolect), merged_id=Newest("sociolects")),
        "sociolect:edit": after(TALKERS, sociolect_id=Newest("sociolects"), values=COUPLING_EDITS["sociolect:edit"], release=[]),
        "sociolect:delete": after(TALKERS, sociolect_id=Newest("sociolects")),
        "sign_language:create": given(community_id=Pick(FOLK), cause="deafness"),
        "sign_origin:edit": after(SIGNERS, language_id=Newest(EntityType.LANGUAGE), values=COUPLING_EDITS["sign_origin:edit"], release=[]),
        "sign_origin:delete": after(SIGNERS, language_id=Newest(EntityType.LANGUAGE)),
        "carrion:keep": given(region_id=Pick(EntityType.REGION), kept=True),
        "carrion:clear": after(UNBURIED, region_id=Pick(EntityType.REGION)),
        "carrion:edit": after(UNBURIED, region_id=Pick(EntityType.REGION), values=COUPLING_EDITS["carrion:edit"], release=[]),
        "beast_lore:grant": after(BEAST, HAPPENING, beast_id=Newest(EntityType.BEAST), collection_id=Newest("incident_collection")),
        "beast_lore:reveal": after(BEAST, HAPPENING, REMEMBERED, beast_id=Newest(EntityType.BEAST), learner_id=Pick(FOLK)),
        "teaching:grant": after(BEAST, HAPPENING, REMEMBERED, teacher_id=Newest(EntityType.BEAST), learner_id=Pick(FOLK), kind="account"),
        "teaching:block": after(BEAST, teacher_id=Newest(EntityType.BEAST), learner_id=Pick(FOLK)),
        "teaching:edit": after(BEAST, HAPPENING, REMEMBERED, TAUGHT, teaching_id=Newest("teachings"), values=COUPLING_EDITS["teaching:edit"], release=[]),
        "teaching:delete": after(BEAST, HAPPENING, REMEMBERED, TAUGHT, teaching_id=Newest("teachings")),
        "field_agreement:force": given(kind="truce", place_id=Pick(TOWN)),
        "field_agreement:void": after(TRUCE, agreement_id=Newest("field_agreements")),
        "field_agreement:edit": after(TRUCE, agreement_id=Newest("field_agreements"), values=COUPLING_EDITS["field_agreement:edit"], release=[]),
        "field_agreement:delete": after(TRUCE, agreement_id=Newest("field_agreements")),
        "deep_seal:seal": given(place_id=Pick(TOWN), kind="divine", strength=80),
        "deep_seal:unseal": after(SEALED, seal_id=Newest("deep_seals")),
        "deep_seal:edit": after(SEALED, seal_id=Newest("deep_seals"), values=COUPLING_EDITS["deep_seal:edit"], release=[]),
        "deep_seal:delete": after(SEALED, seal_id=Newest("deep_seals")),
        "novelty:set": after(FORM, holder_id=Newest(EntityType.ART_FORM), values=FASHION, release=[]),
        "novelty:delete": after(FORM, FASHIONED, holder_id=Newest(EntityType.ART_FORM)),
    }
)


async def chartered_company(session: AsyncSession) -> None:
    faction = await session.scalar(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )
    assert faction is not None
    if await session.get(CompanyProfileRow, faction) is None:
        session.add(CompanyProfileRow(faction_entity_id=faction, locked=[]))
    await session.flush()


NETWORK = Newest(EntityType.NETWORK)
NETWORK_UP = ("network:found", {"name": "The Coast Relay", "carrier": "relay", "owner_id": Pick(MORTAL), "place_id": Pick(TOWN)})
NETWORK_TOO = ("network:found", {"name": "The Hill Relay", "carrier": "wired", "owner_id": Pick(MORTAL, 1), "place_id": Pick(TOWN, 1)})
AUGMENT_UP = ("augment:install", {"bearer_id": Pick(MORTAL), "slot": "whole_body", "kind": "enhancement", "make": "made", "quality": 50})
EFFECT_UP = ("augment:effect", {"augment_id": Newest("augments"), "target": "skill", "key": "engineering", "amount": 10})
STORE_UP = ("data_store:open", {"holder_id": Pick(MORTAL), "owner_id": Pick(MORTAL), "security": 30})
CONTENT_UP = ("data_store:put", {"store_id": Newest("data_stores"), "content": "secret", "subject_id": Pick(MORTAL, 1)})
LINE_UP = ("replicator:found", {"name": "The Grey Line", "place_id": Pick(EntityType.REGION), "owner_id": Pick(MORTAL)})
SAVED_UP = ("mind:save", {"mind_id": Pick(MORTAL), "holder_id": Pick(MORTAL, 1), "owner_id": Pick(MORTAL, 1), "medium": "record"})
MINDS_EDITS: Mapping[str, Mapping[str, Any]] = {"augment:edit_effect": {"target": "capacity", "target_key": "grasp", "amount": 15}}
EDITS = {**EDITS, **MINDS_EDITS}
LEVERS.update(
    {
        "augment:install": given(bearer_id=Pick(MORTAL), slot="whole_body", kind="enhancement", make="made", quality=50),
        "augment:remove": after(AUGMENT_UP, augment_id=Newest("augments")),
        "augment:effect": after(AUGMENT_UP, augment_id=Newest("augments"), target="skill", key="engineering", amount=10),
        "augment:edit_effect": after(AUGMENT_UP, EFFECT_UP, effect_id=Newest("augment_effects"), values=MINDS_EDITS["augment:edit_effect"], release=[]),
        "augment:drop_effect": after(AUGMENT_UP, EFFECT_UP, effect_id=Newest("augment_effects")),
        "network:join": after(NETWORK_UP, network_id=NETWORK, member_id=Pick(TOWN, 2), role="end"),
        "network:link": after(NETWORK_UP, NETWORK_TOO, first_id=Newest(EntityType.NETWORK), second_id=Pick(EntityType.NETWORK)),
        "network:cut": after(NETWORK_UP, network_id=NETWORK, cause="storm", epochs=1, severity=40),
        "data_store:put": after(STORE_UP, store_id=Newest("data_stores"), content="secret", subject_id=Pick(MORTAL, 1)),
        "data_store:take": after(STORE_UP, CONTENT_UP, content_id=Newest("data_store_contents")),
        "company:hold": setup_then(chartered_company, company_id=Pick(EntityType.FACTION), holding_id=Pick(TOWN), kind="structure"),
        "replicator:stop": after(LINE_UP, line_id=Newest("replicator_lines")),
        "replicator:seed": after(LINE_UP, line_id=Newest("replicator_lines"), place_id=Pick(EntityType.REGION, 1), mass=5),
        "replicator:lift": after(LINE_UP, presence_id=Newest("replicator_presence")),
        "mind:restore": after(SAVED_UP, state_id=Newest("mind_states")),
        "salvage:open": given(site_id=Pick(TOWN), holder_id=Pick(MORTAL), yield_left=40),
    }
)


SOURCE_UP = ("source:create", {"name": "The Deep Well", "scope_id": Pick(EntityType.REGION), "locus": "place"})
MAGIC_SYSTEM_UP = ("magic_system:create", {"name": "The Old Way", "scope_id": Pick("world"), "structure": "innate"})
POWER_UP = ("power:create", {"holder_id": Pick(MORTAL), "technique": "perceive", "form": "mind", "strength": 4})
GRANTED_UP = ("power:grant", {"holder_id": Pick(MORTAL), "god_id": Pick("son"), "technique": "control", "form": "fate", "strength": 2})
TRUTH_UP = ("truth:create", {"title": "those who walk unseen", "subject_id": Pick(MORTAL), "kind": "presence", "methods": ["by_oath"]})
COST_UP = ("source_part:create", {"owner_id": Newest("power_sources"), "part": "cost", "values": {"cost": "hp", "weight": 40}})
GRAMMAR_UP = ("system_part:create", {"owner_id": Newest("magic_systems"), "part": "grammar", "values": {"technique": "ward", "form": "mind"}})
LIMIT_UP = ("power_part:create", {"owner_id": Newest("powers"), "part": "restriction", "values": {"kind": "spoken_vow", "strength_gain_pct": 20}})
POWER_EDITS: Mapping[str, Mapping[str, Any]] = {
    "source:edit": {"stability": 70, "renewal": "season", "visibility": "overt"},
    "source_part:edit": {"weight": 30},
    "magic_system:edit": {"predictability": 70, "structure": "mixed", "learnability": "gifted_only"},
    "system_part:edit": {"technique": "perceive", "form": "time"},
    "power:edit": {"strength": 5, "control": 60, "state": "strained"},
    "power_part:edit": {"strength_gain_pct": 35, "detail": "only before witnesses"},
    "truth:edit": {"strength": 70, "by_cover_story": True, "sanity_cost": 10},
}
EDITS = {**EDITS, **POWER_EDITS}
LEVERS.update(
    {
        "source:create": given(name="The Deep Well", scope_id=Pick(EntityType.REGION), locus="place"),
        "source:edit": after(SOURCE_UP, source_id=Newest("power_sources"), values=POWER_EDITS["source:edit"], release=[]),
        "source:delete": after(SOURCE_UP, source_id=Newest("power_sources")),
        "source_part:create": after(SOURCE_UP, owner_id=Newest("power_sources"), part="cost", values={"cost": "hp", "weight": 40}),
        "source_part:edit": after(SOURCE_UP, COST_UP, part_id=Newest("power_source_costs"), part="cost", values=POWER_EDITS["source_part:edit"]),
        "source_part:delete": after(SOURCE_UP, COST_UP, part_id=Newest("power_source_costs"), part="cost"),
        "magic_system:create": given(name="The Old Way", scope_id=Pick("world"), structure="innate"),
        "magic_system:edit": after(MAGIC_SYSTEM_UP, system_id=Newest("magic_systems"), values=POWER_EDITS["magic_system:edit"], release=[]),
        "magic_system:delete": after(MAGIC_SYSTEM_UP, system_id=Newest("magic_systems")),
        "system_part:create": after(MAGIC_SYSTEM_UP, owner_id=Newest("magic_systems"), part="grammar", values={"technique": "ward", "form": "mind"}),
        "system_part:edit": after(MAGIC_SYSTEM_UP, GRAMMAR_UP, part_id=Newest("magic_system_grammar"), part="grammar", values=POWER_EDITS["system_part:edit"]),
        "system_part:delete": after(MAGIC_SYSTEM_UP, GRAMMAR_UP, part_id=Newest("magic_system_grammar"), part="grammar"),
        "power:create": given(holder_id=Pick(MORTAL), technique="perceive", form="mind", strength=4),
        "power:edit": after(POWER_UP, power_id=Newest("powers"), values=POWER_EDITS["power:edit"], release=[]),
        "power:delete": after(POWER_UP, power_id=Newest("powers")),
        "power:awaken": after(POWER_UP, power_id=Newest("powers")),
        "power:suppress": after(POWER_UP, power_id=Newest("powers")),
        "power:grant": given(holder_id=Pick(MORTAL), god_id=Pick("son"), technique="control", form="fate", strength=2),
        "power:revoke": after(GRANTED_UP, power_id=Newest("powers"), god_id=Pick("son")),
        "power_part:create": after(POWER_UP, owner_id=Newest("powers"), part="trigger", values={"trigger": "danger"}),
        "power_part:edit": after(POWER_UP, LIMIT_UP, part_id=Newest("power_restrictions"), part="restriction", values=POWER_EDITS["power_part:edit"]),
        "power_part:delete": after(POWER_UP, LIMIT_UP, part_id=Newest("power_restrictions"), part="restriction"),
        "truth:create": given(title="those who walk unseen", subject_id=Pick(MORTAL), kind="presence", methods=["by_oath"]),
        "truth:edit": after(TRUTH_UP, truth_id=Newest("hidden_truths"), values=POWER_EDITS["truth:edit"], release=[]),
        "truth:delete": after(TRUTH_UP, truth_id=Newest("hidden_truths")),
        "truth:reveal": after(TRUTH_UP, truth_id=Newest("hidden_truths"), population_id=Pick(TOWN)),
        "truth:hide": after(TRUTH_UP, truth_id=Newest("hidden_truths")),
        "breach:trigger": after(TRUTH_UP, truth_id=Newest("hidden_truths"), cause="witness", place_id=Pick(TOWN)),
    }
)
LINE_UP = ("line:create", {"name": "The Long-Legged Line", "method": "selective_breeding", "maker_id": Pick(MORTAL), "source_ids": [Pick(EntityType.SPECIES)]})
LIFE_UP = ("living:create", {"thing_id": Pick(STRUCTURE), "metabolism": "light", "lifespan": 60})
TRAIT_UP = ("line_part:create", {"owner_id": Newest("living_lines"), "part": "trait", "values": {"trait": "speed", "strength": 30}})
BANK_UP = ("bank:create", {"structure_id": Pick(STRUCTURE), "holder_id": Pick(MORTAL)})
SAMPLE_UP = ("sample:create", {"owner_id": Pick(STRUCTURE), "part": "sample", "values": {"organism_node_id": Pick(EntityType.SPECIES), "quality": 70}})
HOST_UP = ("symbiont:host", {"host_id": Pick(MORTAL), "placement": "blood", "relation": "mutual"})
LIVING_EDITS: Mapping[str, Mapping[str, Any]] = {
    "living:edit": {"health": 70, "growth_stage": "grown", "bond": 60, "metabolism": "feeding", "feed_commodity": "fodder"},
    "line:edit": {"stability": 55, "fertility": "breeds_wild", "licensed": True},
    "line_part:edit": {"strength": 45},
    "bank:edit": {"upkeep": 3, "unpaid_epochs": 1},
    "sample:edit": {"quality": 90},
    "symbiont:edit": {"strength": 50, "relation": "parasitic"},
}
EDITS = {**EDITS, **LIVING_EDITS}
LEVERS.update(
    {
        "living:create": given(thing_id=Pick(STRUCTURE), metabolism="light", lifespan=60),
        "living:edit": after(LIFE_UP, thing_id=Pick(STRUCTURE), values=LIVING_EDITS["living:edit"], release=[]),
        "living:delete": after(LIFE_UP, thing_id=Pick(STRUCTURE)),
        "living:end": after(LIFE_UP, thing_id=Pick(STRUCTURE)),
        "line:create": given(name="The Long-Legged Line", method="selective_breeding", maker_id=Pick(MORTAL), source_ids=[Pick(EntityType.SPECIES)]),
        "line:edit": after(LINE_UP, line_id=Newest("living_lines"), values=LIVING_EDITS["line:edit"], release=[]),
        "line:delete": after(LINE_UP, line_id=Newest("living_lines")),
        "line:escape": after(LINE_UP, line_id=Newest("living_lines")),
        "line:contain": after(LINE_UP, ("line:escape", {"line_id": Newest("living_lines")}), line_id=Newest("living_lines")),
        "line_part:create": after(LINE_UP, owner_id=Newest("living_lines"), part="trait", values={"trait": "yield", "strength": 25}),
        "line_part:edit": after(LINE_UP, TRAIT_UP, part_id=Newest("living_line_traits"), part="trait", values=LIVING_EDITS["line_part:edit"]),
        "line_part:delete": after(LINE_UP, TRAIT_UP, part_id=Newest("living_line_traits"), part="trait"),
        "bank:create": given(structure_id=Pick(STRUCTURE), holder_id=Pick(MORTAL)),
        "bank:edit": after(BANK_UP, structure_id=Pick(STRUCTURE), values=LIVING_EDITS["bank:edit"], release=[]),
        "bank:delete": after(BANK_UP, structure_id=Pick(STRUCTURE)),
        "sample:create": after(BANK_UP, owner_id=Pick(STRUCTURE), part="sample", values={"organism_node_id": Pick(EntityType.SPECIES), "quality": 70}),
        "sample:edit": after(BANK_UP, SAMPLE_UP, part_id=Newest("gene_bank_samples"), part="sample", values=LIVING_EDITS["sample:edit"]),
        "sample:delete": after(BANK_UP, SAMPLE_UP, part_id=Newest("gene_bank_samples"), part="sample"),
        "sample:raise": after(BANK_UP, SAMPLE_UP, sample_id=Newest("gene_bank_samples"), maker_id=Pick(MORTAL)),
        "clone:create": given(source_id=Pick(MORTAL), maker_id=Pick(MORTAL)),
        "symbiont:host": given(host_id=Pick(MORTAL), placement="blood", relation="mutual"),
        "symbiont:edit": after(HOST_UP, symbiont_id=Newest("symbionts"), values=LIVING_EDITS["symbiont:edit"], release=[]),
        "symbiont:remove": after(HOST_UP, symbiont_id=Newest("symbionts")),
    }
)
FORTUNE_SOURCE_UP = ("fortune_source:create", {"holder_id": Pick(MORTAL), "kind": "blessing", "strength": 15, "epochs": 4})
FORTUNE_EDITS: Mapping[str, Mapping[str, Any]] = {
    "fortune:edit": {"fortune": 25, "streak": 3},
    "fortune_source:edit": {"strength": 20, "kind": "charm"},
}
EDITS = {**EDITS, **FORTUNE_EDITS}
LEVERS.update(
    {
        "fortune:edit": given(node_id=Pick(MORTAL), values=FORTUNE_EDITS["fortune:edit"], release=[]),
        "fortune_source:create": given(holder_id=Pick(MORTAL), kind="blessing", strength=15, epochs=4),
        "fortune_source:edit": after(FORTUNE_SOURCE_UP, source_id=Newest("fortune_sources"), values=FORTUNE_EDITS["fortune_source:edit"], release=[]),
        "fortune_source:delete": after(FORTUNE_SOURCE_UP, source_id=Newest("fortune_sources")),
        "fortune_law:set": given(world_id=Pick("world"), law="divine"),
        "mishap:trigger": given(victim_id=Pick(MORTAL), kind="fall", level=1),
    }
)
TECH_UP = ("technology:set", {"node_id": Pick("world"), "family": "medicine", "level": 4, "hold": True})
LEVERS.update(
    {
        "technology:set": given(node_id=Pick("world"), family="medicine", level=4, hold=True),
        "technology:release": after(TECH_UP, node_id=Pick("world"), family="medicine"),
        "technology:delete": after(TECH_UP, node_id=Pick("world"), family="medicine"),
    }
)
DIVINE_POWER = ("divine_power:create", {"holder_id": Pick(EntityType.MORTAL), "name": "A Kind Hand", "mode": "active", "cost": "attention", "cost_amount": 1})
LEVERS.update(
    {
        "divine_power:create": given(
            holder_id=Pick(EntityType.MORTAL), name="A Kind Hand", verb="heal", object="stat", object_key="hp", scope="person", domains=[]
        ),
        **{name: after(DIVINE_POWER, power_id=Newest("divine_powers")) for name in ("divine_power:delete", "divine_power:use")},
        "divine_power:edit": after(DIVINE_POWER, power_id=Newest("divine_powers"), values={"strength": 30, "verb": "protect", "scope": "community"}),
    }
)
EDITS = {**EDITS, "divine_power:edit": {"strength": 30, "verb": "protect", "scope": "community", "cooldown": 1}}
LEVERS.update({"divine_power:domains": after(DIVINE_POWER, power_id=Newest("divine_powers"), domains=["war", "harvest"])})
COVENANT_UP = ("covenant:offer", {"people_id": Pick(EntityType.PEOPLE), "duty": "peace", "promise": "plenty", "epochs": 4})
CHOSEN_UP = ("chosen:choose", {"node_id": Pick(EntityType.MORTAL), "favour": "gift"})
EDITS = {
    **EDITS,
    "creator_standing:edit": {"awe": 40, "love": 30, "stance": "reverence", "heresy": "absent_creator"},
    "covenant:edit": {"duty": "offerings", "promise": "guidance", "state": "sealed", "breaches": 1},
    "chosen:edit": {"favour": "foresight"},
    "depiction:edit": {"name": "The One Before", "nature": "unknowable", "aspect": "time"},
}
LEVERS.update(
    {
        "creator_standing:edit": given(people_id=Pick(EntityType.PEOPLE), values=EDITS["creator_standing:edit"], release=[]),
        "covenant:offer": given(people_id=Pick(EntityType.PEOPLE), duty="worship", promise="protection", epochs=3),
        "covenant:edit": after(COVENANT_UP, covenant_id=Newest("covenants"), values=EDITS["covenant:edit"], release=[]),
        "covenant:delete": after(COVENANT_UP, covenant_id=Newest("covenants")),
        "chosen:choose": given(node_id=Pick(EntityType.MORTAL), favour="protection"),
        "chosen:edit": after(CHOSEN_UP, node_id=Pick(EntityType.MORTAL), values=EDITS["chosen:edit"], release=[]),
        "chosen:release": after(CHOSEN_UP, node_id=Pick(EntityType.MORTAL)),
        "depiction:edit": given(people_id=Pick(EntityType.PEOPLE), values=EDITS["depiction:edit"], release=[]),
    }
)
TIE_UP = ("pantheon_tie:set", {"god_id": Pick("son"), "other_id": Pick("foreign_god"), "tie": "partner"})
SYNCRETISM_UP = ("syncretism:create", {"foreign_god_id": Pick("foreign_god"), "son_id": Pick("son"), "people_id": Pick(EntityType.PEOPLE)})
EDITS = {
    **EDITS,
    "pantheon:edit": {"structure": "court"},
    "pantheon_tie:edit": {"tie": "elder"},
    "syncretism:edit": {"dominant_node_id": Pick("son")},
}
LEVERS.update(
    {
        "pantheon:edit": given(world_id=Pick("world"), values=EDITS["pantheon:edit"], release=[]),
        "pantheon_tie:set": setup_then(foreign_god, god_id=Pick("son"), other_id=Pick("foreign_god"), tie="rival"),
        "pantheon_tie:edit": setup_then(foreign_god, TIE_UP, god_id=Pick("son"), other_id=Pick("foreign_god"), values=EDITS["pantheon_tie:edit"], release=[]),
        "pantheon_tie:delete": setup_then(foreign_god, TIE_UP, god_id=Pick("son"), other_id=Pick("foreign_god")),
        "syncretism:create": setup_then(foreign_god, foreign_god_id=Pick("foreign_god"), son_id=Pick("son"), people_id=Pick(EntityType.PEOPLE)),
        "syncretism:edit": setup_then(foreign_god, SYNCRETISM_UP, syncretism_id=Newest("syncretisms"), values=EDITS["syncretism:edit"], release=[]),
        "syncretism:delete": setup_then(foreign_god, SYNCRETISM_UP, syncretism_id=Newest("syncretisms")),
    }
)
SEAT_UP = ("divine_seat:set", {"god_id": Pick("son"), "seat": "invited"})
COUNCIL_UP = ("council_record:create", {"topic": "Whether the seas belong to one god", "passed": True})
VIOLATION_UP = ("council_violation:create", {"ruling_id": Newest("council_rulings"), "violator_id": Pick("son"), "step": "censure"})
EDITS = {
    **EDITS,
    "council_procedure:edit": {"quorum_pct": 40, "voting_rule": "weighted_by_rank", "creator_veto": True, "term_epochs": 8},
    "divine_seat:edit": {"seat": "recognised", "excluded_until": 3},
    "council_violation:edit": {"step": "duel"},
}
LEVERS.update(
    {
        "council_procedure:edit": given(values=EDITS["council_procedure:edit"], release=[]),
        "council_procedure:reset": after(("council_procedure:edit", {"values": {"quorum_pct": 60}, "release": []})),
        "divine_seat:set": given(god_id=Pick("son"), seat="by_pact"),
        "divine_seat:edit": after(SEAT_UP, god_id=Pick("son"), values=EDITS["divine_seat:edit"], release=[]),
        "divine_seat:delete": after(SEAT_UP, god_id=Pick("son")),
        "council_violation:create": after(DECREE, ruling_id=Newest("council_rulings"), violator_id=Pick("son"), step="sanction"),
        "council_violation:edit": after(DECREE, VIOLATION_UP, violation_id=Newest("council_violations"), values=EDITS["council_violation:edit"], release=[]),
        "council_violation:delete": after(DECREE, VIOLATION_UP, violation_id=Newest("council_violations")),
        "council:veto": after(DECREE, ruling_id=Newest("council_rulings")),
        "council_record:create": given(topic="Whether the seas belong to one god", passed=True),
        "council_record:edit": after(COUNCIL_UP, council_id=Newest("councils"), topic="Whether the seas are shared", passed=False),
        "council_record:delete": after(COUNCIL_UP, council_id=Newest("councils")),
    }
)


async def second_outer_being(session: AsyncSession) -> int:
    first = await outer_being(session)
    others = select(EntityRow.id).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.id != first)
    found = await session.scalar(others.order_by(EntityRow.id).limit(1))
    if found is not None:
        return found
    world = await session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    assert world is not None
    being = await EntityRepository(session).create(
        EntityDraft(
            name="The Second Listener",
            entity_type=EntityType.OUTER_BEING,
            description="From further outside.",
            stats=OuterBeingStats(size=20, interest=40, influence=20),
            power_level=3,
            origin=EntityOrigin.CREATOR,
            birth_epoch=1,
            world_id=world,
        )
    )
    await session.flush()
    return being.id


THE_LAW = Computed(natural_law)
THE_BEING = Computed(outer_being)
EXCEPTION_UP = ("law_exception:create", {"law_id": THE_LAW, "kind": "person", "node_id": Pick(MORTAL)})
THEORY_UP = ("law_theory:create", {"law_id": THE_LAW, "holder_id": Pick(EntityType.PEOPLE), "believed_operator": "set", "believed_value": 80})
PLAN_UP = ("outer_plan:set", {"being_id": THE_BEING, "goal": "gain_name", "progress": 20})
HERALD_UP = ("outer_herald:bind", {"being_id": THE_BEING, "herald_id": Pick(MORTAL, 1), "zeal": 70})
INCURSION_UP = ("outer_incursion:open", {"being_id": THE_BEING, "region_id": Pick(EntityType.REGION)})
PACT_UP = ("outer_pact:strike", {"being_id": THE_BEING, "holder_id": Pick(MORTAL, 2), "price": "offering"})
RELATION_UP = ("outer_relation:set", {"being_id": THE_BEING, "other_id": Computed(second_outer_being), "relation": "rival"})
SEAL_UP = ("outer_seal:set", {"being_id": THE_BEING, "kind": "seal", "strength": 70})
EDITS = {
    **EDITS,
    "law_exception:edit": {"kind": "kind", "entity_type": "mortal"},
    "law_theory:edit": {"believed_value": 90, "confidence": 60, "adapted_epochs": 3},
    "outer_plan:edit": {"progress": 50, "stage": 2},
    "outer_herald:edit": {"zeal": 80},
    "outer_incursion:edit": {"strength": 55, "stage": "breach"},
    "outer_pact:edit": {"price": "years", "paid": True},
    "outer_relation:edit": {"relation": "feeds_on"},
    "outer_seal:edit": {"strength": 40, "kind": "banish"},
}
LEVERS.update(
    {
        "law_grammar:set": given(law_id=THE_LAW, target="stat", operator="multiply", key="prosperity", value=120, condition="at_peace"),
        "law_exception:create": given(law_id=THE_LAW, kind="kind", entity_type="mortal"),
        "law_exception:edit": after(EXCEPTION_UP, exception_id=Newest("natural_law_exceptions"), values=EDITS["law_exception:edit"], release=[]),
        "law_exception:delete": after(EXCEPTION_UP, exception_id=Newest("natural_law_exceptions")),
        "law_theory:create": given(law_id=THE_LAW, holder_id=Pick(EntityType.PEOPLE), believed_operator="multiply", believed_value=60),
        "law_theory:edit": after(THEORY_UP, theory_id=Newest("law_theories"), values=EDITS["law_theory:edit"], release=[]),
        "law_theory:delete": after(THEORY_UP, theory_id=Newest("law_theories")),
        "outer_plan:set": given(being_id=THE_BEING, goal="open_rift", progress=10),
        "outer_plan:edit": after(PLAN_UP, plan_id=Newest("outer_plans"), values=EDITS["outer_plan:edit"], release=[]),
        "outer_plan:delete": after(PLAN_UP, plan_id=Newest("outer_plans")),
        "outer_herald:bind": given(being_id=THE_BEING, herald_id=Pick(MORTAL, 1), zeal=60),
        "outer_herald:edit": after(HERALD_UP, herald_id=Pick(MORTAL, 1), values=EDITS["outer_herald:edit"], release=[]),
        "outer_herald:release": after(HERALD_UP, herald_id=Pick(MORTAL, 1)),
        "outer_incursion:open": given(being_id=THE_BEING, region_id=Pick(EntityType.REGION)),
        "outer_incursion:edit": after(INCURSION_UP, incursion_id=Newest("outer_incursions"), values=EDITS["outer_incursion:edit"], release=[]),
        "outer_incursion:end": after(INCURSION_UP, incursion_id=Newest("outer_incursions")),
        "outer_pact:strike": given(being_id=THE_BEING, holder_id=Pick(MORTAL, 2), price="sanity"),
        "outer_pact:edit": after(PACT_UP, pact_id=Newest("outer_pacts"), values=EDITS["outer_pact:edit"], release=[]),
        "outer_pact:void": after(PACT_UP, pact_id=Newest("outer_pacts")),
        "outer_relation:set": given(being_id=THE_BEING, other_id=Computed(second_outer_being), relation="ignore"),
        "outer_relation:edit": after(RELATION_UP, being_id=THE_BEING, other_id=Computed(second_outer_being), values=EDITS["outer_relation:edit"], release=[]),
        "outer_relation:delete": after(RELATION_UP, being_id=THE_BEING, other_id=Computed(second_outer_being)),
        "outer_seal:set": given(being_id=THE_BEING, kind="banish", strength=60),
        "outer_seal:edit": after(SEAL_UP, seal_id=Newest("outer_seals"), values=EDITS["outer_seal:edit"], release=[]),
        "outer_seal:break": after(SEAL_UP, seal_id=Newest("outer_seals")),
        "outer:destroy": Lever(values={"being_id": THE_BEING}, setup=rich_creator),
    }
)
SECOND_IDEOLOGY = ("lore:create", {"entity_type": "ideology", "name": "The Long Ledger", "world_id": Pick("world"), "values": {"tenets": ["legalism"]}})
FOLLOWED = ("creed:adherent", {"ideology_id": Newest(EntityType.IDEOLOGY), "community_id": Pick(TOWN), "strength": 60})
PART_UP = ("relation_component:set", {"first_id": Pick(TOWN), "second_id": Pick(TOWN, 1), "component": "trade", "value": 20})
CHARTER_UP = ("constitution:write", {"polity_id": Pick(REALM)})
ENCOUNTER_UP = ("journey_encounter:create", {"environment": "land", "effect": "attack", "weight": 40, "loss_pct": 12})
EDITS = {
    **EDITS,
    "relation_component:edit": {"value": -30},
    "constitution:edit": {"rights": 70, "offices": 4, "selectorate": "citizens"},
    "journey_encounter:edit": {"weight": 60, "loss_pct": 5, "effect": "delay"},
}
LEVERS.update(
    {
        "relation_component:set": given(first_id=Pick(TOWN), second_id=Pick(TOWN, 1), component="faith", value=-15),
        "relation_component:edit": after(
            PART_UP, first_id=Pick(TOWN), second_id=Pick(TOWN, 1), component="trade", values=EDITS["relation_component:edit"], release=[]
        ),
        "relation_component:delete": after(PART_UP, first_id=Pick(TOWN), second_id=Pick(TOWN, 1), component="trade"),
        "constitution:write": given(polity_id=Pick(REALM)),
        "constitution:edit": after(CHARTER_UP, polity_id=Pick(REALM), values=EDITS["constitution:edit"], release=[]),
        "constitution:delete": after(CHARTER_UP, polity_id=Pick(REALM)),
        "journey_encounter:create": given(environment="sea", effect="find", weight=30, loss_pct=0),
        "journey_encounter:edit": after(ENCOUNTER_UP, encounter_id=Newest("journey_encounters"), values=EDITS["journey_encounter:edit"], release=[]),
        "journey_encounter:delete": after(ENCOUNTER_UP, encounter_id=Newest("journey_encounters")),
        "ideology:split": after(IDEOLOGY, FOLLOWED, ideology_id=Newest(EntityType.IDEOLOGY), community_id=Pick(TOWN), added="rationalism"),
        "ideology:merge": after(IDEOLOGY, SECOND_IDEOLOGY, keeper_id=Pick(EntityType.IDEOLOGY), absorbed_id=Newest(EntityType.IDEOLOGY)),
    }
)
REGION_TENSION_UP = ("regional_tension:set", {"region_id": Pick(EntityType.REGION), "tension": 40})
SUBSYSTEM_UP = ("subsystem_tension:edit", {"world_id": Pick("world"), "subsystem": "war", "values": {"tension": 30}, "release": []})
TRUST_UP = ("source_trust:set", {"holder_id": Pick(EntityType.MORTAL), "source": "rumour", "trust": 50})
RIFT_CONTROL_UP = ("rift_control:set", {"rift_id": Newest("rift"), "work": "stabilising", "toll": 1})
EDITS = {
    **EDITS,
    "regional_tension:edit": {"tension": 75},
    "subsystem_tension:edit": {"tension": 45},
    "source_trust:edit": {"trust": 20},
    "rift_control:edit": {"work": "sealing", "toll": 3, "adapted": 40},
}
LEVERS.update(
    {
        "storyteller_points:set": given(world_id=Pick("world"), points=[{"epoch": 2, "target": 30}, {"epoch": 8, "target": 70}]),
        "regional_tension:set": given(region_id=Pick(EntityType.REGION), tension=65),
        "regional_tension:edit": after(REGION_TENSION_UP, region_id=Pick(EntityType.REGION), values=EDITS["regional_tension:edit"], release=[]),
        "regional_tension:delete": after(REGION_TENSION_UP, region_id=Pick(EntityType.REGION)),
        "subsystem_tension:edit": given(world_id=Pick("world"), subsystem="war", values=EDITS["subsystem_tension:edit"], release=[]),
        "subsystem_tension:delete": after(SUBSYSTEM_UP, world_id=Pick("world"), subsystem="war"),
        "source_trust:set": given(holder_id=Pick(EntityType.MORTAL), source="spy", trust=70),
        "source_trust:edit": after(TRUST_UP, holder_id=Pick(EntityType.MORTAL), source="rumour", values=EDITS["source_trust:edit"], release=[]),
        "source_trust:delete": after(TRUST_UP, holder_id=Pick(EntityType.MORTAL), source="rumour"),
        "rift_control:set": setup_then(heavens, rift_id=Newest("rift"), work="gate", toll=2, claimant_id=Pick(EntityType.POLITY)),
        "rift_control:edit": setup_then(heavens, RIFT_CONTROL_UP, rift_id=Newest("rift"), values=EDITS["rift_control:edit"], release=[]),
        "rift_control:delete": setup_then(heavens, RIFT_CONTROL_UP, rift_id=Newest("rift")),
    }
)
HORROR_UP = ("horror:event", {"world_id": Pick("world"), "target": "light", "effect": "suppress", "scope": "world", "sense": "seen", "source": "unknown"})
ATTACK_UP = ("creature_attack:create", {"node_id": Pick(EntityType.SPECIES), "delivery": "spit", "effect": "corrosion", "range": "near"})
ASPECT_UP = ("dimension_aspect:create", {"dimension_id": Computed(prime_dimension), "form": "time", "strength": 40})
QUEST_UP: tuple[str, dict[str, Any]] = ("hero:quest", {"hero_id": Computed(free_hero)})
LEGEND_UP = ("cosmic:legendary_quest", {"aim": "restore", "target_kind": "star"})
EDITS = {
    **EDITS,
    "horror_event:edit": {"name": "The Long Hush", "target": "sound", "effect": "take", "sanity_cost": 7},
    "creature_attack:edit": {"delivery": "voice", "effect": "fear", "range": "far", "recharge": 2, "permanent": True},
    "dimension_aspect:edit": {"strength": 70},
    "hero_quest:edit": {"obstacle": "guardian", "reward": "office", "scale": "legendary"},
    "legendary_quest:edit": {"obstacle": "law", "reward": "knowledge"},
}
LEVERS.update(
    {
        "horror:event": given(world_id=Pick("world"), target="minds", effect="mark", scope="world", sense="heard", source="phenomenon"),
        "horror_event:edit": after(HORROR_UP, horror_id=Newest("horror_events"), values=EDITS["horror_event:edit"], release=[]),
        "horror_event:delete": after(HORROR_UP, horror_id=Newest("horror_events")),
        "creature_attack:create": given(node_id=Pick(EntityType.SPECIES), delivery="sting", effect="venom", range="touch", recharge=1),
        "creature_attack:edit": after(ATTACK_UP, attack_id=Newest("creature_attacks"), values=EDITS["creature_attack:edit"], release=[]),
        "creature_attack:delete": after(ATTACK_UP, attack_id=Newest("creature_attacks")),
        "dimension_aspect:create": Lever(values={"dimension_id": Computed(prime_dimension), "element": "earth", "strength": 60}, setup=rich_creator),
        "dimension_aspect:edit": Lever(
            values={"aspect_id": Newest("dimension_aspects"), "values": EDITS["dimension_aspect:edit"], "release": []}, before=(ASPECT_UP,), setup=rich_creator
        ),
        "dimension_aspect:delete": Lever(values={"aspect_id": Newest("dimension_aspects")}, before=(ASPECT_UP,), setup=rich_creator),
        "hero_quest:edit": after(QUEST_UP, quest_id=Newest("hero_quests"), values=EDITS["hero_quest:edit"], release=[]),
        "legendary_quest:edit": after(
            ("cosmic:extinguish_star", {"star_id": Pick("star")}), LEGEND_UP, thread_id=Newest("thread"), values=EDITS["legendary_quest:edit"], release=[]
        ),
        "storyteller:palette": given(world_id=Pick("world"), key="raid", weight_pct=150),
    }
)
KIND_UP = (
    "authored_kind:create",
    {
        "concept": "good",
        "name": "Ember Loaf",
        "category": "grain",
        "world_id": Pick("world"),
        "origin_node_id": Pick(EntityType.PEOPLE),
        "values": {"bulk": 30},
    },
)
EDITS = {
    **EDITS,
    "authored_kind:edit": {
        "name": "Ember Cake",
        "category": "fruit",
        "perishability": 4,
        "bulk": 15,
        "base_value": 40,
        "nourishment": 50,
        "prestige": 30,
        "sacred": 10,
    },
}
LEVERS.update(
    {
        "authored_kind:create": given(
            concept="good",
            name="Ember Loaf",
            category="grain",
            world_id=Pick("world"),
            origin_node_id=Pick(EntityType.PEOPLE),
            values={"perishability": 2, "prestige": 40},
        ),
        "authored_kind:edit": after(KIND_UP, concept="good", kind_id=Newest("good_kinds"), values=EDITS["authored_kind:edit"], release=[]),
        "authored_kind:hold": after(KIND_UP, concept="good", kind_id=Newest("good_kinds"), hold=True),
        "authored_kind:spread": after(
            KIND_UP, concept="good", kind_id=Newest("good_kinds"), holder_node_id=Pick(EntityType.SETTLEMENT), stance="favours", strength=60
        ),
        "authored_kind:retire": after(KIND_UP, concept="good", kind_id=Newest("good_kinds"), retired=True),
        "authored_kind:delete": after(KIND_UP, concept="good", kind_id=Newest("good_kinds")),
    }
)


def newest_row(table: type[Any], key: str) -> Computed:
    column = getattr(table, key)
    return Computed(lambda session: session.scalar(select(column).order_by(column.desc()).limit(1)))


def row_levers(prefix: str, table: str, values: Mapping[str, Any], key: Mapping[str, Any], edits: Mapping[str, Any]) -> dict[str, Lever]:
    made = (f"{prefix}:create", {"table": table, "values": dict(values)})
    return {
        f"{prefix}:create": given(table=table, values=dict(values)),
        f"{prefix}:edit": after(made, table=table, key=dict(key), values=dict(edits)),
        f"{prefix}:delete": after(made, table=table, key=dict(key)),
    }


def seeded_levers(prefix: str, table: str, values: Mapping[str, Any], key: Mapping[str, Any], edits: Mapping[str, Any]) -> dict[str, Lever]:
    unmade = (f"{prefix}:delete", {"table": table, "key": dict(key)})
    return {
        f"{prefix}:create": after(unmade, table=table, values=dict(values)),
        f"{prefix}:edit": given(table=table, key=dict(key), values=dict(edits)),
        f"{prefix}:delete": given(table=table, key=dict(key)),
    }


DAILY_FOLK = Pick(FOLK, 2)
STAFFED_FOLK = Computed(lambda session: session.scalar(select(func.max(DeathWorkRow.people_entity_id))))
STAFFED_WASHERS = Computed(
    lambda session: session.scalar(
        select(DeathWorkRow.id).where(
            DeathWorkRow.role == DeathRole.WASHER, DeathWorkRow.people_entity_id == select(func.max(DeathWorkRow.people_entity_id)).scalar_subquery()
        )
    )
)
LEVERS.update(
    {
        **seeded_levers(
            "care_custom",
            "care_customs",
            {"people_entity_id": DAILY_FOLK, "wash_frequency": "daily", "wash_place": "bath_house", "cleanliness": 60},
            {"people_entity_id": DAILY_FOLK},
            {"cleanliness": 70, "waste_handling": "sewers"},
        ),
        **row_levers(
            "housework",
            "housework",
            {"household_id": HOUSEHOLD, "duty": "water", "doer_node_id": Pick(MORTAL, 1), "load": 25},
            {"id": newest_row(HouseworkRow, "id")},
            {"load": 40},
        ),
        **row_levers(
            "domestic_service",
            "domestic_service",
            {"servant_node_id": Pick(MORTAL, 4), "household_id": HOUSEHOLD, "terms": "wage", "wage": 3},
            {"servant_node_id": Pick(MORTAL, 4)},
            {"wage": 5, "terms": "board"},
        ),
        **row_levers(
            "leisure_pursuit",
            "leisure_pursuits",
            {"holder_node_id": Pick(MORTAL, 1), "kind": "games", "share": 30},
            {"id": newest_row(LeisurePursuitRow, "id")},
            {"share": 45},
        ),
        **seeded_levers(
            "space_norm",
            "space_norms",
            {"people_entity_id": DAILY_FOLK, "distance": "wide", "touch": "open", "posture": "kneel"},
            {"people_entity_id": DAILY_FOLK},
            {"touch": "kin_only"},
        ),
    }
)


KIN_MEMBER_UP = (
    "kin_group_member:create",
    {"table": "kin_group_members", "values": {"group_id": newest_row(KinGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)}},
)
KIN_GROUP_UP = ("kin_group:create", {"table": "kin_groups", "values": {"people_entity_id": DAILY_FOLK, "name": "Kin of the Ford", "form": "clan"}})
LEVERS.update(
    {
        **seeded_levers(
            "kin_role_duty",
            "kin_role_duties",
            {"people_entity_id": DAILY_FOLK, "role": "parent", "duty": "raise", "strength": 70},
            {"people_entity_id": DAILY_FOLK, "role": "parent", "duty": "raise"},
            {"strength": 85},
        ),
        **row_levers(
            "kin_group",
            "kin_groups",
            {"people_entity_id": DAILY_FOLK, "name": "Kin of the Ford", "form": "clan", "exogamy": 80},
            {"id": newest_row(KinGroupRow, "id")},
            {"exogamy": 60, "council_size": 5},
        ),
        "kin_group_member:create": after(
            KIN_GROUP_UP, table="kin_group_members", values={"group_id": newest_row(KinGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)}
        ),
        "kin_group_member:edit": after(
            KIN_GROUP_UP,
            (
                "kin_group_member:create",
                {"table": "kin_group_members", "values": {"group_id": newest_row(KinGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)}},
            ),
            table="kin_group_members",
            key={"group_id": newest_row(KinGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)},
            values={"adopted": True},
        ),
        "kin_group_member:delete": after(
            KIN_GROUP_UP,
            (
                "kin_group_member:create",
                {"table": "kin_group_members", "values": {"group_id": newest_row(KinGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)}},
            ),
            table="kin_group_members",
            key={"group_id": newest_row(KinGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)},
        ),
    }
)


LEVERS.update(
    {
        **seeded_levers(
            "infant_care",
            "infant_care",
            {"people_entity_id": DAILY_FOLK, "feeding": "by_other_nurse", "weaning_age": 3, "carer": "community"},
            {"people_entity_id": DAILY_FOLK},
            {"weaning_age": 4, "carry": "cradled"},
        ),
        **seeded_levers(
            "child_standing",
            "child_standing",
            {"people_entity_id": DAILY_FOLK, "work_age": 10, "marriage_age": 18, "labour_share": 10},
            {"people_entity_id": DAILY_FOLK},
            {"labour_share": 5, "protected": True},
        ),
        **seeded_levers(
            "socialization",
            "socialization",
            {"people_entity_id": DAILY_FOLK, "play": 25, "example": 10},
            {"people_entity_id": DAILY_FOLK},
            {"aim_piety": 70},
        ),
        **row_levers(
            "pedagogy",
            "pedagogy",
            {"holder_node_id": DAILY_FOLK, "theory": "dialectic", "depth": 70},
            {"id": newest_row(PedagogyRow, "id")},
            {"theory": "discovery"},
        ),
    }
)


LEVERS.update(
    {
        **seeded_levers(
            "intimacy_norm",
            "intimacy_norms",
            {"people_entity_id": DAILY_FOLK, "context": "with_kin", "stance": "forbidden", "enforcer": "kin", "sanction": "shaming", "kin_scope": "extended"},
            {"people_entity_id": DAILY_FOLK, "context": "with_kin"},
            {"stance": "discouraged", "sanction": "fine"},
        ),
        **row_levers(
            "restraint_custom",
            "restraint_customs",
            {"people_entity_id": DAILY_FOLK, "role": "clergy", "occasion": "always", "strength": 70},
            {"id": newest_row(RestraintCustomRow, "id")},
            {"strength": 40, "occasion": "rite"},
        ),
        **seeded_levers(
            "reproductive_course",
            "reproductive_courses",
            {"people_entity_id": DAILY_FOLK, "gestation_months": 11, "attendant": "specialist", "postnatal": "rest_period", "rest_months": 2},
            {"people_entity_id": DAILY_FOLK},
            {"risk": 40, "birth_place": "birth_house"},
        ),
        **seeded_levers(
            "legitimacy_rule",
            "legitimacy_rules",
            {"people_entity_id": DAILY_FOLK, "parent_union": "unwed", "standing": "partial", "path": "rite", "cost": 5},
            {"people_entity_id": DAILY_FOLK, "parent_union": "unwed"},
            {"standing": "none", "path": "payment"},
        ),
        **row_levers(
            "child_recognition",
            "child_recognitions",
            {"child_node_id": Pick(MORTAL, 2), "path": "rite"},
            {"child_node_id": Pick(MORTAL, 2)},
            {"path": "adoption"},
        ),
    }
)


YOUTH_GROUP_UP = (
    "youth_group:create",
    {"table": "youth_groups", "values": {"settlement_entity_id": Pick(TOWN, 1), "name": "the youth of the ford", "purpose": "sport"}},
)
YOUTH_MEMBER_UP = (
    "youth_group_member:create",
    {"table": "youth_group_members", "values": {"group_id": newest_row(YouthGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)}},
)
LEVERS.update(
    {
        **seeded_levers(
            "youth_standing",
            "youth_standing",
            {"people_entity_id": DAILY_FOLK, "youth_from": 13, "youth_to": 21, "place": "youth_house", "freedom": 60},
            {"people_entity_id": DAILY_FOLK},
            {"duty": 70, "place": "service"},
        ),
        **row_levers(
            "youth_group",
            "youth_groups",
            {"settlement_entity_id": Pick(TOWN, 1), "name": "the youth of the ford", "purpose": "defence", "standing": 60},
            {"id": newest_row(YouthGroupRow, "id")},
            {"purpose": "faith", "standing": 40},
        ),
        "youth_group_member:create": after(
            YOUTH_GROUP_UP, table="youth_group_members", values={"group_id": newest_row(YouthGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)}
        ),
        "youth_group_member:edit": after(
            YOUTH_GROUP_UP,
            YOUTH_MEMBER_UP,
            table="youth_group_members",
            key={"group_id": newest_row(YouthGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)},
            values={"joined_epoch": 1},
        ),
        "youth_group_member:delete": after(
            YOUTH_GROUP_UP,
            YOUTH_MEMBER_UP,
            table="youth_group_members",
            key={"group_id": newest_row(YouthGroupRow, "id"), "member_node_id": Pick(MORTAL, 3)},
        ),
    }
)


POLICY_UP = ("population_policy:create", {"table": "population_policies", "values": {"holder_node_id": DAILY_FOLK, "aim": "grow"}})
LEVERS.update(
    {
        **row_levers(
            "population_policy",
            "population_policies",
            {"holder_node_id": DAILY_FOLK, "aim": "settle_land", "strength": 60, "enforcement": 40},
            {"id": newest_row(PopulationPolicyRow, "id")},
            {"aim": "hold", "enforcement": 70},
        ),
        "population_instrument:create": after(
            POLICY_UP,
            table="population_instruments",
            values={"policy_id": newest_row(PopulationPolicyRow, "id"), "holder_node_id": DAILY_FOLK, "instrument": "health_campaign", "strength": 50},
        ),
        "population_instrument:edit": after(
            POLICY_UP,
            (
                "population_instrument:create",
                {
                    "table": "population_instruments",
                    "values": {"policy_id": newest_row(PopulationPolicyRow, "id"), "holder_node_id": DAILY_FOLK, "instrument": "birth_reward"},
                },
            ),
            table="population_instruments",
            key={"policy_id": newest_row(PopulationPolicyRow, "id"), "instrument": "birth_reward"},
            values={"strength": 80},
        ),
        "population_instrument:delete": after(
            POLICY_UP,
            (
                "population_instrument:create",
                {
                    "table": "population_instruments",
                    "values": {"policy_id": newest_row(PopulationPolicyRow, "id"), "holder_node_id": DAILY_FOLK, "instrument": "birth_reward"},
                },
            ),
            table="population_instruments",
            key={"policy_id": newest_row(PopulationPolicyRow, "id"), "instrument": "birth_reward"},
        ),
    }
)


SHOP_UP = ("shop:create", {"table": "shops", "values": {"settlement_entity_id": Pick(TOWN, 1), "keeper_node_id": Pick(MORTAL, 1), "form": "stall"}})
SHOP_GOOD_UP = (
    "shop_good:create",
    {"table": "shop_goods", "values": {"shop_id": newest_row(ShopRow, "id"), "commodity": "bread", "keeper_node_id": Pick(MORTAL, 1)}},
)
LEVERS.update(
    {
        **row_levers(
            "shop",
            "shops",
            {"settlement_entity_id": Pick(TOWN, 1), "keeper_node_id": Pick(MORTAL, 1), "form": "market_hall", "margin": 25, "stock": 20},
            {"id": newest_row(ShopRow, "id")},
            {"margin": 30, "credit": 10},
        ),
        "shop_good:create": after(
            SHOP_UP, table="shop_goods", values={"shop_id": newest_row(ShopRow, "id"), "commodity": "tools", "keeper_node_id": Pick(MORTAL, 1)}
        ),
        "shop_good:edit": after(
            SHOP_UP,
            SHOP_GOOD_UP,
            table="shop_goods",
            key={"shop_id": newest_row(ShopRow, "id"), "commodity": "bread"},
            values={"keeper_node_id": Pick(MORTAL, 2)},
        ),
        "shop_good:delete": after(SHOP_UP, SHOP_GOOD_UP, table="shop_goods", key={"shop_id": newest_row(ShopRow, "id"), "commodity": "bread"}),
        **row_levers(
            "supply_tier",
            "supply_tiers",
            {"market_entity_id": Pick(TOWN, 1), "commodity": "grain", "tier": "wholesale", "holder_node_id": Pick(MORTAL, 1), "share": 60},
            {"id": newest_row(SupplyTierRow, "id")},
            {"margin": 15, "share": 90},
        ),
        **row_levers(
            "promotion",
            "promotions",
            {"holder_node_id": Pick(MORTAL, 1), "medium": "sign", "reach": 40, "accuracy": 70},
            {"id": newest_row(PromotionRow, "id")},
            {"reach": 60, "medium": "display"},
        ),
        **row_levers(
            "lease",
            "leases",
            {"owner_node_id": Pick(MORTAL, 1), "lessee_node_id": Pick(MORTAL, 2), "thing_node_id": Pick(TOWN, 1), "thing": "land", "rent": 4},
            {"id": newest_row(LeaseRow, "id")},
            {"rent": 6, "on_default": "debt"},
        ),
    }
)


WORKS_UP = (
    "public_works:create",
    {"table": "public_works", "values": {"polity_entity_id": DAILY_FOLK, "place_node_id": Pick(TOWN, 1), "kind": "road", "labour": "paid", "budget": 50}},
)
STAGE_VALUES = {"works_id": newest_row(PublicWorksRow, "id"), "polity_entity_id": DAILY_FOLK, "stage": 1, "spent": 5, "labour": "corvee"}
LEVERS.update(
    {
        **row_levers(
            "public_works",
            "public_works",
            {"polity_entity_id": DAILY_FOLK, "place_node_id": Pick(TOWN, 1), "kind": "aqueduct", "labour": "paid", "budget": 50},
            {"id": newest_row(PublicWorksRow, "id")},
            {"quality": 80, "stage": 1},
        ),
        "public_works:advance": after(WORKS_UP, works_id=newest_row(PublicWorksRow, "id")),
        "public_work_stage:create": after(WORKS_UP, table="public_work_stages", values=STAGE_VALUES),
        "public_work_stage:edit": after(
            WORKS_UP,
            ("public_work_stage:create", {"table": "public_work_stages", "values": STAGE_VALUES}),
            table="public_work_stages",
            key={"id": newest_row(PublicWorkStageRow, "id")},
            values={"spent": 9, "quality": 75},
        ),
        "public_work_stage:delete": after(
            WORKS_UP,
            ("public_work_stage:create", {"table": "public_work_stages", "values": STAGE_VALUES}),
            table="public_work_stages",
            key={"id": newest_row(PublicWorkStageRow, "id")},
        ),
        **row_levers(
            "state_enterprise",
            "state_enterprises",
            {"polity_entity_id": DAILY_FOLK, "sector": "tools", "form": "monopoly", "output": 20},
            {"id": newest_row(StateEnterpriseRow, "id")},
            {"corruption": 40, "form": "arsenal"},
        ),
    }
)


LEVERS.update(
    {
        **row_levers(
            "market_structure",
            "market_structures",
            {"market_entity_id": Pick(TOWN, 1), "commodity": "cloth", "concentration": 40, "form": "few_sellers"},
            {"id": newest_row(MarketStructureRow, "id")},
            {"concentration": 60, "form": "one_seller"},
        ),
        **row_levers(
            "cartel",
            "cartels",
            {"name": "the cloth compact", "leader_node_id": Pick(FACTION, 0), "commodity": "cloth", "aim": "price", "agreed_price": 12},
            {"id": newest_row(CartelRow, "id")},
            {"discipline": 50, "aim": "quota"},
        ),
        **row_levers(
            "price_war",
            "price_wars",
            {"aggressor_node_id": Pick(FACTION, 0), "market_entity_id": Pick(TOWN, 1), "commodity": "cloth", "cut_pct": 25},
            {"id": newest_row(PriceWarRow, "id")},
            {"cut_pct": 35, "outcome": "called_off"},
        ),
    }
)


LEVERS.update(
    {
        **row_levers(
            "departure",
            "departures",
            {"holder_node_id": Pick(MORTAL, 0), "kind": "retirement", "conditions": ["pension"], "standing": 20},
            {"id": newest_row(DepartureRow, "id")},
            {"standing": 50, "kind": "resignation"},
        ),
    }
)


LEVERS.update(
    {
        **row_levers(
            "leader_cult",
            "leader_cults",
            {"leader_node_id": Pick(MORTAL, 0), "instruments": ["holidays"], "intensity": 30},
            {"id": newest_row(LeaderCultRow, "id")},
            {"intensity": 60, "sincerity": 40},
        ),
    }
)


RESTORATION_VALUES = {"fallen_polity_id": Pick(REALM, 0), "memory": 30}
LEVERS.update(
    {
        **row_levers("restoration", "restorations", RESTORATION_VALUES, {"id": newest_row(RestorationRow, "id")}, {"memory": 60, "bases": ["law"]}),
        "restoration:advance": after(
            ("restoration:create", {"table": "restorations", "values": RESTORATION_VALUES}), record_id=newest_row(RestorationRow, "id")
        ),
    }
)


LEVERS.update(
    {
        **row_levers(
            "mass_weapon",
            "mass_weapons",
            {"holder_entity_id": Pick(REALM, 0), "harm": "rite", "reach": "region"},
            {"id": newest_row(MassWeaponRow, "id")},
            {"stage": "ready", "count": 2, "readiness": 40},
        ),
        **row_levers(
            "deterrence_posture",
            "deterrence_postures",
            {"holder_entity_id": Pick(REALM, 0), "posture": "ambiguous"},
            {"id": newest_row(DeterrencePostureRow, "id")},
            {"credibility": 70, "posture": "retaliation_only"},
        ),
        **row_levers(
            "war_remnant",
            "war_remnants",
            {"region_entity_id": Pick(REGION, 0), "kind": "fallout", "density": 50},
            {"id": newest_row(WarRemnantRow, "id")},
            {"density": 20, "cleared": 30},
        ),
    }
)


LEVERS.update(
    {
        **row_levers(
            "interworld_campaign",
            "interworld_campaigns",
            {"attacker_entity_id": Pick(REALM, 0), "from_world_id": Pick("world"), "target_world_id": Pick("world"), "stage": "gathering"},
            {"id": newest_row(InterworldCampaignRow, "id")},
            {"stage": "transit", "supply": 70, "forces": 300},
        ),
        **row_levers(
            "orbital_control",
            "orbital_control",
            {"world_id": Pick("world"), "holder_entity_id": Pick(REALM, 0), "strength": 40},
            {"id": newest_row(OrbitalControlRow, "id")},
            {"strength": 75},
        ),
        **row_levers(
            "interworld_migration",
            "interworld_migrations",
            {"community_entity_id": Pick(TOWN, 0), "from_world_id": Pick("world"), "to_world_id": Pick("world"), "cause": "exile"},
            {"id": newest_row(InterworldMigrationRow, "id")},
            {"reception": "quota", "per_epoch": 40},
        ),
    }
)


LEVERS.update(
    {
        **row_levers(
            "protected_area",
            "protected_areas",
            {"region_entity_id": Pick(LAND, 0), "basis": "custom", "banned_uses": ["hunting"]},
            {"id": newest_row(ProtectedAreaRow, "id")},
            {"strength": 70, "wardens": 3},
        ),
        **row_levers(
            "species_protection",
            "species_protections",
            {"species_entity_id": Pick(EntityType.SPECIES, 0), "measures": ["breeding_programme"]},
            {"id": newest_row(SpeciesProtectionRow, "id")},
            {"basis": "faith"},
        ),
        **row_levers(
            "conservation_movement",
            "conservation_movements",
            {"movement_entity_id": Pick(EntityType.FACTION, 0), "aims": ["hunting"]},
            {"movement_entity_id": newest_row(ConservationMovementRow, "movement_entity_id")},
            {"aims": ["logging"]},
        ),
    }
)


LEVERS.update(
    row_levers(
        "feeling_spread",
        "feeling_spread",
        {"settlement_entity_id": Pick(TOWN, 0), "feelings": {"joy": 40}, "leading": "joy"},
        {"id": newest_row(FeelingSpreadRow, "id")},
        {"feelings": {"fear": 55}, "leading": "fear"},
    )
)
LEVERS.update(
    row_levers(
        "interpretation",
        "interpretations",
        {"first_party_id": Pick(TOWN, 0), "second_party_id": Pick(TOWN, 1), "fidelity": 60, "event": "parley"},
        {"id": newest_row(InterpretationRow, "id")},
        {"fidelity": 30, "fault": "softened"},
    )
)
LEVERS.update(
    row_levers(
        "grave_good",
        "grave_goods",
        {"dead_entity_id": Pick(MORTAL, 1), "grave_entity_id": Pick(TOWN, 0), "goods_value": 30, "guard": "sealed"},
        {"id": newest_row(GraveGoodsRow, "id")},
        {"goods_value": 10, "guard": "guarded"},
    )
)
LEVERS.update(
    row_levers(
        "agentless_condition",
        "agentless_conditions",
        {"world_id": Pick("world"), "name": "A wearing of the breath", "cause": "age", "system": "breath", "course": "worsening", "onset_pct": 50},
        {"id": newest_row(AgentlessConditionRow, "id")},
        {"weight": 20, "course": "episodic"},
    )
)
LEVERS.update(
    row_levers(
        "fertility_means",
        "fertility_means",
        {"people_entity_id": Pick(EntityType.PEOPLE, 0), "means": "prevention", "reliability": 50, "use_pct": 10},
        {"people_entity_id": Pick(EntityType.PEOPLE, 0), "means": "prevention"},
        {"reliability": 70, "stance": "discouraged"},
    )
)
LEVERS.update(
    row_levers(
        "fertility_use",
        "fertility_uses",
        {"user_entity_id": Pick(MORTAL, 0), "people_entity_id": Pick(EntityType.PEOPLE, 0), "means": "prevention"},
        {"id": newest_row(FertilityUseRow, "id")},
        {"hidden": True},
    )
)
LEVERS.update(
    row_levers(
        "honour_kind",
        "honour_kinds",
        {"conferrer_node_id": Pick(EntityType.POLITY, 0), "name": "Order of the Lever", "rank": 1, "privileges": ["title"]},
        {"id": newest_row(HonourKindRow, "id")},
        {"rank": 2, "hereditary": True},
    )
)
HONOUR_KIND_VALUES = {"conferrer_node_id": Pick(EntityType.POLITY, 0), "name": "Order of the Held", "rank": 1}
HONOUR_KIND_MADE = ("honour_kind:create", {"table": "honour_kinds", "values": HONOUR_KIND_VALUES})
HONOUR_HELD_VALUES = {"holder_node_id": Pick(MORTAL, 0), "kind_id": newest_row(HonourKindRow, "id")}
HONOUR_HELD_MADE = ("honour_held:create", {"table": "honours_held", "values": HONOUR_HELD_VALUES})
HONOUR_HELD_KEY = {"id": newest_row(HonourHeldRow, "id")}
LEVERS.update(
    {
        "honour_held:create": after(HONOUR_KIND_MADE, table="honours_held", values=HONOUR_HELD_VALUES),
        "honour_held:edit": after(HONOUR_KIND_MADE, HONOUR_HELD_MADE, table="honours_held", key=HONOUR_HELD_KEY, values={"sold": True}),
        "honour_held:delete": after(HONOUR_KIND_MADE, HONOUR_HELD_MADE, table="honours_held", key=HONOUR_HELD_KEY),
    }
)
SEA_WAVE_VALUES = {"world_id": Pick("world"), "origin": "quake", "origin_region_id": Pick(EntityType.REGION, 0), "strength": 40}
SEA_WAVE_MADE = ("sea_wave:create", {"table": "sea_waves", "values": SEA_WAVE_VALUES})
LEVERS.update(row_levers("sea_wave", "sea_waves", SEA_WAVE_VALUES, {"id": newest_row(SeaWaveRow, "id")}, {"strength": 60}))
STRUCK_VALUES = {"wave_id": newest_row(SeaWaveRow, "id"), "region_entity_id": Pick(EntityType.REGION, 0), "height": 30}
STRUCK_MADE = ("sea_wave_coast:create", {"table": "sea_wave_coasts", "values": STRUCK_VALUES})
STRUCK_KEY = {"id": newest_row(SeaWaveCoastRow, "id")}
LEVERS.update(
    {
        "sea_wave_coast:create": after(SEA_WAVE_MADE, table="sea_wave_coasts", values=STRUCK_VALUES),
        "sea_wave_coast:edit": after(SEA_WAVE_MADE, STRUCK_MADE, table="sea_wave_coasts", key=STRUCK_KEY, values={"warned": True, "height": 20}),
        "sea_wave_coast:delete": after(SEA_WAVE_MADE, STRUCK_MADE, table="sea_wave_coasts", key=STRUCK_KEY),
    }
)
LEVERS.update(
    row_levers(
        "wave_warning",
        "wave_warnings",
        {"region_entity_id": Pick(EntityType.REGION, 0), "method": "sight", "until_epoch": 2},
        {"id": newest_row(WaveWarningRow, "id")},
        {"until_epoch": 3},
    )
)
LEVERS.update(
    row_levers(
        "creature_group",
        "creature_groups",
        {"species_entity_id": Pick(EntityType.SPECIES, 0), "region_entity_id": Pick(EntityType.REGION, 0), "form": "herd", "size": 300},
        {"id": newest_row(CreatureGroupRow, "id")},
        {"size": 200, "hunger": 70, "form": "pack"},
    )
)
FRESH_CULT = ("horror:cult", {"entity_id": Pick(TOWN)})
CONCEPTION_VALUES = {"cult_entity_id": Newest(EntityType.CULT), "count": "one", "nearness": "distant"}
CONCEPTION_MADE = ("divine_conception:create", {"table": "divine_conceptions", "values": CONCEPTION_VALUES})
CONCEPTION_KEY = {"cult_entity_id": Newest(EntityType.CULT)}
READING_VALUES = {"cult_entity_id": Pick(EntityType.CULT, 0), "god_node_id": Pick("foreign_god"), "reading": "servant"}
READING_MADE = ("god_reading:create", {"table": "god_readings", "values": READING_VALUES})
READING_KEY = {"cult_entity_id": Pick(EntityType.CULT, 0), "god_node_id": Pick("foreign_god")}
LEVERS.update(
    {
        "divine_conception:create": after(FRESH_CULT, table="divine_conceptions", values=CONCEPTION_VALUES),
        "divine_conception:edit": after(FRESH_CULT, CONCEPTION_MADE, table="divine_conceptions", key=CONCEPTION_KEY, values={"count": "many"}),
        "divine_conception:delete": after(FRESH_CULT, CONCEPTION_MADE, table="divine_conceptions", key=CONCEPTION_KEY),
        "god_reading:create": setup_then(foreign_god, table="god_readings", values=READING_VALUES),
        "god_reading:edit": setup_then(foreign_god, READING_MADE, table="god_readings", key=READING_KEY, values={"reading": "true"}),
        "god_reading:delete": setup_then(foreign_god, READING_MADE, table="god_readings", key=READING_KEY),
    }
)
KIN_DYNAMIC = ("kin_dynamic:create", {"table": "kin_dynamics", "values": {"house_entity_id": Pick(EntityType.HOUSE, 0)}})
NEWEST_DYNAMIC = newest_row(KinDynamicRow, "id")
KIN_ROWS: dict[str, tuple[str, type[Base], dict[str, Any], dict[str, Any]]] = {
    "kin_favour": ("kin_favours", KinFavourRow, {"parent_node_id": Pick(MORTAL, 0), "child_node_id": Pick(MORTAL, 1), "strength": 40}, {"strength": 70}),
    "kin_rivalry": ("kin_rivalries", KinRivalryRow, {"first_node_id": Pick(MORTAL, 0), "second_node_id": Pick(MORTAL, 1), "cause": "love"}, {"heat": 50}),
    "kin_disowning": ("kin_disownings", KinDisowningRow, {"disowner_node_id": Pick(MORTAL, 0), "disowned_node_id": Pick(MORTAL, 1)}, {"reason": "faith"}),
    "kin_blend": ("kin_blends", KinBlendRow, {"member_node_id": Pick(MORTAL, 1), "standing": 40}, {"standing": 60}),
    "elder_sway": ("elder_sway", ElderSwayRow, {"elder_node_id": Pick(MORTAL, 0), "sway": 50}, {"sway": 30}),
}
LEVERS.update(row_levers("kin_dynamic", "kin_dynamics", {"house_entity_id": Pick(EntityType.HOUSE, 0)}, {"id": NEWEST_DYNAMIC}, {"tension": 40}))
for family, (table, row, values, edits) in KIN_ROWS.items():
    made = {"dynamic_id": NEWEST_DYNAMIC, **values}
    LEVERS.update(
        {
            f"{family}:create": after(KIN_DYNAMIC, table=table, values=made),
            f"{family}:edit": after(
                KIN_DYNAMIC, (f"{family}:create", {"table": table, "values": made}), table=table, key={"id": newest_row(row, "id")}, values=edits
            ),
            f"{family}:delete": after(KIN_DYNAMIC, (f"{family}:create", {"table": table, "values": made}), table=table, key={"id": newest_row(row, "id")}),
        }
    )


CITY_VALUES = {"core_entity_id": Pick(TOWN, 0), "members": [Pick(TOWN, 1)], "governance": "federated_councils"}
LEVERS.update(
    {
        **row_levers(
            "land_use_rule",
            "land_use_rules",
            {"settlement_entity_id": Pick(TOWN, 0), "rule": "green_share", "strength": 60},
            {"id": newest_row(LandUseRuleRow, "id")},
            {"enforcement": 80, "rule": "fire_spacing"},
        ),
        **row_levers(
            "municipal_service",
            "municipal_services",
            {"settlement_entity_id": Pick(TOWN, 0), "service": "lighting", "budget": 40},
            {"id": newest_row(MunicipalServiceRow, "id")},
            {"quality": 70, "budget": 60},
        ),
        **row_levers("conurbation", "conurbations", CITY_VALUES, {"id": newest_row(ConurbationRow, "id")}, {"governance": "one_council"}),
        "conurbation:split": after(("conurbation:create", {"table": "conurbations", "values": CITY_VALUES}), record_id=newest_row(ConurbationRow, "id")),
    }
)


REGIME_VALUES = {"region_entity_id": Pick(REGION, 0), "occupier_entity_id": Pick(REALM, 0), "rule": "military", "tax_pct": 30}
REGIMED = ("occupation_regime:create", {"table": "occupation_regimes", "values": REGIME_VALUES})
NEWEST_REGIME = newest_row(OccupationRegimeRow, "id")
SERVICE_VALUES = {"regime_id": NEWEST_REGIME, "collaborator_node_id": Pick(MORTAL, 0), "kind": "informing"}
PRESSED_VALUES = {"regime_id": NEWEST_REGIME, "region_entity_id": Pick(REGION, 0), "measure": "curfew", "strength": 40}
LEVERS.update(
    {
        **row_levers("occupation_regime", "occupation_regimes", REGIME_VALUES, {"id": NEWEST_REGIME}, {"rule": "protectorate", "labour_pct": 20}),
        "collaboration:create": after(REGIMED, table="collaborations", values=SERVICE_VALUES),
        "collaboration:edit": after(
            REGIMED,
            ("collaboration:create", {"table": "collaborations", "values": SERVICE_VALUES}),
            table="collaborations",
            key={"id": newest_row(CollaborationRow, "id")},
            values={"exposure": 60, "reward": 5},
        ),
        "collaboration:delete": after(
            REGIMED,
            ("collaboration:create", {"table": "collaborations", "values": SERVICE_VALUES}),
            table="collaborations",
            key={"id": newest_row(CollaborationRow, "id")},
        ),
        "occupation_measure:create": after(REGIMED, table="occupation_measures", values=PRESSED_VALUES),
        "occupation_measure:edit": after(
            REGIMED,
            ("occupation_measure:create", {"table": "occupation_measures", "values": PRESSED_VALUES}),
            table="occupation_measures",
            key={"id": newest_row(OccupationMeasureRow, "id")},
            values={"strength": 70, "measure": "hostages"},
        ),
        "occupation_measure:delete": after(
            REGIMED,
            ("occupation_measure:create", {"table": "occupation_measures", "values": PRESSED_VALUES}),
            table="occupation_measures",
            key={"id": newest_row(OccupationMeasureRow, "id")},
        ),
    }
)


RECKONED = ("reckoning:create", {"table": "reckonings", "values": {"polity_entity_id": Pick(REALM, 0), "fallen_epoch": 0}})
NEWEST_RECKONING = newest_row(ReckoningRow, "id")
MEASURE_VALUES = {"reckoning_id": NEWEST_RECKONING, "polity_entity_id": Pick(REALM, 0), "measure": "memorial", "strength": 40}
CASE_VALUES = {"reckoning_id": NEWEST_RECKONING, "accused_node_id": Pick(MORTAL, 0), "measure": "tribunal"}
LEVERS.update(
    {
        **row_levers("reckoning", "reckonings", {"polity_entity_id": Pick(REALM, 0), "fallen_epoch": 0}, {"id": NEWEST_RECKONING}, {"resistance": 40}),
        "reckoning_measure:create": after(RECKONED, table="reckoning_measures", values=MEASURE_VALUES),
        "reckoning_measure:edit": after(
            RECKONED,
            ("reckoning_measure:create", {"table": "reckoning_measures", "values": MEASURE_VALUES}),
            table="reckoning_measures",
            key={"id": newest_row(ReckoningMeasureRow, "id")},
            values={"strength": 70, "stage": "active"},
        ),
        "reckoning_measure:delete": after(
            RECKONED,
            ("reckoning_measure:create", {"table": "reckoning_measures", "values": MEASURE_VALUES}),
            table="reckoning_measures",
            key={"id": newest_row(ReckoningMeasureRow, "id")},
        ),
        "reckoning_case:create": after(RECKONED, table="reckoning_cases", values=CASE_VALUES),
        "reckoning_case:edit": after(
            RECKONED,
            ("reckoning_case:create", {"table": "reckoning_cases", "values": CASE_VALUES}),
            table="reckoning_cases",
            key={"id": newest_row(ReckoningCaseRow, "id")},
            values={"outcome": "pardoned"},
        ),
        "reckoning_case:delete": after(
            RECKONED,
            ("reckoning_case:create", {"table": "reckoning_cases", "values": CASE_VALUES}),
            table="reckoning_cases",
            key={"id": newest_row(ReckoningCaseRow, "id")},
        ),
    }
)


VOTE_VALUES = {"holder_node_id": Pick(REALM, 0), "subject": "law", "name": "the vote on the old law", "yes_pct": 70}
LEVERS.update(
    {
        **row_levers("referendum", "referendums", VOTE_VALUES, {"id": newest_row(ReferendumRow, "id")}, {"yes_pct": 30, "binding": False}),
        "referendum:decide": after(
            ("referendum:create", {"table": "referendums", "values": VOTE_VALUES}), record_id=newest_row(ReferendumRow, "id"), result="failed"
        ),
    }
)


FOUNDED = ("league:found", {"founder_id": Pick(REALM, 0), "partner_ids": [Pick(REALM, 1), Pick(REALM, 2)], "aims": ["defence", "law"]})
NEWEST_LEAGUE = Newest(EntityType.LEAGUE)
CHARTER_KEY = {"league_entity_id": NEWEST_LEAGUE}
LEVERS.update(
    {
        "league:found": given(founder_id=Pick(REALM, 0), partner_ids=[Pick(REALM, 1), Pick(REALM, 2)], aims=["trade"], vote_basis="by_dues"),
        "league:dissolve": after(FOUNDED, league_id=NEWEST_LEAGUE),
        "polity_league:create": after(
            FOUNDED,
            ("polity_league:delete", {"table": "polity_leagues", "key": CHARTER_KEY}),
            table="polity_leagues",
            values={"league_entity_id": NEWEST_LEAGUE, "aims": ["peace"], "vote_basis": "by_population"},
        ),
        "polity_league:edit": after(FOUNDED, table="polity_leagues", key=CHARTER_KEY, values={"depth": 40, "common_tariff_pct": 15}),
        "polity_league:delete": after(FOUNDED, table="polity_leagues", key=CHARTER_KEY),
        "league_member:create": after(
            FOUNDED, table="league_members", values={"league_entity_id": NEWEST_LEAGUE, "polity_entity_id": Pick(REALM, 3), "standing": "observer"}
        ),
        "league_member:edit": after(FOUNDED, table="league_members", key={"id": newest_row(LeagueMemberRow, "id")}, values={"veto": True, "defiance": 1}),
        "league_member:delete": after(FOUNDED, table="league_members", key={"id": newest_row(LeagueMemberRow, "id")}),
        "league_decision:create": after(
            FOUNDED, table="league_decisions", values={"league_entity_id": NEWEST_LEAGUE, "organ": "assembly", "kind": "budget", "rate_pct": 10}
        ),
        "league_decision:edit": after(
            FOUNDED,
            ("league_decision:create", {"table": "league_decisions", "values": {"league_entity_id": NEWEST_LEAGUE, "organ": "court", "kind": "ruling"}}),
            table="league_decisions",
            key={"id": newest_row(LeagueDecisionRow, "id")},
            values={"outcome": "passed", "votes_for": 3},
        ),
        "league_decision:delete": after(
            FOUNDED,
            ("league_decision:create", {"table": "league_decisions", "values": {"league_entity_id": NEWEST_LEAGUE, "organ": "court", "kind": "ruling"}}),
            table="league_decisions",
            key={"id": newest_row(LeagueDecisionRow, "id")},
        ),
    }
)


ISSUED = (
    "issued_security:create",
    {"table": "issued_securities", "values": {"name": "the bonds of the guild", "issuer_node_id": Pick(FACTION, 0), "kind": "bond"}},
)
NEWEST_SECURITY = newest_row(IssuedSecurityRow, "id")
HOLDING_VALUES = {"holder_node_id": Pick(FACTION, 0), "security_id": NEWEST_SECURITY, "amount": 5}
HELD = ("security_holding:create", {"table": "security_holdings", "values": HOLDING_VALUES})
PRICE_VALUES = {"security_id": NEWEST_SECURITY, "issuer_node_id": Pick(FACTION, 0), "epoch": 0, "price": 12}
LEVERS.update(
    {
        **row_levers(
            "stock_exchange",
            "stock_exchanges",
            {"name": "the exchange of the hill", "settlement_entity_id": Pick(TOWN, 1), "margin_pct": 20},
            {"id": newest_row(StockExchangeRow, "id")},
            {"mood": 30, "listing_fee": 5},
        ),
        **row_levers(
            "issued_security",
            "issued_securities",
            {"name": "the notes of the guild", "issuer_node_id": Pick(FACTION, 0), "kind": "note", "amount": 50},
            {"id": NEWEST_SECURITY},
            {"price": 14, "bubble": True},
        ),
        "security_holding:create": after(ISSUED, table="security_holdings", values=HOLDING_VALUES),
        "security_holding:edit": after(
            ISSUED,
            (
                "security_holding:create",
                {"table": "security_holdings", "values": {"holder_node_id": Pick(FACTION, 0), "security_id": NEWEST_SECURITY, "amount": 5}},
            ),
            table="security_holdings",
            key={"id": newest_row(SecurityHoldingRow, "id")},
            values={"amount": 8, "on_margin": 3},
        ),
        "security_holding:delete": after(
            ISSUED,
            (
                "security_holding:create",
                {"table": "security_holdings", "values": {"holder_node_id": Pick(FACTION, 0), "security_id": NEWEST_SECURITY, "amount": 5}},
            ),
            table="security_holdings",
            key={"id": newest_row(SecurityHoldingRow, "id")},
        ),
        "security_price:create": after(ISSUED, table="security_prices", values=PRICE_VALUES),
        "security_price:edit": after(
            ISSUED,
            ("security_price:create", {"table": "security_prices", "values": PRICE_VALUES}),
            table="security_prices",
            key={"id": newest_row(SecurityPriceRow, "id")},
            values={"price": 15, "volume": 4},
        ),
        "security_price:delete": after(
            ISSUED,
            ("security_price:create", {"table": "security_prices", "values": PRICE_VALUES}),
            table="security_prices",
            key={"id": newest_row(SecurityPriceRow, "id")},
        ),
    }
)


STRUCK = ("currency:create", {"issuer_id": Pick(TOWN), "name": "Ledger Crown"})
NEWEST_AUTHORITY = {"id": newest_row(MonetaryAuthorityRow, "id")}
UNSET = ("monetary_authority:delete", {"table": "monetary_authorities", "key": NEWEST_AUTHORITY})
LEVERS.update(
    {
        "monetary_authority:create": after(
            STRUCK,
            UNSET,
            table="monetary_authorities",
            values={"currency_id": Newest("currency"), "holder_node_id": Pick(FACTION, 0), "aim": "growth", "lender_of_last_resort": True},
        ),
        "monetary_authority:edit": after(STRUCK, table="monetary_authorities", key=NEWEST_AUTHORITY, values={"rate": 9, "aim": "cheap_credit"}),
        "monetary_authority:delete": after(STRUCK, table="monetary_authorities", key=NEWEST_AUTHORITY),
    }
)


BODY_VALUES = {"faction_node_id": Pick(FACTION, 1), "form": "craft_union", "trades": ["crafting"], "members": 40, "fund": 100}
BODY_UP = ("worker_body:create", {"table": "worker_bodies", "values": BODY_VALUES})
DISPUTE_UP = (
    "labour_dispute:create",
    {"table": "labour_disputes", "values": {"body_node_id": Pick(FACTION, 1), "hirer_node_id": Pick(FACTION, 0), "act": "strike", "workers_out": 10}},
)
LEVERS.update(
    {
        "worker_body:create": given(table="worker_bodies", values=BODY_VALUES),
        "worker_body:edit": after(
            BODY_UP, table="worker_bodies", key={"faction_node_id": Pick(FACTION, 1)}, values={"solidarity": 70, "standing": "recognised"}
        ),
        "worker_body:delete": after(BODY_UP, table="worker_bodies", key={"faction_node_id": Pick(FACTION, 1)}),
        **row_levers(
            "labour_contract",
            "labour_contracts",
            {"hirer_node_id": Pick(FACTION, 0), "settlement_entity_id": Pick(TOWN, 1), "trade": "mining", "wage": 120},
            {"id": newest_row(LabourContractRow, "id")},
            {"hours": 48, "status": "agreed"},
        ),
        **row_levers(
            "labour_dispute",
            "labour_disputes",
            {"body_node_id": Pick(FACTION, 1), "hirer_node_id": Pick(FACTION, 0), "act": "go_slow", "workers_out": 5},
            {"id": newest_row(LabourDisputeRow, "id")},
            {"workers_out": 8, "demand": "rest"},
        ),
        "labour_dispute:end": after(DISPUTE_UP, BODY_UP, record_id=newest_row(LabourDisputeRow, "id"), outcome="won"),
    }
)


MERGER_UP = (
    "org_merger:create",
    {"table": "org_mergers", "values": {"acquirer_node_id": Pick(FACTION, 0), "target_node_id": Pick(FACTION, 1), "kind": "merger", "price": 50}},
)
LEVERS.update(
    {
        **seeded_levers(
            "org_governance",
            "org_governance",
            {"org_node_id": Pick(FACTION, 0), "decision_body": "chapter", "head_selection": "seniority", "strategy": "grow"},
            {"org_node_id": Pick(FACTION, 0)},
            {"quorum_pct": 60, "strategy": "lobby"},
        ),
        **row_levers(
            "org_seat",
            "org_seats",
            {"org_node_id": Pick(FACTION, 0), "member_node_id": Pick(MORTAL, 3), "vote_weight": 10},
            {"id": newest_row(OrgSeatRow, "id")},
            {"vote_weight": 20},
        ),
        **row_levers(
            "org_clique",
            "org_cliques",
            {"org_node_id": Pick(FACTION, 0), "name": "the reformers", "aim": "strategy", "aim_strategy": "grow", "strength": 20},
            {"id": newest_row(OrgCliqueRow, "id")},
            {"strength": 30, "aim": "split"},
        ),
        **row_levers(
            "org_merger",
            "org_mergers",
            {"acquirer_node_id": Pick(FACTION, 0), "target_node_id": Pick(FACTION, 1), "kind": "merger", "price": 50},
            {"id": newest_row(OrgMergerRow, "id")},
            {"price": 80, "kind": "buyout"},
        ),
        "org_merger:advance": after(MERGER_UP, record_id=newest_row(OrgMergerRow, "id")),
        **row_levers(
            "org_research",
            "org_research",
            {"org_node_id": Pick(FACTION, 0), "technique": LAST_TECHNIQUE, "budget": 100},
            {"id": newest_row(OrgResearchRow, "id")},
            {"budget": 200, "staff": 3},
        ),
        **row_levers(
            "insolvency_case",
            "insolvency_cases",
            {"debtor_node_id": Pick(FACTION, 0), "path": "liquidation", "owed": 100},
            {"id": newest_row(InsolvencyCaseRow, "id")},
            {"path": "restructuring", "recovered_pct": 40},
        ),
    }
)


OUTLET_UP = (
    "media_outlet:create",
    {"table": "media_outlets", "values": {"owner_node_id": Pick(MORTAL, 1), "seat_entity_id": Pick(TOWN, 1), "name": "The Vale Crier"}},
)
LEVERS.update(
    {
        **row_levers(
            "record_medium",
            "record_media",
            {"holder_node_id": DAILY_FOLK, "name": "written word", "form": "written", "fidelity": 60},
            {"id": newest_row(RecordMediumRow, "id")},
            {"durability": 80, "form": "printed"},
        ),
        **row_levers(
            "media_outlet",
            "media_outlets",
            {"owner_node_id": Pick(MORTAL, 1), "seat_entity_id": Pick(TOWN, 1), "name": "The Vale Crier", "funding": "patronage"},
            {"id": newest_row(MediaOutletRow, "id")},
            {"trust": 70, "lean": 20},
        ),
        "media_item:create": after(
            OUTLET_UP, table="media_items", values={"outlet_id": newest_row(MediaOutletRow, "id"), "owner_node_id": Pick(MORTAL, 1), "kind": "opinion"}
        ),
        "media_item:edit": after(
            OUTLET_UP,
            ("media_item:create", {"table": "media_items", "values": {"outlet_id": newest_row(MediaOutletRow, "id"), "owner_node_id": Pick(MORTAL, 1)}}),
            table="media_items",
            key={"id": newest_row(MediaItemRow, "id")},
            values={"slant": 30, "kind": "devotion"},
        ),
        "media_item:delete": after(
            OUTLET_UP,
            ("media_item:create", {"table": "media_items", "values": {"outlet_id": newest_row(MediaOutletRow, "id"), "owner_node_id": Pick(MORTAL, 1)}}),
            table="media_items",
            key={"id": newest_row(MediaItemRow, "id")},
        ),
    }
)


LEVERS.update(
    {
        **seeded_levers(
            "humour_style",
            "humour_styles",
            {"people_entity_id": DAILY_FOLK, "form": "satire", "mock_rulers": True, "offence_threshold": 40},
            {"people_entity_id": DAILY_FOLK},
            {"form": "irony", "directness": 70},
        ),
        **row_levers(
            "speech",
            "speeches",
            {"speaker_node_id": Pick(MORTAL, 1), "place_entity_id": Pick(TOWN, 1), "venue": "assembly", "aim": "persuade", "skill": 60},
            {"id": newest_row(SpeechRow, "id")},
            {"aim": "rally", "reach": 50},
        ),
        **seeded_levers(
            "folk_knowledge",
            "folk_knowledge",
            {"people_entity_id": newest_row(FolkKnowledgeRow, "people_entity_id"), "domain": "time", "depth": 40, "accuracy": 55, "transmission": "rite"},
            {"id": newest_row(FolkKnowledgeRow, "id")},
            {"accuracy": 70, "holders": "specialists", "transmission": "written"},
        ),
        **seeded_levers(
            "death_work",
            "death_work",
            {"people_entity_id": STAFFED_FOLK, "role": "washer", "standing": "honoured", "purity": 60, "fee": 2, "workers": 3},
            {"id": STAFFED_WASHERS},
            {"standing": "avoided", "purity": 20, "workers": 1},
        ),
        **row_levers(
            "endowment",
            "endowments",
            {"founder_node_id": Pick(MORTAL, 1), "beneficiary_node_id": Pick(TOWN, 1), "purpose": "health", "capital": 200, "terms": "perpetual"},
            {"id": newest_row(EndowmentRow, "id")},
            {"purpose": "learning", "capital": 300, "sheltered": True},
        ),
        **row_levers(
            "folk_class",
            "folk_classes",
            {"people_entity_id": DAILY_FOLK, "domain": "society", "name": "Elders of the hearth", "taken_as": "sacred"},
            {"id": newest_row(FolkClassRow, "id")},
            {"name": "Keepers of the count", "taken_as": "omen"},
        ),
    }
)


async def first_town(session: AsyncSession) -> int | None:
    found: int | None = await session.scalar(select(func.min(EntityRow.id)).where(EntityRow.entity_type == EntityType.SETTLEMENT))
    return found


async def free_facet(session: AsyncSession) -> str:
    town = await first_town(session)
    kept = set(await session.scalars(select(FacetPracticeRow.facet).where(FacetPracticeRow.community_entity_id == town)))
    return next(facet.value for facet in FacetKind if facet not in kept)


FIRST_TOWN = Computed(first_town)
FREE_FACET = Computed(free_facet)
FIRST_LAND = Computed(lambda session: session.scalar(select(func.min(RegionEnvironmentRow.entity_id))))
FIRST_SHORE = Computed(
    lambda session: session.scalar(select(func.min(RegionEnvironmentRow.entity_id)).where(RegionEnvironmentRow.coast_kind.in_(list(COAST_OF_KIND))))
)
FIRST_PLANT = Computed(lambda session: session.scalar(select(func.min(PlantProfileRow.species_entity_id))))
LEVERS.update(
    {
        **row_levers(
            "facet_practice",
            "facet_practices",
            {"community_entity_id": FIRST_TOWN, "facet": FREE_FACET, "level": 40},
            {"id": newest_row(FacetPracticeRow, "id")},
            {"level": 70},
        ),
        **seeded_levers(
            "world_field",
            "world_fields",
            {"world_id": Pick("world"), "shielding": 40, "aurora_reach": 20},
            {"world_id": Pick("world")},
            {"shielding": 70, "compass_error": 10},
        ),
        **seeded_levers(
            "star_activity",
            "star_activity",
            {"star_id": Pick("star"), "cycle_years": 22, "flare_rate": 40},
            {"star_id": Pick("star")},
            {"phase": 50, "storm_rate": 30},
        ),
        **row_levers(
            "space_weather_event",
            "space_weather_events",
            {"world_id": Pick("world"), "kind": "flare", "strength": 40, "dose": 10},
            {"id": newest_row(SpaceWeatherEventRow, "id")},
            {"kind": "wind_surge", "strength": 60},
        ),
        **seeded_levers(
            "region_cryosphere",
            "region_cryosphere",
            {"region_entity_id": FIRST_LAND, "ice_months": 4, "snowpack": 30},
            {"region_entity_id": FIRST_LAND},
            {"ice_months": 6, "glacier_extent": 20},
        ),
        **row_levers(
            "sediment_flow",
            "sediment_flows",
            {"source_region_id": Pick(EntityType.REGION), "sink_region_id": Pick(EntityType.REGION, 1), "carrier": "river", "kind": "silt", "load": 30},
            {"id": newest_row(SedimentFlowRow, "id")},
            {"carrier": "wind", "kind": "sand", "load": 10},
        ),
        **seeded_levers(
            "coast",
            "coasts",
            {"region_entity_id": FIRST_SHORE, "form": "beach", "harbour_silting": 20},
            {"region_entity_id": FIRST_SHORE},
            {"form": "delta", "rate": 5},
        ),
        **seeded_levers(
            "local_climate",
            "local_climates",
            {"place_entity_id": Pick(TOWN), "cause": "built", "heat_shift": 5},
            {"place_entity_id": Pick(TOWN)},
            {"cause": "valley", "humidity_shift": 10},
        ),
        "disease_agent:create": after(
            DISEASE, table="disease_agents", values={"disease_entity_id": Newest(EntityType.DISEASE), "agent": "bacterium", "survival_water": 60}
        ),
        "disease_agent:edit": after(
            DISEASE,
            ("disease_agent:create", {"table": "disease_agents", "values": {"disease_entity_id": Newest(EntityType.DISEASE), "agent": "bacterium"}}),
            table="disease_agents",
            key={"disease_entity_id": Newest(EntityType.DISEASE)},
            values={"agent": "fungus", "survival_soil": 70},
        ),
        "disease_agent:delete": after(
            DISEASE,
            ("disease_agent:create", {"table": "disease_agents", "values": {"disease_entity_id": Newest(EntityType.DISEASE), "agent": "bacterium"}}),
            table="disease_agents",
            key={"disease_entity_id": Newest(EntityType.DISEASE)},
        ),
        **row_levers(
            "body_system",
            "body_systems",
            {"holder_entity_id": Pick(MORTAL, 1), "system": "breath", "air_need": 20},
            {"id": newest_row(BodySystemRow, "id")},
            {"gravity_max": 60, "heat_max": 70},
        ),
        **row_levers(
            "sensitivity",
            "sensitivities",
            {"holder_entity_id": Pick(MORTAL, 1), "kind": "to_food", "trigger_commodity": "grain", "severity": 30},
            {"id": newest_row(SensitivityRow, "id")},
            {"kind": "to_plant", "severity": 50},
        ),
        **seeded_levers(
            "plant_anatomy",
            "plant_anatomy",
            {"species_entity_id": FIRST_PLANT, "form": "tree", "reproduction": "animal_seed", "lifespan_years": 100},
            {"species_entity_id": FIRST_PLANT},
            {"form": "shrub", "growth_months": 8},
        ),
        **row_levers(
            "plant_part",
            "plant_parts",
            {"species_entity_id": FIRST_PLANT, "part": "tuber", "commodity": "tubers", "share": 30},
            {"id": newest_row(PlantPartRow, "id")},
            {"share": 50, "commodity": "fodder"},
        ),
        **row_levers(
            "observation_method",
            "observation_methods",
            {"people_entity_id": DAILY_FOLK, "domain": "sky", "method": "model", "accuracy": 70},
            {"id": newest_row(ObservationMethodRow, "id")},
            {"accuracy": 80, "reach": 40},
        ),
        **row_levers(
            "weather_work",
            "weather_works",
            {"holder_node_id": Pick(MORTAL, 1), "region_entity_id": Pick(EntityType.REGION), "method": "rite", "aim": "rain", "strength": 20},
            {"id": newest_row(WeatherWorkRow, "id")},
            {"aim": "calm", "epochs_left": 2},
        ),
        **row_levers(
            "profession_of_value",
            "professions_of_value",
            {"holder_node_id": Pick("son"), "axis": "honour", "strength": 60},
            {"id": newest_row(ProfessionOfValueRow, "id")},
            {"gap": 40, "knowers": 2},
        ),
    }
)
