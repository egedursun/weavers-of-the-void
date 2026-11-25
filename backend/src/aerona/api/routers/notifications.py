from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.api.schemas.records import NotificationRecord
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.services.notifications import CategoryCount, CategoryInfo, linked_nodes, list_notifications, mark_read, update_settings

router = APIRouter(tags=["notifications"])

TITLE_MAX_LENGTH = 200
BODY_MAX_LENGTH = 4000


class NotificationList(ApiModel):
    unread: int
    counts: list[CategoryCount]
    settings: dict[NotificationCategory, bool]
    categories: list[CategoryInfo]
    items: list[NotificationRecord]


class MarkReadRequest(RequestModel):
    ids: list[int] = Field(default_factory=list)
    every: bool = False
    category: NotificationCategory | None = None
    unread: bool = False


class MarkReadResult(ApiModel):
    changed: int


class NoteRequest(RequestModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    body: str | None = Field(default=None, max_length=BODY_MAX_LENGTH)
    target_node_id: int | None = Field(default=None, ge=1)


class NotificationQuery(BaseModel):
    unread_only: bool = False
    category: NotificationCategory | None = None
    limit: int | None = Field(default=None, ge=1)
    before: int | None = Field(default=None, ge=1)
    exclude: list[NotificationCategory] = Field(default_factory=list)


@router.get("/notifications", response_model=NotificationList)
async def notifications(services: ServicesDep, query: Annotated[NotificationQuery, Query()]) -> NotificationList:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        size = min(query.limit or rules.server.notification_page_size, rules.server.notification_page_max)
        page = await list_notifications(
            session, limit=size, unread_only=query.unread_only, category=query.category, before_id=query.before, exclude=query.exclude
        )
        links = await linked_nodes(session, page.items, rules)
    return NotificationList(
        unread=page.unread,
        counts=page.counts,
        settings=page.settings,
        categories=page.categories,
        items=[
            NotificationRecord.model_validate(row).model_copy(update={"entity_ids": links.get(row.id, []), "is_read": page.read(row)}) for row in page.items
        ],
    )


@router.post("/notifications/read", response_model=MarkReadResult)
async def read_notifications(request: MarkReadRequest, services: ServicesDep) -> MarkReadResult:
    async with services.database.write() as session:
        changed = await mark_read(session, ids=request.ids, every=request.every, category=request.category, unread=request.unread)
    return MarkReadResult(changed=changed)


@router.put("/notifications/settings", response_model=dict[NotificationCategory, bool])
async def notification_settings(request: dict[NotificationCategory, bool], services: ServicesDep) -> dict[NotificationCategory, bool]:
    async with services.database.write() as session:
        return await update_settings(session, request)


@router.post("/notifications", response_model=NotificationRecord)
async def add_note(request: NoteRequest, services: ServicesDep) -> NotificationRecord:
    async with services.database.write() as session:
        rules = await world_rules(services, session)
        row = await services.application.notifier.creator_note(session, rules, request.title, request.body, request.target_node_id)
        return NotificationRecord.model_validate(row)


@router.post("/notifications/from-chronicle/{chronicle_id}", response_model=NotificationRecord)
async def pin_chronicle_line(chronicle_id: int, services: ServicesDep) -> NotificationRecord:
    async with services.database.write() as session:
        rules = await world_rules(services, session)
        row = await services.application.notifier.pin_chronicle(session, rules, chronicle_id)
        return NotificationRecord.model_validate(row)
