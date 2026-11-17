from sqlalchemy import select

from aerona.db.tables.economy import WorldMaterialRow
from aerona.domain.enums.economy import MaterialOrigin
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import PeopleStats, PlaceStats, RegionStats
from aerona.engine.context import TickContext
from aerona.engine.economy.deposits import new_substance
from aerona.services.integrity.money_links import stray_sources
from tests.engine.cosmos.factories import Cosmos, make_entity


async def test_remains_of_a_dead_god_name_their_source_and_pass_the_integrity_check(ctx: TickContext, cosmos: Cosmos) -> None:
    place = await make_entity(ctx.session, "Vale", EntityType.REGION, RegionStats(), world_id=cosmos.home.id)
    corpse = await make_entity(ctx.session, "Remains", EntityType.PLACE, PlaceStats(), world_id=cosmos.home.id, location_id=place.id)
    row = await new_substance(ctx, MaterialOrigin.DEAD_GOD, corpse, source_node_id=corpse.id)
    assert row.source_node_id == corpse.id
    assert await stray_sources(ctx.session) == []


async def test_every_substance_the_engine_makes_keeps_a_source_the_integrity_check_accepts(ctx: TickContext, cosmos: Cosmos) -> None:
    town = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    for origin, source in ((MaterialOrigin.RESEARCH, town.id), (MaterialOrigin.STAR, cosmos.star.id), (MaterialOrigin.RIFT, town.id)):
        await new_substance(ctx, origin, town, source_node_id=source)
    rows = list(await ctx.session.scalars(select(WorldMaterialRow)))
    assert rows and all(row.source_node_id is not None for row in rows)
    assert await stray_sources(ctx.session) == []
