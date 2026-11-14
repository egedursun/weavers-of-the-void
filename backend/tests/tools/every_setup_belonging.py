from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import OutlawRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import StructureStats
from tests.tools.every_setup import ruled_realm, second_mortal
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm, make_entity


async def at_home(session: AsyncSession, realm: Realm) -> None:
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id


async def hunted_by_a_temple(session: AsyncSession, realm: Realm) -> Ids:
    await at_home(session, realm)
    temple = await make_entity(
        session, "Hall of Rest", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=StructureStats()
    )
    session.add(StructureProfileRow(structure_entity_id=temple.id, kind=StructureKind.TEMPLE))
    session.add(OutlawRow(mortal_entity_id=realm.mortal_id, polity_entity_id=None, declared_epoch=0, locked=[]))
    await session.flush()
    return {"temple": temple.id}


async def mocked_court(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    other = await second_mortal(session, realm)
    office = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == found["polity"], OfficeRow.kind == OfficeKind.RULER))
    assert office is not None
    office.holder_entity_id = other["mortal"]
    await at_home(session, realm)
    await session.flush()
    return found
