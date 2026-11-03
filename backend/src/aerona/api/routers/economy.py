from collections import defaultdict

from fastapi import APIRouter, Path, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.economy import (
    ChainStepView,
    CommodityView,
    CommunityEconomyView,
    CurrencyView,
    DebtView,
    FlowView,
    LedgerView,
    LoanView,
    MarketSummary,
    MarketView,
    MaterialsView,
    MaterialView,
    MechanicParamView,
    PricePoint,
    PriceSeries,
    QuoteView,
    ResourceProfileView,
    RouteFlowView,
    RunView,
    StockLotView,
    TollView,
    TradeRouteDetail,
    TradeRouteView,
    WorkerView,
    WorkshopView,
)
from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.materials import MATERIALS
from aerona.catalog.production import CHAIN_STEPS, WORKSHOP_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.economy import (
    CommunityStockRow,
    CurrencyRow,
    GoodsFlowRow,
    LoanRow,
    MarketPriceRow,
    ProductionRunRow,
    ResourceProfileRow,
    ResourceWorkerRow,
    TradeFlowRow,
    TradeRouteProfileRow,
    TradeRouteRegionRow,
    TradeRouteTollRow,
    WorkshopRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import MaterialOrigin, WorkshopKind
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.society import Commodity
from aerona.engine.economy.household import storage_index, store_kind
from aerona.engine.economy.materials import MaterialBook, MaterialProps
from aerona.engine.economy.money import owed
from aerona.engine.economy.stocks import aggregate_index
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

router = APIRouter(tags=["economy"])


def material_view(props: MaterialProps, origin: MaterialOrigin, *, edited: bool, description: str | None = None, deposit_id: int | None = None) -> MaterialView:
    return MaterialView(
        kind=props.kind,
        world_material_id=props.world_material_id,
        label=props.label,
        family=props.family,
        origin=origin,
        edited=edited,
        hardness=props.hardness,
        toughness=props.toughness,
        weight=props.weight,
        edge=props.edge,
        conductivity=props.conductivity,
        sanctity=props.sanctity,
        corruption=props.corruption,
        rarity=props.rarity,
        base_value=props.base_value,
        decay=props.decay,
        branch=props.branch,
        level=props.level,
        gate=props.gate,
        description=description,
        deposit_id=deposit_id,
    )


async def names_of(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {entity_id: name for entity_id, name in await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_(list(ids))))}


async def rules_of(session: AsyncSession) -> tuple[Rules, int]:
    cosmos = await CosmosRepository(session).require_cosmos()
    return rules_from_snapshot(cosmos.rules_snapshot), cosmos.epoch


@router.get("/worlds/{world_id}/materials", response_model=MaterialsView)
async def world_materials(services: ServicesDep, world_id: int = Path(ge=1)) -> MaterialsView:
    async with reader(services) as session:
        rules, _ = await rules_of(session)
        book = await MaterialBook.load(session)
        views: list[MaterialView] = []
        for kind in MATERIALS:
            props = book.props(world_id, kind)
            if props is not None:
                views.append(material_view(props, MaterialOrigin.CATALOG, edited=(world_id, kind) in book.overrides))
        for row in book.of_world(world_id):
            props = book.props(world_id, world_material_id=row.id)
            if props is not None:
                views.append(material_view(props, row.origin, edited=False, description=row.description, deposit_id=row.deposit_entity_id))
        commodities = [
            CommodityView(
                kind=item.kind,
                label=item.label,
                family=item.family,
                base_price=item.base_price,
                nourishment=item.nourishment,
                strategic=item.strategic,
                per_1000=item.consumption(rules),
            )
            for item in COMMODITIES.values()
        ]
        return MaterialsView(world_id=world_id, materials=views, commodities=commodities)


def lot_label(row: CommunityStockRow, book: MaterialBook, world_id: int | None) -> str:
    base = COMMODITIES[row.commodity].label
    props = book.props(world_id, row.material, row.world_material_id)
    return f"{props.label} {base.lower()}" if props is not None else base


@router.get("/communities/{community_id}/economy", response_model=CommunityEconomyView)
async def community_economy(services: ServicesDep, community_id: int = Path(ge=1)) -> CommunityEconomyView:
    async with reader(services) as session:
        community = await session.get(EntityRow, community_id)
        if community is None or community.entity_type not in SOCIETY_TYPES:
            raise NotFoundError("No such people or settlement.")
        rules, epoch = await rules_of(session)
        book = await MaterialBook.load(session)
        lots = list(
            await session.scalars(
                select(CommunityStockRow)
                .where(CommunityStockRow.community_entity_id == community_id)
                .order_by(CommunityStockRow.commodity, CommunityStockRow.id)
            )
        )
        workshops = {row.kind: row for row in await session.scalars(select(WorkshopRow).where(WorkshopRow.community_entity_id == community_id))}
        last = await session.scalar(select(func.max(ProductionRunRow.epoch)).where(ProductionRunRow.community_entity_id == community_id))
        runs = (
            list(await session.scalars(select(ProductionRunRow).where(ProductionRunRow.community_entity_id == community_id, ProductionRunRow.epoch == last)))
            if last is not None
            else []
        )
        by_step: dict[str, list[ProductionRunRow]] = defaultdict(list)
        for run in runs:
            by_step[run.step].append(run)
        chain = [
            ChainStepView(
                key=step.key,
                label=step.label,
                workshop=step.workshop,
                inputs={commodity.value: amount for commodity, amount in step.inputs},
                output=step.output,
                output_qty=step.output_qty,
                made=sum(run.quantity for run in by_step.get(step.key, [])),
                quality=max((run.quality for run in by_step.get(step.key, []) if run.quantity), default=0),
                material=next((run.material for run in by_step.get(step.key, []) if run.material is not None), None),
                bottleneck=next((run.bottleneck for run in by_step.get(step.key, []) if run.bottleneck is not None), None),
                runs=step.workshop is None or step.workshop in workshops,
            )
            for step in CHAIN_STEPS
        ]
        flow_epoch = await session.scalar(select(func.max(GoodsFlowRow.epoch)).where(GoodsFlowRow.community_entity_id == community_id))
        flows = (
            [
                FlowView(commodity=row.commodity, flow=row.flow.value, quantity=row.quantity)
                for row in await session.scalars(select(GoodsFlowRow).where(GoodsFlowRow.community_entity_id == community_id, GoodsFlowRow.epoch == flow_epoch))
            ]
            if flow_epoch is not None
            else []
        )
        price_epoch = await session.scalar(select(func.max(MarketPriceRow.epoch)).where(MarketPriceRow.market_entity_id == community_id))
        quotes = (
            [
                QuoteView(commodity=row.commodity, price=row.price, supply=row.supply, demand=row.demand, imported=row.imported, exported=row.exported)
                for row in await session.scalars(
                    select(MarketPriceRow).where(MarketPriceRow.market_entity_id == community_id, MarketPriceRow.epoch == price_epoch)
                )
            ]
            if price_epoch is not None
            else []
        )
        society = await session.get(CommunitySocietyRow, community_id)
        return CommunityEconomyView(
            community_id=community_id,
            epoch=epoch,
            stocks=[
                StockLotView(
                    id=row.id,
                    commodity=row.commodity,
                    material=row.material,
                    world_material_id=row.world_material_id,
                    label=lot_label(row, book, community.world_id),
                    quantity=row.quantity,
                    quality=row.quality,
                )
                for row in lots
                if row.quantity > 0
            ],
            supply={aggregate.value: await aggregate_index(session, rules, community, aggregate) for aggregate in Commodity},
            storage={aggregate.value: storage_index(rules, workshops.get(store_kind(aggregate)), aggregate) for aggregate in Commodity},
            workshops=[
                WorkshopView(
                    kind=row.kind,
                    label=WORKSHOP_LABELS[row.kind],
                    level=row.level,
                    fleet=row.fleet,
                    idle_epochs=row.idle_epochs,
                    built_epoch=row.built_epoch,
                    structure_id=row.structure_entity_id,
                )
                for row in sorted(workshops.values(), key=lambda item: item.kind.value)
            ],
            chain=chain,
            flows=flows,
            quotes=quotes,
            currency_id=society.currency_id if society is not None else None,
            market=WorkshopKind.MARKET in workshops,
        )


@router.get("/resources/{resource_id}/profile", response_model=ResourceProfileView)
async def resource_profile(services: ServicesDep, resource_id: int = Path(ge=1)) -> ResourceProfileView:
    async with reader(services) as session:
        profile = await session.get(ResourceProfileRow, resource_id)
        entity = await session.get(EntityRow, resource_id)
        if profile is None or entity is None:
            raise NotFoundError("No such resource.")
        book = await MaterialBook.load(session)
        props = book.props(entity.world_id, profile.material, profile.world_material_id)
        workers = list(await session.scalars(select(ResourceWorkerRow).where(ResourceWorkerRow.resource_entity_id == resource_id)))
        runs = list(
            await session.scalars(
                select(ProductionRunRow).where(ProductionRunRow.resource_entity_id == resource_id).order_by(ProductionRunRow.epoch, ProductionRunRow.id)
            )
        )
        params = list(await session.scalars(select(ResourceMechanicRow).where(ResourceMechanicRow.entity_id == resource_id)))
        owners = [
            bond.source_node_id
            for bond in await session.scalars(
                select(BondRow)
                .where(BondRow.target_node_id == resource_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
                .order_by(BondRow.id)
            )
        ]
        names = await names_of(session, {row.community_entity_id for row in workers})
        return ResourceProfileView(
            resource_id=resource_id,
            commodity=profile.commodity,
            material=profile.material,
            world_material_id=profile.world_material_id,
            material_label=props.label if props is not None else None,
            reserve=profile.reserve,
            initial_reserve=profile.initial_reserve,
            richness=profile.richness,
            regeneration=profile.regeneration,
            extraction_difficulty=profile.extraction_difficulty,
            required_branch=profile.required_branch,
            required_level=profile.required_level,
            quality=profile.quality,
            byproduct_material=profile.byproduct_material,
            byproduct_pct=profile.byproduct_pct,
            revealed=profile.revealed,
            sealed_until_epoch=profile.sealed_until_epoch,
            last_output=profile.last_output,
            workers=[
                WorkerView(community_id=row.community_entity_id, community_name=names.get(row.community_entity_id, ""), workers=row.workers) for row in workers
            ],
            runs=[
                RunView(epoch=run.epoch, community_id=run.community_entity_id, quantity=run.quantity, quality=run.quality, workers=run.workers) for run in runs
            ],
            params=[MechanicParamView(mechanic=row.mechanic.value, magnitude=row.magnitude, epochs=row.epochs) for row in params],
            owners=owners,
        )


@router.get("/markets/{market_id}/prices", response_model=MarketView)
async def market_prices(services: ServicesDep, market_id: int = Path(ge=1)) -> MarketView:
    async with reader(services) as session:
        market = await session.get(EntityRow, market_id)
        if market is None:
            raise NotFoundError("No such market.")
        series: dict[str, list[PricePoint]] = defaultdict(list)
        for row in await session.scalars(
            select(MarketPriceRow).where(MarketPriceRow.market_entity_id == market_id).order_by(MarketPriceRow.commodity, MarketPriceRow.epoch)
        ):
            series[row.commodity.value].append(
                PricePoint(epoch=row.epoch, price=row.price, supply=row.supply, demand=row.demand, imported=row.imported, exported=row.exported)
            )
        return MarketView(
            market_id=market_id,
            name=market.name,
            world_id=market.world_id,
            series=[PriceSeries(commodity=kind, points=series[kind.value]) for kind in COMMODITIES if kind.value in series],
        )


async def route_views(session: AsyncSession, profiles: list[TradeRouteProfileRow]) -> list[TradeRouteView]:
    ids = [row.route_entity_id for row in profiles]
    if not ids:
        return []
    entities = {row.id: row for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(ids)))}
    paths: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for step in await session.scalars(select(TradeRouteRegionRow).where(TradeRouteRegionRow.route_entity_id.in_(ids))):
        paths[step.route_entity_id].append((step.position, step.region_entity_id))
    tolls: dict[int, list[TradeRouteTollRow]] = defaultdict(list)
    for toll in await session.scalars(select(TradeRouteTollRow).where(TradeRouteTollRow.route_entity_id.in_(ids))):
        tolls[toll.route_entity_id].append(toll)
    latest = await session.scalar(select(func.max(TradeFlowRow.epoch)))
    volumes: dict[int, int] = defaultdict(int)
    if latest is not None:
        for route_id, volume in await session.execute(
            select(TradeFlowRow.route_entity_id, TradeFlowRow.volume).where(TradeFlowRow.epoch == latest, TradeFlowRow.route_entity_id.in_(ids))
        ):
            volumes[route_id] += volume
    wanted = {row.first_market_id for row in profiles} | {row.second_market_id for row in profiles}
    wanted |= {toll.region_entity_id for items in tolls.values() for toll in items} | {toll.controller_entity_id for items in tolls.values() for toll in items}
    names = await names_of(session, wanted)
    views: list[TradeRouteView] = []
    for row in profiles:
        entity = entities.get(row.route_entity_id)
        if entity is None:
            continue
        views.append(
            TradeRouteView(
                route_id=row.route_entity_id,
                name=entity.name,
                world_id=entity.world_id,
                first_id=row.first_market_id,
                first_name=names.get(row.first_market_id, ""),
                second_id=row.second_market_id,
                second_name=names.get(row.second_market_id, ""),
                mode=row.mode,
                status=row.status,
                length=row.length,
                capacity=stat(entity, "capacity") or 0,
                danger=stat(entity, "danger") or 0,
                renown=stat(entity, "renown") or 0,
                culture=stat(entity, "culture") or 0,
                path=[region for _, region in sorted(paths[row.route_entity_id])],
                tolls=[
                    TollView(
                        region_id=toll.region_entity_id,
                        region_name=names.get(toll.region_entity_id, ""),
                        controller_id=toll.controller_entity_id,
                        controller_name=names.get(toll.controller_entity_id, ""),
                        rate_pct=toll.rate_pct,
                        set_by_player=toll.set_by_player,
                    )
                    for toll in sorted(tolls[row.route_entity_id], key=lambda item: item.region_entity_id)
                ],
                controller_id=row.controller_entity_id,
                blockaded_by_id=row.blockaded_by_entity_id,
                founded_epoch=row.founded_epoch,
                last_traffic_epoch=row.last_traffic_epoch,
                volume=volumes.get(row.route_entity_id, 0),
                closed_by_player=row.closed_by_player,
            )
        )
    return views


@router.get("/trade-routes", response_model=list[TradeRouteView])
async def trade_routes(services: ServicesDep, world_id: int | None = Query(default=None, ge=1)) -> list[TradeRouteView]:
    async with reader(services) as session:
        statement = select(TradeRouteProfileRow).order_by(TradeRouteProfileRow.route_entity_id)
        if world_id is not None:
            statement = statement.join(EntityRow, EntityRow.id == TradeRouteProfileRow.route_entity_id).where(EntityRow.world_id == world_id)
        return await route_views(session, list(await session.scalars(statement)))


@router.get("/trade-routes/{route_id}", response_model=TradeRouteDetail)
async def trade_route(services: ServicesDep, route_id: int = Path(ge=1)) -> TradeRouteDetail:
    async with reader(services) as session:
        profile = await session.get(TradeRouteProfileRow, route_id)
        if profile is None:
            raise NotFoundError("No such trade route.")
        views = await route_views(session, [profile])
        if not views:
            raise NotFoundError("No such trade route.")
        flows = [
            RouteFlowView(
                epoch=row.epoch,
                commodity=row.commodity,
                material=row.material,
                from_id=row.from_entity_id,
                to_id=row.to_entity_id,
                volume=row.volume,
                lost=row.lost,
                loss=row.loss,
                value=row.value,
                toll_paid=row.toll_paid,
            )
            for row in await session.scalars(select(TradeFlowRow).where(TradeFlowRow.route_entity_id == route_id).order_by(TradeFlowRow.epoch, TradeFlowRow.id))
        ]
        return TradeRouteDetail(**views[0].model_dump(), flows=flows)


@router.get("/currencies", response_model=list[CurrencyView])
async def currencies(services: ServicesDep) -> list[CurrencyView]:
    async with reader(services) as session:
        rows = list(await session.scalars(select(CurrencyRow).order_by(CurrencyRow.id)))
        users: dict[int, list[int]] = defaultdict(list)
        for entity_id, currency_id in await session.execute(
            select(CommunitySocietyRow.entity_id, CommunitySocietyRow.currency_id).where(CommunitySocietyRow.currency_id.is_not(None))
        ):
            if currency_id is not None:
                users[currency_id].append(entity_id)
        names = await names_of(session, {row.issuer_entity_id for row in rows})
        return [
            CurrencyView(
                id=row.id,
                name=row.name,
                issuer_id=row.issuer_entity_id,
                issuer_name=names.get(row.issuer_entity_id, ""),
                item_id=row.item_entity_id,
                metal=row.metal,
                purity=row.purity,
                trust=row.trust,
                supply=row.supply,
                minted_epoch=row.minted_epoch,
                debased_epoch=row.debased_epoch,
                users=sorted(users.get(row.id, [])),
            )
            for row in rows
        ]


@router.get("/ledger/debts", response_model=LedgerView)
async def debts_ledger(services: ServicesDep) -> LedgerView:
    async with reader(services) as session:
        loans = list(await session.scalars(select(LoanRow).order_by(LoanRow.issued_epoch.desc(), LoanRow.id.desc())))
        bonds = list(await session.scalars(select(BondRow).where(BondRow.kind == BondKind.OWES, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)))
        names = await names_of(
            session,
            {loan.lender_entity_id for loan in loans}
            | {loan.borrower_entity_id for loan in loans}
            | {bond.source_node_id for bond in bonds}
            | {bond.target_node_id for bond in bonds},
        )
        return LedgerView(
            loans=[
                LoanView(
                    id=loan.id,
                    lender_id=loan.lender_entity_id,
                    lender_name=names.get(loan.lender_entity_id, ""),
                    borrower_id=loan.borrower_entity_id,
                    borrower_name=names.get(loan.borrower_entity_id, ""),
                    currency_id=loan.currency_id,
                    principal=loan.principal,
                    interest_pct=loan.interest_pct,
                    repaid=loan.repaid,
                    owed=max(0, owed(loan)),
                    issued_epoch=loan.issued_epoch,
                    due_epoch=loan.due_epoch,
                    status=loan.status,
                    purpose=loan.purpose,
                )
                for loan in loans
            ],
            debts=[
                DebtView(
                    bond_id=bond.id,
                    debtor_id=bond.source_node_id,
                    debtor_name=names.get(bond.source_node_id, ""),
                    creditor_id=bond.target_node_id,
                    creditor_name=names.get(bond.target_node_id, ""),
                    amount=bond.debt_amount or 0,
                    what=bond.debt_what or "",
                    due_epoch=bond.debt_due_epoch,
                    currency_id=bond.debt_currency_id,
                )
                for bond in bonds
            ],
        )


@router.get("/markets", response_model=list[MarketSummary])
async def market_list(services: ServicesDep, world_id: int | None = Query(default=None, ge=1)) -> list[MarketSummary]:
    async with reader(services) as session:
        statement = select(EntityRow).join(WorkshopRow, WorkshopRow.community_entity_id == EntityRow.id).where(WorkshopRow.kind == WorkshopKind.MARKET)
        if world_id is not None:
            statement = statement.where(EntityRow.world_id == world_id)
        rows = list(await session.scalars(statement.order_by(EntityRow.name)))
        return [MarketSummary(id=row.id, name=row.name, world_id=row.world_id, entity_type=row.entity_type) for row in rows]
