from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from aerona.db.tables.cosmos import AppliedFixupRow

BORN_CURRENT = "universe.born_current"
MARKER_PREFIXES = (
    "history_repairs",
    "divine_will_index_mark",
    "cosmic_wounds.remains.",
    "cosmography.scale_ladder",
    "structures.typed_backfill",
    "works.founded_in_age",
    "homeland_body.",
    "flora.world_life.",
    "world_make.",
    "securities.company.",
    "restoration.claim.",
    "municipal_services.water.",
    "municipal_services.post.",
    "land_use_rules.planned.",
    "state_enterprises.order.",
    "protected_areas.reserve.",
    "protected_areas.grove.",
    "chronicle.told.",
    "chronicle.renamed.",
)


class UnknownMarkerError(ValueError):
    pass


def marker_key(key: str) -> str:
    if not key.startswith(MARKER_PREFIXES):
        raise UnknownMarkerError(key)
    return key


async def born_current(session: AsyncSession) -> bool:
    return await session.get(AppliedFixupRow, BORN_CURRENT) is not None


async def fixup_due(session: AsyncSession, key: str) -> bool:
    if await session.get(AppliedFixupRow, key) is not None:
        return False
    return not await born_current(session)


async def marker(session: AsyncSession, key: str) -> AppliedFixupRow | None:
    return await session.get(AppliedFixupRow, marker_key(key))


async def marked(session: AsyncSession, prefix: str) -> set[str]:
    return set(await session.scalars(select(AppliedFixupRow.key).where(AppliedFixupRow.key.like(f"{marker_key(prefix)}%"))))


async def settle(session: AsyncSession, key: str, result: dict[str, Any]) -> None:
    if await session.get(AppliedFixupRow, key) is None:
        session.add(AppliedFixupRow(key=key, result=result))


async def unmark(session: AsyncSession, prefix: str) -> None:
    await session.execute(delete(AppliedFixupRow).where(AppliedFixupRow.key.like(f"{marker_key(prefix)}%")))


async def mark_born_current(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with AsyncSession(engine) as session:
            await settle(session, BORN_CURRENT, {})
            await session.commit()
    finally:
        await engine.dispose()
