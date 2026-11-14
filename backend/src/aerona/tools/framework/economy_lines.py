from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.core.grammar import several
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import CohortRow, LabourRow
from aerona.db.tables.disease import EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.economy import (
    CommunityStockRow,
    CurrencyRow,
    LoanRow,
    MarketPriceRow,
    TradeRouteLossRow,
    TradeRouteProfileRow,
    TradeRouteRegionRow,
    TradeRouteTollRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.engine.economy.materials import MaterialBook
from aerona.engine.economy.money import owed
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from aerona.prompts.contexts.economy_depth import (
    CohortLine,
    CommodityLine,
    CurrencyLine,
    DebtLine,
    EconomyBlock,
    EndemicLine,
    LabourLine,
    LoanLine,
    OutbreakLine,
    RouteLine,
    SettlementPlanLine,
    TollLine,
)
from aerona.rules.registry import Rules

UNTOLLED = "untolled."


def words(value: str) -> str:
    return value.replace("_", " ")


class Names:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = NodeRepository(session)
        self.cache: dict[int, str] = {}

    async def load(self, ids: Iterable[int | None]) -> None:
        wanted = sorted(item for item in ids if item is not None and item not in self.cache)
        self.cache.update(await self.repository.names_of(wanted))

    def of(self, node_id: int | None) -> str:
        return self.cache.get(node_id, "") if node_id is not None else ""


async def commodity_lines(session: AsyncSession, community: EntityRow) -> list[CommodityLine]:
    book = await MaterialBook.load(session)
    lots: dict[CommodityKind, list[CommunityStockRow]] = defaultdict(list)
    for lot in await session.scalars(
        select(CommunityStockRow)
        .where(CommunityStockRow.community_entity_id == community.id, CommunityStockRow.quantity > 0)
        .order_by(CommunityStockRow.commodity, CommunityStockRow.id)
    ):
        lots[lot.commodity].append(lot)
    latest = await session.scalar(select(func.max(MarketPriceRow.epoch)).where(MarketPriceRow.market_entity_id == community.id))
    prices = (
        {
            row.commodity: row
            for row in await session.scalars(select(MarketPriceRow).where(MarketPriceRow.market_entity_id == community.id, MarketPriceRow.epoch == latest))
        }
        if latest is not None
        else {}
    )
    lines: list[CommodityLine] = []
    for kind in COMMODITIES:
        held = lots.get(kind, [])
        price = prices.get(kind)
        if not held and price is None:
            continue
        quantity = sum(lot.quantity for lot in held)
        labels = []
        for lot in held:
            props = book.props(community.world_id, lot.material, lot.world_material_id)
            labels.append(f"{props.label if props is not None else 'common'} {lot.quantity} (quality {lot.quality})")
        lines.append(
            CommodityLine(
                label=COMMODITIES[kind].label,
                quantity=quantity,
                quality=round(sum(lot.quantity * lot.quality for lot in held) / quantity) if quantity else 0,
                lots=labels,
                price=price.price if price is not None else None,
                supply=price.supply if price is not None else None,
                demand=price.demand if price is not None else None,
                imported=price.imported if price is not None else 0,
                exported=price.exported if price is not None else 0,
            )
        )
    return lines


async def currency_line(session: AsyncSession, community_id: int, names: Names) -> CurrencyLine | None:
    society = await session.get(CommunitySocietyRow, community_id)
    currency = await session.get(CurrencyRow, society.currency_id) if society is not None and society.currency_id is not None else None
    if currency is None:
        return None
    await names.load({currency.issuer_entity_id})
    return CurrencyLine(
        id=currency.id,
        name=currency.name,
        metal=words(currency.metal.value),
        purity=currency.purity,
        trust=currency.trust,
        supply=currency.supply,
        issuer=names.of(currency.issuer_entity_id),
        debased=currency.debased_epoch is not None,
    )


async def loan_lines(session: AsyncSession, node_id: int, names: Names) -> list[LoanLine]:
    loans = list(
        await session.scalars(select(LoanRow).where(or_(LoanRow.lender_entity_id == node_id, LoanRow.borrower_entity_id == node_id)).order_by(LoanRow.id))
    )
    currencies = {row.id: row.name for row in await session.scalars(select(CurrencyRow).where(CurrencyRow.id.in_([loan.currency_id for loan in loans])))}
    await names.load({loan.lender_entity_id for loan in loans} | {loan.borrower_entity_id for loan in loans})
    return [
        LoanLine(
            id=loan.id,
            role="borrowed from" if loan.borrower_entity_id == node_id else "lent to",
            other=names.of(loan.lender_entity_id if loan.borrower_entity_id == node_id else loan.borrower_entity_id),
            principal=loan.principal,
            owed=max(0, owed(loan)),
            interest_pct=loan.interest_pct,
            due_epoch=loan.due_epoch,
            status=words(loan.status.value),
            currency=currencies.get(loan.currency_id, "") if loan.currency_id is not None else "",
            purpose=loan.purpose,
        )
        for loan in loans
    ]


async def debt_lines(session: AsyncSession, node_id: int, names: Names) -> list[DebtLine]:
    bonds = list(
        await session.scalars(
            select(BondRow)
            .where(BondRow.kind == BondKind.OWES, BondRow.state == BondState.ACTIVE, or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id))
            .order_by(BondRow.id)
        )
    )
    currencies = {row.id: row.name for row in await session.scalars(select(CurrencyRow).where(CurrencyRow.id.in_([bond.debt_currency_id for bond in bonds])))}
    await names.load({bond.source_node_id for bond in bonds} | {bond.target_node_id for bond in bonds})
    return [
        DebtLine(
            id=bond.id,
            role="owes" if bond.source_node_id == node_id else "is owed by",
            other=names.of(bond.target_node_id if bond.source_node_id == node_id else bond.source_node_id),
            amount=bond.debt_amount or 0,
            what=bond.debt_what or "",
            due_epoch=bond.debt_due_epoch,
            status=words(bond.debt_status.value) if bond.debt_status is not None else "open",
            currency=currencies.get(bond.debt_currency_id, "") if bond.debt_currency_id is not None else "",
        )
        for bond in bonds
    ]


async def route_line(session: AsyncSession, profile: TradeRouteProfileRow, names: Names, *, viewpoint: int | None) -> RouteLine | None:
    entity = await session.get(EntityRow, profile.route_entity_id)
    if entity is None:
        return None
    tolls = list(
        await session.scalars(select(TradeRouteTollRow).where(TradeRouteTollRow.route_entity_id == entity.id).order_by(TradeRouteTollRow.region_entity_id))
    )
    losses = list(
        await session.scalars(
            select(TradeRouteLossRow).where(TradeRouteLossRow.route_entity_id == entity.id).order_by(TradeRouteLossRow.epoch, TradeRouteLossRow.id)
        )
    )
    path = list(await session.scalars(select(TradeRouteRegionRow.region_entity_id).where(TradeRouteRegionRow.route_entity_id == entity.id)))
    await names.load(
        {profile.first_market_id, profile.second_market_id, profile.controller_entity_id, profile.blockaded_by_entity_id, *path}
        | {toll.controller_entity_id for toll in tolls}
        | {toll.polity_entity_id for toll in tolls}
        | {toll.region_entity_id for toll in tolls}
        | {loss.culprit_entity_id for loss in losses}
    )
    partner = profile.second_market_id if viewpoint == profile.first_market_id else profile.first_market_id
    ends = (
        names.of(partner)
        if viewpoint in (profile.first_market_id, profile.second_market_id)
        else f"{names.of(profile.first_market_id)} and {names.of(profile.second_market_id)}"
    )
    untolled = [names.of(int(key.removeprefix(UNTOLLED))) for key in profile.locked or [] if key.startswith(UNTOLLED) and key.removeprefix(UNTOLLED).isdigit()]
    return RouteLine(
        id=entity.id,
        name=entity.name,
        mode=words(profile.mode.value),
        status=words(profile.status.value),
        partner=ends,
        capacity=stat(entity, "capacity") or 0,
        danger=stat(entity, "danger") or 0,
        bandits=profile.danger_bandits,
        beasts=profile.danger_beasts,
        weather=profile.danger_weather,
        sea=profile.danger_sea,
        season_pct=profile.season_pct,
        length=profile.length,
        renown=stat(entity, "renown") or 0,
        controller=names.of(profile.controller_entity_id),
        blockaded_by=names.of(profile.blockaded_by_entity_id),
        chokepoint=profile.chokepoint,
        closed_by_player=profile.closed_by_player,
        held=[words(key.replace("_entity_id", "")) for key in profile.locked or [] if not key.startswith(UNTOLLED)]
        + [f"no toll in {name}" for name in untolled],
        tolls=[
            TollLine(
                region=names.of(toll.region_entity_id),
                controller=names.of(toll.controller_entity_id),
                rate_pct=toll.rate_pct,
                treasury=names.of(toll.polity_entity_id),
                held=toll.set_by_player or toll.controller_held,
            )
            for toll in tolls
        ],
        losses=[
            f"age {loss.epoch}: {loss.units} {COMMODITIES[loss.commodity].label.lower()} to {words(loss.cause.value)}"
            + (f" ({names.of(loss.culprit_entity_id)})" if loss.culprit_entity_id is not None else "")
            for loss in losses
        ],
    )


async def route_lines(session: AsyncSession, node_id: int, names: Names) -> list[RouteLine]:
    statement = select(TradeRouteProfileRow).where(
        or_(
            TradeRouteProfileRow.first_market_id == node_id,
            TradeRouteProfileRow.second_market_id == node_id,
            TradeRouteProfileRow.controller_entity_id == node_id,
            TradeRouteProfileRow.route_entity_id.in_(
                select(TradeRouteTollRow.route_entity_id).where(
                    or_(TradeRouteTollRow.controller_entity_id == node_id, TradeRouteTollRow.polity_entity_id == node_id)
                )
            ),
        )
    )
    lines = [
        await route_line(session, profile, names, viewpoint=node_id)
        for profile in await session.scalars(statement.order_by(TradeRouteProfileRow.route_entity_id))
    ]
    return [line for line in lines if line is not None]


async def settlement_line(session: AsyncSession, settlement_id: int) -> SettlementPlanLine | None:
    profile = await session.get(SettlementProfileRow, settlement_id)
    if profile is None:
        return None
    districts = list(
        await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement_id).order_by(DistrictRow.kind, DistrictRow.id))
    )
    works = await session.get(SettlementInfrastructureRow, settlement_id)
    infrastructure = (
        [
            f"walls level {works.walls_level} of {words(works.walls_material.value)} (condition {works.walls_condition})",
            f"{several(works.gates, 'gate', 'gates')}",
            f"{several(works.towers, 'tower', 'towers')}",
            f"{several(works.roads, 'road', 'roads')}",
            f"water from {words(works.water.value)}",
            "sewers" if works.sewers else "no sewers",
            f"granary for {works.granary_capacity}",
            f"warehouses for {works.warehouse_capacity}",
            f"harbour for {works.harbour_capacity}",
        ]
        if works is not None
        else []
    )
    return SettlementPlanLine(
        tier=words(profile.size_tier.value),
        treasury=profile.treasury,
        tax_rate=profile.tax_rate,
        order=profile.public_order,
        crime=profile.crime,
        unrest=profile.unrest,
        sanitation=profile.sanitation,
        fire_risk=profile.fire_risk,
        prestige=profile.prestige,
        militia=profile.militia,
        free_city=profile.free_city,
        rationing=profile.rationing,
        districts=[f"{words(row.kind.value)} level {row.level} of {words(row.material.value)} (condition {row.condition})" for row in districts],
        infrastructure=infrastructure,
    )


async def cohort_lines(session: AsyncSession, community_id: int) -> list[CohortLine]:
    rows = await session.scalars(
        select(CohortRow)
        .where(CohortRow.community_entity_id == community_id, CohortRow.count > 0)
        .order_by(CohortRow.age_band, CohortRow.sex, CohortRow.social_class, CohortRow.condition)
    )
    return [
        CohortLine(
            age_band=row.age_band.value, sex=row.sex.value, social_class=words(row.social_class.value), condition=words(row.condition.value), count=row.count
        )
        for row in rows
    ]


async def labour_lines(session: AsyncSession, community_id: int) -> list[LabourLine]:
    rows = await session.scalars(select(LabourRow).where(LabourRow.community_entity_id == community_id).order_by(LabourRow.job))
    return [LabourLine(job=words(row.job.value), workers=row.workers, output_pct=row.output_pct) for row in rows if row.workers > 0]


async def sickness_lines(session: AsyncSession, region_id: int | None, names: Names) -> tuple[list[OutbreakLine], list[EndemicLine]]:
    if region_id is None:
        return [], []
    outbreaks = list(
        await session.scalars(
            select(OutbreakRow).where(OutbreakRow.region_entity_id == region_id, OutbreakRow.status != OutbreakStatus.ENDED).order_by(OutbreakRow.id)
        )
    )
    endemic = list(
        await session.scalars(select(EndemicDiseaseRow).where(EndemicDiseaseRow.region_entity_id == region_id).order_by(EndemicDiseaseRow.disease_entity_id))
    )
    await names.load({row.disease_entity_id for row in outbreaks} | {row.disease_entity_id for row in endemic} | {region_id})
    return (
        [
            OutbreakLine(
                disease=names.of(row.disease_entity_id),
                region=names.of(region_id),
                status=words(row.status.value),
                severity=row.severity,
                infected=row.infected,
                dead=row.dead,
                quarantined=row.quarantined,
                path=words(row.path.value),
            )
            for row in outbreaks
        ],
        [EndemicLine(disease=names.of(row.disease_entity_id), region=names.of(region_id), load=row.load) for row in endemic],
    )


async def pact_lines(session: AsyncSession, node_id: int, names: Names) -> list[str]:
    statement = (
        select(TreatyClauseRow, TreatyProfileRow)
        .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
        .where(
            TreatyClauseRow.kind == ClauseKind.RESOURCE_DEMAND,
            or_(TreatyClauseRow.obligor_node_id == node_id, TreatyClauseRow.beneficiary_node_id == node_id),
        )
        .order_by(TreatyClauseRow.id)
    )
    found = list(await session.execute(statement))
    await names.load({clause.obligor_node_id for clause, _ in found} | {clause.beneficiary_node_id for clause, _ in found})
    lines: list[str] = []
    for clause, profile in found:
        params = clause.params or {}
        goods = f"{params.get('units', 0)} {words(str(params.get('commodity')))}" if params.get("commodity") else f"prosperity {params.get('cost', 0)}"
        state = "in force" if profile.status is TreatyStatus.IN_FORCE else words(profile.status.value)
        lines.append(
            f"pact#{profile.treaty_entity_id} ({state}): {names.of(clause.obligor_node_id)} gives {names.of(clause.beneficiary_node_id)} "
            f"{params.get('demand', 'its due')} ({goods}) every {params.get('every', 1)} ages, "
            f"last given in age {params.get('paid_epoch', profile.signed_epoch)}"
        )
    return lines


async def economy_block(session: AsyncSession, rules: Rules, entity: EntityRow) -> EconomyBlock | None:
    del rules
    names = Names(session)
    if entity.entity_type is EntityType.TRADE_ROUTE:
        profile = await session.get(TradeRouteProfileRow, entity.id)
        line = await route_line(session, profile, names, viewpoint=None) if profile is not None else None
        return EconomyBlock(routes=[line]) if line is not None else None
    parts: dict[str, object] = {
        "loans": await loan_lines(session, entity.id, names),
        "debts": await debt_lines(session, entity.id, names),
        "pacts": await pact_lines(session, entity.id, names),
    }
    if entity.entity_type in COMMUNITY_TYPES or entity.entity_type is EntityType.POLITY:
        parts["routes"] = await route_lines(session, entity.id, names)
    if entity.entity_type in COMMUNITY_TYPES:
        parts["commodities"] = await commodity_lines(session, entity)
        parts["currency"] = await currency_line(session, entity.id, names)
        parts["settlement"] = await settlement_line(session, entity.id)
        parts["cohorts"] = await cohort_lines(session, entity.id)
        parts["labour"] = await labour_lines(session, entity.id)
    if entity.entity_type in (*COMMUNITY_TYPES, EntityType.REGION):
        region = entity.id if entity.entity_type is EntityType.REGION else (await RegionAtlas.load(session)).top_region(entity.id)
        parts["outbreaks"], parts["endemic"] = await sickness_lines(session, region, names)
    block = EconomyBlock.model_validate(parts)
    return None if block.empty() else block
