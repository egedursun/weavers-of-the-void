import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.divine_will import FINISHED_CYCLES, cycle_events, window_cycles
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillCycleRow, DivineWillEventRow
from aerona.domain.enums.divine_will import AttachmentKind, CycleEventKind, DivineWillMode
from aerona.domain.enums.world import LoreLanguage
from aerona.llm.content import ImagePart
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.divine_will import (
    DivineWillSystemContext,
    DivineWillUserContext,
    RememberedExchange,
    WillAttachmentLine,
    WillModeLine,
    WillToolStep,
    WillTraceLine,
)
from aerona.prompts.data.divine_will import MODE_TEXTS
from aerona.rules.registry import Rules
from aerona.services.divine_will.language import player_language

E = CycleEventKind
UNANSWERED = "no result came back"
KIND_NAMES = {AttachmentKind.IMAGE: "picture", AttachmentKind.DOCUMENT: "document"}


@dataclass(frozen=True)
class Speaker:
    creator_id: int
    creator_name: str
    world_name: str
    lore_language: LoreLanguage


def arguments_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload.get("arguments", {}), ensure_ascii=False, sort_keys=True, default=str)


def steps_of(events: Sequence[DivineWillEventRow]) -> list[WillToolStep]:
    calls: dict[str, DivineWillEventRow] = {}
    steps: list[WillToolStep] = []
    for event in events:
        if event.kind is E.TOOL_CALL:
            calls[str(event.payload.get("call_id", ""))] = event
        elif event.kind is E.TOOL_RESULT:
            call = calls.pop(str(event.payload.get("call_id", "")), None)
            steps.append(
                WillToolStep(
                    tool=event.tool,
                    arguments=arguments_text(call.payload) if call is not None else "",
                    outcome=str(event.payload.get("outcome", "")),
                    handle=event.handle,
                    failed=bool(event.payload.get("is_error")),
                )
            )
    steps.extend(WillToolStep(tool=call.tool, arguments=arguments_text(call.payload), outcome=UNANSWERED, failed=True) for call in calls.values())
    return steps


def trace_text(event: DivineWillEventRow) -> str:
    payload = event.payload
    if event.kind is E.TOOL_CALL:
        return arguments_text(payload)
    if event.kind is E.CONFIRMATION_REQUEST:
        return json.dumps({key: payload.get(key) for key in ("action_id", "reason", "input")}, ensure_ascii=False, sort_keys=True, default=str)
    if event.kind is E.CONFIRMATION_REPLY:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    if event.kind is E.RETRY:
        return str(payload.get("reason", ""))
    return str(payload.get("text", ""))


def trace_of(events: Sequence[DivineWillEventRow]) -> list[WillTraceLine]:
    return [
        WillTraceLine(kind=event.kind.value, text=trace_text(event), tool=event.tool, handle=event.handle) for event in events if event.kind is not E.PLAYER
    ]


def exchange_of(cycle: DivineWillCycleRow, events: Sequence[DivineWillEventRow]) -> RememberedExchange:
    return RememberedExchange(
        ordinal=cycle.ordinal,
        mode_name=MODE_TEXTS[cycle.mode].name,
        player_text=cycle.player_text,
        final_text=cycle.final_text or cycle.error,
        steps=steps_of(events),
    )


def attachment_line(row: DivineWillAttachmentRow) -> WillAttachmentLine:
    seen = row.seen_by_model or row.kind is not AttachmentKind.IMAGE
    return WillAttachmentLine(attachment_id=row.id, filename=row.filename, kind_name=KIND_NAMES[row.kind], seen=seen, note=row.note)


async def events_by_cycle(session: AsyncSession, cycle_ids: Sequence[int]) -> dict[int, list[DivineWillEventRow]]:
    found: dict[int, list[DivineWillEventRow]] = defaultdict(list)
    if not cycle_ids:
        return found
    rows = await session.scalars(
        select(DivineWillEventRow).where(DivineWillEventRow.cycle_id.in_(cycle_ids)).order_by(DivineWillEventRow.cycle_id, DivineWillEventRow.ordinal)
    )
    for row in rows:
        found[row.cycle_id].append(row)
    return found


async def speaker(session: AsyncSession) -> Speaker:
    repository = CosmosRepository(session)
    cosmos = await repository.require_cosmos()
    creator = await repository.require_creator()
    return Speaker(creator.id, creator.name, cosmos.name, cosmos.lore_language)


def system_prompt(rules: Rules, who: Speaker, mode: DivineWillMode, tools: Sequence[str]) -> str:
    context = DivineWillSystemContext(
        lore_language=who.lore_language,
        rules=rules,
        world_name=who.world_name,
        creator_name=who.creator_name,
        mode_name=MODE_TEXTS[mode].name,
        modes=[WillModeLine(value=item.value, name=text.name, purpose=text.purpose, current=item is mode) for item, text in MODE_TEXTS.items()],
        tools=list(tools),
    )
    return f"{render(PromptId.DIVINE_WILL_SYSTEM, context)}\n\n{render(MODE_TEXTS[mode].prompt_id, context)}"


async def forgotten_count(session: AsyncSession, cycle: DivineWillCycleRow, kept: int) -> int:
    before = await session.scalar(
        select(func.count())
        .select_from(DivineWillCycleRow)
        .where(DivineWillCycleRow.session_id == cycle.session_id, DivineWillCycleRow.ordinal < cycle.ordinal, DivineWillCycleRow.status.in_(FINISHED_CYCLES))
    )
    return max(0, int(before or 0) - kept)


async def user_prompt(session: AsyncSession, rules: Rules, who: Speaker, cycle: DivineWillCycleRow, attachments: Sequence[DivineWillAttachmentRow]) -> str:
    window = await window_cycles(session, cycle.session_id, rules.divine_will.remembered_cycles, before_ordinal=cycle.ordinal)
    history = await events_by_cycle(session, [row.id for row in window])
    context = DivineWillUserContext(
        lore_language=who.lore_language,
        rules=rules,
        mode_name=MODE_TEXTS[cycle.mode].name,
        player_text=cycle.player_text,
        player_language=player_language(cycle.player_text, [row.player_text for row in window]),
        forgotten=await forgotten_count(session, cycle, len(window)),
        remembered=[exchange_of(row, history[row.id]) for row in window],
        attachments=[attachment_line(row) for row in attachments],
        trace=trace_of(await cycle_events(session, cycle.id)),
    )
    return render(PromptId.DIVINE_WILL_USER, context)


def pictures(found: Sequence[tuple[DivineWillAttachmentRow, bytes | None]]) -> list[ImagePart]:
    return [ImagePart(row.mime, data) for row, data in found if data]
