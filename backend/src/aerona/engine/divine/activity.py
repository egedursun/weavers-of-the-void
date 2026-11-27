from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.catalog.domain_effects import DOMAIN_EFFECTS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import CastingRow
from aerona.db.tables.divine import DomainActivityRow
from aerona.db.tables.economy import GoodsFlowRow, TradeFlowRow, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.mind import DreamRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine import DomainActivity
from aerona.domain.enums.economy import GoodsFlow, TradeMode
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.polity import OathStatus
from aerona.engine.context import TickContext
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.primitives.queries import living_sons
from aerona.engine.sacred.feeding import harvest_feelings
from aerona.rules.registry import Rules

A = DomainActivity
Counts = dict[int, int]
Counter = Callable[[AsyncSession, int, Rules], Awaitable[Counts]]
WORK_TYPES = (EntityType.ARTWORK, EntityType.ITEM)


async def grouped(session: AsyncSession, statement: Select[Any, Any]) -> Counts:
    return {int(world): int(count) for world, count in await session.execute(statement) if world is not None}


def born(epoch: int, *kinds: EntityType) -> Select[int, int]:
    return (
        select(EntityRow.world_id, func.count(EntityRow.id))
        .where(EntityRow.birth_epoch == epoch, EntityRow.entity_type.in_(list(kinds)))
        .group_by(EntityRow.world_id)
    )


async def battles(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(EntityRow.id))
        .where(EntityRow.birth_epoch == epoch, EntityRow.engine_kind.in_([EngineKind.BATTLE, EngineKind.SIEGE]))
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def deaths(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(EntityRow.id))
        .where(EntityRow.end_epoch == epoch, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status != EntityStatus.CANON)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def births(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    return await grouped(session, born(epoch, EntityType.MORTAL))


async def voyages(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(TradeFlowRow.id))
        .join(TradeRouteProfileRow, TradeRouteProfileRow.route_entity_id == TradeFlowRow.route_entity_id)
        .join(EntityRow, EntityRow.id == TradeFlowRow.from_entity_id)
        .where(TradeFlowRow.epoch == epoch, TradeRouteProfileRow.mode == TradeMode.SEA)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def trade(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count())
        .select_from(GoodsFlowRow)
        .join(EntityRow, EntityRow.id == GoodsFlowRow.community_entity_id)
        .where(GoodsFlowRow.epoch == epoch, GoodsFlowRow.flow == GoodsFlow.TRADE)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def sickness(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(EntityRow.id))
        .where(EntityRow.birth_epoch == epoch, EntityRow.engine_kind == EngineKind.PLAGUE)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def oaths(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(OathRow.id))
        .join(EntityRow, EntityRow.id == OathRow.swearer_entity_id)
        .where(OathRow.ended_epoch == epoch, OathRow.status.in_([OathStatus.KEPT, OathStatus.FULFILLED]))
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def legends(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    return await grouped(session, born(epoch, EntityType.LEGEND))


async def works(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    return await grouped(session, born(epoch, *WORK_TYPES))


async def discoveries(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    return await grouped(session, born(epoch, EntityType.KNOWLEDGE))


async def marriages(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(BondRow.id))
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.SPOUSE_OF, BondRow.epoch == epoch)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def hunts(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    prey = aliased(EntityRow)
    statement = (
        select(prey.world_id, func.count(BondRow.id))
        .join(prey, prey.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.KILLED, BondRow.epoch == epoch, prey.entity_type == EntityType.BEAST)
        .group_by(prey.world_id)
    )
    return await grouped(session, statement)


async def schemes(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    owner = aliased(EntityRow)
    statement = (
        select(owner.world_id, func.count(SchemeRow.id))
        .join(owner, owner.id == SchemeRow.owner_node_id)
        .where(SchemeRow.started_epoch == epoch)
        .group_by(owner.world_id)
    )
    return await grouped(session, statement)


async def rites(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(CastingRow.id))
        .join(EntityRow, EntityRow.id == CastingRow.caster_entity_id)
        .where(CastingRow.epoch == epoch)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def dreams(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = select(DreamRow.world_id, func.count(DreamRow.id)).where(DreamRow.epoch == epoch).group_by(DreamRow.world_id)
    return await grouped(session, statement)


async def hunger(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(EntityRow.id))
        .where(EntityRow.birth_epoch == epoch, EntityRow.engine_kind == EngineKind.FAMINE)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def madness(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.count(EntityRow.id))
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.sanity.is_not(None), EntityRow.sanity < rules.domains.madness_below)
        .group_by(EntityRow.world_id)
    )
    return await grouped(session, statement)


async def journeys(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = select(JourneyRow.origin_world_id, func.count(JourneyRow.id)).where(JourneyRow.start_epoch == epoch).group_by(JourneyRow.origin_world_id)
    travels = await grouped(session, statement)
    caravans = (
        select(EntityRow.world_id, func.count(TradeFlowRow.id))
        .join(TradeRouteProfileRow, TradeRouteProfileRow.route_entity_id == TradeFlowRow.route_entity_id)
        .join(EntityRow, EntityRow.id == TradeFlowRow.from_entity_id)
        .where(TradeFlowRow.epoch == epoch, TradeRouteProfileRow.mode == TradeMode.ROAD)
        .group_by(EntityRow.world_id)
    )
    for world, count in (await grouped(session, caravans)).items():
        travels[world] = travels.get(world, 0) + count
    return travels


async def harvests(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    statement = (
        select(EntityRow.world_id, func.sum(GoodsFlowRow.quantity))
        .join(EntityRow, EntityRow.id == GoodsFlowRow.community_entity_id)
        .where(GoodsFlowRow.epoch == epoch, GoodsFlowRow.flow == GoodsFlow.HARVEST)
        .group_by(EntityRow.world_id)
    )
    found = await grouped(session, statement)
    return {world: count // max(1, rules.domains.harvest_units_per_count) for world, count in found.items()}


async def building(session: AsyncSession, epoch: int, rules: Rules) -> Counts:
    return await grouped(session, born(epoch, EntityType.STRUCTURE))


COUNTERS: dict[DomainActivity, Counter] = {
    A.BATTLES: battles,
    A.DEATHS: deaths,
    A.BIRTHS: births,
    A.VOYAGES: voyages,
    A.TRADE: trade,
    A.SICKNESS: sickness,
    A.OATHS: oaths,
    A.LEGENDS: legends,
    A.WORKS: works,
    A.DISCOVERIES: discoveries,
    A.MARRIAGES: marriages,
    A.HUNTS: hunts,
    A.SCHEMES: schemes,
    A.RITES: rites,
    A.DREAMS: dreams,
    A.HUNGER: hunger,
    A.MADNESS: madness,
    A.JOURNEYS: journeys,
    A.HARVESTS: harvests,
    A.BUILDING: building,
}


def income(rules: Rules, count: float) -> int:
    table = rules.domains
    if count <= 0:
        return 0
    return round(table.activity_essence_max * count / (count + max(1, table.activity_half)))


async def presence(ctx: TickContext) -> dict[int, set[int]]:
    book = await ctx.divine()
    worlds: dict[int, set[int]] = defaultdict(set)
    for worshipper, gods in book.patrons.items():
        _, _, world_id = await book.place_of(ctx.session, worshipper)
        for god_id in gods:
            if world_id:
                worlds[god_id].add(world_id)
    for son in await living_sons(ctx.session):
        if son.current_world_id is not None:
            worlds[son.id].add(son.current_world_id)
    return worlds


async def tend_domain_economy(ctx: TickContext) -> int:
    book = await ctx.divine()
    worlds = await presence(ctx)
    counts: dict[DomainActivity, Counts] = {}
    claimants: dict[tuple[DomainActivity, int], int] = defaultdict(int)
    for god_id, god in book.gods.items():
        for domain in god.living_domains:
            for world_id in worlds.get(god_id, set()):
                claimants[(DOMAIN_EFFECTS[domain].activity, world_id)] += 1
    written = 0
    feelings = await harvest_feelings(ctx, book) if ctx.rules.emotion_feeding.essence_max else {}
    for god_id, god in sorted(book.gods.items()):
        if held(god_id):
            continue
        gained = feelings.get(god_id, 0)
        for domain in god.living_domains:
            activity = DOMAIN_EFFECTS[domain].activity
            if activity not in counts:
                counts[activity] = await COUNTERS[activity](ctx.session, ctx.epoch, ctx.rules)
            share = sum(counts[activity].get(world, 0) / max(1, claimants[(activity, world)]) for world in worlds.get(god_id, set()))
            essence = round(income(ctx.rules, share) * god.potency)
            ctx.session.add(DomainActivityRow(god_node_id=god_id, epoch=ctx.epoch, domain=domain, activity=activity, count=round(share), essence=essence))
            gained += essence
            written += 1
        await credit(ctx, god_id, gained)
    return written


async def credit(ctx: TickContext, god_id: int, gained: int) -> None:
    if gained <= 0:
        return
    son = await ctx.session.get(SonRow, god_id)
    if son is not None:
        before = son.essence
        son.essence += gained
        cap_gained_essence(ctx.rules, son, before)
        return
    god = await ctx.session.get(ForeignGodRow, god_id)
    if god is not None:
        god.power = min(PERCENT, god.power + round(gained * ctx.rules.domains.foreign_power_pct / PERCENT))
