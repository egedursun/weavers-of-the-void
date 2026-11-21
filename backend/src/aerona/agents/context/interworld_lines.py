from sqlalchemy import or_, select

from aerona.agents.context.arsenal_lines import led_by
from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interworld import InterworldCampaignRow, InterworldMigrationRow, OrbitalControlRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.interworld import OPEN_CAMPAIGN


async def world_name(scope: Scope, world_id: int) -> str:
    world = await scope.session.get(WorldRow, world_id)
    return world.name if world is not None else "another world"


async def campaign_line(scope: Scope, campaign: InterworldCampaignRow) -> str:
    target = await world_name(scope, campaign.target_world_id)
    state = f"{spoken(campaign.stage)}, {campaign.forces} soldiers, supply {campaign.supply}"
    return f"campaign {campaign.id} of {await named(scope, campaign.attacker_entity_id)} on {target}: {state}"


async def mortal_interworld_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    mine = await led_by(scope, me)
    found: list[str] = []
    if mine:
        sides = or_(InterworldCampaignRow.attacker_entity_id.in_(sorted(mine)), InterworldCampaignRow.defender_entity_id.in_(sorted(mine)))
        under_way = (InterworldCampaignRow.stage.in_(sorted(OPEN_CAMPAIGN)), InterworldCampaignRow.ended_epoch.is_(None))
        for campaign in await session.scalars(select(InterworldCampaignRow).where(sides, *under_way).order_by(InterworldCampaignRow.id)):
            found.append(await campaign_line(scope, campaign))
        for route in await session.scalars(select(RouteRow).where(RouteRow.active.is_(True)).order_by(RouteRow.id)):
            if me.world_id in (route.world_a_id, route.world_b_id):
                found.append(f"way {route.id} between {await world_name(scope, route.world_a_id)} and {await world_name(scope, route.world_b_id)}")
    if me.world_id is not None:
        orbit = await session.scalar(select(OrbitalControlRow).where(OrbitalControlRow.world_id == me.world_id).limit(1))
        if orbit is not None:
            found.append(f"the space around your world is held by {await named(scope, orbit.holder_entity_id)} at strength {orbit.strength}")
    if me.location_id is not None:
        leaving = (InterworldMigrationRow.community_entity_id == me.location_id, InterworldMigrationRow.ended_epoch.is_(None))
        for movement in await session.scalars(select(InterworldMigrationRow).where(*leaving).order_by(InterworldMigrationRow.id)):
            gone = f"{movement.moved} gone, met with {spoken(movement.reception)}"
            found.append(f"your people leave for {await world_name(scope, movement.to_world_id)} for {spoken(movement.cause)}, {gone}")
    return found
