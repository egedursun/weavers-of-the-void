from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import SINGLETON_ID
from aerona.db.repositories.cosmos import rules_from_snapshot
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalEquipmentRow, MortalProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.mortal.life import stage_now
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules


async def profile_of(session: AsyncSession, mortal_id: int) -> MortalProfileRow | None:
    return await session.get(MortalProfileRow, mortal_id)


async def ensure_profile(session: AsyncSession, mortal_id: int, epoch: int) -> tuple[MortalProfileRow, bool]:
    row = await session.get(MortalProfileRow, mortal_id)
    if row is not None:
        return row, False
    mortal = await session.get(EntityRow, mortal_id)
    cosmos = await session.get(CosmosRow, SINGLETON_ID)
    rules = rules_from_snapshot(cosmos.rules_snapshot) if cosmos is not None else Rules()
    stage = (
        await stage_now(session, rules, mortal) if mortal is not None and mortal.entity_type is EntityType.MORTAL and stat(mortal, "age") is not None else None
    )
    row = MortalProfileRow(entity_id=mortal_id, updated_epoch=max(0, epoch), locked=[], **({"life_stage": stage} if stage is not None else {}))
    session.add(row)
    await session.flush()
    return row, True


async def ensure_equipment(session: AsyncSession, mortal_id: int) -> MortalEquipmentRow:
    row = await session.get(MortalEquipmentRow, mortal_id)
    if row is None:
        row = MortalEquipmentRow(entity_id=mortal_id, locked=[])
        session.add(row)
        await session.flush()
    return row


def is_held(row: MortalProfileRow | MortalEquipmentRow | None, field: str) -> bool:
    return row is not None and field in (row.locked or [])
