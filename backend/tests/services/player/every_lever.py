import enum
import types
import typing
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.random import SeededRandom
from aerona.db.base import Base
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.agency import CreationRewardRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import NaturalLawProfileRow, OuterBeingProfileRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import DeferredStepRow, EpochRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import HistorianViewRow, MessageRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.routes import HorizonIntuitionRow, RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.divine import LawScope, OuterHunger
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.epoch import DeferredStepStatus
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import NaturalLawStats, OuterBeingStats
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.economy.route_control import route_of
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import set_stats
from aerona.engine.services.war import sides_of
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


def exact_table(name: str) -> Any:
    for table in (f"{name}s", f"{name}es", f"{name[:-1]}ies" if name.endswith("y") else "", f"{name[:-2]}es" if name.endswith("is") else "", name):
        found = TABLES.get(table)
        if found is not None and "id" in found.__table__.c:
            return found
    for table, found in TABLES.items():
        if table.endswith(f"_{name}s") and "id" in found.__table__.c:
            return found
    return None


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
    found = exact_table(kind)
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


REALM = EntityType.POLITY
TOWN = EntityType.SETTLEMENT
MORTAL = EntityType.MORTAL
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
DISEASE = ("disease:create", {"region_id": Pick(EntityType.REGION), "name": "Grey Cough"})
FOREIGN = ("foreign_god:place", {"world_id": Pick("world"), "name": "Ussamar"})


async def route_region(session: AsyncSession) -> int:
    route = await canon(session, EntityType.TRADE_ROUTE, 0)
    assert route is not None
    found = await route_of(await manual_context(session, "lever", Rules()), route)
    return found.path[0]


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
    session.add(NaturalLawProfileRow(law_entity_id=law.id, effect=NaturalLaw.BOUNTY, scope=LawScope.WORLD, world_id=world, locked=[]))
    await session.flush()
    return law.id


async def outer_being(session: AsyncSession) -> int:
    found = await session.scalar(select(EntityRow.id).where(EntityRow.entity_type == EntityType.OUTER_BEING).order_by(EntityRow.id).limit(1))
    if found is not None:
        if await session.get(OuterBeingProfileRow, found) is None:
            session.add(OuterBeingProfileRow(outer_entity_id=found, hunger=OuterHunger.NAMES, locked=[]))
            await session.flush()
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
    session.add(OuterBeingProfileRow(outer_entity_id=being.id, hunger=OuterHunger.NAMES, locked=[]))
    await session.flush()
    return being.id


CUSTOM_KIND = ("kind:create", {"catalog": "technique", "base": "phalanx_drill", "name": "Shieldwall Drill"})
SPEAKERS = ("language:speakers", {"community_id": Pick(TOWN), "language_id": Pick(EntityType.LANGUAGE, 2), "share": 30, "kind": "second"})
TEMPLE = ("structure:commission", {"site_id": Pick(TOWN), "kind": "temple"})
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
FEDERATION = ("federation", {"member_ids": [Pick(TOWN), Computed(far_town)], "name": "The Concord"})
ASSEMBLY = Where("entities", "id", {"engine_kind": EngineKind.INTERWORLD_FEDERATION})
PASSION = ("passion:set", {"holder_id": Pick(MORTAL), "kind": "love", "object_id": Pick(MORTAL, 1), "strength": 90})
GATE_LORE = ("research:level", {"holder_id": Pick(EntityType.PEOPLE), "branch": "gate_lore", "level": 2})
PROPHECY = (
    "lore:create",
    {"entity_type": "prophecy", "name": "The Second Dawn", "world_id": Pick("world"), "values": {"predicate": "dies", "subject_id": Pick(MORTAL)}},
)
MAIMED = ("body:maim", {"bearer_id": Pick(MORTAL), "part": "left_arm", "severity": 3, "lethal": False})

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
        name: after(("case:open", {"settlement_id": Pick(TOWN), "crime": "theft", "accused_id": Pick(MORTAL)}), case_id=Newest("case"))
        for name in ("case:hold", "case:try", "case:delete")
    },
    "case:edit": after(("case:open", {"settlement_id": Pick(TOWN), "crime": "theft", "accused_id": Pick(MORTAL)}), case_id=Newest("case"), evidence=50),
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
    **{
        name: after(("civilization:loan", {"lender_id": Pick(TOWN), "borrower_id": Pick(TOWN, 1), "amount": 10}), bond_id=Newest("bond"))
        for name in ("civilization:forgive_debt", "civilization:enforce_debt")
    },
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
    "entity:tags": given(add_flags=["cursed"]),
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
    "fact:remove": after(("fact:add", {"subject_id": Pick(MORTAL), "relation": "remembers", "object_text": "the old river"}), fact_id=Newest("fact")),
    "faction:spy": given(spymaster_id=Pick(REALM), target_id=Pick(TOWN)),
    "feud:end": after(("feud:start", {"first_id": Pick(TOWN), "second_id": Pick(TOWN, 1)})),
    **{name: setup_then(foreign_god, god_id=Pick("foreign_god")) for name in ("foreign_god:raise_land", "kill:foreign_god", "drain:foreign_god")},
    "foreign_god:edit": setup_then(foreign_god, god_id=Pick("foreign_god"), stance=10),
    "foreign_god:strike": setup_then(foreign_god, god_id=Pick("foreign_god"), entity_id=Pick(MORTAL)),
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
    "knowledge:set": given(known=False),
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
    "military:create": given(kind="unit_design", values={"name": "Spearwall", "base_kind": "spearmen", "owner_entity_id": Pick(TOWN)}),
    **{
        name: after(
            ("military:create", {"kind": "unit_design", "values": {"name": "Spearwall", "base_kind": "spearmen", "owner_entity_id": Pick(TOWN)}}),
            kind="unit_design",
            record_id=Newest("unit_design"),
        )
        for name in ("military:delete", "military:edit", "military:release")
    },
    "mind:lock": given(field="traits"),
    "mind:unlock": after(("mind:lock", {"node_id": Pick(MORTAL), "field": "traits"}), field="traits"),
    "mind:pressure": given(node_id=Pick(TOWN)),
    "mind:skill_remove": after(("mind:skill", {"node_id": Pick(MORTAL), "skill": "blade", "level": 30})),
    "mind:trait_remove": after(("mind:trait", {"node_id": Pick(MORTAL), "trait": "brave"})),
    "modifier:add": given(key="strength", magnitude=5.0),
    "modifier:create": given(key="strength", magnitude=5.0),
    "modifier:release": after(("modifier:hold", {"modifier_id": Pick("modifier")})),
    "mortal:ability_release": after(("mortal:ability", {"mortal_id": Pick(MORTAL), "ability": "endurance", "value": 60, "hold": True})),
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
        ("region:danger_create", {"region_id": Pick(EntityType.REGION), "strength": 30, "hold": True}), danger_id=Newest("region_danger")
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
    "rite:dispel": after(RITE, ("rite:cast", {"rite_id": Newest(EntityType.RITE), "caster_id": Pick(MORTAL)}), rite_id=Newest(EntityType.RITE)),
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
    "species:chimera": given(first_id=Pick(EntityType.SPECIES), second_id=Pick(EntityType.SPECIES, 1)),
    "species:custom_use": after(("use_kind:create", {"name": "Lantern Bearer", "base_use": "food"}), kind_id=Newest("species_use_kind")),
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
    "son:outer_bargain": after(("horror:outer_being", {"world_id": Pick("world")}), outer_id=Newest(EntityType.OUTER_BEING), request="a clear sky"),
    "star:edit": given(brightness=60),
    "strip_power": after(("son:power", {"son_id": Pick("son"), "slot": 1, "name": "Long Stride", "effect": "tireless"}), slot=1),
    "structure:commission": given(site_id=Pick(TOWN), kind="temple"),
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
        name: after(("use_kind:create", {"name": "Lantern Bearer", "base_use": "food"}), kind_id=Newest("species_use_kind"))
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
    "witness:set": after(CASE, case_id=Newest("case"), witness_id=Pick(MORTAL, 1)),
    "witness:remove": after(
        CASE,
        ("witness:set", {"case_id": Newest("case"), "witness_id": Pick(MORTAL, 1), "testimony": "accuses", "reliability": 50}),
        case_id=Newest("case"),
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
        ("lore:create", {"entity_type": "art_form", "name": "Reed Song", "world_id": Pick("world"), "values": {"discipline": "music"}}),
        art_form_id=Newest(EntityType.ART_FORM),
    ),
    "community:crown": given(community_id=Pick(EntityType.PEOPLE, 1)),
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
    "cosmic:legendary_quest": after(("cosmic:extinguish_star", {"star_id": Pick("star")}), kind="dead_star"),
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
    "exile": given(world_id=Pick("world", 1)),
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
        ("research:technique", {"holder_id": Pick(TOWN, 2), "technique": "phalanx_drill"}),
        ("faction:found", {"community_id": Pick(TOWN, 2), "kind": "craft_guild"}),
        guild_id=Newest(EntityType.FACTION),
    ),
    "hero:hunt": given(monster_id=Pick(EntityType.SPECIES)),
    **{name: after(("hero:quest", {"hero_id": Pick(MORTAL)})) for name in ("hero:recall", "hero:resolve")},
    "holy_order:edit": after(*HOLY, order_id=Newest(EntityType.FACTION), tithe_share=10),
    "holy_order:remove": after(*HOLY, ("holy_order:edit", {"order_id": Newest(EntityType.FACTION), "tithe_share": 10}), order_id=Newest(EntityType.FACTION)),
    "horror:suppress_cult": after(("horror:cult", {"entity_id": Pick(TOWN)}), cult_id=Newest(EntityType.CULT)),
    "house:merge": given(house_id=Pick(EntityType.HOUSE), into_id=Pick(EntityType.HOUSE, 1)),
    "identity:edit": after(("identity:assume", {"mortal_id": Pick(MORTAL), "false_name": "Wren"}), mortal_id=Pick(MORTAL), exposure=20),
    "incident:unlink_cause": after(
        ("incident:link_cause", {"incident_id": Newest("incident"), "cause_incident_id": Pick("incident")}), incident_id=Newest("incident")
    ),
    "item:transfer": given(receiver_id=Pick(MORTAL, 1)),
    "kin:end_marriage": after(("kin:marry", {"first_id": Pick(MORTAL), "second_id": Pick(MORTAL, 1)}), marriage_id=Newest("marriage")),
    "kin:unbond": after(("kin:bond", {"source_id": Pick(MORTAL), "target_id": Pick(MORTAL, 1), "kind": "parent_of"}), bond_id=Newest("bond")),
    "market:write_off": after(("civilization:loan", {"lender_id": Pick(TOWN), "borrower_id": Pick(TOWN, 1), "amount": 10}), bond_id=Newest("bond")),
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
    "rite": Lever(values={"entity_id": Pick(TOWN), "son_id": Pick("son", 1), "kind": "rite"}, setup=dead_sibling),
    **{name: Lever(values={"sibling_id": Pick("son"), "son_id": Pick("son", 1)}, setup=dead_sibling) for name in ("sibling:scatter", "sibling:scheme")},
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
        ("afterlife:stratum", {"realm_id": Pick(REALM), "kind": "plain", "name": "The Grey Field"}),
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
    "quest:abandon": after(
        ("cosmic:extinguish_star", {"star_id": Pick("star")}), ("cosmic:legendary_quest", {"kind": "dead_star"}), thread_id=Newest("thread")
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
    "body:prosthesis": after(("body:maim", {"bearer_id": Pick(MORTAL), "part": "left_arm", "severity": 5, "lethal": False}), material="wood", quality=40),
}

EDITS: Mapping[str, Mapping[str, Any]] = {
    "trade_route:edit": {"danger_bandits": 30, "capacity": 50, "length": 3, "chokepoint": True},
    "structure:edit": {"condition": 80, "anchor": True, "splendor": 60},
    "structure_design:edit": {"cost_pct": 110},
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
    "law_profile:edit": {"strength": 70, "scope": "cosmos"},
    "outer_profile:edit": {"reach": 2, "hunger": "light"},
    "breach:edit": {"strength": 40},
}
LEVERS.update({name: replace(LEVERS.get(name, Lever()), values={**LEVERS.get(name, Lever()).values, "values": values}) for name, values in EDITS.items()})


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
    ("route", "stitch"): after(("route", {"route_id": Pick("route"), "action": "sever", "duration": 3}), route_id=Pick("route")),
}


ART_FORM = ("lore:create", {"entity_type": "art_form", "name": "Reed Song", "world_id": Pick("world"), "values": {"discipline": "music"}})
LORE_LEVERS: Mapping[str, Lever] = {
    kind.value: after(step, entity_id=Newest(kind))
    for kind, step in (
        (EntityType.ART_FORM, ART_FORM),
        (EntityType.IDEOLOGY, IDEOLOGY),
        (EntityType.PROPHECY, PROPHECY),
        (EntityType.RITE, RITE),
        (EntityType.THEORY, THEORY),
    )
}
