from collections.abc import Mapping
from enum import StrEnum

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.finance import (
    FinanceCreditView,
    FinanceHoardView,
    FinanceIndicatorView,
    FinanceLivingView,
    FinancePolicyView,
    FinanceView,
)
from aerona.api.schemas.mind import LabelView
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.finance import CREDIT_LABELS, POLICY_LABELS, SPECULATION_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.tables.finance import CreditProfileRow, EconomicIndicatorRow, SpeculationRow, TradePolicyRow
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.society import SocialClass

router = APIRouter(tags=["finance"])
NO_NODE = "Nothing lives there."
EVERY_GOOD = "Every good"


def labels[K: StrEnum](table: Mapping[K, str]) -> list[LabelView]:
    return [LabelView(key=key.value, label=label) for key, label in table.items()]


async def policy_views(session: AsyncSession, node_id: int, realm: int | None) -> list[FinancePolicyView]:
    issuers = [node_id, *([realm] if realm is not None else [])]
    rows = list(
        await session.scalars(
            select(TradePolicyRow)
            .where(or_(TradePolicyRow.issuer_node_id.in_(issuers), TradePolicyRow.partner_node_id.in_(issuers)))
            .order_by(TradePolicyRow.since_epoch.desc(), TradePolicyRow.id)
        )
    )
    refs = await node_refs(session, [item for row in rows for item in (row.issuer_node_id, row.partner_node_id) if item])
    return [
        FinancePolicyView(
            id=row.id,
            issuer=refs.get(row.issuer_node_id),
            kind=row.kind,
            kind_label=POLICY_LABELS[row.kind],
            commodity=row.commodity,
            commodity_label=COMMODITIES[row.commodity].label if row.commodity is not None else EVERY_GOOD,
            partner=refs.get(row.partner_node_id) if row.partner_node_id is not None else None,
            rate_pct=row.rate_pct,
            since_epoch=row.since_epoch,
            reason=row.reason,
            held=bool(row.locked),
        )
        for row in rows
    ]


async def hoard_views(session: AsyncSession, node_id: int) -> list[FinanceHoardView]:
    rows = list(
        await session.scalars(
            select(SpeculationRow)
            .where(or_(SpeculationRow.merchant_node_id == node_id, SpeculationRow.market_node_id == node_id))
            .order_by(SpeculationRow.opened_epoch.desc(), SpeculationRow.id.desc())
        )
    )
    refs = await node_refs(session, [item for row in rows for item in (row.merchant_node_id, row.market_node_id)])
    return [
        FinanceHoardView(
            id=row.id,
            merchant=refs.get(row.merchant_node_id),
            market=refs.get(row.market_node_id),
            commodity=row.commodity,
            commodity_label=COMMODITIES[row.commodity].label,
            units=row.units,
            price=row.price,
            status=row.status,
            status_label=SPECULATION_LABELS[row.status],
            opened_epoch=row.opened_epoch,
            settled_epoch=row.settled_epoch,
            gain=row.gain,
            held=bool(row.locked),
        )
        for row in rows
    ]


async def indicator_views(session: AsyncSession, node_id: int) -> list[FinanceIndicatorView]:
    rows = await session.scalars(
        select(EconomicIndicatorRow).where(EconomicIndicatorRow.subject_node_id == node_id).order_by(EconomicIndicatorRow.epoch.desc())
    )
    return [
        FinanceIndicatorView(
            id=row.id,
            epoch=row.epoch,
            output=row.output,
            price_index=row.price_index,
            trade_balance=row.trade_balance,
            treasury=row.treasury,
            debt_ratio=row.debt_ratio,
            unemployment=row.unemployment,
            market_access=row.market_access,
            black_market=row.black_market,
            living=[
                FinanceLivingView(key=SocialClass(key), value=value) for key, value in (row.living or {}).items() if key in SocialClass.__members__.values()
            ],
            held=list(row.locked or []),
        )
        for row in rows
    ]


@router.get("/finance/{node_id}", response_model=FinanceView)
async def finance_view(services: ServicesDep, node_id: int = Path(ge=1)) -> FinanceView:
    async with reader(services) as session:
        ref = await node_ref(session, node_id)
        if ref is None:
            raise NotFoundError(NO_NODE)
        realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == node_id).limit(1))
        credit = await session.get(CreditProfileRow, node_id)
        industry = await session.get(CommunityIndustryRow, node_id)
        return FinanceView(
            node_id=node_id,
            name=ref.name,
            realm=await node_ref(session, realm) if realm is not None else None,
            credit=FinanceCreditView(
                rating=credit.rating,
                state=credit.state,
                state_label=CREDIT_LABELS[credit.state],
                interest_pct=credit.interest_pct,
                reserves=credit.reserves,
                defaults=credit.defaults,
                restructured_until=credit.restructured_until,
                epoch=credit.epoch,
                held=list(credit.locked or []),
            )
            if credit is not None
            else None,
            policies=await policy_views(session, node_id, realm),
            hoards=await hoard_views(session, node_id),
            indicators=await indicator_views(session, node_id),
            market_access=industry.market_access if industry is not None else None,
            black_market=industry.black_market if industry is not None else None,
            policy_kinds=labels(POLICY_LABELS),
            credit_states=labels(CREDIT_LABELS),
            commodities=[LabelView(key=kind.value, label=spec.label) for kind, spec in COMMODITIES.items()],
        )
