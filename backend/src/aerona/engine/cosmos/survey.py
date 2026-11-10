from dataclasses import dataclass

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import WorldSurveyRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.physics import SURVEY_ORDER, SurveyLevel
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import Cosmography, Placement
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import canon
from aerona.rules.registry import Rules

OBSERVER_TYPES = (EntityType.POLITY, EntityType.PEOPLE)
SURVEYING = frozenset({JourneyIntent.EXPLORATION, JourneyIntent.COLONY, JourneyIntent.CONQUEST, JourneyIntent.TRADE, JourneyIntent.PILGRIMAGE})


def index_of(level: SurveyLevel) -> int:
    return SURVEY_ORDER.index(level)


def at(index: int) -> SurveyLevel:
    return SURVEY_ORDER[max(0, min(len(SURVEY_ORDER) - 1, index))]


async def observers_of(session: AsyncSession, entity: EntityRow) -> list[int]:
    if entity.entity_type in OBSERVER_TYPES:
        return [entity.id]
    statement = (
        select(BondRow.source_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == entity.id, EntityRow.entity_type == EntityType.POLITY
        )
    )
    found = list(await session.scalars(statement.order_by(BondRow.id)))
    people = await people_of(session, entity)
    if people is not None:
        found.append(people.id)
    return list(dict.fromkeys(found)) or [entity.id]


async def level_of(session: AsyncSession, observer_id: int, world_id: int) -> SurveyLevel:
    observer = await session.get(EntityRow, observer_id)
    if observer is not None and observer.world_id == world_id:
        return SurveyLevel.MAPPED
    row = await session.scalar(select(WorldSurveyRow).where(WorldSurveyRow.observer_entity_id == observer_id, WorldSurveyRow.world_id == world_id))
    if row is not None:
        return row.level
    if observer is None or observer.world_id is None:
        return SurveyLevel.UNKNOWN
    joined = select(RouteRow.id).where(
        RouteRow.known.is_(True),
        or_(
            and_(RouteRow.world_a_id == observer.world_id, RouteRow.world_b_id == world_id),
            and_(RouteRow.world_a_id == world_id, RouteRow.world_b_id == observer.world_id),
        ),
    )
    return SurveyLevel.RUMOURED if await session.scalar(joined.limit(1)) is not None else SurveyLevel.UNKNOWN


async def knows_enough(session: AsyncSession, traveller: EntityRow, world_id: int, needed: int) -> bool:
    if traveller.world_id == world_id:
        return True
    levels = [index_of(await level_of(session, observer, world_id)) for observer in await observers_of(session, traveller)]
    return max(levels) >= needed


@dataclass(frozen=True)
class Eyes:
    home: Placement
    home_world: int
    astronomy: int
    sailing: bool


def seen(rules: Rules, eyes: Eyes, place: Placement, world_id: int, routes: list[RouteRow]) -> SurveyLevel:
    table = rules.survey
    level = SurveyLevel.UNKNOWN
    if any({route.world_a_id, route.world_b_id} == {eyes.home_world, world_id} for route in routes):
        level = SurveyLevel.RUMOURED
    if place.galaxy_id is not None and place.galaxy_id == eyes.home.galaxy_id and eyes.astronomy >= table.detect_level:
        level = SurveyLevel.DETECTED
    if place.star is not None and eyes.home.star is not None and place.star.id == eyes.home.star.id and eyes.astronomy >= table.observe_level:
        level = SurveyLevel.OBSERVED
    if eyes.sailing and index_of(level) >= index_of(SurveyLevel.DETECTED):
        level = at(min(index_of(level) + table.sail_steps, index_of(SurveyLevel.OBSERVED)))
    return level


def visited(level: SurveyLevel, trips: list[tuple[int, JourneyIntent]], world_id: int) -> SurveyLevel:
    for destination, intent in trips:
        if destination == world_id and intent in SURVEYING:
            level = SurveyLevel.MAPPED if intent is JourneyIntent.EXPLORATION else max(level, SurveyLevel.SURVEYED, key=index_of)
    return level


async def survey_cycle(ctx: TickContext, cosmography: Cosmography) -> int:
    knowledge = await KnowledgeMap.load(ctx.session)
    raised = 0
    arrivals: dict[int, list[tuple[int, JourneyIntent]]] = {}
    recent = select(JourneyRow).where(JourneyRow.status == JourneyStatus.ARRIVED, JourneyRow.end_epoch >= ctx.epoch - 1).order_by(JourneyRow.id)
    for journey in list(await ctx.session.scalars(recent)):
        traveller = await ctx.session.get(EntityRow, journey.traveller_entity_id)
        for seer in await observers_of(ctx.session, traveller) if traveller is not None else []:
            arrivals.setdefault(seer, []).append((journey.destination_world_id, journey.intent))
    routes = list(await ctx.session.scalars(select(RouteRow).where(RouteRow.known.is_(True)).order_by(RouteRow.id)))
    known = {(row.observer_entity_id, row.world_id): row for row in await ctx.session.scalars(select(WorldSurveyRow))}
    for observer in sorted(await canon(ctx.session, list(OBSERVER_TYPES)), key=lambda row: row.id):
        if held(observer.id) or observer.world_id is None:
            continue
        eyes = Eyes(
            cosmography.place_world_id(observer.world_id),
            observer.world_id,
            knowledge.level(observer.id, KnowledgeBranch.ASTRONOMY),
            KnowledgeBranch.SKY_NAVIGATION in knowledge.branches(observer.id),
        )
        for world in sorted(cosmography.worlds.values(), key=lambda row: row.id):
            if world.id == observer.world_id:
                continue
            level = visited(seen(ctx.rules, eyes, cosmography.place_world(world), world.id, routes), arrivals.get(observer.id, []), world.id)
            row = known.get((observer.id, world.id))
            if level is SurveyLevel.UNKNOWN or (row is not None and ("level" in row.locked or index_of(row.level) >= index_of(level))):
                continue
            if row is None:
                row = WorldSurveyRow(observer_entity_id=observer.id, world_id=world.id, level=level, epoch=ctx.epoch, locked=[])
                ctx.session.add(row)
                known[(observer.id, world.id)] = row
            row.level, row.epoch = level, ctx.epoch
            raised += 1
    await ctx.session.flush()
    return raised
