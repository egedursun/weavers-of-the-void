from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeBirthRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.moment import Moment, latest

CREATION_ROLES = frozenset({IncidentRole.PRODUCT, IncidentRole.CHILD})


async def born_floor(session: AsyncSession, nodes: Iterable[int]) -> Moment | None:
    ids = sorted({node for node in nodes if node is not None})
    if not ids:
        return None
    rows = await session.execute(select(NodeBirthRow.year, NodeBirthRow.season, NodeBirthRow.day, NodeBirthRow.hour).where(NodeBirthRow.node_id.in_(ids)))
    return latest(*(Moment(year, season, day, hour) for year, season, day, hour in rows))


async def mark_born(session: AsyncSession, participants: Iterable[tuple[int, IncidentRole]], moment: Moment, epoch: int) -> None:
    ids = sorted({node for node, role in participants if role in CREATION_ROLES})
    if not ids:
        return
    older = set(await session.scalars(select(EntityRow.id).where(EntityRow.id.in_(ids), EntityRow.birth_epoch != epoch)))
    dated = set(await session.scalars(select(NodeBirthRow.node_id).where(NodeBirthRow.node_id.in_(ids))))
    for node in ids:
        if node not in older and node not in dated:
            session.add(NodeBirthRow(node_id=node, year=moment.year, season=moment.season, day=moment.day, hour=moment.hour, locked=[]))
