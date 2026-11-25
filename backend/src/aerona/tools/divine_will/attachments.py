import json
from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.db.repositories.divine_will import remembered_cycle_ids
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillCycleRow
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus, ChunkSource
from aerona.media.store import read_all
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool, envelope, page_text
from aerona.tools.divine_will.paging import arguments_of, beyond, failed, paged, remembered
from aerona.tools.divine_will.retrieval import HANDLE_MAX_LENGTH, NO_QUERY, QUERY_MAX_LENGTH, found_page, restored, window_attachments
from aerona.tools.divine_will.retrieval_ports import attachment_store_of, lore_index_of

W = DivineWillToolId
ATTACHMENTS = frozenset({Toolset.ATTACHMENTS})
NONE_ATTACHED = "No file is attached in the exchanges within memory."
NOT_ATTACHED = "No file {attachment_id} is attached in the exchanges within memory."
IMAGE_SEEN = "Attachment {attachment_id} is an image ({name}); you were shown it with the exchange it came with. It has no text to read."
IMAGE_UNSEEN = "Attachment {attachment_id} is an image ({name}) that you were not able to see; tell the player so. It has no text to read."
UNREADABLE = "Attachment {attachment_id} ({name}) could not be turned into text: {note}"
NOT_CONVERTED = "Attachment {attachment_id} ({name}) has not been turned into text yet."
MISSING_TEXT = "The text of attachment {attachment_id} ({name}) is missing from the media store."
EMPTY_TEXT = "Attachment {attachment_id} ({name}) holds no text."
READABLE = frozenset({AttachmentStatus.CONVERTED, AttachmentStatus.INDEXED})


class AttachmentReadInput(PagedInput):
    attachment_id: int = Field(ge=1)


class AttachmentSearchInput(PagedInput):
    query: str = Field(default="", max_length=QUERY_MAX_LENGTH)
    handle: str = Field(default="", max_length=HANDLE_MAX_LENGTH)


def attachment_item(row: DivineWillAttachmentRow, exchange: int | None) -> str:
    return json.dumps(
        {
            "attachment_id": row.id,
            "name": row.filename,
            "kind": row.kind.value,
            "type": row.mime,
            "size_bytes": row.size,
            "exchange": exchange,
            "status": row.status.value,
            "shown_as_image": row.seen_by_model,
            "note": row.note or None,
        },
        ensure_ascii=False,
    )


async def remembered_attachments(call: WillCall) -> list[tuple[DivineWillAttachmentRow, int | None]]:
    async with call.database.read() as session:
        window = await remembered_cycle_ids(session, call.session_id, call.rules.divine_will.remembered_cycles)
        if not window:
            return []
        rows = await session.execute(
            select(DivineWillAttachmentRow, DivineWillCycleRow.ordinal)
            .join(DivineWillCycleRow, DivineWillCycleRow.id == DivineWillAttachmentRow.cycle_id)
            .where(DivineWillAttachmentRow.cycle_id.in_(sorted(window)))
            .order_by(DivineWillCycleRow.ordinal, DivineWillAttachmentRow.id)
        )
        return [(row, ordinal) for row, ordinal in rows]


async def attachment_list(call: WillCall, query: PagedInput) -> WillResult:
    items = [attachment_item(row, ordinal) for row, ordinal in await remembered_attachments(call)]
    return await paged(call, W.ATTACHMENT_LIST, query, items, empty=NONE_ATTACHED)


async def attachment_text(call: WillCall, row: DivineWillAttachmentRow) -> str | WillResult:
    names = {"attachment_id": row.id, "name": row.filename}
    if row.kind is AttachmentKind.IMAGE:
        return WillResult(text=(IMAGE_SEEN if row.seen_by_model else IMAGE_UNSEEN).format(**names))
    if row.status is AttachmentStatus.UNREADABLE:
        return WillResult(text=UNREADABLE.format(note=row.note, **names))
    if row.status not in READABLE or not row.markdown_key:
        return WillResult(text=NOT_CONVERTED.format(**names))
    data = await read_all(attachment_store_of(call), row.markdown_key)
    if data is None:
        return failed(MISSING_TEXT.format(**names))
    text = data.decode("utf-8", errors="replace").strip()
    return text or WillResult(text=EMPTY_TEXT.format(**names))


async def attachment_read(call: WillCall, query: AttachmentReadInput) -> WillResult:
    found = next((row for row, _ in await remembered_attachments(call) if row.id == query.attachment_id), None)
    if found is None:
        return failed(NOT_ATTACHED.format(attachment_id=query.attachment_id))
    text = await attachment_text(call, found)
    if isinstance(text, WillResult):
        return text
    budget = call.rules.divine_will.page_tokens
    body, page, has_next = page_text(text, budget, query.page)
    total = len(text.split("\n\n"))
    handle = await remembered(call, W.ATTACHMENT_READ, arguments_of(query, page), total)
    past = query.page > page
    shown = beyond(query.page, page) if past else body
    head = f"{found.filename} ({found.mime}), page {page}{', more follows' if has_next and not past else ''}."
    return WillResult(
        text=envelope(f"{head}\n{shown}", total=total, shown=0 if past else len(body.split("\n\n")), page=page, has_next=has_next and not past, handle=handle),
        handle=handle,
        payload={"page": page, "next": has_next and not past},
    )


async def attachment_search(call: WillCall, query: AttachmentSearchInput) -> WillResult:
    text = query.query.strip()
    if query.handle:
        found = await restored(call, W.ATTACHMENT_SEARCH, query.handle)
        if isinstance(found, WillResult):
            return found
        text = str(found.get("query", ""))
    if not text:
        return failed(NO_QUERY)
    allowed = await window_attachments(call)
    outcome = await lore_index_of(call).search(text, sources=frozenset({ChunkSource.ATTACHMENT}), attachments=allowed)
    return await found_page(call, W.ATTACHMENT_SEARCH, {"query": text}, query.page, outcome)


def tools() -> list[WillTool[Any]]:
    return [
        WillTool(W.ATTACHMENT_LIST, ATTACHMENTS, PagedInput, attachment_list),
        WillTool(W.ATTACHMENT_READ, ATTACHMENTS, AttachmentReadInput, attachment_read),
        WillTool(W.ATTACHMENT_SEARCH, ATTACHMENTS, AttachmentSearchInput, attachment_search),
    ]
