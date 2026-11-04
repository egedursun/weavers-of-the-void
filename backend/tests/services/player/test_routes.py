from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import TreatyStatus
from aerona.domain.enums.society import ResourceMechanic
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import routes
from aerona.services.player.scope import PlayerScope
from tests.engine.core.factories import region_record
from tests.services.player.factories import PlayerWorld, make_entity


async def undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    return (await UndoRun(session, epoch, changes, label_names(changes, await node_names(session, changes))).run()).conflicts


async def mapped(session: AsyncSession, world: PlayerWorld) -> None:
    session.add(
        WorldMapRow(world_id=world.world.id, generator_version=1, epoch=1, geometry={"regions": [region_record(world.region.id, []).model_dump(mode="json")]})
    )
    await session.flush()


async def test_a_route_is_laid_held_struck_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await mapped(session, world)
    first = await make_entity(session, "Arvenmoor", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Brissoll", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    founded = await routes.found_route(scope, routes.FoundRoute(first_id=first.id, second_id=second.id, mode=TradeMode.SKY))
    route_id = founded.created_ids[0]
    profile = await session.get(TradeRouteProfileRow, route_id)
    assert profile is not None and profile.mode is TradeMode.SKY and profile.locked == ["mode"]
    edited = await routes.edit_route(scope, routes.EditRoute(route_id=route_id, values={"status": "closed", "season_pct": 55}))
    assert profile.status is TradeRouteStatus.CLOSED and profile.closed_by_player and "season_pct" in profile.locked
    assert await undo(session, edited.ledger_entry_id, world.cosmos.epoch) == []
    await session.refresh(profile)
    assert profile.status is TradeRouteStatus.OPEN and profile.season_pct != 55
    struck = await routes.delete_route(scope, routes.RouteTarget(route_id=route_id))
    road = await session.get(type(first), route_id)
    assert road is not None and road.status is EntityStatus.DESTROYED
    assert await undo(session, struck.ledger_entry_id, world.cosmos.epoch) == []
    await session.refresh(road)
    assert road.status is EntityStatus.CANON


async def test_a_pact_is_struck_retermed_and_released_through_the_ledger(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    keeper = await make_entity(session, "Corvessa", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    vein = await make_entity(session, "The Murmuring Lode", EntityType.RESOURCE, world_id=world.world.id, location_id=world.region.id)
    session.add(ResourceMechanicRow(entity_id=vein.id, mechanic=ResourceMechanic.SENTIENT, magnitude=5, epochs=None))
    struck = await routes.strike_pact(scope, routes.StrikePact(resource_id=vein.id, owner_id=keeper.id, terms={"demand": "silence at dusk", "units": 4}))
    treaty_id = struck.created_ids[0]
    clause = await session.scalar(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty_id))
    assert clause is not None and clause.params["demand"] == "silence at dusk"
    await routes.pact_terms(scope, routes.PactTerms(treaty_id=treaty_id, terms={"units": 9}))
    assert clause.params["units"] == 9
    await routes.end_pact(scope, routes.PactTarget(treaty_id=treaty_id))
    profile = await session.get(TreatyProfileRow, treaty_id)
    assert profile is not None and profile.status is TreatyStatus.FULFILLED
