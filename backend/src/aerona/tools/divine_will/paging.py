import json
from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from contextlib import aclosing
from datetime import date, datetime
from enum import Enum
from typing import Any

from aerona.core.grammar import several
from aerona.llm.token_count import count_tokens
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import PagedInput, WillCall, WillResult, envelope, page_items


def number_text(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def json_text(value: Any) -> str:
    return json.dumps(value.model_dump(mode="json") if hasattr(value, "model_dump") else value, ensure_ascii=False, default=str)


FORMATS: tuple[tuple[type | tuple[type, ...], Callable[[Any], str]], ...] = (
    (bool, lambda value: "yes" if value else "no"),
    (Enum, lambda value: str(value.value)),
    ((datetime, date), lambda value: value.isoformat()),
    (float, number_text),
    ((list, tuple, dict), json_text),
)


def plain(value: Any) -> str:
    if value is None:
        return "none"
    found = next((render for kind, render in FORMATS if isinstance(value, kind)), None)
    if found is not None:
        return found(value)
    return json_text(value) if hasattr(value, "model_dump") else str(value)


def arguments_of(query: PagedInput, page: int) -> dict[str, Any]:
    return {**query.model_dump(mode="json"), "page": page}


async def remembered(call: WillCall, tool: DivineWillToolId, arguments: Mapping[str, Any], total: int) -> str:
    async with call.database.write() as session:
        return await call.remember(session, tool, arguments, total)


def beyond(page: int, last: int) -> str:
    return f"There is no page {page}: this result ends on page {last}."


async def paged(call: WillCall, tool: DivineWillToolId, query: PagedInput, items: Sequence[str], *, head: str = "", empty: str) -> WillResult:
    info, body = page_items(items, lambda item: item, call.rules.divine_will.page_tokens, query.page)
    handle = await remembered(call, tool, arguments_of(query, info.page), info.total)
    past = query.page > info.page and info.total > 0
    shown = 0 if past else len(info.items)
    text = beyond(query.page, info.page) if past else body or empty
    payload = {"total": info.total, "shown": shown, "page": info.page, "next": info.has_next and not past}
    return WillResult(
        text=envelope(
            "\n".join(part for part in (head, text) if part), total=info.total, shown=shown, page=info.page, has_next=bool(payload["next"]), handle=handle
        ),
        handle=handle,
        payload=payload,
    )


async def paged_hits(call: WillCall, tool: DivineWillToolId, query: PagedInput, hits: Sequence[str], *, empty: str) -> WillResult:
    size = call.rules.divine_will.search_page
    pages = max(1, -(-len(hits) // size))
    page = min(max(1, query.page), pages)
    chosen = hits[(page - 1) * size : page * size]
    handle = await remembered(call, tool, arguments_of(query, page), len(hits))
    past = query.page > pages and bool(hits)
    shown = 0 if past else len(chosen)
    has_next = page < pages and not past
    body = beyond(query.page, pages) if past else "\n".join(chosen) or empty
    head = f"{several(len(hits), 'match', 'matches')}, best first." if hits else ""
    text = envelope("\n".join(part for part in (head, body) if part), total=len(hits), shown=shown, page=page, has_next=has_next, handle=handle)
    return WillResult(text=text, handle=handle, payload={"total": len(hits), "shown": shown, "page": page, "next": has_next})


async def paged_stream(
    call: WillCall, tool: DivineWillToolId, query: PagedInput, items: AsyncGenerator[str], total: int, *, head: str = "", empty: str
) -> WillResult:
    budget = call.rules.divine_will.page_tokens
    wanted = max(1, query.page)
    page = 1
    used = 0
    held = 0
    chosen: list[str] = []
    has_next = False
    async with aclosing(items) as stream:
        async for item in stream:
            cost = count_tokens(item)
            if held and used + cost > budget:
                if page == wanted:
                    has_next = True
                    break
                page += 1
                used = 0
                held = 0
            used += cost
            held += 1
            if page == wanted:
                chosen.append(item)
    past = wanted > page and total > 0
    handle = await remembered(call, tool, arguments_of(query, min(wanted, page)), total)
    body = beyond(wanted, page) if past else "\n".join(chosen) or empty
    text = envelope("\n".join(part for part in (head, body) if part), total=total, shown=len(chosen), page=min(wanted, page), has_next=has_next, handle=handle)
    return WillResult(text=text, handle=handle, payload={"total": total, "shown": len(chosen), "page": min(wanted, page), "next": has_next})


def failed(text: str) -> WillResult:
    return WillResult(text=text, is_error=True)
