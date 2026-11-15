from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.read_memo import memo_of
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.domain.enums.lifecycle_end import LifecycleState

S = LifecycleState
LIFECYCLE_TABLES = frozenset({LifecycleStateRow.__tablename__})
GONE = frozenset({S.DORMANT, S.EXTINCT, S.LOST, S.ERADICATED, S.BANISHED, S.DESTROYED})


async def states(session: AsyncSession) -> dict[int, LifecycleState]:
    memo = memo_of(session, "lifecycle_states", LIFECYCLE_TABLES)
    if memo is not None and "all" in memo:
        known: dict[int, LifecycleState] = memo["all"]
        return known
    found = {holder: state for holder, state in await session.execute(select(LifecycleStateRow.holder_entity_id, LifecycleStateRow.state))}
    if memo is not None:
        memo["all"] = found
    return found


async def state_of(session: AsyncSession, holder_id: int) -> LifecycleState:
    return (await states(session)).get(holder_id, S.ACTIVE)


async def ended_ids(session: AsyncSession) -> frozenset[int]:
    return frozenset(holder for holder, state in (await states(session)).items() if state in GONE)
