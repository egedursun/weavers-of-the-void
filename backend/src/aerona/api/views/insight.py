from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.entities import (
    CapacityInsight,
    EntityInsight,
    ExplorationInsight,
    FaithInsight,
    KnowledgeInsight,
    LifeInsight,
    ResourceInsight,
    RewardInsight,
    SocietyInsight,
)
from aerona.api.views.common import node_ref, node_refs
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.agency import CreationRewardRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import ReverenceRow
from aerona.domain.enums.entity import AGENT_TYPES, SOCIETY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.engine.gods.economy import mechanics_of
from aerona.engine.gods.lineage import ancestors, descendants
from aerona.engine.lifecycle.aging import life_info
from aerona.engine.phases.exploration import land_measure
from aerona.engine.phases.society_economy import society_view
from aerona.engine.primitives.capacity import carrying_capacity
from aerona.engine.primitives.knowledge import knowledge_level, level_multiplier
from aerona.engine.primitives.mechanics import resource_weighed
from aerona.rules.registry import Rules
from aerona.services.gods.death import kill_price


async def society_insight(session: AsyncSession, rules: Rules, entity: EntityRow) -> SocietyInsight | None:
    if entity.entity_type not in SOCIETY_TYPES or entity.status is not EntityStatus.CANON:
        return None
    view = await society_view(session, rules, entity.id)
    society = view.society
    return SocietyInsight(
        shares={key.value: value for key, value in society.shares.items()},
        satisfaction={key.value: value for key, value in society.satisfaction.items()},
        stocks={key.value: value for key, value in society.stocks.items()},
        prices={key.value: value for key, value in society.prices.items()},
        unhappiest=view.unhappiest,
        bankruptcy_risk=view.bankruptcy_risk,
        uprising_risk=view.uprising_risk,
    )


async def life_insight(session: AsyncSession, rules: Rules, entity: EntityRow) -> LifeInsight | None:
    if entity.entity_type is not EntityType.MORTAL:
        return None
    info = await life_info(session, rules, entity)
    price = await kill_price(session, rules, entity.id)
    return LifeInsight(
        age=info.age,
        lifespan=info.lifespan.effective,
        lifespan_base=info.lifespan.base,
        medicine_bonus=info.lifespan.medicine,
        immortal=info.immortal,
        death_year=info.death_year,
        kill_chance_pct=price.chance.percent,
        son_kill_cost=price.son_cost,
        creator_kill_cost=price.creator_cost,
    )


async def capacity_insight(session: AsyncSession, rules: Rules, entity: EntityRow) -> CapacityInsight | None:
    reading = await carrying_capacity(session, rules, entity)
    if reading is None:
        return None
    return CapacityInsight(
        capacity=reading.capacity,
        region_population=reading.region_population,
        occupancy_pct=reading.occupancy_pct,
        region=await node_ref(session, reading.region_id),
    )


async def exploration_insight(session: AsyncSession, rules: Rules, entity: EntityRow) -> ExplorationInsight | None:
    if entity.entity_type not in SOCIETY_TYPES and entity.entity_type is not EntityType.REGION:
        return None
    measure = await land_measure(session, rules, entity.world_id)
    return ExplorationInsight(regions=measure.regions, places=measure.places, communities=measure.communities, pressure=measure.ratio, narrow=measure.narrow)


def knowledge_insight(rules: Rules, entity: EntityRow) -> KnowledgeInsight | None:
    if entity.entity_type is not EntityType.KNOWLEDGE:
        return None
    level = knowledge_level(rules, entity)
    return KnowledgeInsight(
        branch=entity.knowledge_branch,
        level=level,
        level_cap=rules.knowledge.level_cap,
        branch_multiplier=level_multiplier(rules.knowledge, level),
    )


async def resource_insight(session: AsyncSession, entity: EntityRow) -> ResourceInsight | None:
    if entity.entity_type is not EntityType.RESOURCE:
        return None
    flags = EntityRepository(session)
    return ResourceInsight(
        mechanics=sorted(item.value for item in await mechanics_of(session, entity)),
        weighed=await resource_weighed(session, entity),
        depleting=await flags.has_flag(entity.id, EntityFlag.DEPLETING),
        depleted=await flags.has_flag(entity.id, EntityFlag.DEPLETED),
    )


async def faith_insight(session: AsyncSession, entity: EntityRow) -> FaithInsight | None:
    if entity.entity_type not in AGENT_TYPES:
        return None
    revered = list(await session.scalars(select(ReverenceRow.god_node_id).where(ReverenceRow.entity_id == entity.id).order_by(ReverenceRow.god_node_id)))
    if not revered:
        return None
    refs = await node_refs(session, revered)
    return FaithInsight(
        revered=[refs[item] for item in revered if item in refs], syncretic=await EntityRepository(session).has_flag(entity.id, EntityFlag.SYNCRETIC)
    )


async def reward_insight(session: AsyncSession, entity: EntityRow) -> RewardInsight | None:
    row = await session.get(CreationRewardRow, entity.id)
    if row is None:
        return None
    return RewardInsight(
        son=await node_ref(session, row.son_id),
        xp=row.xp,
        renown=row.renown,
        essence=row.essence,
        cost=row.cost,
        land=row.land,
        fade_pct=row.fade_pct,
        repeats=row.repeats,
        taken_back_pct=row.taken_back_pct,
        has_thread=row.thread_id is not None,
        thread_reverted=row.thread_reverted,
        partner=await node_ref(session, row.partner_son_id) if row.partner_son_id is not None else None,
        partner_xp=row.partner_xp,
        partner_renown=row.partner_renown,
        reason=row.reason,
    )


async def entity_insight(session: AsyncSession, rules: Rules, entity: EntityRow) -> EntityInsight:
    depth = rules.god_power.bloodline_curse_depth
    elders = await ancestors(session, entity, depth)
    heirs = [item for item in await descendants(session, entity, depth) if item.id != entity.id]
    refs = await node_refs(session, [item.id for item in [*elders, *heirs]])
    return EntityInsight(
        society=await society_insight(session, rules, entity),
        life=await life_insight(session, rules, entity),
        capacity=await capacity_insight(session, rules, entity),
        exploration=await exploration_insight(session, rules, entity),
        knowledge=knowledge_insight(rules, entity),
        resource=await resource_insight(session, entity),
        faith=await faith_insight(session, entity),
        reward=await reward_insight(session, entity),
        ancestors=[refs[item.id] for item in elders if item.id in refs],
        descendants=[refs[item.id] for item in heirs if item.id in refs],
    )
