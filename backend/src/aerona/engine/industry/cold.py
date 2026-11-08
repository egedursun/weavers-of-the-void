from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.folk import folk_of
from aerona.engine.primitives.naming import seed_of


async def frostbite(ctx: TickContext, community: EntityRow) -> int:
    table = ctx.rules.energy
    if table.frostbite_cap <= 0:
        return 0
    statement = (
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await folk_of(ctx.session, community),
        )
        .order_by(EntityRow.id)
    )
    bitten = 0
    for mortal in unheld(list(await ctx.session.scalars(statement))):
        if bitten >= table.frostbite_cap:
            break
        if not ctx.rng(seed_of("frostbite", mortal.id, ctx.epoch)).chance(table.frostbite_pct):
            continue
        harm = Harm(ctx.rules.injury.exposure_cold_hp, HarmCause.EXPOSURE, "died of the bitter cold", damage_type=DamageType.COLD)
        await apply_hits(ctx, mortal, harm, lethal=False)
        bitten += 1
    return bitten
