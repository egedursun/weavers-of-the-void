from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.agents.context.scope import Scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import ThreadLine, ThreadLinesContext

PERCENT = 100


@dataclass(frozen=True)
class ThreadFacts:
    thread: ThreadRow
    related: list[int]
    worlds: set[int]
    owners: dict[int, int | None]
    last_advanced: int | None


async def open_threads(scope: Scope) -> list[ThreadFacts]:
    threads = list(await scope.session.scalars(select(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN).order_by(ThreadRow.id)))
    if not threads:
        return []
    ids = [thread.id for thread in threads]
    links = await scope.session.execute(
        select(ThreadLinkRow.thread_id, ThreadLinkRow.entity_id, ThreadLinkRow.role, ThreadLinkRow.epoch, EntityRow.world_id, EntityRow.creator_son_id)
        .join(EntityRow, EntityRow.id == ThreadLinkRow.entity_id)
        .where(ThreadLinkRow.thread_id.in_(ids))
    )
    related: dict[int, list[int]] = defaultdict(list)
    worlds: dict[int, set[int]] = defaultdict(set)
    owners: dict[int, dict[int, int | None]] = defaultdict(dict)
    last: dict[int, int] = {}
    for thread_id, entity_id, role, epoch, world_id, son_id in links:
        if role is ThreadLinkRole.RELATED:
            related[thread_id].append(entity_id)
        else:
            last[thread_id] = max(last.get(thread_id, 0), epoch)
        worlds[thread_id].add(world_id)
        owners[thread_id][entity_id] = son_id
    return [ThreadFacts(thread, related[thread.id], worlds[thread.id], owners[thread.id], last.get(thread.id)) for thread in threads]


def score(scope: Scope, facts: ThreadFacts, son: SonRow) -> float:
    context = scope.rules.context
    owned = sum(1 for owner in facts.owners.values() if owner == son.id)
    stale = scope.epoch - (facts.last_advanced or facts.thread.epoch)
    named = context.thread_name_score if son.name.casefold() in facts.thread.text.casefold() else 0
    progressed = context.thread_progressed_score if facts.thread.progress > 0 else 0
    return owned * context.thread_related_score + named - stale * context.thread_stale_penalty / PERCENT + progressed


def thread_line(scope: Scope, facts: ThreadFacts, with_worlds: bool) -> ThreadLine:
    names = [scope.world_name(world_id) for world_id in sorted(facts.worlds)] if with_worlds else []
    return ThreadLine(
        id=facts.thread.id,
        age=facts.thread.epoch,
        worlds=[name for name in names if name],
        advanced=facts.thread.progress,
        last_age=facts.last_advanced,
        text=facts.thread.text,
        related_ids=facts.related,
    )


async def thread_lines_context(scope: Scope, viewer: SonRow | None = None) -> ThreadLinesContext:
    threads = await open_threads(scope)
    if viewer is None:
        return ThreadLinesContext(threads=[thread_line(scope, facts, scope.multi_world) for facts in threads])
    here = [facts for facts in threads if not facts.worlds or viewer.current_world_id in facts.worlds]
    ranked = sorted(here, key=lambda facts: (-score(scope, facts, viewer), facts.thread.id))
    limit = scope.rules.context.son_threads
    return ThreadLinesContext(
        threads=[thread_line(scope, facts, False) for facts in ranked[:limit]],
        more=max(0, len(ranked) - limit),
        elsewhere=len(threads) - len(here),
    )


async def thread_lines(scope: Scope, viewer: SonRow | None = None) -> str:
    context = await thread_lines_context(scope, viewer)
    return render(PromptId.THREAD_LINES, context) if context.threads or context.elsewhere else ""


async def open_thread_count(scope: Scope) -> int:
    return int(await scope.session.scalar(select(func.count()).select_from(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN)) or 0)
