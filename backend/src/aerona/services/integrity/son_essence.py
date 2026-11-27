from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stats import max_essence
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held


async def sons_over_their_cap(session: AsyncSession) -> list[int]:
    rules = await CosmosRepository(session).rules()
    return [son.id for son in await session.scalars(select(SonRow).order_by(SonRow.id)) if son.essence > max_essence(rules, son.might) and not held(son.id)]


async def fit_son_essence(session: AsyncSession, son_id: int) -> None:
    son = await session.get(SonRow, son_id)
    if son is None:
        return
    son.essence = min(son.essence, max_essence(await CosmosRepository(session).rules(), son.might))
