from sqlalchemy import select

from aerona.catalog.diets import DIETS
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind
from aerona.engine.context import TickContext
from aerona.engine.mind.hooks import committed
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of


async def feed_on_hosts(ctx: TickContext, peoples: list[EntityRow]) -> int:
    fed = 0
    for people in peoples:
        biology = await ctx.session.get(PeopleBiologyRow, people.id)
        if biology is None or not DIETS[biology.diet].feeds_on_hosts:
            continue
        feeders = list(
            await ctx.session.scalars(
                select(EntityRow)
                .where(await present_among(ctx.session, [people.id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
        )
        own = {feeder.id for feeder in feeders}
        for feeder in feeders:
            if held(feeder.id) or feeder.location_id is None:
                continue
            hosts = [
                host
                for host in await ctx.session.scalars(
                    select(EntityRow.id)
                    .where(
                        await present_among(ctx.session, [feeder.location_id]),
                        EntityRow.entity_type == EntityType.MORTAL,
                        EntityRow.status == EntityStatus.CANON,
                    )
                    .order_by(EntityRow.id)
                )
                if host not in own
            ]
            if not hosts:
                continue
            host = ctx.rng(seed_of("host", feeder.id, ctx.epoch)).pick(hosts)
            await committed(ctx, feeder.id, ActKind.FEEDING_ON_HOSTS, host)
            fed += 1
    return fed
