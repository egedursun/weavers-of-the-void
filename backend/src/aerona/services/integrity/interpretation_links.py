from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.mind import SkillKind
from aerona.rules.registry import Rules


async def skilled(session: AsyncSession, row: InterpretationRow) -> bool:
    if row.interpreter_node_id is None:
        return True
    tongues = [tongue for tongue in (row.first_language_id, row.second_language_id) if tongue is not None]
    floor = Rules().interpreters.interpreter_skill
    mine = (SkillRow.holder_node_id == row.interpreter_node_id, SkillRow.skill == SkillKind.LANGUAGES, SkillRow.level >= floor)
    known = await session.scalars(select(SkillRow).where(*mine))
    subjects = {skill.subject_node_id for skill in known}
    return None in subjects or all(tongue in subjects for tongue in tongues)


async def unskilled_readers(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(InterpretationRow).order_by(InterpretationRow.id))
    return [row.id for row in rows if row.first_party_id == row.second_party_id or not await skilled(session, row)]


async def unseat_reader(session: AsyncSession, key: int) -> None:
    row = await session.get(InterpretationRow, key)
    if row is None:
        return
    if row.first_party_id == row.second_party_id:
        await session.delete(row)
    else:
        row.interpreter_node_id = None
