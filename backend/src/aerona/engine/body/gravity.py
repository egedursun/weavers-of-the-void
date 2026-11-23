from sqlalchemy import select

from aerona.catalog.gravity import GRAVITY
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.lifeforms import bears_gravity
from aerona.engine.primitives.stats import shift_stat

TEN = 10


async def bear_gravity(ctx: TickContext) -> int:
    table = ctx.rules.physics
    strained = 0
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        strain = GRAVITY[world.gravity].strain(ctx.rules)
        physics = await ctx.session.get(WorldPhysicsRow, world.id)
        loss = strain * table.strain_endurance // TEN
        if loss <= 0 or physics is None or held(world.id):
            continue
        mortals = await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
        for mortal in list(mortals):
            folk = await people_id_of(ctx.session, mortal)
            biology = await ctx.session.get(PeopleBiologyRow, folk) if folk is not None else None
            if held(mortal.id) or (biology is not None and bears_gravity(biology, physics)):
                continue
            shift_stat(mortal, "hp", -loss, low=1)
            strained += 1
    return strained
