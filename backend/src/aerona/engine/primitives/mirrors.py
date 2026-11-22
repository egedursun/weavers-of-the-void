from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import AppliedFixupRow


async def first_sight(session: AsyncSession, family: str, source_id: int) -> bool:
    key = f"{family}.{source_id}"
    if await session.get(AppliedFixupRow, key) is not None:
        return False
    session.add(AppliedFixupRow(key=key, result={}))
    return True


async def close_legacy(session: AsyncSession, key: str, result: dict[str, int]) -> None:
    if await session.get(AppliedFixupRow, key) is None:
        session.add(AppliedFixupRow(key=key, result=result))
