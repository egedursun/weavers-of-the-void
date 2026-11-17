from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.common import ApiModel
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus, UsageBucket, UsageSort
from aerona.services.usage import UsageFilter, UsageReport, usage_calls, usage_report

router = APIRouter(tags=["usage"])


class UsageCall(ApiModel):
    id: int
    epoch: int | None
    job: str
    role: str | None
    model: str
    kind: LlmCallKind
    status: LlmCallStatus
    duration_ms: int
    attempts: int
    turns: int | None
    input_tokens: int
    output_tokens: int
    actions: int | None
    error: str | None
    created_at: datetime


class UsageCallPage(ApiModel):
    items: list[UsageCall]
    total: int
    offset: int
    limit: int


def usage_filter(
    *,
    search: str | None = Query(default=None, max_length=NAME_MAX_LENGTH),
    model: Annotated[list[str] | None, Query()] = None,
    role: Annotated[list[str] | None, Query()] = None,
    step: Annotated[list[str] | None, Query()] = None,
    kind: Annotated[list[LlmCallKind] | None, Query()] = None,
    status: Annotated[list[LlmCallStatus] | None, Query()] = None,
    epoch_from: int | None = Query(default=None, ge=0),
    epoch_to: int | None = Query(default=None, ge=0),
    since: datetime | None = None,
) -> UsageFilter:
    return UsageFilter(
        search=search,
        models=tuple(model or ()),
        roles=tuple(role or ()),
        steps=tuple(step or ()),
        kinds=tuple(kind or ()),
        statuses=tuple(status or ()),
        epoch_from=epoch_from,
        epoch_to=epoch_to,
        since=since,
    )


UsageFilterDep = Annotated[UsageFilter, Depends(usage_filter)]


@router.get("/usage/summary", response_model=UsageReport)
async def read_usage_summary(services: ServicesDep, chosen: UsageFilterDep, bucket: UsageBucket = UsageBucket.EPOCH) -> UsageReport:
    async with services.application.telemetry.sessions() as session:
        return await usage_report(session, chosen, bucket)


@router.get("/usage/calls", response_model=UsageCallPage)
async def read_usage_calls(
    *,
    services: ServicesDep,
    chosen: UsageFilterDep,
    sort: UsageSort = UsageSort.TIME,
    descending: bool = True,
    offset: int = Query(default=0, ge=0),
    limit: int | None = Query(default=None, ge=1),
) -> UsageCallPage:
    server = services.rules.current.server
    size = min(limit or server.usage_page_size, server.usage_page_max)
    async with services.application.telemetry.sessions() as session:
        page = await usage_calls(session, chosen, sort=sort, descending=descending, offset=offset, limit=size)
    return UsageCallPage(items=[UsageCall.model_validate(row) for row in page.rows], total=page.total, offset=offset, limit=size)
