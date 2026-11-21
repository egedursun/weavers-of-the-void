from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interworld import InterworldCampaignRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.interworld import OPEN_CAMPAIGN, CampaignStage
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.landing import landing_region
from aerona.engine.interworld.book import InterworldTally, carriers_of, orbit_of, route_between, route_open
from aerona.engine.interworld.orbit import contest
from aerona.engine.military.units import resize
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.services.war import current_war, declare_war

GATE_SHARE = 10


async def launch(
    ctx: TickContext, attacker: EntityRow, army: EntityRow, target_world: int, route: RouteRow, *, tally: InterworldTally, defender: int | None = None
) -> InterworldCampaignRow:
    per = ctx.rules.interworld.carrier_people_per_capacity
    carriers = await carriers_of(ctx.session, attacker.id)
    capacity = carriers * per + route.capacity * per // GATE_SHARE
    carried = min(stat(army, "size") or 0, capacity)
    await resize(ctx.session, ctx.rules, army, carried)
    row = InterworldCampaignRow(
        attacker_entity_id=attacker.id,
        defender_entity_id=defender,
        from_world_id=army.world_id or attacker.world_id or target_world,
        target_world_id=target_world,
        route_id=route.id,
        army_entity_id=army.id,
        stage=CampaignStage.TRANSIT,
        carriers=carriers,
        capacity=capacity,
        forces=carried,
        transit_left=max(1, route.duration_epochs),
        supply_hops=max(1, route.duration_epochs),
        begun_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.launched += 1
    await record(
        ctx,
        "war.campaign_launched",
        roles={IncidentRole.ACTOR: attacker.id, IncidentRole.TARGET: defender},
        facts={"forces": carried, "carriers": carriers, "transit": row.transit_left},
        world_id=target_world,
    )
    return row


async def withdraw(ctx: TickContext, row: InterworldCampaignRow, army: EntityRow | None, tally: InterworldTally) -> None:
    row.stage, row.ended_epoch = CampaignStage.WITHDRAWN, ctx.epoch
    if army is not None:
        army_row = await ctx.session.get(ArmyRow, army.id)
        if army_row is not None and army_row.disbanded_epoch is None:
            army_row.disbanded_epoch = ctx.epoch
    tally.withdrawn += 1
    await record(
        ctx, "war.campaign_withdrawn", roles={IncidentRole.SUBJECT: row.attacker_entity_id}, facts={"forces": row.forces}, world_id=row.target_world_id
    )


async def cross(ctx: TickContext, row: InterworldCampaignRow, army: EntityRow, tally: InterworldTally) -> None:
    route = await ctx.session.get(RouteRow, row.route_id) if row.route_id is not None else None
    if route is None or not await route_open(ctx, route):
        return
    lost = round_half_up(row.forces * ctx.rules.interworld.transit_loss_pct / PERCENT)
    if lost and "forces" not in (row.locked or []):
        row.forces -= lost
        await resize(ctx.session, ctx.rules, army, row.forces)
        tally.lost_in_transit += lost
        await record(ctx, "war.transit_lost", roles={IncidentRole.SUBJECT: row.attacker_entity_id}, facts={"lost": lost}, world_id=row.target_world_id)
    row.transit_left = max(0, row.transit_left - 1)
    if not row.forces:
        await withdraw(ctx, row, army, tally)
    elif not row.transit_left:
        row.stage = CampaignStage.SUPREMACY


async def land(ctx: TickContext, row: InterworldCampaignRow, army: EntityRow, tally: InterworldTally) -> bool:
    orbit = await orbit_of(ctx.session, row.target_world_id)
    if orbit is None or orbit.holder_entity_id != row.attacker_entity_id or orbit.strength < ctx.rules.interworld.landing_needs_control_pct:
        return False
    region = await landing_region(ctx.session, ctx.rules, row.target_world_id)
    if region is None:
        return False
    army.world_id, army.location_id = row.target_world_id, region.id
    profile = await ctx.session.get(ArmyProfileRow, army.id)
    if profile is not None:
        profile.region_entity_id = region.id
    if row.defender_entity_id is not None and await current_war(ctx.session, row.attacker_entity_id, row.defender_entity_id) is None:
        await declare_war(ctx, row.attacker_entity_id, row.defender_entity_id, "a host crossed between worlds to make war", world_cap=False, brokered=True)
    row.stage = CampaignStage.HOLDING
    tally.landings += 1
    await record(
        ctx,
        "war.landing",
        roles={IncidentRole.ACTOR: row.attacker_entity_id, IncidentRole.PLACE: region.id, IncidentRole.TARGET: row.defender_entity_id},
        facts={"forces": row.forces},
        place=region.id,
    )
    return True


async def supply(ctx: TickContext, row: InterworldCampaignRow, army: EntityRow, tally: InterworldTally) -> None:
    table = ctx.rules.interworld
    orbit = await orbit_of(ctx.session, row.target_world_id)
    if "supply" not in (row.locked or []):
        if orbit is not None and orbit.holder_entity_id == row.attacker_entity_id:
            row.supply = max(row.supply, table.orbit_hold_supply)
        else:
            row.supply = clamp_int(row.supply - table.supply_decay_per_hop * row.supply_hops, 0, PERCENT)
    if row.supply < table.starving_supply:
        size = stat(army, "size") or 0
        left = round_half_up(size * row.supply / max(1, table.starving_supply))
        await resize(ctx.session, ctx.rules, army, left)
        row.forces = left
    if not row.forces or not row.supply:
        await withdraw(ctx, row, army, tally)


async def war_over(ctx: TickContext, row: InterworldCampaignRow) -> bool:
    if row.defender_entity_id is None:
        return False
    sides = select(WarSideRow.war_id).where(WarSideRow.entity_id == row.attacker_entity_id)
    query = select(WarRow.id).where(WarRow.id.in_(sides), WarRow.status.in_([WarStatus.ONGOING, WarStatus.MOBILIZING]))
    return await ctx.session.scalar(query.limit(1)) is None and await current_war(ctx.session, row.attacker_entity_id, row.defender_entity_id) is None


async def tend_campaign(ctx: TickContext, row: InterworldCampaignRow, tally: InterworldTally) -> None:
    army = await living_entity(ctx.session, row.army_entity_id) if row.army_entity_id is not None else None
    if army is None or (stat(army, "size") or 0) <= 0:
        await withdraw(ctx, row, army, tally)
        return
    if row.stage is CampaignStage.GATHERING:
        row.stage = CampaignStage.TRANSIT
    elif row.stage is CampaignStage.TRANSIT:
        await cross(ctx, row, army, tally)
    elif row.stage is CampaignStage.SUPREMACY:
        if await contest(ctx, row.target_world_id, row.attacker_entity_id, army, tally):
            row.stage = CampaignStage.LANDING
    elif row.stage is CampaignStage.LANDING:
        await land(ctx, row, army, tally)
    elif row.stage is CampaignStage.HOLDING:
        await supply(ctx, row, army, tally)
        if row.stage is CampaignStage.HOLDING and await war_over(ctx, row):
            row.ended_epoch = ctx.epoch


async def campaigns_to_send(ctx: TickContext, tally: InterworldTally) -> None:
    query = (
        select(WarSideRow)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarRow.status == WarStatus.ONGOING)
        .order_by(WarSideRow.war_id, WarSideRow.entity_id)
    )
    sides = list(await ctx.session.scalars(query))
    for side in sides:
        attacker = await living_entity(ctx.session, side.entity_id)
        if attacker is None or held(attacker.id) or await ctx.session.get(PolityProfileRow, attacker.id) is None:
            continue
        for foe in sides:
            enemy = await living_entity(ctx.session, foe.entity_id) if foe.war_id == side.war_id and foe.side is not side.side else None
            if enemy is None or enemy.world_id is None or enemy.world_id == attacker.world_id or attacker.world_id is None:
                continue
            route = await route_between(ctx, attacker.world_id, enemy.world_id)
            army = await idle_army(ctx, attacker)
            if route is None or army is None or not ctx.rng(f"campaign.{attacker.id}.{enemy.id}.{ctx.epoch}").chance(ctx.rules.interworld.campaign_chance_pct):
                continue
            await launch(ctx, attacker, army, enemy.world_id, route, tally=tally, defender=enemy.id)
            break


async def idle_army(ctx: TickContext, owner: EntityRow) -> EntityRow | None:
    busy = select(InterworldCampaignRow.army_entity_id).where(
        InterworldCampaignRow.stage.in_(sorted(OPEN_CAMPAIGN)), InterworldCampaignRow.army_entity_id.is_not(None)
    )
    query = select(ArmyRow.entity_id).where(ArmyRow.owner_entity_id == owner.id, ArmyRow.disbanded_epoch.is_(None), ArmyRow.entity_id.not_in(busy))
    for army_id in await ctx.session.scalars(query.order_by(ArmyRow.entity_id)):
        army = await living_entity(ctx.session, army_id)
        if army is not None and army.world_id == owner.world_id and not held(army.id):
            return army
    return None


async def tend_campaigns(ctx: TickContext, tally: InterworldTally) -> None:
    query = select(InterworldCampaignRow).where(InterworldCampaignRow.stage.in_(sorted(OPEN_CAMPAIGN)), InterworldCampaignRow.ended_epoch.is_(None))
    for row in list(await ctx.session.scalars(query.order_by(InterworldCampaignRow.id))):
        if held(row.attacker_entity_id) or "stage" in (row.locked or []):
            continue
        await tend_campaign(ctx, row, tally)
    await campaigns_to_send(ctx, tally)
