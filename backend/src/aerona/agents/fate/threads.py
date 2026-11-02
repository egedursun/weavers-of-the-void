from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LegendaryQuestRow, ThreadLinkRow, ThreadRow
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class ThreadState:
    thread: ThreadRow
    advancers: list[str]
    advance_count: int
    stagnant: int

    @property
    def steps(self) -> int:
        return max(self.thread.progress, self.advance_count)


def closable(rules: Rules, state: ThreadState) -> bool:
    return state.steps > 0 or state.stagnant >= rules.fate.zero_progress_close_epochs


@dataclass(frozen=True)
class ThreadQuota:
    threads: list[ThreadState]
    candidates: list[int]
    min_close: int
    new_max: int
    closable_ids: list[int]


async def thread_states(session: AsyncSession, rules: Rules, epoch: int) -> list[ThreadState]:
    great = select(LegendaryQuestRow.thread_id)
    threads = list(await session.scalars(select(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN, ThreadRow.id.not_in(great)).order_by(ThreadRow.id)))
    if not threads:
        return []
    rows = await session.execute(
        select(ThreadLinkRow.thread_id, ThreadLinkRow.epoch, EntityRow.name)
        .join(EntityRow, EntityRow.id == ThreadLinkRow.entity_id)
        .where(ThreadLinkRow.thread_id.in_([thread.id for thread in threads]), ThreadLinkRow.role == ThreadLinkRole.ADVANCED)
        .order_by(ThreadLinkRow.epoch)
    )
    advancers: dict[int, list[str]] = defaultdict(list)
    last: dict[int, int] = {}
    for thread_id, link_epoch, name in rows:
        advancers[thread_id].append(name)
        last[thread_id] = max(last.get(thread_id, 0), link_epoch)
    shown = rules.fate.thread_recent_advancers
    states = [
        ThreadState(
            thread=thread,
            advancers=advancers[thread.id][-shown:] if shown else [],
            advance_count=len(advancers[thread.id]),
            stagnant=epoch - last.get(thread.id, thread.epoch),
        )
        for thread in threads
    ]
    return sorted(states, key=lambda state: (-state.stagnant, state.thread.id))


def quota(rules: Rules, states: list[ThreadState]) -> ThreadQuota:
    fate = rules.fate
    open_to_close = [state for state in states if closable(rules, state)]
    due = [state for state in open_to_close if state.stagnant >= fate.stale_thread_epochs or state.steps >= fate.long_thread_steps]
    due.sort(key=lambda state: (-state.steps, -state.stagnant, state.thread.id))
    candidates = [state.thread.id for state in due][: fate.closure_candidates_shown]
    count = len(states)
    min_close = min(fate.forced_close_cap, len(open_to_close), max(1 if candidates else 0, count - fate.open_thread_cap + 2))
    new_max = max(min(1, fate.new_thread_cap), min(fate.new_thread_cap, fate.open_thread_cap - count + min_close))
    return ThreadQuota(states, candidates, min_close, new_max, [state.thread.id for state in open_to_close])


async def thread_closable(session: AsyncSession, rules: Rules, thread: ThreadRow, epoch: int) -> bool:
    links = list(await session.scalars(select(ThreadLinkRow.epoch).where(ThreadLinkRow.thread_id == thread.id, ThreadLinkRow.role == ThreadLinkRole.ADVANCED)))
    stagnant = epoch - max(links, default=thread.epoch)
    return closable(rules, ThreadState(thread=thread, advancers=[], advance_count=len(links), stagnant=stagnant))


async def single_world_links(session: AsyncSession, entity_ids: list[int]) -> list[int]:
    wanted = list(dict.fromkeys(entity_ids))
    if not wanted:
        return []
    worlds = dict((row[0], row[1]) for row in await session.execute(select(EntityRow.id, EntityRow.world_id).where(EntityRow.id.in_(wanted))))
    counts = Counter(worlds[entity_id] for entity_id in wanted if entity_id in worlds)
    if len(counts) < 2:
        return wanted
    order = [worlds[entity_id] for entity_id in wanted if entity_id in worlds]
    main = max(counts, key=lambda world_id: (counts[world_id], -order.index(world_id)))
    kept = [entity_id for entity_id in wanted if worlds.get(entity_id) == main]
    others = [entity_id for entity_id in wanted if entity_id in worlds and worlds[entity_id] != main]
    if not others:
        return kept
    touching = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.state == BondState.ACTIVE,
            or_(
                and_(BondRow.source_node_id.in_(others), BondRow.target_node_id.in_(kept)),
                and_(BondRow.source_node_id.in_(kept), BondRow.target_node_id.in_(others)),
            ),
        )
    )
    linked = {node for pair in touching for node in pair}
    return [entity_id for entity_id in wanted if worlds.get(entity_id) == main or entity_id in linked]
