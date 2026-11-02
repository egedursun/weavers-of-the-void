from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import EntityLineContext
from aerona.prompts.contexts.common import EntityLineItem


def status_label(entity: EntityRow) -> str | None:
    return None if entity.status is EntityStatus.CANON else entity.status.value


def line_item(entity: EntityRow, location: str | None = None) -> EntityLineItem:
    return EntityLineItem(
        id=entity.id,
        name=entity.name,
        type_label=ENTITY_TYPES[entity.entity_type].label,
        subtype=entity.subtype,
        power_level=entity.power_level,
        location=location,
        status_label=status_label(entity),
    )


async def location_names(session: AsyncSession, entities: Sequence[EntityRow]) -> dict[int, str]:
    ids = {entity.location_id for entity in entities if entity.location_id is not None}
    if not ids:
        return {}
    rows = await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_(ids)))
    return {entity_id: name for entity_id, name in rows}


async def line_items(session: AsyncSession, entities: Sequence[EntityRow], with_location: bool = True) -> list[EntityLineItem]:
    names = await location_names(session, entities) if with_location else {}
    return [line_item(entity, names.get(entity.location_id) if entity.location_id is not None else None) for entity in entities]


async def entity_line_text(session: AsyncSession, entity: EntityRow, with_location: bool = True) -> str:
    items = await line_items(session, [entity], with_location)
    return render(PromptId.ENTITY_LINE, EntityLineContext(entity=items[0], with_location=with_location))
