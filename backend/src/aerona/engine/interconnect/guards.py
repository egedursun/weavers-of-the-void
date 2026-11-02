from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.context import TickContext
from aerona.engine.interconnect.registry import mechanic_keys_for_phase, suppression_key
from aerona.engine.phase import Phase
from aerona.engine.primitives.modifiers import GUARD_SOURCES


@dataclass(frozen=True)
class GuardIndex:
    pins: frozenset[tuple[int, str]]
    suppressions: frozenset[tuple[int, str]]

    @classmethod
    async def load(cls, session: AsyncSession, epoch: int) -> "GuardIndex":
        statement = select(ModifierRow.target_node_id, ModifierRow.target_key, ModifierRow.source_kind).where(
            ModifierRow.source_kind.in_(GUARD_SOURCES),
            ModifierRow.start_epoch <= epoch,
            or_(ModifierRow.end_epoch.is_(None), ModifierRow.end_epoch >= epoch),
        )
        pins: set[tuple[int, str]] = set()
        suppressions: set[tuple[int, str]] = set()
        for node_id, key, source in await session.execute(statement):
            (pins if source is ModifierSource.PIN else suppressions).add((node_id, key))
        return cls(frozenset(pins), frozenset(suppressions))


CONSERVED_KEYS = frozenset({"population", "followers", "size"})


@dataclass(frozen=True)
class GuardState:
    index: GuardIndex
    writers: frozenset[str]
    phase: str = ""
    flows: Counter[tuple[str, str, int]] | None = None

    def blocks(self, node_id: int, key: str) -> bool:
        if (node_id, key) in self.index.pins:
            return True
        return any((node_id, suppression_key(writer)) in self.index.suppressions for writer in self.writers)


ACTIVE_GUARD: ContextVar[GuardState | None] = ContextVar("active_guard", default=None)


def blocked(node_id: int, key: str) -> bool:
    state = ACTIVE_GUARD.get()
    return state is not None and state.blocks(node_id, key)


def record_flow(node_id: int, key: str, delta: int) -> None:
    state = ACTIVE_GUARD.get()
    if state is not None and state.flows is not None and key in CONSERVED_KEYS and delta:
        state.flows[(state.phase, key, node_id)] += delta


@contextmanager
def guarded(state: GuardState) -> Iterator[None]:
    token = ACTIVE_GUARD.set(state)
    try:
        yield
    finally:
        ACTIVE_GUARD.reset(token)


async def run_guarded(phase: Phase, ctx: TickContext) -> None:
    state = GuardState(await GuardIndex.load(ctx.session, ctx.epoch), mechanic_keys_for_phase(phase.name), phase.name, ctx.environment.stats.flows)
    with guarded(state):
        await phase.run(ctx)
