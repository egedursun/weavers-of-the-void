import json
from collections.abc import Sequence
from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.core.grammar import several
from aerona.db.repositories.divine_will import remembered_cycle_ids
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillHandleRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.divine_will import ChunkSource
from aerona.llm.token_count import count_tokens
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool, envelope
from aerona.tools.divine_will.paging import beyond, failed, number_text, remembered
from aerona.tools.divine_will.retrieval_ports import LoreHit, LoreSearch, lore_index_of

W = DivineWillToolId
READ = frozenset({Toolset.READ})
QUERY_MAX_LENGTH = 2000
HANDLE_MAX_LENGTH = 64
NOTHING_FOUND = "No passage matches. Try other words, words of the lore language, or a wider set of sources."
NO_QUERY = "Give the words to search for, or the handle of an earlier search."
UNKNOWN_HANDLE = "No search is kept under handle {handle}."
FOREIGN_HANDLE = "Handle {handle} belongs to {tool}, not to this search."
BEYOND_MEMORY = "Handle {handle} belongs to an exchange beyond memory. Search again."
FOUND = "{count}, best first."


class SearchLoreInput(PagedInput):
    query: str = Field(default="", max_length=QUERY_MAX_LENGTH)
    sources: list[ChunkSource] = Field(default_factory=list)
    handle: str = Field(default="", max_length=HANDLE_MAX_LENGTH)


async def window_attachments(call: WillCall) -> frozenset[int]:
    async with call.database.read() as session:
        window = await remembered_cycle_ids(session, call.session_id, call.rules.divine_will.remembered_cycles)
        if not window:
            return frozenset()
        found = await session.scalars(select(DivineWillAttachmentRow.id).where(DivineWillAttachmentRow.cycle_id.in_(sorted(window))))
        return frozenset(found)


async def restored(call: WillCall, tool: DivineWillToolId, handle: str) -> dict[str, Any] | WillResult:
    async with call.database.read() as session:
        row = await session.get(DivineWillHandleRow, handle)
        if row is None:
            return failed(UNKNOWN_HANDLE.format(handle=handle))
        if row.tool != tool.value:
            return failed(FOREIGN_HANDLE.format(handle=handle, tool=row.tool))
        if row.cycle_id not in await remembered_cycle_ids(session, call.session_id, call.rules.divine_will.remembered_cycles):
            return failed(BEYOND_MEMORY.format(handle=handle))
        return dict(row.query)


async def node_names(call: WillCall, hits: Sequence[LoreHit]) -> dict[int, str]:
    wanted = sorted({hit.node_id for hit in hits if hit.node_id is not None})
    if not wanted:
        return {}
    async with call.database.read() as session:
        return {node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(wanted)))}


def hit_block(rank: int, hit: LoreHit, names: dict[int, str]) -> str:
    head: dict[str, Any] = {
        "rank": rank,
        "source": hit.source.value,
        "record": hit.record,
        "part": f"{hit.ordinal + 1} of {hit.parts}",
        "node_id": hit.node_id,
        "node": names.get(hit.node_id) if hit.node_id is not None else None,
        "word_rank": hit.lexical_rank,
        "meaning": number_text(hit.similarity) if hit.similarity is not None else None,
    }
    if hit.cycle_id is not None:
        head["exchange"] = hit.cycle_id
    return f"{json.dumps(head, ensure_ascii=False)}\n{hit.text}\n"


def page_bounds(blocks: Sequence[str], per_page: int, budget: int, wanted: int) -> tuple[int, int, int, bool]:
    start = 0
    page = 0
    while start < len(blocks):
        page += 1
        end = start
        used = 0
        while end < len(blocks) and end - start < per_page:
            cost = count_tokens(blocks[end])
            if end > start and used + cost > budget:
                break
            used += cost
            end += 1
        if page == wanted or end >= len(blocks):
            return page, start, end, end < len(blocks)
        start = end
    return 1, 0, 0, False


def reach_of(call: WillCall, page: int) -> int:
    return max(1, page) * call.rules.divine_will.search_page


async def found_page(call: WillCall, tool: DivineWillToolId, arguments: dict[str, Any], page: int, outcome: LoreSearch) -> WillResult:
    names = await node_names(call, outcome.hits)
    blocks = [hit_block(rank, hit, names) for rank, hit in enumerate(outcome.hits, start=1)]
    rules = call.rules.divine_will
    shown_page, start, end, has_next = page_bounds(blocks, rules.search_page, rules.page_tokens, max(1, page))
    total = max(outcome.total, len(blocks))
    has_next = has_next or (bool(blocks) and end >= len(blocks) and total > len(blocks))
    handle = await remembered(call, tool, {**arguments, "page": shown_page}, total) if total else ""
    past = page > shown_page and total > 0
    chosen = [] if past else blocks[start:end]
    head = [FOUND.format(count=several(total, "passage", "passages"))] if total else []
    if outcome.note:
        head.append(outcome.note)
    body = beyond(page, shown_page) if past else "\n".join(chosen) or NOTHING_FOUND
    text = envelope("\n".join([*head, body]), total=total, shown=len(chosen), page=shown_page, has_next=has_next and not past, handle=handle)
    payload = {"total": total, "shown": len(chosen), "page": shown_page, "next": has_next and not past, "semantic": outcome.semantic}
    return WillResult(text=text, handle=handle, payload=payload)


async def search_lore(call: WillCall, query: SearchLoreInput) -> WillResult:
    arguments: dict[str, Any] = {"query": query.query.strip(), "sources": [source.value for source in query.sources]}
    if query.handle:
        found = await restored(call, W.SEARCH_LORE, query.handle)
        if isinstance(found, WillResult):
            return found
        arguments = {"query": str(found.get("query", "")), "sources": [str(value) for value in found.get("sources", [])]}
    if not arguments["query"]:
        return failed(NO_QUERY)
    sources = frozenset(ChunkSource(value) for value in arguments["sources"]) or None
    outcome = await lore_index_of(call).search(
        arguments["query"], sources=sources, attachments=await window_attachments(call), reach=reach_of(call, query.page)
    )
    return await found_page(call, W.SEARCH_LORE, arguments, query.page, outcome)


def tools() -> list[WillTool[Any]]:
    return [WillTool(W.SEARCH_LORE, READ, SearchLoreInput, search_lore)]
