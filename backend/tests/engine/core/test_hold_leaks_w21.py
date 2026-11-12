from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, PolityTerritoryRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.factions.book import FactionBook
from aerona.engine.factions.outlaws import hire
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import map_territory, sync_members
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.war import declare_war, ongoing_wars, open_war
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


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


async def test_a_held_town_neither_joins_nor_leaves_a_realm(session: AsyncSession, world: CoreWorld) -> None:
    kept = await settlement(session, "Kept", world, world.regions[0])
    held_out = await settlement(session, "Held Out", world, world.regions[0])
    polity = await entity(session, "Crown of Kept", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            core_entity_id=kept.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=kept.id))
    await session.flush()
    ctx = await manual_context(session, "hold")
    book = await RealmBook.load(session)
    realm = book.realms[polity.id]
    token = HELD_SCOPE.set(HeldScope(None, frozenset({kept.id, held_out.id})))
    try:
        assert await sync_members(ctx, book, realm, {held_out.id}) == (0, 0)
    finally:
        HELD_SCOPE.reset(token)
    await session.flush()
    members = set(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity.id)))
    assert members == {kept.id}


async def test_a_held_realm_at_war_hires_no_mercenaries(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashby", world, world.regions[0])
    foe_town = await settlement(session, "Farside", world, world.regions[2])
    realms = []
    for name, seat in (("Crown of Ashby", town), ("Crown of Farside", foe_town)):
        polity = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
        session.add(
            PolityProfileRow(
                polity_entity_id=polity.id,
                government=next(iter(GovernmentKind)),
                decision_rule=next(iter(DecisionRule)),
                core_entity_id=polity.id,
                treasury=10_000,
                emblem={},
                legitimacy_parts={},
                locked=[],
            )
        )
        session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=seat.id))
        realms.append(polity)
    company = await entity(session, "Free Spears", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add(FactionProfileRow(faction_entity_id=company.id, kind=FactionKind.MERCENARY_COMPANY, home_entity_id=town.id, treasury=0))
    await session.flush()
    ctx = await manual_context(session, "hold", rules=tuned_rules(mercenaries={"hire_chance": 100}))
    assert await declare_war(ctx, realms[0].id, realms[1].id, "an old quarrel", world_cap=False)
    await open_war(ctx, realms[0], realms[1])
    assert await ongoing_wars(session, realms[0].id)
    token = HELD_SCOPE.set(HeldScope(None, frozenset({realms[0].id, realms[1].id})))
    try:
        hired = await hire(ctx, await FactionBook.load(session), await RealmBook.load(session))
    finally:
        HELD_SCOPE.reset(token)
    profile = await session.get(FactionProfileRow, company.id)
    assert hired == 0 and profile is not None and profile.employer_entity_id is None
