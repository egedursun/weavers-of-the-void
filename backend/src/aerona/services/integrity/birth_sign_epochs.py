from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sacred import BirthSignRow
from aerona.db.write_guard import held
from aerona.engine.sacred.astrology import epoch_born_in
from aerona.services.integrity.chronology import rules_of


async def signs_born_too_late(session: AsyncSession) -> list[int]:
    rules, epoch = await rules_of(session)
    rows = await session.execute(
        select(BirthSignRow, EntityRow).join(EntityRow, EntityRow.id == BirthSignRow.mortal_entity_id).order_by(BirthSignRow.mortal_entity_id)
    )
    return [
        sign.mortal_entity_id
        for sign, mortal in rows
        if not held(mortal.id) and "born_epoch" not in sign.locked and sign.born_epoch > epoch_born_in(mortal, epoch, rules.time.years_per_epoch)
    ]


async def date_birth_sign(session: AsyncSession, mortal_id: int) -> None:
    rules, epoch = await rules_of(session)
    sign = await session.get(BirthSignRow, mortal_id)
    mortal = await session.get(EntityRow, mortal_id)
    if sign is not None and mortal is not None:
        sign.born_epoch = min(sign.born_epoch, epoch_born_in(mortal, epoch, rules.time.years_per_epoch))
