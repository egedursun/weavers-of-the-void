from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.queries import spoken_language
from aerona.language.succession import local_language
from aerona.rules.registry import Rules

SPEAKING_COMMUNITIES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION, EntityType.CULT)


async def canon_spoken_language(session: AsyncSession, entity_id: int | None) -> EntityRow | None:
    if entity_id is None:
        return None
    language = await spoken_language(session, entity_id)
    return language if language is not None and language.status is EntityStatus.CANON else None


async def community_language_at(session: AsyncSession, location_id: int) -> EntityRow | None:
    statement = (
        select(EntityRow)
        .where(
            (EntityRow.location_id == location_id) | (EntityRow.id == location_id),
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(SPEAKING_COMMUNITIES),
        )
        .order_by(EntityRow.id)
    )
    for community in await session.scalars(statement):
        language = await canon_spoken_language(session, community.id)
        if language is not None:
            return language
    return None


async def local_language_of(session: AsyncSession, rules: Rules, record: EntityRow) -> EntityRow | None:
    spoken = await canon_spoken_language(session, record.id)
    maker = await canon_spoken_language(session, record.maker_entity_id)
    chain: list[EntityRow | None] = []
    if spoken is None and maker is None:
        location_id = record.location_id
        for _ in range(rules.language.local_language_depth):
            if location_id is None:
                break
            found = await community_language_at(session, location_id)
            chain.append(found)
            if found is not None:
                break
            parent = await session.get(EntityRow, location_id)
            location_id = parent.location_id if parent is not None else None
    chosen = local_language(
        spoken.id if spoken is not None else None,
        maker.id if maker is not None else None,
        [item.id if item is not None else None for item in chain],
        rules,
    )
    if chosen is None:
        return None
    for candidate in (spoken, maker, *chain):
        if candidate is not None and candidate.id == chosen:
            return candidate
    return None
