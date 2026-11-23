from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agrarian import ReconstructionRow
from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.means import SecurityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.belonging import FugitiveKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.means import LockKind
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.models.entity_stats import StructureStats
from tests.tools.every_setup import led_faction, ruled_realm, second_mortal, wealthy
from tests.tools.every_setup_belonging import at_home
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm, make_entity


async def town_ruler(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    await at_home(session, realm)
    await session.flush()
    return found


async def ruined_rule(session: AsyncSession, realm: Realm) -> Ids:
    found = await town_ruler(session, realm)
    row = ReconstructionRow(settlement_entity_id=realm.settlement_id, cause=RebuildCause.SEA_WAVE, cost=300, locked=[])
    session.add(row)
    await session.flush()
    return {**found, "rebuild": row.id}


async def work_in_town(session: AsyncSession, realm: Realm, state: ConstructionState) -> Ids:
    found = await town_ruler(session, realm)
    work = await make_entity(
        session, "The Long Hall", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=StructureStats()
    )
    session.add(StructureProfileRow(structure_entity_id=work.id, kind=StructureKind.GRANARY, host_entity_id=realm.settlement_id, construction_state=state))
    await session.flush()
    return {**found, "structure": work.id}


async def work_being_raised(session: AsyncSession, realm: Realm) -> Ids:
    return await work_in_town(session, realm, ConstructionState.BUILDING)


async def standing_work(session: AsyncSession, realm: Realm) -> Ids:
    return await work_in_town(session, realm, ConstructionState.COMPLETE)


async def wealthy_at_home(session: AsyncSession, realm: Realm) -> Ids:
    await at_home(session, realm)
    return await wealthy(session, realm)


async def locked_store(session: AsyncSession, realm: Realm) -> Ids:
    await at_home(session, realm)
    store = await make_entity(
        session, "The Sealed Vault", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=StructureStats()
    )
    session.add(StructureProfileRow(structure_entity_id=store.id, kind=StructureKind.WAREHOUSE, host_entity_id=realm.settlement_id))
    session.add(SecurityRow(holder_entity_id=store.id, lock=LockKind.WORKED, lock_quality=60, sealed=False, guards=1, since_epoch=0, locked=[]))
    await session.flush()
    return {"structure": store.id}


async def realm_with_gang(session: AsyncSession, realm: Realm) -> Ids:
    found = await town_ruler(session, realm)
    gang = await led_faction(session, realm, FactionKind.STREET_GANG, "The Low Lanes")
    return {**found, "faction": gang}


async def realm_hunting(session: AsyncSession, realm: Realm) -> Ids:
    found = await town_ruler(session, realm)
    other = await second_mortal(session, realm)
    row = FugitiveRow(mortal_entity_id=other["mortal"], kind=FugitiveKind.RUNAWAY, pursuer_entity_id=found["polity"], fled_epoch=0, locked=[])
    session.add(row)
    await session.flush()
    return {**found, "fugitive": row.id}
