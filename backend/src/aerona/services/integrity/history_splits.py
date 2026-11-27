from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gatherings import GATHERING_COLLECTIONS, INCIDENT_ROLES
from aerona.catalog.incident_kinds.onlookers import ONLOOKER_ROLES
from aerona.core.grammar import spoken
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionMemberRow, CollectionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.history.collections import names_of, title_text, titled_nodes

OCCASIONS = frozenset({*GATHERING_COLLECTIONS.values(), CollectionKind.DUEL} - {CollectionKind.WAR})
SPLIT_LOCKS = frozenset({"members", "name"})


@dataclass
class Occasion:
    title: set[int]
    last: int
    epoch: int
    incidents: list[IncidentRow] = field(default_factory=list)
    members: dict[int, CollectionRole] = field(default_factory=dict)


async def incident_roles(session: AsyncSession, incident_id: int) -> dict[int, CollectionRole]:
    rows = await session.execute(
        select(IncidentParticipantRow.node_id, IncidentParticipantRow.role)
        .where(IncidentParticipantRow.incident_id == incident_id)
        .order_by(IncidentParticipantRow.position, IncidentParticipantRow.node_id)
    )
    return {node: INCIDENT_ROLES[role] for node, role in rows if role is not IncidentRole.PLACE and role not in ONLOOKER_ROLES}


async def occasions_in(session: AsyncSession, row: CollectionRow, window: int) -> list[Occasion]:
    incidents = await session.scalars(
        select(IncidentRow)
        .join(CollectionIncidentRow, CollectionIncidentRow.incident_id == IncidentRow.id)
        .where(CollectionIncidentRow.collection_id == row.id, IncidentRow.year.is_not(None))
        .order_by(IncidentRow.year, IncidentRow.id)
    )
    found: list[Occasion] = []
    for incident in incidents:
        members = await incident_roles(session, incident.id)
        title = set(titled_nodes(row.kind, members))
        year = incident.year or 0
        home = next(
            (
                occasion
                for occasion in found
                if (incident.epoch == occasion.epoch or year - occasion.last <= window) and (not title or not occasion.title or title & occasion.title)
            ),
            None,
        )
        if home is None:
            home = Occasion(title, year, incident.epoch)
            found.append(home)
        home.title |= title
        home.last, home.epoch = year, incident.epoch
        home.incidents.append(incident)
        home.members.update({node: role for node, role in members.items() if node not in home.members})
    return found


async def splittable(session: AsyncSession, row: CollectionRow, window: int) -> bool:
    if row.kind not in OCCASIONS or held(row.world_id) or SPLIT_LOCKS & set(row.locked or []):
        return False
    return len(await occasions_in(session, row, window)) > 1


async def occasions_joined_in_one(session: AsyncSession) -> list[int]:
    window = (await CosmosRepository(session).rules()).collections.join_window_years
    rows = await session.scalars(select(CollectionRow).where(CollectionRow.kind.in_(sorted(OCCASIONS))).order_by(CollectionRow.id))
    return [row.id for row in rows if await splittable(session, row, window)]


async def split_occasions(session: AsyncSession, collection_id: int) -> None:
    row = await session.get(CollectionRow, collection_id)
    if row is None:
        return
    window = (await CosmosRepository(session).rules()).collections.join_window_years
    occasions = await occasions_in(session, row, window)
    if len(occasions) < 2:
        return
    for occasion in occasions[1:]:
        names = await names_of(session, occasion.members)
        epochs = [incident.epoch for incident in occasion.incidents]
        part = CollectionRow(
            kind=row.kind,
            name=title_text(row.kind, occasion.members, [], names),
            world_id=row.world_id,
            start_epoch=min(epochs),
            end_epoch=max(epochs) if row.end_epoch is not None else None,
            source_key=row.source_key,
            locked=[],
        )
        session.add(part)
        await session.flush()
        for incident in occasion.incidents:
            link = await session.get(CollectionIncidentRow, (row.id, incident.id))
            if link is not None:
                await session.delete(link)
            session.add(CollectionIncidentRow(collection_id=part.id, incident_id=incident.id))
        session.add_all(
            CollectionMemberRow(collection_id=part.id, node_id=node, role=role, since_epoch=part.start_epoch) for node, role in occasion.members.items()
        )
    await session.flush()


async def plague_sickness(session: AsyncSession, collection_id: int) -> str | None:
    found = await session.execute(
        select(EntityRow.name, func.count())
        .join(IncidentParticipantRow, IncidentParticipantRow.node_id == EntityRow.id)
        .join(CollectionIncidentRow, CollectionIncidentRow.incident_id == IncidentParticipantRow.incident_id)
        .where(CollectionIncidentRow.collection_id == collection_id, EntityRow.entity_type == EntityType.DISEASE)
        .group_by(EntityRow.id, EntityRow.name)
        .order_by(func.count().desc(), EntityRow.id)
        .limit(1)
    )
    row = found.first()
    return row[0] if row is not None else None


def plague_title(sickness: str) -> str:
    return f"{spoken(CollectionKind.PLAGUE).capitalize()} of {sickness}"


async def plagues_named_otherwise(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(CollectionRow).where(CollectionRow.kind == CollectionKind.PLAGUE).order_by(CollectionRow.id)):
        if held(row.world_id) or SPLIT_LOCKS & set(row.locked or []):
            continue
        sickness = await plague_sickness(session, row.id)
        if sickness is not None and row.name != plague_title(sickness):
            found.append(row.id)
    return found


async def name_plague_by_its_sickness(session: AsyncSession, collection_id: int) -> None:
    row = await session.get(CollectionRow, collection_id)
    sickness = await plague_sickness(session, collection_id) if row is not None else None
    if row is not None and sickness is not None:
        row.name = plague_title(sickness)
