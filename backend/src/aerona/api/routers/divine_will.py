from collections import defaultdict
from collections.abc import Sequence

from fastapi import APIRouter, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.divine_will import (
    WillActiveView,
    WillCapabilitiesView,
    WillConfirmationView,
    WillCycleAccepted,
    WillCycleAttachment,
    WillCycleRequest,
    WillCycleView,
    WillDecisionRequest,
    WillEventView,
    WillModesView,
    WillModeView,
    WillSessionList,
    WillSessionSummary,
    WillSessionView,
)
from aerona.constants.llm import HAIKU_MODEL_ID
from aerona.core.errors import NotFoundError
from aerona.db.repositories.divine_will import active_session, memory_boundary
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillConfirmationRow, DivineWillCycleRow, DivineWillSessionRow
from aerona.prompts.data.divine_will import MODE_TEXTS
from aerona.services.container import Services
from aerona.services.divine_will.context import events_by_cycle
from aerona.services.divine_will.runtime import DivineWillRuntime
from aerona.tools.divine_will.registry import mode_tools, mode_toolsets

router = APIRouter(prefix="/divine-will", tags=["divine_will"])

CYCLE_PAGE = 20
CYCLE_PAGE_MAX = 500
NO_SESSION = "No such session of the Divine Will."
NO_CYCLE = "No such exchange with the Divine Will."


async def cycle_views(session: AsyncSession, cycles: Sequence[DivineWillCycleRow]) -> list[WillCycleView]:
    ids = [row.id for row in cycles]
    events = await events_by_cycle(session, ids)
    confirmations: dict[int, list[DivineWillConfirmationRow]] = defaultdict(list)
    attachments: dict[int, list[DivineWillAttachmentRow]] = defaultdict(list)
    if ids:
        for row in await session.scalars(
            select(DivineWillConfirmationRow).where(DivineWillConfirmationRow.cycle_id.in_(ids)).order_by(DivineWillConfirmationRow.id)
        ):
            confirmations[row.cycle_id].append(row)
        for found in await session.scalars(
            select(DivineWillAttachmentRow).where(DivineWillAttachmentRow.cycle_id.in_(ids)).order_by(DivineWillAttachmentRow.id)
        ):
            if found.cycle_id is not None:
                attachments[found.cycle_id].append(found)
    return [
        WillCycleView.model_validate(
            {
                **{column: getattr(row, column) for column in WillCycleView.model_fields if hasattr(row, column)},
                "events": [WillEventView.model_validate(event) for event in events[row.id]],
                "confirmations": [WillConfirmationView.model_validate(item) for item in confirmations[row.id]],
                "attachments": [WillCycleAttachment.model_validate(item) for item in attachments[row.id]],
            }
        )
        for row in cycles
    ]


async def summary_of(session: AsyncSession, row: DivineWillSessionRow) -> WillSessionSummary:
    count = await session.scalar(select(func.count()).select_from(DivineWillCycleRow).where(DivineWillCycleRow.session_id == row.id))
    return WillSessionSummary(
        id=row.id,
        title=row.title,
        opened_epoch=row.opened_epoch,
        opened_at=row.opened_at,
        closed_epoch=row.closed_epoch,
        closed_at=row.closed_at,
        cycle_count=int(count or 0),
    )


async def capabilities_view(services: Services) -> WillCapabilitiesView:
    found = await DivineWillRuntime(services).capabilities()
    settings = services.settings
    return WillCapabilitiesView(
        enabled=services.application.model.enabled,
        images=found.images,
        probed=found.probed,
        note=found.note,
        model=HAIKU_MODEL_ID,
        upload_max_files=settings.divine_will_upload_max_files,
        upload_max_mb=settings.divine_will_upload_max_mb,
    )


async def active_view(services: Services, before: int | None, limit: int) -> WillActiveView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        remembered = rules.divine_will.remembered_cycles
        holder = await active_session(session)
        cycles: list[DivineWillCycleRow] = []
        boundary = 1
        has_earlier = False
        summary = None
        if holder is not None:
            statement = select(DivineWillCycleRow).where(DivineWillCycleRow.session_id == holder.id)
            if before is not None:
                statement = statement.where(DivineWillCycleRow.ordinal < before)
            newest = list(await session.scalars(statement.order_by(DivineWillCycleRow.ordinal.desc()).limit(limit + 1)))
            has_earlier = len(newest) > limit
            cycles = list(reversed(newest[:limit]))
            boundary = await memory_boundary(session, holder.id, remembered)
            summary = await summary_of(session, holder)
        views = await cycle_views(session, cycles)
    return WillActiveView(
        session=summary,
        cycles=views,
        memory_boundary=boundary,
        has_earlier=has_earlier,
        remembered_cycles=remembered,
        running_cycle_id=DivineWillRuntime(services).running_cycle_id(),
        capabilities=await capabilities_view(services),
    )


@router.get("/session", response_model=WillActiveView)
async def read_active_session(
    services: ServicesDep, before: int | None = Query(default=None, ge=1), limit: int = Query(default=CYCLE_PAGE, ge=1, le=CYCLE_PAGE_MAX)
) -> WillActiveView:
    return await active_view(services, before, limit)


@router.get("/sessions", response_model=WillSessionList)
async def read_closed_sessions(services: ServicesDep) -> WillSessionList:
    async with reader(services) as session:
        rows = await session.scalars(select(DivineWillSessionRow).where(DivineWillSessionRow.closed_at.is_not(None)).order_by(DivineWillSessionRow.id.desc()))
        return WillSessionList(sessions=[await summary_of(session, row) for row in rows])


@router.get("/sessions/{session_id}", response_model=WillSessionView)
async def read_session(services: ServicesDep, session_id: int = Path(ge=1)) -> WillSessionView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        row = await session.get(DivineWillSessionRow, session_id)
        if row is None:
            raise NotFoundError(NO_SESSION)
        cycles = list(await session.scalars(select(DivineWillCycleRow).where(DivineWillCycleRow.session_id == row.id).order_by(DivineWillCycleRow.ordinal)))
        boundary = await memory_boundary(session, row.id, rules.divine_will.remembered_cycles) if row.closed_at is None else len(cycles) + 1
        return WillSessionView(session=await summary_of(session, row), cycles=await cycle_views(session, cycles), memory_boundary=boundary, has_earlier=False)


@router.post("/cycles", response_model=WillCycleAccepted, status_code=status.HTTP_202_ACCEPTED)
async def start_cycle(services: ServicesDep, body: WillCycleRequest) -> WillCycleAccepted:
    cycle = await DivineWillRuntime(services).submit(body.text, body.mode, body.attachment_ids)
    return WillCycleAccepted(cycle_id=cycle.id, session_id=cycle.session_id, ordinal=cycle.ordinal)


async def one_cycle(services: Services, cycle_id: int) -> WillCycleView:
    async with reader(services) as session:
        row = await session.get(DivineWillCycleRow, cycle_id)
        if row is None:
            raise NotFoundError(NO_CYCLE)
        return (await cycle_views(session, [row]))[0]


@router.get("/cycles/{cycle_id}", response_model=WillCycleView)
async def read_cycle(services: ServicesDep, cycle_id: int = Path(ge=1)) -> WillCycleView:
    return await one_cycle(services, cycle_id)


@router.post("/cycles/{cycle_id}/cancel", response_model=WillCycleView)
async def cancel_cycle(services: ServicesDep, cycle_id: int = Path(ge=1)) -> WillCycleView:
    await DivineWillRuntime(services).cancel(cycle_id)
    return await one_cycle(services, cycle_id)


@router.post("/confirmations/{confirmation_id}", response_model=WillConfirmationView)
async def decide_confirmation(services: ServicesDep, body: WillDecisionRequest, confirmation_id: int = Path(ge=1)) -> WillConfirmationView:
    row = await DivineWillRuntime(services).decide(confirmation_id, body.decision.value)
    return WillConfirmationView.model_validate(row)


@router.post("/session/reset", response_model=WillActiveView)
async def reset_session(services: ServicesDep) -> WillActiveView:
    await DivineWillRuntime(services).reset()
    return await active_view(services, None, CYCLE_PAGE)


@router.get("/modes", response_model=WillModesView)
async def read_modes() -> WillModesView:
    return WillModesView(
        modes=[
            WillModeView(
                mode=mode,
                name=text.name,
                purpose=text.purpose,
                changes_world=text.changes_world,
                toolsets=mode_toolsets(mode),
                tools=[tool.tool_id for tool in mode_tools(mode)],
            )
            for mode, text in MODE_TEXTS.items()
        ]
    )


@router.get("/capabilities", response_model=WillCapabilitiesView)
async def read_capabilities(services: ServicesDep) -> WillCapabilitiesView:
    return await capabilities_view(services)
