from collections import Counter
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import cached_property

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.profile_guard import restore_held
from aerona.db.read_memo import memo_of, table_names
from aerona.db.repositories.chronicle import LAST_INCIDENT
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.write_guard import HELD_SCOPE, WRITE_GUARD, HeldScope
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import current_category
from aerona.engine.interconnect.registry import mechanic_keys_for_phase, suppression_key
from aerona.engine.phase import Phase
from aerona.engine.primitives.modifiers import GUARD_SOURCES, ModifierIndex, live_modifiers

MODIFIER_TABLES = table_names((ModifierRow,))


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

    @cached_property
    def guarded_nodes(self) -> frozenset[int]:
        return frozenset(node_id for node_id, _ in self.pins | self.suppressions)


CONSERVED_KEYS = frozenset({"population", "followers", "size"})


@dataclass(frozen=True)
class GuardState:
    index: GuardIndex
    writers: frozenset[str]
    phase: str = ""
    flows: Counter[tuple[str, str, int, str]] | None = None
    only: int | None = None
    moved: Counter[tuple[int, str]] = field(default_factory=Counter)

    @property
    def blocks_nothing(self) -> bool:
        return self.only is None and not self.index.guarded_nodes

    def blocks(self, node_id: int, key: str) -> bool:
        if self.only is not None and node_id != self.only:
            return True
        if node_id not in self.index.guarded_nodes:
            return False
        if (node_id, key) in self.index.pins:
            return True
        return any((node_id, suppression_key(writer)) in self.index.suppressions for writer in self.writers)


ACTIVE_GUARD: ContextVar[GuardState | None] = ContextVar("active_guard", default=None)
HEADCOUNT_KEY = "population"
PhaseHook = Callable[[TickContext, Counter[tuple[int, str]]], Awaitable[None]]
AFTER_PHASE: list[PhaseHook] = []
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
    if state is None or key not in CONSERVED_KEYS or not delta:
        return
    category = current_category(state.phase).value
    if state.flows is not None:
        state.flows[(state.phase, key, node_id, category)] += delta
    if key == HEADCOUNT_KEY:
        state.moved[(node_id, category)] += delta


def absorb_flow(node_id: int, delta: int) -> None:
    state = ACTIVE_GUARD.get()
    if state is None or not delta:
        return
    key = (node_id, current_category(state.phase).value)
    state.moved[key] -= delta
    if not state.moved[key]:
        del state.moved[key]


@contextmanager
def guarded(state: GuardState) -> Iterator[None]:
    token = ACTIVE_GUARD.set(state)
    write_token = WRITE_GUARD.set(state.blocks)
    suppressed = frozenset(node_id for node_id, key in state.index.suppressions if any(key == suppression_key(writer) for writer in state.writers))
    held_token = HELD_SCOPE.set(HeldScope(state.only, suppressed))
    try:
        yield
    finally:
        HELD_SCOPE.reset(held_token)
        WRITE_GUARD.reset(write_token)
        ACTIVE_GUARD.reset(token)


async def phase_indexes(ctx: TickContext) -> tuple[GuardIndex, ModifierIndex]:
    memo = memo_of(ctx.session, "phase_indexes", MODIFIER_TABLES)
    found: tuple[GuardIndex, ModifierIndex] | None = memo.get(ctx.epoch) if memo is not None else None
    if found is None:
        found = (await GuardIndex.load(ctx.session, ctx.epoch), await ModifierIndex.load(ctx.session, ctx.epoch))
        after = memo_of(ctx.session, "phase_indexes", MODIFIER_TABLES)
        if after is not None:
            after[ctx.epoch] = found
    return found


async def run_guarded(phase: Phase, ctx: TickContext, *, only: int | None = None) -> None:
    ctx.session.info.pop(LAST_INCIDENT, None)
    guard_index, index = await phase_indexes(ctx)
    state = GuardState(guard_index, mechanic_keys_for_phase(phase.name), phase.name, ctx.environment.stats.flows, only)
    with guarded(state), live_modifiers(index, ctx.epoch, ctx.rules):
        await phase.run(ctx)
        sync = ctx.session.sync_session
        for modified in list(sync.identity_map._modified):
            if modified not in sync._deleted and not modified.pending:
                found = modified.obj()
                if found is not None:
                    restore_held(found)
        await ctx.session.flush()
    if state.moved:
        for hook in AFTER_PHASE:
            await hook(ctx, state.moved)
