from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.economy import TradeRouteProfileRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.vehicles import DesignTechniqueRow, VehicleGroupRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, TradeMode, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.structure import STANDING_STATES, StructureKind
from aerona.domain.enums.vehicles import VehicleStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.lore.research import techniques_of
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.vehicles.caravans import carrier_design
from aerona.engine.vehicles.fleet import role_design
from aerona.engine.vehicles.groups import add_vehicles, burn_fuel, groups_of, repair_group

W = WorkshopKind
YARD_ROLES: MappingProxyType[WorkshopKind, tuple[UnitKind, ...]] = MappingProxyType(
    {
        W.SHIPYARD: (UnitKind.NAVAL_CREW,),
        W.SIEGE_YARD: (UnitKind.SIEGE_CREW, UnitKind.ARTILLERY_CREW, UnitKind.VEHICLE_CREW),
        W.STABLE: (UnitKind.CHARIOTS,),
    }
)
SPACE_WORKS = frozenset({StructureKind.ORBITAL_RING, StructureKind.SPACE_STATION, StructureKind.SPACE_ELEVATOR, StructureKind.SPACEPORT})
SKY_WORKS = frozenset({StructureKind.AIRFIELD})


@dataclass
class WorksTally:
    built: int = 0
    fuelled: int = 0
    laid_up: int = 0
    repaired: int = 0
    upkeep_unpaid: int = 0


async def builder_of(ctx: TickContext, community_id: int) -> EntityRow | None:
    realm_id = await realm_of_community(ctx.session, community_id)
    return await living_entity(ctx.session, realm_id) if realm_id is not None else await living_entity(ctx.session, community_id)


async def stocked(ctx: TickContext, owner: EntityRow, design: DesignRow) -> int:
    return sum(group.count for group in await groups_of(ctx.session, owner.id) if group.design_id == design.id)


async def buildable(ctx: TickContext, owner: EntityRow, design: DesignRow) -> bool:
    needed = set(await ctx.session.scalars(select(DesignTechniqueRow.technique).where(DesignTechniqueRow.design_id == design.id)))
    return not needed or needed <= await techniques_of(ctx.session, owner.id)


async def build(ctx: TickContext, town: EntityRow, owner: EntityRow, design: DesignRow, *, points: int, tally: WorksTally) -> int:
    table = ctx.rules.vehicles
    each = max(1, design.cost // max(1, table.cost_per_point))
    room = max(0, table.park_cap - await stocked(ctx, owner, design))
    count = min(room, points // each)
    if count <= 0 or not await buildable(ctx, owner, design):
        return points
    material = CommodityKind.TIMBER if design.tech_level <= 2 else CommodityKind.ORE
    need = max(1, design.structure // 10) * count
    taken = (
        int(await goods_of(ctx.session, ctx.epoch).take_units(town.id, material, need, GoodsFlow.INPUT)) if await holding(ctx.session, town.id, material) else 0
    )
    count = min(count, taken // max(1, design.structure // 10))
    if count <= 0 or not await take_coin(ctx.session, ctx.rules, owner, design.cost * count // max(1, table.coin_share)):
        return points
    await add_vehicles(ctx.session, owner.id, design, count, epoch=ctx.epoch, region_id=town.location_id)
    tally.built += count
    return points - count * each


async def yards(ctx: TickContext, knowledge: KnowledgeMap, tally: WorksTally) -> None:
    table = ctx.rules.vehicles
    for yard in list(await ctx.session.scalars(select(WorkshopRow).where(WorkshopRow.kind.in_(list(YARD_ROLES))).order_by(WorkshopRow.id))):
        town = await living_entity(ctx.session, yard.community_entity_id)
        owner = await builder_of(ctx, yard.community_entity_id) if town is not None else None
        if town is None or owner is None or held(town.id) or held(owner.id):
            continue
        points = yard.level * table.yard_points
        for role in YARD_ROLES[yard.kind]:
            design = await role_design(ctx, owner, role, knowledge)
            if design is not None:
                points = await build(ctx, town, owner, design, points=points, tally=tally)
        if yard.kind is W.SHIPYARD and points > 0:
            carrier = await carrier_design(ctx, owner, await trade_mode(ctx, town.id), knowledge)
            if carrier is not None:
                await build(ctx, town, owner, carrier, points=points, tally=tally)


async def trade_mode(ctx: TickContext, town_id: int) -> TradeMode:
    from_routes = await ctx.session.scalar(
        select(TradeRouteProfileRow.mode)
        .where(
            (TradeRouteProfileRow.first_market_id == town_id) | (TradeRouteProfileRow.second_market_id == town_id),
            TradeRouteProfileRow.status == TradeRouteStatus.OPEN,
        )
        .limit(1)
    )
    return from_routes if from_routes is not None else TradeMode.SEA


async def space_works(ctx: TickContext, knowledge: KnowledgeMap, tally: WorksTally) -> None:
    table = ctx.rules.vehicles
    works = await ctx.session.scalars(
        select(StructureProfileRow).where(StructureProfileRow.kind.in_(list(SPACE_WORKS | SKY_WORKS))).order_by(StructureProfileRow.structure_entity_id)
    )
    for work in list(works):
        if work.construction_state not in STANDING_STATES or work.host_entity_id is None:
            continue
        town = await living_entity(ctx.session, work.host_entity_id)
        owner = await builder_of(ctx, work.host_entity_id) if town is not None else None
        if town is None or owner is None or held(town.id) or held(owner.id):
            continue
        role = UnitKind.SKY_CREW if work.kind in SKY_WORKS else UnitKind.VOID_CREW
        design = await role_design(ctx, owner, role, knowledge)
        if design is not None:
            points = round_half_up(
                work.level
                * table.yard_points
                * work.effect_pct
                / PERCENT
                * (table.ring_points_pct if work.kind is StructureKind.ORBITAL_RING else PERCENT)
                / PERCENT
            )
            await build(ctx, town, owner, design, points=points, tally=tally)


async def keep_fleets(ctx: TickContext, tally: WorksTally) -> None:
    table = ctx.rules.vehicles
    for group in list(await ctx.session.scalars(select(VehicleGroupRow).where(VehicleGroupRow.count > 0).order_by(VehicleGroupRow.id))):
        holder = await ctx.session.get(EntityRow, group.holder_node_id)
        if holder is None or held(group.holder_node_id) or holder.status is not EntityStatus.CANON:
            continue
        army = await ctx.session.get(ArmyRow, holder.id)
        payer = await living_entity(ctx.session, army.owner_entity_id) if army is not None else holder
        if payer is None:
            continue
        if army is not None:
            tally.fuelled += 1
            if not await burn_fuel(ctx, group, payer.id):
                tally.laid_up += 1
            elif "status" not in (group.locked or []):
                group.status = VehicleStatus.MOVING
        design = await ctx.session.get(DesignRow, group.design_id)
        if design is not None and not await take_coin(ctx.session, ctx.rules, payer, design.upkeep * group.count // max(1, table.coin_share)):
            tally.upkeep_unpaid += 1
            if "condition" not in (group.locked or []):
                group.condition = max(0, group.condition - table.unpaid_decay)
        elif army is None:
            tally.repaired += await repair_group(ctx.session, group, table.park_repair, yard=False)


async def vehicle_works(ctx: TickContext) -> WorksTally:
    tally = WorksTally()
    knowledge = await KnowledgeMap.load(ctx.session)
    await yards(ctx, knowledge, tally)
    await space_works(ctx, knowledge, tally)
    await keep_fleets(ctx, tally)
    return tally
