from dataclasses import dataclass, field

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, LexemeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType

WOVEN_BOND_STATES = (BondState.ACTIVE, BondState.PAST)


@dataclass(frozen=True)
class LoreTotals:
    records: int = 0
    by_type: dict[EntityType, int] = field(default_factory=dict)
    bonds: int = 0
    wars: int = 0
    chronicle: int = 0
    words: int = 0


async def _scalar_count(session: AsyncSession, statement: Select[int]) -> int:
    return int(await session.scalar(statement) or 0)


async def lore_totals(session: AsyncSession) -> LoreTotals:
    rows = await session.execute(select(EntityRow.entity_type, func.count()).where(EntityRow.status != EntityStatus.REJECTED).group_by(EntityRow.entity_type))
    by_type = {entity_type: int(count) for entity_type, count in rows}
    woven = select(func.count()).select_from(BondRow).where(BondRow.state.in_(WOVEN_BOND_STATES))
    return LoreTotals(
        records=sum(by_type.values()),
        by_type=by_type,
        bonds=await _scalar_count(session, woven),
        wars=await _scalar_count(session, woven.where(BondRow.kind == BondKind.ENEMY)),
        chronicle=await _scalar_count(session, select(func.count()).select_from(ChronicleRow)),
        words=await _scalar_count(session, select(func.count()).select_from(LexemeRow)),
    )
