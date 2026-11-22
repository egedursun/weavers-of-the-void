from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.securities import SecurityKind
from aerona.engine.context import TickContext
from aerona.engine.governance.seats import apportioned
from aerona.engine.primitives.mirrors import close_legacy, first_sight
from aerona.engine.recording.record import record
from aerona.engine.securities.holdings import SecuritiesTally, holdings_of
from aerona.engine.securities.pricing import traded

LEGACY_FIXUP = "securities.legacy_shares"
COMPANY_FAMILY = "securities.company"
SHARE_UNITS = 100
SHARE_FACE = 10


async def issue_shares(ctx: TickContext, company: EntityRow, rows: list[CompanyShareRow]) -> IssuedSecurityRow:
    security = IssuedSecurityRow(
        name=f"the shares of {company.name}",
        issuer_node_id=company.id,
        kind=SecurityKind.SHARE,
        amount=SHARE_UNITS,
        face_value=SHARE_FACE,
        price=SHARE_FACE,
        listed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(security)
    await ctx.session.flush()
    weights = {row.holder_node_id: float(max(0, row.share)) for row in rows}
    for holder, amount in sorted(apportioned(weights, SHARE_UNITS).items()):
        if amount:
            ctx.session.add(SecurityHoldingRow(holder_node_id=holder, security_id=security.id, amount=amount, bought_price=SHARE_FACE, locked=[]))
            await traded(ctx, security, amount)
    return security


async def float_shares(ctx: TickContext, tally: SecuritiesTally) -> None:
    rows = list(await ctx.session.scalars(select(CompanyShareRow).order_by(CompanyShareRow.company_entity_id, CompanyShareRow.holder_node_id)))
    made = 0
    for company_id in sorted({row.company_entity_id for row in rows}):
        company = await ctx.session.get(EntityRow, company_id)
        if company is None or company.status is not EntityStatus.CANON or held(company_id) or not await first_sight(ctx.session, COMPANY_FAMILY, company_id):
            continue
        issued = select(IssuedSecurityRow.id).where(IssuedSecurityRow.issuer_node_id == company_id, IssuedSecurityRow.kind == SecurityKind.SHARE)
        if await ctx.session.scalar(issued.limit(1)) is not None:
            continue
        await issue_shares(ctx, company, [row for row in rows if row.company_entity_id == company_id])
        made += 1
    tally.floated += made
    await close_legacy(ctx.session, LEGACY_FIXUP, {"shares": made})
    await ctx.session.flush()


async def sync_shares(ctx: TickContext, tally: SecuritiesTally) -> None:
    query = select(IssuedSecurityRow).where(
        IssuedSecurityRow.kind == SecurityKind.SHARE, IssuedSecurityRow.exchange_id.is_not(None), IssuedSecurityRow.delisted_epoch.is_(None)
    )
    for security in await ctx.session.scalars(query.order_by(IssuedSecurityRow.id)):
        if held(security.issuer_node_id):
            continue
        rows = await holdings_of(ctx.session, security.id)
        total = sum(row.amount for row in rows)
        if not total:
            continue
        shares = apportioned({row.holder_node_id: float(row.amount) for row in rows}, PERCENT)
        stored = {
            row.holder_node_id: row
            for row in await ctx.session.scalars(select(CompanyShareRow).where(CompanyShareRow.company_entity_id == security.issuer_node_id))
        }
        for holder, share in sorted(shares.items()):
            row = stored.get(holder)
            if row is None:
                ctx.session.add(CompanyShareRow(company_entity_id=security.issuer_node_id, holder_node_id=holder, share=share, locked=False))
            elif not row.locked:
                row.share = share
        for holder, row in sorted(stored.items()):
            if holder not in shares and not row.locked:
                await ctx.session.delete(row)
        tally.synced += 1


async def delist_orphans(ctx: TickContext, tally: SecuritiesTally) -> None:
    query = select(IssuedSecurityRow).where(IssuedSecurityRow.delisted_epoch.is_(None)).order_by(IssuedSecurityRow.id)
    for security in await ctx.session.scalars(query):
        issuer = await ctx.session.get(EntityRow, security.issuer_node_id)
        if issuer is not None and issuer.status is EntityStatus.CANON:
            continue
        if held(security.issuer_node_id) or "delisted_epoch" in (security.locked or []):
            continue
        security.delisted_epoch = ctx.epoch
        tally.delisted += 1
        await record(
            ctx, "securities.delisted", roles={IncidentRole.SUBJECT: security.issuer_node_id}, facts={"security": security.name, "why": "its issuer is gone"}
        )
