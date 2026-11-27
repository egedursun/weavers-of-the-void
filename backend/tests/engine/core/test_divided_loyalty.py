from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.war import WarCause, WarSide
from aerona.domain.models.entity_stats import EventStats, FactionStats, PolityStats
from aerona.engine.polity.divided_loyalty import heads_a_foe, serves_a_foe
from tests.engine.core.factories import CoreWorld, entity, mortal


async def test_no_one_heads_a_body_at_war_with_the_realm_they_serve(session: AsyncSession, world: CoreWorld) -> None:
    realm = await entity(session, "Realm of Quays", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    rebels = await entity(session, "Free Band", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    rising = await entity(session, "The Rising", EntityType.EVENT, EventStats(), world_id=world.world.id)
    rebel_head = await mortal(session, "Ponar", world, world.regions[0].id)
    envoy = await mortal(session, "Envor", world, world.regions[0].id)
    loyal = await mortal(session, "Lerra", world, world.regions[0].id)
    war = WarRow(event_entity_id=rising.id, world_id=world.world.id, cause=WarCause.UPRISING, started_epoch=1)
    session.add(war)
    await session.flush()
    session.add_all(
        [
            WarSideRow(war_id=war.id, entity_id=realm.id, side=WarSide.DEFENDER, joined_epoch=1),
            WarSideRow(war_id=war.id, entity_id=rebels.id, side=WarSide.ATTACKER, joined_epoch=1),
            OrgGovernanceRow(org_node_id=rebels.id, head_node_id=rebel_head.id, locked=[]),
            OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.AMBASSADOR, holder_entity_id=envoy.id, since_epoch=1, locked=[]),
        ]
    )
    await session.flush()
    assert await heads_a_foe(session, rebel_head.id, realm.id)
    assert not await heads_a_foe(session, loyal.id, realm.id)
    assert await serves_a_foe(session, [envoy.id, loyal.id], rebels.id) == {envoy.id}
