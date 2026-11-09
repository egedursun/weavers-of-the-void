from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.foreign_god import ForeignGodStatus
from tests.engine.society.factories import Realm, link, son


async def god(realm: Realm, name: str, first: Domain, second: Domain, *, existence: int = 100) -> SonRow:
    found = await son(realm.session, name, realm.world.id)
    found.domain_primary, found.domain_secondary, found.existence = first, second, existence
    await realm.session.flush()
    return found


async def foreign(session: AsyncSession, realm: Realm, name: str, first: Domain, *, stance: int = 0, power: int = 60) -> ForeignGodRow:
    row = ForeignGodRow(
        name=name,
        domain_primary=first,
        world_id=realm.world.id,
        power=power,
        stance=stance,
        status=ForeignGodStatus.AWAKE,
        strength=50,
        endurance=50,
        agility=50,
        wisdom=50,
        cunning=50,
        will=50,
        creativity=50,
        charisma=50,
        might=50,
        sanity=80,
        created_epoch=1,
    )
    session.add(row)
    await session.flush()
    return row


async def worship(realm: Realm, community: EntityRow, god_id: int) -> None:
    await link(realm.session, community.id, god_id, BondKind.WORSHIPS)
    await realm.session.flush()
