from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.son import SonStatus
from aerona.engine.gods.reputation import last_audience


async def sons_unaware_of_an_audience(session: AsyncSession) -> list[int]:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None:
        return []
    horizon = cosmos.epoch - (await CosmosRepository(session).rules()).reputation.window_epochs
    found: list[int] = []
    for son in await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)):
        if held(son.id) or son.reputation_epoch is None:
            continue
        if await last_audience(session, son.id, horizon) > (son.reputation_last_contact_epoch or 0):
            found.append(son.id)
    return found


async def remember_the_audience(session: AsyncSession, son_id: int) -> None:
    son = await session.get(SonRow, son_id)
    cosmos = await CosmosRepository(session).get()
    if son is None or cosmos is None:
        return
    horizon = cosmos.epoch - (await CosmosRepository(session).rules()).reputation.window_epochs
    son.reputation_last_contact_epoch = max(son.reputation_last_contact_epoch or 0, await last_audience(session, son.id, horizon))


def lived_epochs(epoch: int, son: SonRow) -> int:
    return max(0, epoch - son.birth_epoch + 1)


async def divine_minds_behind(session: AsyncSession) -> list[int]:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None:
        return []
    found: list[int] = []
    for son in await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)):
        mind = await session.get(MindProfileRow, son.id)
        if mind is None or held(son.id) or "run_epochs" in (mind.locked or []):
            continue
        if mind.run_epochs < lived_epochs(cosmos.epoch - 1, son):
            found.append(son.id)
    return found


async def count_divine_mind_epochs(session: AsyncSession, son_id: int) -> None:
    son = await session.get(SonRow, son_id)
    mind = await session.get(MindProfileRow, son_id)
    cosmos = await CosmosRepository(session).get()
    if son is None or mind is None or cosmos is None:
        return
    mind.run_epochs = max(mind.run_epochs, lived_epochs(cosmos.epoch - 1, son))
