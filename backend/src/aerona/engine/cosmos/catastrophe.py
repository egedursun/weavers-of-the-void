from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus
from aerona.domain.enums.world import Atmosphere, Discovery, WorldType
from aerona.engine.context import TickContext
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.queries import canon
from aerona.engine.recording.record import StepDraft, record


async def scorch_world(ctx: TickContext, world: WorldRow, cause_id: int, *, lost: bool = False) -> bool:
    if held(world.id):
        return False
    burned = 0
    for region in await canon(ctx.session, [EntityType.REGION], world.id):
        if not held(region.id):
            await apply_disaster(ctx, region, Disaster.ERUPTION, 1.0)
            burned += 1
    if "biosphere_health" not in world.locked:
        world.biosphere_health = 0
    if "world_type" not in world.locked:
        world.world_type = WorldType.CHTHONIAN
    if "atmosphere" not in world.locked:
        world.atmosphere = Atmosphere.NONE
    if lost and "discovery" not in world.locked:
        world.discovery = Discovery.FORGOTTEN
    physics = await ctx.session.get(WorldPhysicsRow, world.id)
    if physics is not None:
        for key, value in (("pressure", 0.0), ("hydrosphere", 0), ("cryosphere", 0), ("oxygen", 0), ("water_vapour", 0)):
            if key not in physics.locked:
                setattr(physics, key, value)
    await record(
        ctx,
        "world.scorched",
        roles={IncidentRole.SUBJECT: world.id, IncidentRole.ACTOR: cause_id},
        facts={"regions": burned},
        steps=(StepDraft(StepAction.BURN_LAND, actor=cause_id, locus_kind=StepLocus.REALM, locus_node=world.id, amount=burned, unit=FactUnit.COUNT),),
        world_id=world.id,
    )
    return True
