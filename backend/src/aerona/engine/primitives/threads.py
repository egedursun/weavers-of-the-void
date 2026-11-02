from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus


async def link_thread(session: AsyncSession, thread_id: int, entity_id: int, role: ThreadLinkRole, epoch: int) -> bool:
    if await session.get(ThreadLinkRow, (thread_id, entity_id, role)) is not None:
        return False
    session.add(ThreadLinkRow(thread_id=thread_id, entity_id=entity_id, role=role, epoch=epoch))
    await session.flush()
    return True


async def open_story(session: AsyncSession, text: str, related_ids: Iterable[int], epoch: int) -> ThreadRow | None:
    if not text:
        return None
    thread = ThreadRow(epoch=epoch, text=text, status=ThreadStatus.OPEN)
    session.add(thread)
    await session.flush()
    wanted = list(dict.fromkeys(related_ids))
    existing = set(await session.scalars(select(EntityRow.id).where(EntityRow.id.in_(wanted)))) if wanted else set()
    for entity_id in wanted:
        if entity_id in existing:
            await link_thread(session, thread.id, entity_id, ThreadLinkRole.RELATED, epoch)
    return thread


async def advance_story(session: AsyncSession, thread: ThreadRow, entity_id: int, epoch: int) -> bool:
    if not await link_thread(session, thread.id, entity_id, ThreadLinkRole.ADVANCED, epoch):
        return False
    if thread.status is ThreadStatus.OPEN:
        thread.progress += 1
    return True


async def story_entities(session: AsyncSession, thread_id: int) -> list[int]:
    return list(await session.scalars(select(ThreadLinkRow.entity_id).where(ThreadLinkRow.thread_id == thread_id).distinct()))


async def close_story(session: AsyncSession, thread: ThreadRow, closing: str | None, epoch: int) -> list[int]:
    thread.status = ThreadStatus.CLOSED
    thread.closing_text = closing
    thread.closed_epoch = epoch
    await session.flush()
    return await story_entities(session, thread.id)
