from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.carriers import CARRIERS
from aerona.catalog.operations import TRANSPORTS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.operations import ArmyOperationRow, DepotRow, SupplyFlowRow, TheatreRow, TransportAssetRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, TradeMode
from aerona.domain.enums.environment import RiverClass, TerrainKind
from aerona.domain.enums.military import RESTING, CommandArea, Stance
from aerona.domain.enums.operations import CarrierKind, EchelonOrder
from aerona.engine.agrarian.rings import eased_regions
from aerona.engine.body.variants import fear_of
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.lore.research import has_technique
from aerona.engine.military.command import command_areas
from aerona.engine.military.logistics import March
from aerona.engine.military.units import stacks_of
from aerona.engine.notes import note
from aerona.engine.operations.fields import keep
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.services.war import ongoing_wars

FOODS = (CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.FISH, CommodityKind.LIVESTOCK)
FORESIGHT_STEP = 25
FAR = 1_000_000


@dataclass
class SupplyTally:
    depots: int = 0
    trains: int = 0
    cut: int = 0
    produced: int = 0
    delivered: int = 0
    lost: int = 0
    culminated: int = 0
    collapsed: int = 0
    paused: int = 0
    abandoned: int = 0
    interdicted: int = 0


@dataclass(frozen=True)
class Network:
    atlas: RegionAtlas
    lands: dict[int, RegionEnvironmentRow]
    roads: set[int]


async def network(ctx: TickContext) -> Network:
    atlas = await RegionAtlas.load(ctx.session)
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    roads, canals = await eased_regions(ctx, atlas)
    return Network(atlas, lands, roads | canals)


async def depots_of(ctx: TickContext, owner_id: int) -> list[DepotRow]:
    return list(await ctx.session.scalars(select(DepotRow).where(DepotRow.owner_entity_id == owner_id).order_by(DepotRow.id)))


async def train_of(ctx: TickContext, owner_id: int) -> list[TransportAssetRow]:
    return list(await ctx.session.scalars(select(TransportAssetRow).where(TransportAssetRow.owner_entity_id == owner_id).order_by(TransportAssetRow.id)))


async def soldiers_of(ctx: TickContext, owner_id: int) -> int:
    total = 0
    for army_id in await ctx.session.scalars(select(ArmyRow.entity_id).where(ArmyRow.owner_entity_id == owner_id, ArmyRow.disbanded_epoch.is_(None))):
        army = await ctx.session.get(EntityRow, army_id)
        total += stat_or(army, "size", 0) if army is not None else 0
    return total


async def carriers_known(ctx: TickContext, owner_id: int) -> list[CarrierKind]:
    found: list[CarrierKind] = []
    for kind, spec in CARRIERS.items():
        if spec.capacity > 0 and (spec.technique is None or await has_technique(ctx.session, owner_id, spec.technique)):
            found.append(kind)
    return found


async def raise_train(ctx: TickContext, owner: EntityRow, tally: SupplyTally) -> None:
    if held(owner.id) or await train_of(ctx, owner.id):
        return
    wagons = max(1, await soldiers_of(ctx, owner.id) * ctx.rules.supply_network.assets_per_thousand // 1000)
    known = [kind for kind in await carriers_known(ctx, owner.id) if TradeMode.ROAD in CARRIERS[kind].modes]
    best = sorted(known, key=lambda kind: (-CARRIERS[kind].capacity, kind.value))[:2] or [CarrierKind.PACK_ANIMALS]
    for kind, count in zip(best, (wagons, max(1, wagons // 2)), strict=False):
        ctx.session.add(TransportAssetRow(owner_entity_id=owner.id, kind=kind, count=count, capacity=TRANSPORTS[kind].capacity, locked=[]))
    tally.trains += 1


async def home_region(ctx: TickContext, owner: EntityRow, web: Network) -> int | None:
    own = web.atlas.top_region(owner.id)
    if own is not None:
        return own
    return next((region for place in sorted(await homes_of(ctx.session, owner)) if (region := web.atlas.top_region(place)) is not None), None)


async def home_depot(ctx: TickContext, owner: EntityRow, web: Network, tally: SupplyTally) -> DepotRow | None:
    home = await home_region(ctx, owner, web)
    rows = await depots_of(ctx, owner.id)
    found = next((row for row in rows if not row.field), None)
    if found is not None or home is None or held(owner.id):
        return found
    row = DepotRow(owner_entity_id=owner.id, region_entity_id=home, capacity=ctx.rules.supply_network.depot_capacity, founded_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    tally.depots += 1
    return row


async def keep_network(ctx: TickContext, tally: SupplyTally) -> None:
    web = await network(ctx)
    wars = await ongoing_wars(ctx.session)
    fighting = {side for item in wars for side in item.sides}
    enemy_regions: dict[int, set[int]] = {}
    for item in wars:
        for side, other in ((item.attacker_id, item.defender_id), (item.defender_id, item.attacker_id)):
            enemy_regions.setdefault(side, set()).update(await army_regions(ctx, other))
    for owner_id in sorted(fighting):
        owner = await ctx.session.get(EntityRow, owner_id)
        if owner is None:
            continue
        await raise_train(ctx, owner, tally)
        await home_depot(ctx, owner, web, tally)
    for depot in await ctx.session.scalars(select(DepotRow).order_by(DepotRow.id)):
        cut = depot.region_entity_id in enemy_regions.get(depot.owner_entity_id, set())
        if cut and not depot.cut:
            tally.cut += 1
        keep(depot, "cut", cut)
    for asset in await ctx.session.scalars(select(TransportAssetRow).where(TransportAssetRow.owner_entity_id.not_in(fighting or {0}))):
        keep(asset, "condition", clamp_int(asset.condition + ctx.rules.supply_network.asset_repair, 0, PERCENT))
    for depot in list(await ctx.session.scalars(select(DepotRow).where(DepotRow.field.is_(True), DepotRow.owner_entity_id.not_in(fighting or {0})))):
        if depot.locked or held(depot.owner_entity_id):
            continue
        await ctx.session.delete(depot)
        tally.abandoned += 1


async def army_regions(ctx: TickContext, owner_id: int) -> set[int]:
    rows = await ctx.session.scalars(
        select(ArmyProfileRow.region_entity_id)
        .join(ArmyRow, ArmyRow.entity_id == ArmyProfileRow.army_entity_id)
        .where(ArmyRow.owner_entity_id == owner_id, ArmyRow.disbanded_epoch.is_(None), ArmyProfileRow.region_entity_id.is_not(None))
    )
    return {region for region in rows if region is not None}


def distance(web: Network, first: int | None, second: int | None) -> int:
    hops = web.atlas.region_hops(first, second)
    return FAR if hops is None else hops


def need_of(ctx: TickContext, march: March) -> int:
    table = ctx.rules.supply_network
    size = stat_or(march.army, "size", 0)
    base = size * table.need_per_hundred // PERCENT
    if march.profile.stance in RESTING:
        return round_half_up(base * table.rest_need_pct / PERCENT)
    if march.attacking and march.profile.stance is not Stance.RETREAT:
        return round_half_up(base * table.attack_need_pct / PERCENT)
    return base


async def feeding_depot(ctx: TickContext, march: March, web: Network, tally: SupplyTally) -> DepotRow | None:
    region = march.profile.region_entity_id
    rows = [row for row in await depots_of(ctx, march.owner.id) if row.region_entity_id is not None]
    if not rows or region is None:
        return rows[0] if rows else None
    near = min(rows, key=lambda row: (distance(web, row.region_entity_id, region), row.id))
    hops = web.atlas.region_hops(near.region_entity_id, region) or 0
    line = march.profile.supply_line or []
    if hops <= ctx.rules.supply_network.field_hops or len(line) < 2 or held(march.owner.id):
        return near
    spot = line[-2]
    field = DepotRow(
        owner_entity_id=march.owner.id,
        region_entity_id=spot,
        capacity=ctx.rules.supply_network.field_capacity,
        field=True,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(field)
    await ctx.session.flush()
    tally.depots += 1
    await note(
        ctx,
        f"{march.army.name} founded a field depot to feed its advance.",
        key="logistics.field_depot",
        ids=[march.army.id, spot],
    )
    return field


async def draw(ctx: TickContext, owner: EntityRow, room: int) -> int:
    if room <= 0 or held(owner.id):
        return 0
    sources = sorted(await homes_of(ctx.session, owner))
    ledger = goods_of(ctx.session, ctx.epoch)
    share = ctx.rules.supply_network.draw_pct
    drawn = 0
    for source in sources:
        if held(source):
            continue
        for commodity in FOODS:
            if drawn >= room:
                return drawn
            stocked = sum(row.quantity for row in await lots_of(ctx.session, source, commodity))
            want = min(room - drawn, stocked * share // PERCENT)
            drawn += await ledger.take_units(source, commodity, want, GoodsFlow.WAR) if want > 0 else 0
    return drawn


async def throughput(ctx: TickContext, march: March, depot: DepotRow, web: Network) -> int:
    if depot.cut:
        return 0
    table = ctx.rules.supply_network
    path = web.atlas.region_path(depot.region_entity_id, march.profile.region_entity_id) or []
    river = bool(path) and all(web.lands.get(region) is not None and web.lands[region].river_class is not RiverClass.NONE for region in path)
    coast = any(web.lands.get(region) is not None and web.lands[region].dominant_terrain is TerrainKind.COAST for region in path[-1:])
    road = bool(path) and all(region in web.roads for region in path)
    carried = 0
    for asset in await train_of(ctx, march.owner.id):
        spec = TRANSPORTS[asset.kind]
        if (spec.river_only and not river) or (spec.sea_only and not coast):
            continue
        lift = asset.count * asset.capacity * asset.condition // PERCENT
        if spec.river_only:
            lift = lift * table.river_throughput_pct // PERCENT
        elif road and not spec.sea_only:
            lift = lift * table.road_throughput_pct // PERCENT
        carried += lift
    if await interdicted(ctx, march, path):
        carried = carried * table.interdicted_pct // PERCENT
    theatres = list(await ctx.session.scalars(select(TheatreRow).where(TheatreRow.owner_entity_id == march.owner.id)))
    if len(theatres) > 1:
        army_row = await ctx.session.get(ArmyRow, march.army.id)
        mine = next((row for row in theatres if army_row is not None and row.war_id == army_row.war_id), None)
        share = mine.priority if mine is not None else PERCENT // len(theatres)
        carried = carried * max(share, 1) * len(theatres) // PERCENT
    return carried


async def interdicted(ctx: TickContext, march: March, path: list[int]) -> bool:
    inner = set(path[:-1])
    if not inner:
        return False
    for item in await ongoing_wars(ctx.session, march.owner.id):
        enemy = item.foe_id
        if inner & await army_regions(ctx, enemy):
            return True
    return False


async def wear(ctx: TickContext, owner_id: int) -> None:
    for asset in await train_of(ctx, owner_id):
        keep(asset, "condition", clamp_int(asset.condition - ctx.rules.supply_network.asset_wear, 0, PERCENT))


async def operation_of(ctx: TickContext, army_id: int) -> ArmyOperationRow:
    row = await ctx.session.get(ArmyOperationRow, army_id)
    if row is None:
        row = ArmyOperationRow(army_entity_id=army_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def supply_season(
    ctx: TickContext, march: March, season: int, *, raided: bool, order: EchelonOrder, web: Network, tally: SupplyTally
) -> SupplyFlowRow | None:
    if held(march.army.id) or march.profile.region_entity_id is None:
        return None
    if march.profile.region_entity_id == await home_region(ctx, march.owner, web):
        return None
    depot = await feeding_depot(ctx, march, web, tally)
    need = need_of(ctx, march)
    if depot is None or need <= 0:
        return None
    table = ctx.rules.supply_network
    home = next((row for row in await depots_of(ctx, march.owner.id) if not row.field), depot)
    produced = await draw(ctx, march.owner, depot.capacity - depot.supplies)
    upstream = (web.atlas.region_hops(home.region_entity_id, depot.region_entity_id) or 0) if depot.field else 0
    lost_up = min(produced, produced * table.hop_loss_pct * upstream // PERCENT)
    keep(depot, "supplies", depot.supplies + produced - lost_up)
    carried = await throughput(ctx, march, depot, web)
    path = web.atlas.region_path(depot.region_entity_id, march.profile.region_entity_id) or []
    if not depot.cut and await interdicted(ctx, march, path):
        tally.interdicted += 1
    if order is EchelonOrder.RESUPPLY:
        carried = carried * table.resupply_pct // PERCENT
    shipped = min(depot.supplies, carried, need)
    keep(depot, "supplies", depot.supplies - shipped)
    hops = web.atlas.region_hops(depot.region_entity_id, march.profile.region_entity_id) or 0
    loss_pct = min(PERCENT, table.hop_loss_pct * hops + (table.raided_loss_pct if raided else 0))
    lost = shipped * loss_pct // PERCENT
    delivered = shipped - lost
    if "supply_days" not in march.profile.locked:
        gain = round_half_up(ctx.rules.logistics.season_days * delivered / need)
        march.profile.supply_days = min(ctx.rules.logistics.supply_days, march.profile.supply_days + gain)
    await wear(ctx, march.owner.id)
    flow = SupplyFlowRow(
        epoch=ctx.epoch,
        season=season,
        owner_entity_id=march.owner.id,
        army_entity_id=march.army.id,
        depot_id=depot.id,
        produced=produced,
        shipped=shipped,
        lost=lost_up + lost,
        delivered=delivered,
        need=need,
        throughput=carried,
        locked=[],
    )
    ctx.session.add(flow)
    tally.produced += produced
    tally.delivered += delivered
    tally.lost += lost_up + lost
    return flow


async def culminate(ctx: TickContext, march: March, flow: SupplyFlowRow | None, tally: SupplyTally) -> ArmyOperationRow:
    table = ctx.rules.culmination
    row = await operation_of(ctx, march.army.id)
    if held(march.army.id):
        return row
    stacks = [stack for stack in await stacks_of(ctx.session, march.army.id) if stack.count > 0]
    organisation = sum(stack.organisation * stack.count for stack in stacks) // max(1, sum(stack.count for stack in stacks)) if stacks else PERCENT
    army_row = await ctx.session.get(ArmyRow, march.army.id)
    areas = await command_areas(ctx.session, army_row.commander_entity_id if army_row is not None else None)
    keep(row, "organisation", clamp_int(organisation, 0, PERCENT))
    keep(row, "foresight", foresight_of(areas))
    if flow is not None:
        keep(row, "need", flow.need)
        keep(row, "delivered", flow.delivered)
    attacking = march.attacking and march.profile.stance not in RESTING and march.profile.stance is not Stance.RETREAT
    if attacking:
        keep(row, "offensive_seasons", row.offensive_seasons + 1)
    row.updated_epoch = ctx.epoch
    if row.pause_seasons > 0:
        keep(row, "pause_seasons", row.pause_seasons - 1)
        hold(march)
        return row
    short = row.need > 0 and row.delivered * PERCENT < row.need * table.supply_pct
    if not (attacking and short and row.organisation < table.organisation):
        keep(row, "culminated", False)
        return row
    keep(row, "culminated", True)
    row.culminated_epoch = ctx.epoch
    tally.culminated += 1
    if areas.get(CommandArea.LOGISTICS, 0) >= table.foresight_area:
        keep(row, "pause_seasons", table.pause_seasons)
        hold(march)
        tally.paused += 1
        await note(
            ctx,
            f"{march.army.name} outran its supply and paused its offensive before it broke.",
            key="logistics.culminated",
            ids=[march.army.id, march.owner.id],
        )
        return row
    if ctx.rng(f"culmination.{march.army.id}.{ctx.epoch}.{row.offensive_seasons}").chance(table.collapse_chance):
        if "cohesion" not in march.profile.locked:
            march.profile.cohesion = clamp_int(march.profile.cohesion - table.collapse_cohesion, 0, PERCENT)
        fear = await fear_of(ctx.session, march.army)
        for stack in stacks:
            if "morale" not in stack.locked:
                stack.morale = clamp_int(stack.morale - round_half_up(table.collapse_morale * fear), 0, PERCENT)
        tally.collapsed += 1
        await note(
            ctx,
            f"{march.army.name} pressed on past the end of its supply, and its offensive collapsed.",
            key="logistics.collapsed",
            ids=[march.army.id, march.owner.id],
        )
    return row


def foresight_of(areas: dict[CommandArea, int]) -> int:
    return areas.get(CommandArea.LOGISTICS, 0) // FORESIGHT_STEP


def hold(march: March) -> None:
    if "stance" not in march.profile.locked and march.profile.stance not in RESTING:
        march.profile.stance = Stance.ENTRENCH
