from collections.abc import Collection
from enum import StrEnum
from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.agent import EntityStateContext, EntityStateKind
from aerona.prompts.tools.results import result
from aerona.tools.framework.errors import RejectionError

STATE_KINDS = {
    EntityStatus.DEAD: EntityStateKind.DEAD,
    EntityStatus.DESTROYED: EntityStateKind.DESTROYED,
    EntityStatus.REJECTED: EntityStateKind.REJECTED,
    EntityStatus.FULFILLED: EntityStateKind.FULFILLED,
}


def label_of(value: StrEnum) -> str:
    return spoken(value)


def fail(template: StrEnum, **values: object) -> NoReturn:
    raise RejectionError(result(template, **values))


def state_reason(entity: EntityRow | None, entity_id: int | None) -> str | None:
    if entity_id is None:
        return render(PromptId.ENTITY_STATE_REASON, EntityStateContext(kind=EntityStateKind.UNSELECTED))
    if entity is None:
        return render(PromptId.ENTITY_STATE_REASON, EntityStateContext(kind=EntityStateKind.MISSING, id=entity_id))
    if entity.status is EntityStatus.CANON:
        return None
    kind = STATE_KINDS.get(entity.status, EntityStateKind.OTHER)
    return render(
        PromptId.ENTITY_STATE_REASON,
        EntityStateContext(kind=kind, id=entity.id, name=entity.name, age=entity.end_epoch, state_label=label_of(entity.status)),
    )


async def require_canon(session: AsyncSession, entity_id: int | None) -> EntityRow:
    entity = await session.get(EntityRow, entity_id) if entity_id is not None else None
    reason = state_reason(entity, entity_id)
    if reason is not None or entity is None:
        raise RejectionError(reason or "")
    return entity


def require_type(entity: EntityRow, types: Collection[EntityType], template: StrEnum, **values: object) -> EntityRow:
    if entity.entity_type not in types:
        fail(template, **values)
    return entity
