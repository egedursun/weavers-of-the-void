import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.mythic import MantlingRow
from aerona.domain.enums.entity import EntityType
from aerona.services.player import mythic
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_a_change_that_points_at_nothing_is_refused_plainly_and_leaves_the_record_as_it_was(
    scope: PlayerScope, session: AsyncSession, world: PlayerWorld
) -> None:
    hero = await make_entity(session, "Ilse", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    await mythic.edit_mantling(scope, mythic.MortalEdit(mortal_id=hero.id, values={"deeds": 4}))
    with pytest.raises(ValidationFailedError, match="points at something that does not exist"):
        await mythic.edit_mantling(scope, mythic.MortalEdit(mortal_id=hero.id, values={"god_node_id": 999999, "deeds": 9}))
    row = await session.get(MantlingRow, hero.id)
    assert row is not None
    assert (row.god_node_id, row.deeds) == (None, 4)
