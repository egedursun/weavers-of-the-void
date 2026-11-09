from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.world import Atmosphere, Discovery, WorldType
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.queries import canon


async def scorch_world(ctx: TickContext, world: WorldRow, cause: str, *, lost: bool = False) -> bool:
    if held(world.id):
        return False
    for region in await canon(ctx.session, [EntityType.REGION], world.id):
        if not held(region.id):
            await apply_disaster(ctx, region, Disaster.ERUPTION, 1.0)
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
    await note(ctx, f"{cause} {world.name}; its seas and air were burned away.", key="world.scorched", world_id=world.id, kind=ChronicleKind.APOCALYPSE)
    return True
