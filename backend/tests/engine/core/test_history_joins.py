from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.chronicle_facts import history_facts
from aerona.agents.context.scope import load_scope
from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.history.collections import CollectionTally, gather_incidents
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, mortal
from tests.engine.cosmos.factories import tick


async def happen(session: AsyncSession, world: CoreWorld, kind: str, *, at: tuple[int, int], roles: dict[int, IncidentRole]) -> IncidentRow:
    epoch, year = at
    incident = IncidentRow(kind=kind, epoch=epoch, year=year, world_id=world.world.id)
    session.add(incident)
    await session.flush()
    session.add_all(IncidentParticipantRow(incident_id=incident.id, node_id=node, role=role) for node, role in roles.items())
    await session.flush()
    return incident


async def gathered(session: AsyncSession, epoch: int) -> None:
    await gather_incidents(tick(session, Rules(), epoch=epoch), CollectionTally())
    await session.flush()


async def collection_of(session: AsyncSession, incident: IncidentRow) -> CollectionRow:
    row = await session.scalar(
        select(CollectionRow)
        .join(CollectionIncidentRow, CollectionIncidentRow.collection_id == CollectionRow.id)
        .where(CollectionIncidentRow.incident_id == incident.id)
    )
    assert row is not None
    return row


async def test_a_duel_an_age_later_is_its_own_history_though_a_fighter_is_the_same(session: AsyncSession, world: CoreWorld) -> None:
    parar, wapnar, onur = [await mortal(session, name, world, world.regions[0].id) for name in ("Parar", "Wapnar", "Onur")]
    first = await happen(session, world, "duel.honour", at=(9, 441), roles={parar.id: IncidentRole.ACTOR, wapnar.id: IncidentRole.OPPONENT})
    await gathered(session, 9)
    later = await happen(session, world, "duel.honour", at=(10, 485), roles={wapnar.id: IncidentRole.ACTOR, onur.id: IncidentRole.OPPONENT})
    await gathered(session, 10)
    old, new = await collection_of(session, first), await collection_of(session, later)
    assert old.id != new.id
    assert new.name == "Duel of Wapnar and Onur"


async def test_two_funerals_sharing_a_host_stay_apart(session: AsyncSession, world: CoreWorld) -> None:
    host, one, two = [await mortal(session, name, world, world.regions[0].id) for name in ("Keeper", "Avek", "Okbem")]
    first = await happen(session, world, "mortal.mourning", at=(10, 482), roles={one.id: IncidentRole.VICTIM, host.id: IncidentRole.HOST})
    second = await happen(session, world, "mortal.mourning", at=(10, 483), roles={two.id: IncidentRole.VICTIM, host.id: IncidentRole.HOST})
    await gathered(session, 10)
    left, right = await collection_of(session, first), await collection_of(session, second)
    assert left.id != right.id
    assert (left.name, right.name) == ("Funeral of Avek", "Funeral of Okbem")


async def test_a_plague_is_named_by_its_sickness_never_by_a_carrier(session: AsyncSession, world: CoreWorld) -> None:
    carrier = await mortal(session, "Mamda", world, world.regions[0].id)
    sickness = await entity(session, "Grey cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    first = await happen(session, world, "disease.army_carried", at=(10, 481), roles={carrier.id: IncidentRole.SUBJECT, sickness.id: IncidentRole.INSTRUMENT})
    await gathered(session, 10)
    assert (await collection_of(session, first)).name == "Plague of Grey cough"


async def test_the_chronicler_hears_only_of_histories_lived_this_age(session: AsyncSession, world: CoreWorld) -> None:
    pair = [await mortal(session, name, world, world.regions[0].id) for name in ("Satlal", "Opcac")]
    wedding = await happen(session, world, "kin.marriage", at=(9, 440), roles={pair[0].id: IncidentRole.SUBJECT, pair[1].id: IncidentRole.SPOUSE})
    await gathered(session, 9)
    old = await collection_of(session, wedding)
    assert old.end_epoch is None
    scope = await load_scope(session, Rules())
    assert old.name not in [history.name for history in await history_facts(scope, 10)]
    assert old.name in [history.name for history in await history_facts(scope, 9)]
