from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, SecurityPriceRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.governance.seats import apportioned


async def overheld(session: AsyncSession) -> list[int]:
    totals = select(SecurityHoldingRow.security_id, func.sum(SecurityHoldingRow.amount)).group_by(SecurityHoldingRow.security_id)
    found: list[int] = []
    for security_id, total in await session.execute(totals):
        security = await session.get(IssuedSecurityRow, security_id)
        if security is not None and int(total or 0) > security.amount:
            found.append(int(security_id))
    return sorted(found)


async def scale_holdings(session: AsyncSession, key: int) -> None:
    security = await session.get(IssuedSecurityRow, key)
    if security is None:
        return
    rows = list(await session.scalars(select(SecurityHoldingRow).where(SecurityHoldingRow.security_id == key).order_by(SecurityHoldingRow.id)))
    shares = apportioned({row.id: float(row.amount) for row in rows}, security.amount)
    for row in rows:
        row.amount = shares.get(row.id, 0)


async def issuerless(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for security in await session.scalars(select(IssuedSecurityRow).where(IssuedSecurityRow.delisted_epoch.is_(None)).order_by(IssuedSecurityRow.id)):
        issuer = await session.get(EntityRow, security.issuer_node_id)
        if issuer is not None and issuer.status is not EntityStatus.CANON:
            found.append(security.id)
    return found


async def delist(session: AsyncSession, key: int) -> None:
    security = await session.get(IssuedSecurityRow, key)
    if security is not None:
        issuer = await session.get(EntityRow, security.issuer_node_id)
        security.delisted_epoch = issuer.end_epoch if issuer is not None and issuer.end_epoch is not None else security.listed_epoch


async def stray_prices(session: AsyncSession) -> list[int]:
    query = (
        select(SecurityPriceRow.id)
        .join(IssuedSecurityRow, IssuedSecurityRow.id == SecurityPriceRow.security_id)
        .where(SecurityPriceRow.issuer_node_id != IssuedSecurityRow.issuer_node_id)
    )
    return list(await session.scalars(query.order_by(SecurityPriceRow.id)))


async def align_price(session: AsyncSession, key: int) -> None:
    row = await session.get(SecurityPriceRow, key)
    security = await session.get(IssuedSecurityRow, row.security_id) if row is not None else None
    if row is not None and security is not None:
        row.issuer_node_id = security.issuer_node_id
