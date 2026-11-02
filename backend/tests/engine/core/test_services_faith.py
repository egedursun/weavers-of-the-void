from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.sons import SonRepository
from aerona.domain.enums.domain import Domain
from aerona.rules.registry import Rules
from aerona.services.faith import give_first_faith, live_faith, patron_of, set_patron, suggested_first_god, worship_the_creator
from tests.engine.core.factories import CoreWorld, settlement, son_draft


async def test_faith_services(session: AsyncSession, world: CoreWorld, rules: Rules) -> None:
    view = await patron_of(session, world.people.id)
    assert view.patron_son_id == world.son.id
    rival = await SonRepository(session).create(son_draft("Varos", world.world.id, (Domain.WAR, Domain.FIRE)))
    assert await set_patron(session, rules, world.people.id, rival.id)
    assert (await patron_of(session, world.people.id)).patron_son_id == rival.id
    assert await live_faith(session, rules, rival.id) > 0
    town = await settlement(session, "Brookhold", world, world.regions[1])
    assert await suggested_first_god(session, rules, town.id) is not None
    first = await give_first_faith(session, rules, town.id, world.people.id)
    assert first.patron_son_id == rival.id
    assert await worship_the_creator(session, rules, town.id)
    assert (await patron_of(session, town.id)).patron_node_id == world.creator.id
