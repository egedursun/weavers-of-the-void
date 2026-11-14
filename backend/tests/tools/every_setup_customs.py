from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.customs import CooperativeRow, MembershipRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.customs import CoopPurpose, Membership, Naturalisation
from tests.tools.every_setup import ruled_realm
from tests.tools.factories import Realm

Ids = dict[str, int]


async def town_pool(session: AsyncSession, realm: Realm) -> Ids:
    faction = await session.get(EntityRow, realm.faction_id)
    me = await session.get(EntityRow, realm.mortal_id)
    assert faction is not None and me is not None
    faction.location_id = realm.settlement_id
    me.location_id = realm.settlement_id
    session.add(CooperativeRow(faction_entity_id=faction.id, purpose=CoopPurpose.MILL, locked=[]))
    await session.flush()
    return {"faction": faction.id}


async def long_foreigner(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    session.add(
        MembershipRow(
            mortal_entity_id=realm.mortal_id,
            polity_entity_id=found["polity"],
            category=Membership.RESIDENT_FOREIGNER,
            path=Naturalisation.BIRTHPLACE,
            since_epoch=0,
            locked=[],
        )
    )
    profile = await session.get(MortalProfileRow, realm.mortal_id)
    if profile is None:
        session.add(MortalProfileRow(entity_id=realm.mortal_id, wealth=100, locked=[]))
    else:
        profile.wealth = 100
    await session.flush()
    return found
