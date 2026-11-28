from collections.abc import Iterable, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.onlookers import ONLOOKER_ROLES
from aerona.db.fast_session import rows_by_id
from aerona.db.read_memo import memo_of, table_names
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.node import NodeBirthRow, NodeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.moment import Moment, latest

CREATION_ROLES = frozenset({IncidentRole.PRODUCT, IncidentRole.CHILD})
HEARSAY_ROLES = ONLOOKER_ROLES


BIRTHS_MEMO = "aerona.recording.births"
BIRTH_TABLES = table_names([NodeBirthRow])
MADE_TABLES = sorted(table_names([NodeRow, EntityRow]))


async def birth_moments(session: AsyncSession, nodes: Iterable[int]) -> dict[int, Moment | None]:
    ids = sorted({node for node in nodes if node is not None})
    if not ids:
        return {}
    memo = memo_of(session, BIRTHS_MEMO, BIRTH_TABLES)
    known: dict[int, Moment | None] = {node: memo[node] for node in ids if memo is not None and node in memo}
    missing = [node for node in ids if node not in known]
    if missing:
        found: dict[int, Moment | None] = dict.fromkeys(missing)
        rows = await session.execute(
            select(NodeBirthRow.node_id, NodeBirthRow.year, NodeBirthRow.season, NodeBirthRow.day, NodeBirthRow.hour).where(NodeBirthRow.node_id.in_(missing))
        )
        for node, year, season, day, hour in rows:
            found[node] = Moment(year, season, day, hour)
        after = memo_of(session, BIRTHS_MEMO, BIRTH_TABLES)
        if after is not None:
            for node, moment in found.items():
                after[node] = moment
        known.update(found)
    return known


async def born_floor(session: AsyncSession, nodes: Iterable[int]) -> Moment | None:
    return latest(*(await birth_moments(session, nodes)).values())


def date_born(session: AsyncSession, node: int, moment: Moment) -> None:
    session.add(NodeBirthRow(node_id=node, year=moment.year, season=moment.season, day=moment.day, hour=moment.hour, locked=[]))


def born_now(row: NodeRow | None, created: bool, epoch: int) -> bool:
    if isinstance(row, EntityRow):
        return row.birth_epoch == epoch
    return created


async def mark_born(session: AsyncSession, participants: Iterable[tuple[int, IncidentRole]], moment: Moment, epoch: int, known: Mapping[int, NodeRow]) -> None:
    named = [(node, role) for node, role in participants if role not in HEARSAY_ROLES]
    if not named:
        return
    created = {node for node, role in named if role in CREATION_ROLES}
    births = await birth_moments(session, [node for node, _ in named])
    for node in sorted(births):
        if births[node] is None and born_now(known.get(node), node in created, epoch):
            first = earliest(moment, await made_at(session, node, epoch))
            date_born(session, node, first if node in created else lived_since(known.get(node), first))


async def made_at(session: AsyncSession, node: int, epoch: int | None = None) -> Moment | None:
    row = (
        await session.execute(
            select(StateChangeRow.year, StateChangeRow.season, StateChangeRow.day, StateChangeRow.hour)
            .where(
                StateChangeRow.node_id == node,
                StateChangeRow.epoch == epoch if epoch is not None else StateChangeRow.epoch.is_not(None),
                StateChangeRow.operation == LedgerOperation.INSERT,
                StateChangeRow.table_name.in_(MADE_TABLES),
                StateChangeRow.year.is_not(None),
            )
            .order_by(StateChangeRow.year, StateChangeRow.season, StateChangeRow.day, StateChangeRow.hour)
            .limit(1)
        )
    ).first()
    return Moment(row[0], row[1], row[2], row[3]) if row is not None and row[0] is not None else None


def earliest(moment: Moment, made: Moment | None) -> Moment:
    return made if made is not None and made.before(moment) else moment


def lived_since(row: NodeRow | None, moment: Moment) -> Moment:
    if not isinstance(row, EntityRow) or row.entity_type is not EntityType.MORTAL:
        return moment
    age = getattr(row.stats, "age", None)
    return Moment(moment.year - age) if isinstance(age, int) and age > 0 else moment


async def birth_year(session: AsyncSession, node: int) -> int | None:
    moment = (await birth_moments(session, [node])).get(node)
    return moment.year if moment is not None else None


async def mark_born_at(session: AsyncSession, participants: Sequence[tuple[int, IncidentRole]], incident_id: int) -> None:
    incident = await session.get(IncidentRow, incident_id)
    if incident is None or incident.year is None:
        return
    known = await rows_by_id(session, NodeRow, sorted({node for node, _ in participants}))
    await mark_born(session, participants, Moment(incident.year, incident.season, incident.day, incident.hour), incident.epoch, known)
