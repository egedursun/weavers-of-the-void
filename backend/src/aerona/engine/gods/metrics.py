from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from aerona.constants.units import PERCENT
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow, RiftRow
from aerona.db.tables.dominion import MiracleRecordRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow, LegendaryQuestRow, MessageRow
from aerona.db.tables.museums import MuseumCollectionRow
from aerona.db.tables.mythic import HeroquestRow, MantlingRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.routes import HorizonIntuitionRow, JourneyRow, RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import LegendaryQuestOutcome
from aerona.domain.enums.cosmography import RiftState
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.meta import GoalMetric
from aerona.domain.enums.mythic import HeroquestState, MantlingState
from aerona.domain.enums.node import ActorKind, NodeKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import HorizonStatus, JourneyStatus
from aerona.domain.enums.world import DARK_STAR_TYPES, EXTINGUISHED_STAR_TYPES, Discovery, StarType
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.voyages import DARK_SCOPES
from aerona.engine.gods.queries import canon_count, cosmos_row, world_count
from aerona.engine.gods.stats import Trait, trait_or
from aerona.engine.gods.worship import creator_node_id
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.queries import canon
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules

COMMUNITY_TIER_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
OPEN_RIFT_STATES = (RiftState.OPENING, RiftState.OPEN, RiftState.CLOSING)

Measure = Callable[[AsyncSession, Rules, int], Awaitable[int]]


async def _scalar(session: AsyncSession, statement: Select[int]) -> int:
    return int(await session.scalar(statement) or 0)


def _rows(column: ColumnElement[Any] | InstrumentedAttribute[Any]) -> Select[int]:
    return select(func.count(column))


def _canon(*types: EntityType) -> Measure:
    async def measure(session: AsyncSession, rules: Rules, epoch: int) -> int:
        return await canon_count(session, types)

    return measure


def _counted(build: Callable[[], Select[int]]) -> Measure:
    async def measure(session: AsyncSession, rules: Rules, epoch: int) -> int:
        return await _scalar(session, build())

    return measure


def _flagged(flag: EntityFlag) -> Measure:
    async def measure(session: AsyncSession, rules: Rules, epoch: int) -> int:
        statement = (
            select(func.count(EntityFlagRow.entity_id))
            .join(EntityRow, EntityRow.id == EntityFlagRow.entity_id)
            .where(EntityFlagRow.flag == flag, EntityRow.status == EntityStatus.CANON)
        )
        return await _scalar(session, statement)

    return measure


async def star_count(session: AsyncSession, types: frozenset[StarType] | None = None) -> int:
    statement = select(func.count(StarRow.id))
    if types is not None:
        statement = statement.where(StarRow.star_type.in_(list(types)))
    return await _scalar(session, statement)


async def peoples_population(session: AsyncSession) -> int:
    return sum(max(0, trait_or(people, Trait.POPULATION, 0)) for people in await canon(session, [EntityType.PEOPLE]))


async def faith_counts(session: AsyncSession) -> tuple[int, int]:
    peoples = await canon(session, [EntityType.PEOPLE])
    gods = Counter([god for god in [await patron_node(session, people) for people in peoples] if god is not None])
    return max(gods.values(), default=0), len(peoples)


async def inhabited_world_ids(session: AsyncSession) -> set[int]:
    worlds = set(await session.scalars(select(WorldRow.id).where(WorldRow.discovery != Discovery.FORGOTTEN)))
    statement = select(EntityRow.world_id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
    return {world_id for world_id in await session.scalars(statement) if world_id is not None} & worlds


async def highest_civ_tier(session: AsyncSession) -> int:
    return max([entity.civ_tier or 0 for entity in await canon(session, COMMUNITY_TIER_TYPES)], default=0)


async def _worlds(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await world_count(session)


async def _inhabited(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return len(await inhabited_world_ids(session))


async def _stars(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await star_count(session)


async def _reborn(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await star_count(session, frozenset({StarType.REBORN_STAR}))


async def _dead(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await star_count(session, EXTINGUISHED_STAR_TYPES & DARK_STAR_TYPES)


async def _far_trade(session: AsyncSession, rules: Rules, epoch: int) -> int:
    routes = list(await session.scalars(select(RouteRow).where(RouteRow.active.is_(True), RouteRow.traffic > 0).order_by(RouteRow.id)))
    if not routes:
        return 0
    cosmography = await Cosmography.load(session)
    return sum(1 for route in routes if cosmography.scope_by_id(route.world_a_id, route.world_b_id) in DARK_SCOPES)


async def _population(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await peoples_population(session)


async def _civ_tier(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await highest_civ_tier(session)


async def _largest_faith(session: AsyncSession, rules: Rules, epoch: int) -> int:
    most, _ = await faith_counts(session)
    return most


async def _creator_scoped(session: AsyncSession, build: Callable[[int], Select[int]]) -> int:
    creator_id = await creator_node_id(session)
    return await _scalar(session, build(creator_id)) if creator_id is not None else 0


async def _worshippers(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await _creator_scoped(
        session,
        lambda creator_id: (
            select(func.count(BondRow.id))
            .join(NodeRow, NodeRow.id == BondRow.source_node_id)
            .where(BondRow.target_node_id == creator_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, NodeRow.kind == NodeKind.ENTITY)
        ),
    )


async def _prayers(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await _creator_scoped(
        session,
        lambda creator_id: (
            select(func.count(MessageRow.id))
            .join(NodeRow, NodeRow.id == MessageRow.sender_node_id)
            .where(MessageRow.recipient_node_id == creator_id, MessageRow.intent == MessageIntent.PRAYER, NodeRow.kind == NodeKind.ENTITY)
        ),
    )


async def _miracles(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await _creator_scoped(session, lambda creator_id: select(func.count(MiracleRecordRow.id)).where(MiracleRecordRow.god_node_id == creator_id))


async def _son_level(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await _scalar(session, select(func.max(SonRow.level)).where(SonRow.status != SonStatus.DEAD))


async def _wonders(session: AsyncSession, rules: Rules, epoch: int) -> int:
    flagged = set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.WONDER)))
    return sum(1 for structure in await canon(session, [EntityType.STRUCTURE]) if structure.engine_kind is EngineKind.WONDER or structure.id in flagged)


async def _wars(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await ongoing_war_count(session)


async def _warless(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return 0 if await ongoing_war_count(session) else await canon_count(session, [EntityType.PEOPLE])


async def _epoch(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return epoch


async def _doom(session: AsyncSession, rules: Rules, epoch: int) -> int:
    cosmos = await cosmos_row(session)
    clock = cosmos.doom_clock if cosmos is not None else 0
    return round(clock * PERCENT / max(1, rules.balance.apocalypse_threshold))


def _creator_deeds(column: ColumnElement[Any] | InstrumentedAttribute[Any]) -> Select[int]:
    return select(func.count(column)).where(ActionRecordRow.actor_kind == ActorKind.CREATOR)


MEASURES: dict[GoalMetric, Measure] = {
    GoalMetric.WORLDS: _worlds,
    GoalMetric.INHABITED_WORLDS: _inhabited,
    GoalMetric.MOONS: _counted(lambda: _rows(WorldRow.id).where(WorldRow.parent_world_id.is_not(None))),
    GoalMetric.STARS: _stars,
    GoalMetric.REBORN_STARS: _reborn,
    GoalMetric.DEAD_STARS: _dead,
    GoalMetric.GALAXIES: _counted(lambda: _rows(GalaxyRow.id)),
    GoalMetric.CLUSTERS: _counted(lambda: _rows(ClusterRow.id)),
    GoalMetric.DIMENSIONS: _counted(lambda: _rows(DimensionRow.id)),
    GoalMetric.OPEN_RIFTS: _counted(lambda: _rows(RiftRow.id).where(RiftRow.state.in_(OPEN_RIFT_STATES))),
    GoalMetric.COSMIC_BEINGS: _canon(EntityType.COSMIC_BEING),
    GoalMetric.FAR_VOYAGES: _counted(lambda: _rows(JourneyRow.id).where(JourneyRow.status == JourneyStatus.ARRIVED, JourneyRow.scope.in_(DARK_SCOPES))),
    GoalMetric.FAR_TRADE_ROUTES: _far_trade,
    GoalMetric.SPECIES: _canon(EntityType.SPECIES),
    GoalMetric.BEASTS: _canon(EntityType.BEAST),
    GoalMetric.SPIRITS: _canon(EntityType.SPIRIT),
    GoalMetric.AWAKENED_SPECIES: _counted(lambda: _rows(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.SPECIES_BECAME_PEOPLE)),
    GoalMetric.PEOPLES: _canon(EntityType.PEOPLE),
    GoalMetric.POPULATION: _population,
    GoalMetric.SETTLEMENTS: _canon(EntityType.SETTLEMENT),
    GoalMetric.POLITIES: _canon(EntityType.POLITY),
    GoalMetric.EMPIRES: _flagged(EntityFlag.EMPIRE),
    GoalMetric.GOLDEN_AGES: _flagged(EntityFlag.GOLDEN_AGE),
    GoalMetric.HIGHEST_CIV_TIER: _civ_tier,
    GoalMetric.TREATIES: _canon(EntityType.TREATY),
    GoalMetric.TRADE_ROUTES: _canon(EntityType.TRADE_ROUTE),
    GoalMetric.LANGUAGES: _canon(EntityType.LANGUAGE),
    GoalMetric.CULTS: _canon(EntityType.CULT),
    GoalMetric.CREATOR_WORSHIPPERS: _worshippers,
    GoalMetric.PRAYERS_TO_CREATOR: _prayers,
    GoalMetric.FULFILLED_PROPHECIES: _counted(
        lambda: _rows(EntityRow.id).where(EntityRow.entity_type == EntityType.PROPHECY, EntityRow.status == EntityStatus.FULFILLED)
    ),
    GoalMetric.LARGEST_FAITH: _largest_faith,
    GoalMetric.ASCENDED_MORTALS: _counted(lambda: _rows(MantlingRow.mortal_entity_id).where(MantlingRow.state == MantlingState.ASCENDED)),
    GoalMetric.LIVING_SONS: _counted(lambda: _rows(SonRow.id).where(SonRow.status != SonStatus.DEAD)),
    GoalMetric.HIGHEST_SON_LEVEL: _son_level,
    GoalMetric.RESURRECTIONS: _counted(lambda: _rows(ChronicleRow.id).where(ChronicleRow.template_key == "gods.death.son_resurrected")),
    GoalMetric.SUPPRESSED_REBELLIONS: _counted(lambda: _rows(ActionRecordRow.id).where(ActionRecordRow.kind == ActionKind.SUPPRESS_REBELLION)),
    GoalMetric.FOREIGN_GODS: _counted(lambda: _rows(ForeignGodRow.id).where(ForeignGodRow.status != ForeignGodStatus.DEAD)),
    GoalMetric.KNOWLEDGE: _canon(EntityType.KNOWLEDGE),
    GoalMetric.THEORIES: _canon(EntityType.THEORY),
    GoalMetric.ARTWORKS: _canon(EntityType.ARTWORK),
    GoalMetric.ART_FORMS: _canon(EntityType.ART_FORM),
    GoalMetric.LEGENDS: _canon(EntityType.LEGEND),
    GoalMetric.TRADITIONS: _canon(EntityType.TRADITION),
    GoalMetric.LAWS: _canon(EntityType.LAW),
    GoalMetric.WONDERS: _wonders,
    GoalMetric.MUSEUMS: _counted(lambda: _rows(MuseumCollectionRow.id)),
    GoalMetric.COMPLETED_SAGAS: _counted(lambda: _rows(LegendaryQuestRow.thread_id).where(LegendaryQuestRow.outcome == LegendaryQuestOutcome.COMPLETED)),
    GoalMetric.HEROQUESTS_WON: _counted(lambda: _rows(HeroquestRow.id).where(HeroquestRow.state == HeroquestState.SUCCEEDED)),
    GoalMetric.ARRIVED_JOURNEYS: _counted(lambda: _rows(JourneyRow.id).where(JourneyRow.status == JourneyStatus.ARRIVED)),
    GoalMetric.DISCOVERIES: _counted(lambda: _rows(BondRow.id).where(BondRow.kind == BondKind.DISCOVERED)),
    GoalMetric.SENSED_WORLDS: _counted(lambda: _rows(HorizonIntuitionRow.id).where(HorizonIntuitionRow.status == HorizonStatus.BORN)),
    GoalMetric.VESSELS: _canon(EntityType.VESSEL),
    GoalMetric.ONGOING_WARS: _wars,
    GoalMetric.WARLESS_PEOPLES: _warless,
    GoalMetric.EPOCH: _epoch,
    GoalMetric.DOOM_PERCENT: _doom,
    GoalMetric.CREATOR_DEEDS: _counted(lambda: _creator_deeds(ActionRecordRow.id)),
    GoalMetric.LEVERS_USED: _counted(lambda: _creator_deeds(distinct(ActionRecordRow.kind))),
    GoalMetric.MIRACLES: _miracles,
}


async def measure_metric(session: AsyncSession, rules: Rules, metric: GoalMetric, epoch: int) -> int:
    return await MEASURES[metric](session, rules, epoch)


@dataclass
class MetricReader:
    session: AsyncSession
    rules: Rules
    epoch: int
    values: dict[GoalMetric, int] = field(default_factory=dict)

    async def value(self, metric: GoalMetric) -> int:
        if metric not in self.values:
            self.values[metric] = await measure_metric(self.session, self.rules, metric, self.epoch)
        return self.values[metric]

    async def total(self, *metrics: GoalMetric) -> int:
        return sum([await self.value(metric) for metric in metrics])
