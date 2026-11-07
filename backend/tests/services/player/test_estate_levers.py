from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow, MovementProfileRow, MovementSupportRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import EstatePrivilege, MovementCause
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import PolityStats
from aerona.services.player import estates
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_gathers_estates_and_raises_movements(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Tamsin", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    polity = await make_entity(session, "Realm of Tamsin", EntityType.POLITY, world_id=world.world.id, stats=PolityStats())
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    await estates.found(scope, estates.FoundEstate(realm_id=polity.id, social_class=SocialClass.PRIEST))
    estate = next(iter(await session.scalars(select(EstateProfileRow))))
    estate_id = estate.faction_entity_id
    await estates.edit(scope, estates.EditEstate(estate_id=estate_id, loyalty=80))
    await estates.privilege(scope, estates.SetPrivilege(estate_id=estate_id, privilege=EstatePrivilege.COUNCIL_SEAT))
    assert await session.get(EstatePrivilegeRow, (estate_id, EstatePrivilege.COUNCIL_SEAT)) is not None
    await estates.privilege(scope, estates.SetPrivilege(estate_id=estate_id, privilege=EstatePrivilege.COUNCIL_SEAT, grant=False))
    assert await session.get(EstatePrivilegeRow, (estate_id, EstatePrivilege.COUNCIL_SEAT)) is None
    await estates.remove(scope, estates.EstateTarget(estate_id=estate_id))
    assert await session.get(EstateProfileRow, estate_id) is None
    raised = await estates.found_cause(scope, estates.FoundMovement(realm_id=polity.id, cause=MovementCause.LAND_REFORM, home_id=town.id))
    movement_id = raised.target_node_id
    assert movement_id is not None
    await estates.edit_movement(scope, estates.EditMovement(movement_id=movement_id, support=55, is_party=True))
    row = await session.get(MovementProfileRow, movement_id)
    assert row is not None and row.support == 55 and row.is_party
    await estates.set_support(scope, estates.SetSupport(movement_id=movement_id, community_id=town.id, share=40))
    assert await session.get(MovementSupportRow, (movement_id, town.id)) is not None
    await estates.remove_support(scope, estates.SupportTarget(movement_id=movement_id, community_id=town.id))
    await estates.remove_movement(scope, estates.MovementTarget(movement_id=movement_id))
    assert await session.get(MovementProfileRow, movement_id) is None
