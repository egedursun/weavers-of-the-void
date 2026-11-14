from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.eras import ProgrammeStage
from aerona.domain.enums.mind import SkillKind, SkillSource
from tests.tools.every_setup import ruled_realm
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm


async def realm_programme(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    row = TechProgrammeRow(
        polity_entity_id=found["polity"], technique=Technique.ROCKETRY, progress=40, stage=ProgrammeStage.BUILDING, started_epoch=0, locked=[]
    )
    session.add(row)
    await session.flush()
    return {**found, "programme": row.id}


async def skilled_for_programme(session: AsyncSession, realm: Realm) -> Ids:
    found = await realm_programme(session, realm)
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.ENGINEERING, level=12, peak=12, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return found
