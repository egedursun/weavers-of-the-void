from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import ModifierRow
from aerona.db.write_guard import WRITE_GUARD
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import current_category
from aerona.engine.interconnect.registry import mechanic_keys_for_phase, suppression_key
from aerona.engine.phase import Phase
from aerona.engine.primitives.modifiers import GUARD_SOURCES, ModifierIndex, live_modifiers


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
    flows: Counter[tuple[str, str, int, str]] | None = None
    only: int | None = None

    def blocks(self, node_id: int, key: str) -> bool:
        if self.only is not None and node_id != self.only:
            return True
        if (node_id, key) in self.index.pins:
            return True
        return any((node_id, suppression_key(writer)) in self.index.suppressions for writer in self.writers)


ACTIVE_GUARD: ContextVar[GuardState | None] = ContextVar("active_guard", default=None)
IO_RECORDER: ContextVar[dict[str, set[tuple[str, str]]] | None] = ContextVar("io_recorder", default=None)
READ_MODE = "read"
WRITE_MODE = "write"


def observed(entity_type: str, key: str, mode: str) -> None:
    recorder = IO_RECORDER.get()
    state = ACTIVE_GUARD.get()
    if recorder is None or state is None:
        return
    recorder.setdefault(state.phase, set()).add((mode, f"{entity_type}.{key}"))


@contextmanager
def recording(recorder: dict[str, set[tuple[str, str]]]) -> Iterator[None]:
    token = IO_RECORDER.set(recorder)
    try:
        yield
    finally:
        IO_RECORDER.reset(token)


def blocked(node_id: int, key: str) -> bool:
    state = ACTIVE_GUARD.get()
    return state is not None and state.blocks(node_id, key)


def record_flow(node_id: int, key: str, delta: int) -> None:
    state = ACTIVE_GUARD.get()
    if state is not None and state.flows is not None and key in CONSERVED_KEYS and delta:
        state.flows[(state.phase, key, node_id, current_category(state.phase).value)] += delta


@contextmanager
def guarded(state: GuardState) -> Iterator[None]:
    token = ACTIVE_GUARD.set(state)
    write_token = WRITE_GUARD.set(state.blocks)
    try:
        yield
    finally:
        WRITE_GUARD.reset(write_token)
        ACTIVE_GUARD.reset(token)


async def run_guarded(phase: Phase, ctx: TickContext, *, only: int | None = None) -> None:
    state = GuardState(await GuardIndex.load(ctx.session, ctx.epoch), mechanic_keys_for_phase(phase.name), phase.name, ctx.environment.stats.flows, only)
    index = await ModifierIndex.load(ctx.session, ctx.epoch)
    with guarded(state), live_modifiers(index, ctx.epoch, ctx.rules):
        await phase.run(ctx)
