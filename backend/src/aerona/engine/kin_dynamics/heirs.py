from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin_dynamics import KinDisowningRow, KinFavourRow
from aerona.domain.enums.demography import InheritanceCustom
from aerona.engine.body.customs import people_of

DISCRETION = frozenset({InheritanceCustom.ELECTIVE, InheritanceCustom.BY_MERIT, InheritanceCustom.EQUAL_SHARES})
FAVOUR_REACH = 4


async def disowned_by(session: AsyncSession, parent_id: int) -> set[int]:
    query = select(KinDisowningRow.disowned_node_id).where(KinDisowningRow.disowner_node_id == parent_id, KinDisowningRow.reconciled_epoch.is_(None))
    return set(await session.scalars(query))


async def favoured_by(session: AsyncSession, parent_id: int, reach_pct: int) -> list[int]:
    floor = max(0, 100 - reach_pct * FAVOUR_REACH)
    query = select(KinFavourRow).where(KinFavourRow.parent_node_id == parent_id, KinFavourRow.strength >= floor)
    rows = await session.scalars(query.order_by(KinFavourRow.strength.desc(), KinFavourRow.id))
    return [row.child_node_id for row in rows]


async def leaves_a_choice(session: AsyncSession, dead: EntityRow) -> bool:
    folk = await people_of(session, dead)
    culture = await session.get(PeopleCultureRow, folk.id) if folk is not None else None
    return culture is not None and culture.inheritance in DISCRETION
