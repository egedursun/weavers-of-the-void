from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.monetary import MonetaryAuthorityRow


async def authorities(session: AsyncSession) -> list[MonetaryAuthorityRow]:
    return list(await session.scalars(select(MonetaryAuthorityRow).order_by(MonetaryAuthorityRow.id)))


async def bad_pegs(session: AsyncSession) -> list[int]:
    return [
        row.id for row in await authorities(session) if row.peg_currency_id == row.currency_id or (row.peg_currency_id is not None and row.peg_good is not None)
    ]


async def clear_peg(session: AsyncSession, key: int) -> None:
    row = await session.get(MonetaryAuthorityRow, key)
    if row is None:
        return
    if row.peg_currency_id == row.currency_id:
        row.peg_currency_id = None
    if row.peg_currency_id is not None:
        row.peg_good = None


async def stray_issuers(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await authorities(session):
        currency = await session.get(CurrencyRow, row.currency_id)
        if currency is not None and "issuer_node_id" not in (row.locked or []) and row.issuer_node_id != currency.issuer_entity_id:
            found.append(row.id)
    return found


async def align_issuer(session: AsyncSession, key: int) -> None:
    row = await session.get(MonetaryAuthorityRow, key)
    currency = await session.get(CurrencyRow, row.currency_id) if row is not None else None
    if row is not None and currency is not None:
        row.issuer_node_id = currency.issuer_entity_id
