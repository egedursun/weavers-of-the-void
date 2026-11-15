from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.discovery import TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.fossil import FossilSource
from aerona.domain.enums.lifecycle_end import LifecycleCause, LifecycleKind, LifecycleState
from aerona.domain.models.entity_stats import TheoryStats
from tests.tools.factories import Realm, make_entity

Ids = dict[str, int]


async def forgotten_theory(session: AsyncSession, realm: Realm) -> Ids:
    theory = await make_entity(session, "The Four Humours", EntityType.THEORY, world_id=realm.cosmos.world_id, stats=TheoryStats())
    session.add(TheoryProfileRow(theory_entity_id=theory.id, domain=TheoryDomain.MEDICINE, locked=[]))
    session.add(
        LifecycleStateRow(holder_entity_id=theory.id, kind=LifecycleKind.THEORY, state=LifecycleState.EXTINCT, cause=LifecycleCause.NO_TEXTS, locked=[])
    )
    await session.flush()
    return {"theory": theory.id}


async def hidden_fossils(session: AsyncSession, realm: Realm) -> Ids:
    town = await session.get(EntityRow, realm.settlement_id)
    assert town is not None and town.location_id is not None
    session.add(FossilBedRow(region_entity_id=town.location_id, world_id=realm.cosmos.world_id, source=FossilSource.MEGAFAUNA, richness=40, locked=[]))
    await session.flush()
    return {"region": town.location_id}
