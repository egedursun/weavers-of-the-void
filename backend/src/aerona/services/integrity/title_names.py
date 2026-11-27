from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.titles import RANK_WORDS, title_name
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.write_guard import held


def old_holder(name: str, rank_word: str) -> str | None:
    prefix = f"the {rank_word} of "
    return name.removeprefix(prefix) if name.startswith(prefix) else None


async def rank_worded_titles(session: AsyncSession) -> list[int]:
    found: list[int] = []
    rows = await session.execute(
        select(EntityRow.id, EntityRow.name, TitleProfileRow.rank).join(TitleProfileRow, TitleProfileRow.title_entity_id == EntityRow.id).order_by(EntityRow.id)
    )
    for entity_id, name, rank in rows:
        if old_holder(name, RANK_WORDS[rank]) is not None and not held(entity_id):
            found.append(entity_id)
    return found


async def rename_by_rank(session: AsyncSession, entity_id: int) -> None:
    entity = await session.get(EntityRow, entity_id)
    profile = await session.get(TitleProfileRow, entity_id)
    if entity is None or profile is None:
        return
    holder = old_holder(entity.name, RANK_WORDS[profile.rank])
    if holder is not None:
        await NameRepository(session).rename(entity_id, title_name(profile.rank, holder))
