from sqlalchemy import Subquery, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.models.moment import Moment
from aerona.engine.recording.births import MADE_TABLES, made_at

YEAR = "year"


def made() -> Subquery:
    return (
        select(StateChangeRow.node_id, func.min(StateChangeRow.year).label("made"))
        .where(StateChangeRow.operation == LedgerOperation.INSERT, StateChangeRow.table_name.in_(MADE_TABLES), StateChangeRow.year.is_not(None))
        .group_by(StateChangeRow.node_id)
        .subquery()
    )


async def born_after_their_making(session: AsyncSession) -> list[int]:
    making = made()
    rows = await session.execute(
        select(NodeBirthRow.node_id, NodeBirthRow.locked)
        .join(making, making.c.node_id == NodeBirthRow.node_id)
        .join(EntityRow, EntityRow.id == NodeBirthRow.node_id)
        .where(NodeBirthRow.year > making.c.made, EntityRow.entity_type != EntityType.MORTAL)
        .order_by(NodeBirthRow.node_id)
    )
    return [node for node, locked in rows if YEAR not in (locked or []) and not held(node)]


async def date_birth_at_making(session: AsyncSession, node_id: int) -> None:
    row = await session.get(NodeBirthRow, node_id)
    making = await made_at(session, node_id) if row is not None else None
    if row is None or making is None or YEAR in (row.locked or []):
        return
    if making.before(Moment(row.year, row.season, row.day, row.hour)):
        row.year, row.season, row.day, row.hour = making.year, making.season, making.day, making.hour
