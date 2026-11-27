from collections.abc import Iterator
from contextlib import contextmanager
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.profile_guard import profile_key, register_holder_column
from aerona.db.read_memo import memo_of, table_names
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import ENDED_GUARD, EndedGuard
from aerona.domain.enums.entity import ENDED_STATUSES
from aerona.engine.context import TickContext

ENDING_STEPS: MappingProxyType[str, str] = MappingProxyType(
    {
        "affairs_of_the_ended": "settles what the ended left behind",
        "lifecycle_ends": "writes the end itself",
        "dead_bonds_opening": "opens the ties death makes",
        "dead_bonds_closing": "closes the ties death ends",
        "death_engine": "carries the dead to their afterlife",
        "death_work": "tends the remains",
        "restoration": "raises a fallen realm again",
        "legacy_traits": "passes the traits of the dead to heirs",
        "language_death": "ends tongues with their last speakers",
    }
)
LASTING = frozenset({profile_key("mortal_profiles", "renown")})
HELD_BY: MappingProxyType[str, str] = MappingProxyType(
    {
        "community_cohorts": "community_entity_id",
        "polity_regard": "holder_entity_id",
        "research_progress": "holder_entity_id",
        "polity_map_knowledge": "polity_entity_id",
        "commemorations": "holder_entity_id",
    }
)
for held_table, holder_column in HELD_BY.items():
    register_holder_column(held_table, holder_column)
ENDED_MEMO = "aerona.engine.ended_before"
ENDED_TABLES = table_names((EntityRow,))
RESTORED_COUNTER = "ended_restored"


async def ended_before(session: AsyncSession, epoch: int) -> frozenset[int]:
    memo = memo_of(session, ENDED_MEMO, ENDED_TABLES)
    found: frozenset[int] | None = memo.get(epoch) if memo is not None else None
    if found is None:
        rows = await session.scalars(
            select(EntityRow.id).where(EntityRow.status.in_(sorted(ENDED_STATUSES)), EntityRow.end_epoch < epoch).order_by(EntityRow.id)
        )
        found = frozenset(rows)
        after = memo_of(session, ENDED_MEMO, ENDED_TABLES)
        if after is not None:
            after[epoch] = found
    return found


@contextmanager
def closing_the_ended() -> Iterator[None]:
    token = ENDED_GUARD.set(None)
    try:
        yield
    finally:
        ENDED_GUARD.reset(token)


@contextmanager
def ended_kept(ctx: TickContext, phase: str, ended: frozenset[int]) -> Iterator[None]:
    if phase in ENDING_STEPS or not ended:
        yield
        return
    guard = EndedGuard(ended, LASTING, [])
    token = ENDED_GUARD.set(guard)
    try:
        yield
    finally:
        ENDED_GUARD.reset(token)
        for key in guard.restored:
            ctx.count(f"{RESTORED_COUNTER}.{key}")
