from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier

HOLD_REASON = "player.pin"
INCITEMENT_KEY = "incited_by_son_id"
GOLDEN_AGE_KEY = "golden_age"
DEDICATION_KEY = "dedicated_son_id"
ANCHOR_KEY = "anchor_entity_id"


async def is_held(session: AsyncSession, node_id: int, key: str, epoch: int) -> bool:
    found = await session.scalar(
        select(ModifierRow.id)
        .where(
            ModifierRow.target_node_id == node_id,
            ModifierRow.target_key == key,
            ModifierRow.source_kind == ModifierSource.PIN,
            ModifierRow.start_epoch <= epoch,
            or_(ModifierRow.end_epoch.is_(None), ModifierRow.end_epoch >= epoch),
        )
        .limit(1)
    )
    return found is not None


async def held_keys(session: AsyncSession, node_id: int, keys: tuple[str, ...], epoch: int) -> frozenset[str]:
    return frozenset([key for key in keys if await is_held(session, node_id, key, epoch)])


async def set_held(session: AsyncSession, node_id: int, key: str, epoch: int, held: bool) -> bool:
    result = await session.execute(
        delete(ModifierRow).where(ModifierRow.target_node_id == node_id, ModifierRow.target_key == key, ModifierRow.source_kind == ModifierSource.PIN)
    )
    released = bool(getattr(result, "rowcount", 0))
    if held:
        await add_modifier(session, ModifierDraft(node_id, key, ModifierOp.ADD, 0, ModifierSource.PIN, HOLD_REASON, start_epoch=epoch))
    await session.flush()
    return released
