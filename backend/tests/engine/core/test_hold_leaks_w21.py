from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, PolityTerritoryRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import map_territory
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, settlement


async def territory_of(session: AsyncSession, polity_id: int) -> list[PolityTerritoryRow]:
    return list(await session.scalars(select(PolityTerritoryRow).where(PolityTerritoryRow.polity_entity_id == polity_id)))


async def test_a_held_realm_keeps_its_lands_as_they_are(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await entity(session, "Crown of Ashby", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            core_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    ctx = await manual_context(session, "hold")
    book = await RealmBook.load(session)
    realm = book.realms[polity.id]
    token = HELD_SCOPE.set(HeldScope(None, frozenset({polity.id})))
    try:
        await map_territory(ctx, book, realm, book.members(realm))
    finally:
        HELD_SCOPE.reset(token)
    await session.flush()
    assert await territory_of(session, polity.id) == []
    await map_territory(ctx, book, realm, book.members(realm))
    await session.flush()
    assert [row.region_entity_id for row in await territory_of(session, polity.id)] == [world.regions[0].id]
