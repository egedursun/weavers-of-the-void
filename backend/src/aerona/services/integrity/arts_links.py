from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.services import OPEN
from aerona.db.tables.arts import ClubRow, LeagueRow
from aerona.db.tables.constructs import InstructionOrderRow, InstructionSetRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.constructs import ContractStatus
from aerona.domain.enums.entity import EntityStatus


async def mend_arts_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    leagues = select(LeagueRow.faction_entity_id)
    mended = 0
    for statement in (
        update(MonsterContractRow)
        .where(MonsterContractRow.status.in_(OPEN), MonsterContractRow.beast_entity_id.in_(vanished))
        .values(status=ContractStatus.WITHDRAWN, closed_epoch=epoch),
        update(MonsterContractRow)
        .where(MonsterContractRow.status == ContractStatus.TAKEN, MonsterContractRow.hunter_entity_id.in_(vanished))
        .values(status=ContractStatus.POSTED, hunter_entity_id=None),
        update(ClubRow).where(ClubRow.league_entity_id.is_not(None), ClubRow.league_entity_id.not_in(leagues)).values(league_entity_id=None),
        update(InstructionOrderRow).where(InstructionOrderRow.target_node_id.in_(vanished)).values(target_node_id=None),
        delete(InstructionSetRow).where(InstructionSetRow.owner_entity_id.in_(vanished)),
    ):
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended
