from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.lore import LexemeRow, lexeme_key


async def known_lexeme(session: AsyncSession, language_id: int, word: str) -> LexemeRow | None:
    found: LexemeRow | None = await session.scalar(
        select(LexemeRow).where(LexemeRow.language_entity_id == language_id, LexemeRow.word_key == lexeme_key(word)).order_by(LexemeRow.id).limit(1)
    )
    return found


async def add_lexeme(session: AsyncSession, row: LexemeRow) -> LexemeRow:
    found = await known_lexeme(session, row.language_entity_id, row.word)
    if found is not None:
        return found
    session.add(row)
    return row
