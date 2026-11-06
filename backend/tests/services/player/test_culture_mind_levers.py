import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.mind import CultureEthicRow, CultureHonourRow, PreferenceRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind, EthicalStance, HonourModel, PreferenceKind
from aerona.services.player import culture_mind
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_sets_holds_and_removes_tastes(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hero = await make_entity(session, "Lis", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    made = await culture_mind.set_preference(scope, culture_mind.SetPreference(holder_id=hero.id, kind=PreferenceKind.COLOUR, target="blue", strength=70))
    row = await session.get(PreferenceRow, made.values["preference_id"])
    assert row is not None and row.strength == 70 and "strength" in row.locked
    with pytest.raises(ValidationFailedError):
        await culture_mind.set_preference(scope, culture_mind.SetPreference(holder_id=hero.id, kind=PreferenceKind.COLOUR, target="not a colour", strength=10))
    await culture_mind.remove_preference(scope, culture_mind.PreferenceTarget(preference_id=row.id))
    assert await session.get(PreferenceRow, row.id) is None


async def test_the_god_sets_a_peoples_ethics_and_honour(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    folk = await make_entity(session, "Ennar", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await culture_mind.set_stance(scope, culture_mind.SetStance(holder_id=folk.id, act=ActKind.THEFT, stance=EthicalStance.REQUIRED))
    row = await session.get(CultureEthicRow, (folk.id, ActKind.THEFT))
    assert row is not None and row.stance is EthicalStance.REQUIRED and "stance" in row.locked
    await culture_mind.set_honour(scope, culture_mind.SetHonour(holder_id=folk.id, model=HonourModel.FACE))
    honour = await session.get(CultureHonourRow, folk.id)
    assert honour is not None and honour.model is HonourModel.FACE
    hero = await make_entity(session, "Rho", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    with pytest.raises(ValidationFailedError):
        await culture_mind.set_stance(scope, culture_mind.SetStance(holder_id=hero.id, act=ActKind.THEFT, stance=EthicalStance.SHAMEFUL))
