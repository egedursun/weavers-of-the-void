from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.mind import Facet
from aerona.engine.mind.split import NEUTRAL_FACET, facets_of, temper_facets, write_facets
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, mortal, tuned_rules


async def test_a_mind_stored_before_a_facet_existed_reads_it_as_neutral_and_tempers_without_failing(session: AsyncSession, world: CoreWorld) -> None:
    hero = await mortal(session, "Old Soul", world, world.regions[0].id)
    known = [facet for facet in Facet if facet is not Facet.PERSEVERANCE]
    await write_facets(session, hero.id, {facet: 10 for facet in known})
    await session.flush()
    facets = await facets_of(session, hero.id)
    assert set(facets) == set(Facet) and facets[Facet.PERSEVERANCE] == NEUTRAL_FACET
    ctx = await manual_context(session, "facets", rules=tuned_rules())
    assert isinstance(await temper_facets(session, ctx.rules, hero, 2), list)
