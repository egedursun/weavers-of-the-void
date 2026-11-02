from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import normalize_name
from aerona.db.tables.entities import EntityRow, EntityTagRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.engine.primitives.renames import rename_everywhere
from aerona.engine.primitives.subtypes import normalized_subtype
from aerona.rules.registry import Rules
from aerona.services import names
from aerona.services.narrative import clean_fate_note, clean_lore, mortal_description


@dataclass(frozen=True)
class EntityEdit:
    name: str | None = None
    title: str | None = None
    subtype: str | None = None
    description: str | None = None
    fate_note: str | None = None


def resolved_origin(origin: EntityOrigin, creator_son_id: int | None) -> EntityOrigin:
    if origin is EntityOrigin.SON and creator_son_id is None:
        return EntityOrigin.CREATOR
    return origin


async def resolve_world(session: AsyncSession, *, location_id: int | None, creator_son_id: int | None, maker_entity_id: int | None) -> int | None:
    if location_id is not None:
        location_world: int | None = await session.scalar(select(EntityRow.world_id).where(EntityRow.id == location_id))
        if location_world is not None:
            return location_world
    if creator_son_id is not None:
        son_world: int | None = await session.scalar(select(SonRow.current_world_id).where(SonRow.id == creator_son_id))
        if son_world is not None:
            return son_world
    if maker_entity_id is not None:
        maker_world: int | None = await session.scalar(select(EntityRow.world_id).where(EntityRow.id == maker_entity_id))
        if maker_world is not None:
            return maker_world
    return await CosmosRepository(session).first_world_id()


async def add_tags(session: AsyncSession, entity_id: int, tags: Iterable[str]) -> list[str]:
    repository = EntityRepository(session)
    await repository.require_entity(entity_id)
    return await repository.add_tags(entity_id, tags)


async def remove_tags(session: AsyncSession, entity_id: int, tags: Iterable[str]) -> list[str]:
    await EntityRepository(session).require_entity(entity_id)
    wanted = [cleaned for cleaned in (normalize_name(tag) for tag in tags) if cleaned]
    existing = set(await EntityRepository(session).tags(entity_id))
    removed = [tag for tag in wanted if tag in existing]
    if removed:
        await session.execute(delete(EntityTagRow).where(EntityTagRow.entity_id == entity_id, EntityTagRow.tag.in_(removed)))
    return removed


def validated_description(entity_type: EntityType, text: str) -> str:
    cleaned = clean_lore(text)
    return mortal_description(cleaned) if entity_type is EntityType.MORTAL else cleaned


async def edit_entity(session: AsyncSession, rules: Rules, entity_id: int, edit: EntityEdit) -> EntityRow:
    entity = await EntityRepository(session).require_entity(entity_id)
    if edit.name is not None and edit.name.strip() != entity.name:
        display = await names.validate_new_name(session, rules, edit.name, ignore_node_id=entity.id)
        await rename_everywhere(session, entity.id, display)
        await names.apply_epithet(session, entity)
    if edit.title is not None:
        entity.title = edit.title.strip() or None
    if edit.subtype is not None:
        entity.subtype = await normalized_subtype(session, entity.entity_type, edit.subtype)
    if edit.description is not None:
        entity.description = validated_description(entity.entity_type, edit.description) or entity.description
    if edit.fate_note is not None:
        entity.fate_note = clean_fate_note(edit.fate_note)
    await session.flush()
    return entity
