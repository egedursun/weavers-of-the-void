from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow
from aerona.domain.enums.securities import SecurityKind


@dataclass
class SecuritiesTally:
    opened: int = 0
    listed: int = 0
    moved: int = 0
    bubbles: int = 0
    crashes: int = 0
    margin_calls: int = 0
    defaults: int = 0
    matured: int = 0
    delisted: int = 0
    insiders: int = 0
    bonds: int = 0
    synced: int = 0


async def holdings_of(session: AsyncSession, security_id: int) -> list[SecurityHoldingRow]:
    query = select(SecurityHoldingRow).where(SecurityHoldingRow.security_id == security_id, SecurityHoldingRow.amount > 0)
    return list(await session.scalars(query.order_by(SecurityHoldingRow.amount.desc(), SecurityHoldingRow.id)))


async def holding(session: AsyncSession, security_id: int, holder_id: int) -> SecurityHoldingRow | None:
    query = select(SecurityHoldingRow).where(SecurityHoldingRow.security_id == security_id, SecurityHoldingRow.holder_node_id == holder_id)
    return await session.scalar(query.order_by(SecurityHoldingRow.id).limit(1))


async def share_security(session: AsyncSession, issuer_id: int) -> IssuedSecurityRow | None:
    query = select(IssuedSecurityRow).where(
        IssuedSecurityRow.issuer_node_id == issuer_id, IssuedSecurityRow.kind == SecurityKind.SHARE, IssuedSecurityRow.delisted_epoch.is_(None)
    )
    return await session.scalar(query.order_by(IssuedSecurityRow.id).limit(1))


async def holds_majority(session: AsyncSession, issuer_id: int, holder_id: int) -> bool:
    security = await share_security(session, issuer_id)
    if security is None or not security.amount:
        return False
    row = await holding(session, security.id, holder_id)
    return row is not None and row.amount * 2 > security.amount


async def default_premium(session: AsyncSession, issuer_id: int, rise: int) -> int:
    query = select(IssuedSecurityRow.id).where(IssuedSecurityRow.issuer_node_id == issuer_id, IssuedSecurityRow.defaulted_epoch.is_not(None))
    return rise * len(list(await session.scalars(query)))
