from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository, caused_by
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarCause
from aerona.engine.interconnect.causes import war_cause_incident
from aerona.engine.interconnect.incident_backfill import ROLES_FIXUP, backfill_incident_roles
from aerona.engine.interconnect.incidents import causality_graph
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx


async def _line(session: AsyncSession, epoch: int, key: str, ids: list[int], cause_incident_id: int | None = None) -> int:
    draft = ChronicleDraft(
        epoch=epoch, kind=ChronicleKind.WORLD, text=f"{key} happened.", entity_ids=ids, template_key=key, cause_incident_id=cause_incident_id
    )
    write = await ChronicleRepository(session).append(draft)
    assert write.incident_id is not None
    return write.incident_id


async def _roles(session: AsyncSession, incident_id: int) -> dict[int, IncidentRole]:
    rows = await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident_id))
    return {row.node_id: row.role for row in rows}


async def test_typed_templates_give_actors_and_targets(session: AsyncSession, world_id: int) -> None:
    avenger = await make(session, "Asa", EntityType.MORTAL, world_id, strength=50)
    enemy = await make(session, "Bors", EntityType.MORTAL, world_id, strength=50)
    incident = await _line(session, 3, "memory.vengeance", [avenger.id, enemy.id])
    assert await _roles(session, incident) == {avenger.id: IncidentRole.ACTOR, enemy.id: IncidentRole.TARGET}


async def test_a_cause_scope_links_everything_written_inside_it(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900)
    other = await make(session, "Osk", EntityType.SETTLEMENT, world_id, population=900)
    battle = await _line(session, 4, "war.battle.victory", [town.id, other.id])
    with caused_by(battle):
        ended = await _line(session, 4, "war.ended_conquest", [other.id])
    row = await session.get(IncidentRow, ended)
    assert row is not None and row.cause_incident_id == battle


async def test_war_causes_reach_back_across_epochs(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900)
    other = await make(session, "Osk", EntityType.SETTLEMENT, world_id, population=900)
    feud = await _line(session, 2, "vendetta.raid", [town.id, other.id])
    await _line(session, 5, "trade.barter", [town.id, other.id])
    assert await war_cause_incident(session, WarCause.VENDETTA, town.id, other.id, 9) == feud
    assert await war_cause_incident(session, WarCause.HOSTILITY, town.id, other.id, 9) != feud


async def test_the_causality_graph_holds_causes_and_consequences(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900)
    other = await make(session, "Osk", EntityType.SETTLEMENT, world_id, population=900)
    root = await _line(session, 1, "grudges.enmity", [other.id])
    own = await _line(session, 3, "war.outbreak", [town.id], cause_incident_id=root)
    after = await _line(session, 6, "war.ended_conquest", [other.id], cause_incident_id=own)
    graph = await causality_graph(session, town.id, 12)
    assert set(graph.incidents) == {root, own, after}
    assert set(graph.edges) == {(root, own), (own, after)}
    assert set(graph.roles) == {own}


async def test_old_incidents_get_their_roles_once(session: AsyncSession, world_id: int) -> None:
    first = await make(session, "Asa", EntityType.MORTAL, world_id, strength=50)
    second = await make(session, "Bors", EntityType.MORTAL, world_id, strength=50)
    incident = await _line(session, 2, "duel.honour", [first.id, second.id])
    for row in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident)):
        row.role = IncidentRole.SUBJECT
    await session.flush()
    ctx = make_ctx(session, Rules())
    assert await backfill_incident_roles(ctx) == 2
    assert await _roles(session, incident) == {first.id: IncidentRole.ACTOR, second.id: IncidentRole.TARGET}
    assert await session.get(AppliedFixupRow, ROLES_FIXUP) is not None
    assert await backfill_incident_roles(ctx) == 0
