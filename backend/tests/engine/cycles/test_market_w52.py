from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.market_kinds import JUDGES, ROLES
from aerona.db.tables.arts import ArtPriceRow, CollectorRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.museums import MuseumCollectionRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.arts import ArtMarketRole
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.museum import HoardKind
from aerona.domain.models.entity_stats import ArtworkStats
from aerona.engine.arts.control import review_work
from aerona.engine.arts.market import appraise
from aerona.engine.arts.market_roles import backfill_curators, show_collections
from tests.engine.core.factories import CoreWorld, entity, mortal
from tests.engine.core.test_cycles_w21 import context, town_of


def test_seven_roles_with_judges_and_a_forger_that_keeps_nothing() -> None:
    assert set(ROLES) == set(ArtMarketRole)
    assert {ArtMarketRole.CONNOISSEUR, ArtMarketRole.CURATOR, ArtMarketRole.CRITIC} == JUDGES
    assert ROLES[ArtMarketRole.FORGER].fakes and not ROLES[ArtMarketRole.FORGER].keeps


async def test_a_critic_moves_a_works_price_by_renown(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    critic = await mortal(session, "Critic", world, town.id)
    maker = await mortal(session, "Maker", world, town.id)
    session.add(MortalProfileRow(entity_id=critic.id, renown=90, locked=[]))
    work = await entity(session, "The Stair", EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id, location_id=town.id)
    session.add(ArtworkProfileRow(artwork_entity_id=work.id, medium=ArtMode.FLAT_IMAGE, author_entity_id=maker.id, quality=95, locked=[]))
    await session.flush()
    ctx = await context(session)
    profile = await session.get(ArtworkProfileRow, work.id)
    assert profile is not None
    before = (await appraise(ctx, work, profile)).price
    swing = await review_work(ctx, work.id, critic.id)
    price = await session.get(ArtPriceRow, work.id)
    assert price is not None and price.acclaim == swing and swing != 0
    after = (await appraise(ctx, work, profile)).price
    assert (after > before) == (swing > 0)
    role = await session.get(CollectorRow, critic.id)
    assert role is not None and role.role is ArtMarketRole.CRITIC
    assert "art.reviewed" in set(await session.scalars(select(IncidentRow.kind)))


async def test_museum_keepers_become_curators_and_raise_their_towns_prestige(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    session.add(CollectorRow(holder_entity_id=town.id, role=ArtMarketRole.COLLECTOR, connoisseurship=40, locked=[]))
    session.add(MuseumCollectionRow(keeper_entity_id=town.id, kind=next(iter(HoardKind)), locked=[]))
    await session.flush()
    ctx = await context(session)
    assert await backfill_curators(ctx) == 1
    assert await backfill_curators(ctx) == 0
    works = await session.get(SettlementProfileRow, town.id)
    assert works is not None
    before = works.prestige
    assert await show_collections(ctx) == 1
    assert works.prestige == before + ctx.rules.art_market.curator_prestige
