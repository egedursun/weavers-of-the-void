from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.customs import MembershipRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.domain.enums.customs import Naturalisation
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.enums.statecraft import CrisisDemand, CrisisState


async def not_mortal(session: AsyncSession, node_id: int | None) -> bool:
    entity = await session.get(EntityRow, node_id) if node_id is not None else None
    return entity is None or entity.entity_type is not EntityType.MORTAL


async def faceless_hand_overs(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(CrisisRow).where(CrisisRow.demand == CrisisDemand.HAND_OVER, CrisisRow.state == CrisisState.ESCALATING).order_by(CrisisRow.id)
    )
    return [row.id for row in rows if await not_mortal(session, row.subject_node_id)]


async def drop_hand_over(session: AsyncSession, key: int) -> None:
    row = await session.get(CrisisRow, key)
    if row is not None and row.state is CrisisState.ESCALATING:
        row.state = CrisisState.BACKED_DOWN


async def unpartnered_unions(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(MembershipRow).where(MembershipRow.path == Naturalisation.UNION).order_by(MembershipRow.mortal_entity_id))
    return [row.mortal_entity_id for row in rows if await not_mortal(session, row.spouse_entity_id)]


async def mark_residence(session: AsyncSession, key: int) -> None:
    row = await session.get(MembershipRow, key)
    if row is not None and row.path is Naturalisation.UNION:
        row.path = Naturalisation.RESIDENCE
        row.spouse_entity_id = None


async def orphaned_adoptions(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ClaimRow).where(ClaimRow.basis == ClaimBasis.ADOPTION, ClaimRow.ended_epoch.is_(None)).order_by(ClaimRow.id))
    return [row.id for row in rows if await not_mortal(session, row.backer_entity_id)]


async def end_adoption(session: AsyncSession, key: int) -> None:
    row = await session.get(ClaimRow, key)
    if row is not None and row.ended_epoch is None:
        row.ended_epoch = row.since_epoch
