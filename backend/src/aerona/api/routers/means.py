from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.means import (
    ArmyUnitChoice,
    AxesView,
    BillView,
    BuildingView,
    ChainView,
    CoinView,
    ContainerStockView,
    HoardView,
    HonoursNodeView,
    HouseholdChoice,
    MeansNodeView,
    NamedUnitView,
    NavigationKitView,
    OrderKindView,
    OrdersNodeView,
    OrderTransitionView,
    OrderView,
    PuttingOutView,
    RateView,
    SavingView,
    TouristFlowView,
    UnitHonourView,
    VaultView,
    VeteranGrantView,
    WaterLiftView,
    WritingCustomView,
    WrittenWorkView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.means import BUILDING, CONTAINERS, LIFTS, WATER_WORKS, aid_cut, container_capacity
from aerona.catalog.units import UNITS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import CurrencyRow, NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.honours import NamedUnitRow, UnitHonourRow, VeteranGrantRow, VeteranPolicyRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.means import ContainerStockRow, NavigationKitRow, SecurityRow, WaterLiftRow, WritingCustomRow, WrittenWorkRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.orders import (
    BillOfExchangeRow,
    ChainHoldingRow,
    EconomicOrderKindRow,
    EconomicOrderRow,
    ExchangeRateRow,
    HoardRow,
    OrderTransitionRow,
    PuttingOutRow,
    SavingRow,
    TouristFlowRow,
)
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.space_weather import WorldFieldRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.orders import AllocationMode, DistributionRule, OrderLabour, OwnershipRegime
from aerona.engine.body.customs import people_id_of
from aerona.engine.eras.effects import era_techniques
from aerona.engine.means.navigation import aid_works
from aerona.engine.sacred.places import town_of
from aerona.engine.space_weather.reading import compass_error_of
from aerona.rules.registry import Rules

router = APIRouter(tags=["means"])
NodeId = Annotated[int, Path(ge=1)]
ROWS = 200


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


def maybe(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return ref(refs, node_id) if node_id is not None else None


async def exists(session: AsyncSession, node_id: int) -> dict[int, NodeRef]:
    own = await node_refs(session, [node_id])
    if node_id not in own:
        raise NotFoundError("No such thing.")
    return own


async def home_town(session: AsyncSession, entity: EntityRow | None) -> EntityRow | None:
    if entity is None:
        return None
    if entity.entity_type is EntityType.SETTLEMENT:
        return entity
    return await town_of(session, entity)


async def realm_of(session: AsyncSession, entity: EntityRow | None, town: EntityRow | None) -> int | None:
    if entity is not None and entity.entity_type is EntityType.POLITY:
        return entity.id
    if town is None:
        return None
    found = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town.id).limit(1))
    return int(found) if found is not None else None


async def building_of(session: AsyncSession, rules: Rules, work: EntityRow) -> BuildingView | None:
    profile = await session.get(StructureProfileRow, work.id)
    if profile is None:
        return None
    body = await session.get(NodeMaterialRow, (work.id, MaterialSlot.BODY))
    material = body.material if body is not None else None
    spec = BUILDING.get(material) if material is not None else None
    region = await session.get(RegionEnvironmentRow, work.location_id) if work.location_id is not None else None
    damp = PERCENT if profile.kind in WATER_WORKS else region.moisture if region is not None else PERCENT // 2
    water = spec.water if spec is not None else PERCENT
    known = await era_techniques(session, profile.host_entity_id or work.id)
    return BuildingView(
        material=material,
        water_resistance=water,
        needs=spec.needs if spec is not None else None,
        can_repair=spec is None or spec.needs is None or spec.needs in known,
        weathering_pct=PERCENT + damp * (PERCENT - water) * rules.building_materials.weathering_pct // PERCENT // PERCENT,
    )


@router.get("/means/of/{node_id}", response_model=MeansNodeView)
async def node_means(services: ServicesDep, node_id: NodeId) -> MeansNodeView:
    async with reader(services) as session:
        await exists(session, node_id)
        rules = await world_rules(services, session)
        entity = await session.get(EntityRow, node_id)
        town = await home_town(session, entity)
        folk = entity.id if entity is not None and entity.entity_type is EntityType.PEOPLE else await people_id_of(session, town)
        custom = await session.get(WritingCustomRow, folk) if folk is not None else None
        places = [item for item in (node_id, town.id if town is not None else None) if item is not None]
        kept = select(EntityRow.id).where(EntityRow.location_id.in_(places))
        works = list(
            await session.scalars(
                select(WrittenWorkRow)
                .where(or_(WrittenWorkRow.work_entity_id == node_id, WrittenWorkRow.work_entity_id.in_(kept)))
                .order_by(WrittenWorkRow.work_entity_id)
                .limit(ROWS)
            )
        )
        hosted = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.host_entity_id.in_(places))
        vaults = list(
            await session.scalars(
                select(SecurityRow)
                .where(or_(SecurityRow.holder_entity_id == node_id, SecurityRow.holder_entity_id.in_(hosted)))
                .order_by(SecurityRow.holder_entity_id)
            )
        )
        town_id = town.id if town is not None else 0
        lifts = list(await session.scalars(select(WaterLiftRow).where(WaterLiftRow.settlement_entity_id == town_id).order_by(WaterLiftRow.device)))
        kits = list(await session.scalars(select(NavigationKitRow).where(NavigationKitRow.holder_entity_id == town_id).order_by(NavigationKitRow.aid)))
        stocks = list(await session.scalars(select(ContainerStockRow).where(ContainerStockRow.community_entity_id == town_id).order_by(ContainerStockRow.kind)))
        world = await session.get(WorldRow, town.world_id) if town is not None else None
        error = compass_error_of(await session.get(WorldFieldRow, world.id)) if world is not None else 0
        accuracy = min(PERCENT, sum(row.quality * aid_cut(rules, row.aid) // PERCENT for row in kits if aid_works(rules, row, world, error)))
        building = await building_of(session, rules, entity) if entity is not None and entity.entity_type is EntityType.STRUCTURE else None
        named = {
            node_id,
            *places,
            *(item for item in (folk,) if item is not None),
            *(row.work_entity_id for row in works),
            *(row.holder_entity_id for row in vaults),
        }
        refs = await node_refs(session, sorted(named))
    return MeansNodeView(
        node=ref(refs, node_id),
        town=maybe(refs, town.id if town is not None else None),
        people=maybe(refs, folk),
        custom=WritingCustomView(people=ref(refs, custom.people_entity_id), medium=custom.medium, since_epoch=custom.since_epoch, locked=custom.locked)
        if custom is not None
        else None,
        works=[
            WrittenWorkView(
                work=ref(refs, row.work_entity_id),
                medium=row.medium,
                condition=row.condition,
                copies=row.copies,
                written_epoch=row.written_epoch,
                locked=row.locked,
            )
            for row in works
        ],
        vaults=[
            VaultView(
                holder=ref(refs, row.holder_entity_id),
                lock=row.lock,
                lock_quality=row.lock_quality,
                sealed=row.sealed,
                guards=row.guards,
                traps=row.traps,
                thwarted=row.thwarted,
                since_epoch=row.since_epoch,
                locked=row.locked,
            )
            for row in vaults
        ],
        lifts=[
            WaterLiftView(device=row.device, count=row.count, capacity=row.count * LIFTS[row.device].capacity, since_epoch=row.since_epoch, locked=row.locked)
            for row in lifts
        ],
        kits=[
            NavigationKitView(aid=row.aid, quality=row.quality, works=aid_works(rules, row, world, error), since_epoch=row.since_epoch, locked=row.locked)
            for row in kits
        ],
        accuracy=accuracy,
        containers=[
            ContainerStockView(
                kind=row.kind,
                count=row.count,
                broken=row.broken,
                capacity=row.count * container_capacity(rules, row.kind) * rules.containers.per_capacity,
                sealed=CONTAINERS[row.kind].sealed,
                locked=row.locked,
            )
            for row in stocks
        ],
        building=building,
    )


def axes_view(axes: dict[str, str]) -> AxesView:
    return AxesView(
        ownership=OwnershipRegime(axes["ownership"]) if "ownership" in axes else None,
        allocation=AllocationMode(axes["allocation"]) if "allocation" in axes else None,
        labour=OrderLabour(axes["labour"]) if "labour" in axes else None,
        distribution=DistributionRule(axes["distribution"]) if "distribution" in axes else None,
    )


@router.get("/orders/of/{node_id}", response_model=OrdersNodeView)
async def node_orders(services: ServicesDep, node_id: NodeId) -> OrdersNodeView:
    async with reader(services) as session:
        await exists(session, node_id)
        entity = await session.get(EntityRow, node_id)
        town = await home_town(session, entity)
        realm = await realm_of(session, entity, town)
        realm_key = realm if realm is not None else 0
        orders = list(await session.scalars(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == realm_key).order_by(EconomicOrderRow.id)))
        kinds = list(await session.scalars(select(EconomicOrderKindRow).order_by(EconomicOrderKindRow.id)))
        names = {row.id: row.name for row in kinds}
        transitions = list(
            await session.scalars(select(OrderTransitionRow).where(OrderTransitionRow.polity_entity_id == realm_key).order_by(OrderTransitionRow.id))
        )
        town_id = town.id if town is not None else 0
        homes = select(HouseholdMemberRow.household_id).where(HouseholdMemberRow.member_node_id == node_id)
        households = {
            row.id: row
            for row in await session.scalars(
                select(HouseholdRow).where(or_(HouseholdRow.settlement_node_id == town_id, HouseholdRow.id.in_(homes))).limit(ROWS)
            )
        }
        savings = list(await session.scalars(select(SavingRow).where(SavingRow.household_id.in_(list(households))).order_by(SavingRow.household_id)))
        places = [item for item in (node_id, town_id) if item]
        hoards = list(
            await session.scalars(
                select(HoardRow).where(or_(HoardRow.place_entity_id.in_(places), HoardRow.holder_node_id == node_id)).order_by(HoardRow.id).limit(ROWS)
            )
        )
        rates = list(await session.scalars(select(ExchangeRateRow).where(ExchangeRateRow.market_entity_id.in_(places)).order_by(ExchangeRateRow.id)))
        bills = list(
            await session.scalars(
                select(BillOfExchangeRow)
                .where(
                    or_(BillOfExchangeRow.from_entity_id.in_(places), BillOfExchangeRow.to_entity_id.in_(places), BillOfExchangeRow.drawer_node_id == node_id)
                )
                .order_by(BillOfExchangeRow.id)
                .limit(ROWS)
            )
        )
        put_out = list(
            await session.scalars(
                select(PuttingOutRow)
                .where(or_(PuttingOutRow.merchant_entity_id == node_id, PuttingOutRow.town_entity_id.in_(places)))
                .order_by(PuttingOutRow.id)
            )
        )
        chains = list(
            await session.scalars(
                select(ChainHoldingRow)
                .where(or_(ChainHoldingRow.holder_entity_id == node_id, ChainHoldingRow.town_entity_id.in_(places)))
                .order_by(ChainHoldingRow.holder_entity_id, ChainHoldingRow.town_entity_id)
            )
        )
        flows = list(
            await session.scalars(
                select(TouristFlowRow)
                .where(or_(TouristFlowRow.origin_entity_id.in_(places), TouristFlowRow.sight_entity_id == node_id))
                .order_by(TouristFlowRow.epoch.desc(), TouristFlowRow.id.desc())
                .limit(ROWS)
            )
        )
        world_id = entity.world_id if entity is not None else None
        issuers = select(EntityRow.id).where(EntityRow.world_id == world_id)
        coins = {row.id: row for row in await session.scalars(select(CurrencyRow).where(CurrencyRow.issuer_entity_id.in_(issuers)).order_by(CurrencyRow.id))}
        for row in rates:
            for coin_id in (row.base_currency_id, row.quote_currency_id):
                if coin_id not in coins and (stray := await session.get(CurrencyRow, coin_id)) is not None:
                    coins[coin_id] = stray
        named = {node_id, *places, *(item for item in (realm,) if item is not None)}
        named |= {item for row in hoards for item in (row.holder_node_id, row.place_entity_id, row.found_by_node_id) if item is not None}
        named |= {item for row in rates for item in (row.market_entity_id, row.changer_node_id) if item is not None}
        named |= {item for row in bills for item in (row.drawer_node_id, row.payee_node_id, row.from_entity_id, row.to_entity_id)}
        named |= {item for row in put_out for item in (row.merchant_entity_id, row.town_entity_id)}
        named |= {item for row in chains for item in (row.holder_entity_id, row.town_entity_id)}
        named |= {item for row in flows for item in (row.origin_entity_id, row.sight_entity_id)}
        refs = await node_refs(session, sorted(named))
    coin = {coin_id: CoinView(id=coin_id, name=row.name) for coin_id, row in coins.items()}
    return OrdersNodeView(
        node=ref(refs, node_id),
        realm=maybe(refs, realm),
        orders=[
            OrderView(
                id=row.id,
                sector=row.sector,
                ownership=row.ownership,
                allocation=row.allocation,
                labour=row.labour,
                distribution=row.distribution,
                planning_capacity=row.planning_capacity,
                kind_id=row.kind_id,
                kind_name=names.get(row.kind_id) if row.kind_id is not None else None,
                since_epoch=row.since_epoch,
                locked=row.locked,
            )
            for row in orders
        ],
        kinds=[
            OrderKindView(
                id=row.id,
                name=row.name,
                ownership=row.ownership,
                allocation=row.allocation,
                labour=row.labour,
                distribution=row.distribution,
                built_in=row.built_in,
                locked=row.locked,
            )
            for row in kinds
        ],
        transitions=[
            OrderTransitionView(
                id=row.id,
                sector=row.sector,
                kind=row.kind,
                stage=row.stage,
                compensation=row.compensation,
                resistance=row.resistance,
                transferred=row.transferred,
                from_axes=axes_view(row.from_axes),
                to_axes=axes_view(row.to_axes),
                started_epoch=row.started_epoch,
                ended_epoch=row.ended_epoch,
                locked=row.locked,
            )
            for row in transitions
        ],
        households=[HouseholdChoice(id=row.id, name=row.name) for row in sorted(households.values(), key=lambda item: item.id)],
        savings=[
            SavingView(
                household_id=row.household_id,
                household=households[row.household_id].name,
                share_pct=row.share_pct,
                form=row.form,
                saved=row.saved,
                updated_epoch=row.updated_epoch,
                locked=row.locked,
            )
            for row in savings
        ],
        hoards=[
            HoardView(
                id=row.id,
                holder=maybe(refs, row.holder_node_id),
                place=ref(refs, row.place_entity_id),
                amount=row.amount,
                state=row.state,
                hidden_epoch=row.hidden_epoch,
                found_by=maybe(refs, row.found_by_node_id),
                found_epoch=row.found_epoch,
                locked=row.locked,
            )
            for row in hoards
        ],
        coins=sorted(coin.values(), key=lambda item: item.id),
        rates=[
            RateView(
                id=row.id,
                base=coin.get(row.base_currency_id, CoinView(id=row.base_currency_id, name="a lost coin")),
                quote=coin.get(row.quote_currency_id, CoinView(id=row.quote_currency_id, name="a lost coin")),
                market=maybe(refs, row.market_entity_id),
                rate=row.rate,
                spread_pct=row.spread_pct,
                changer=maybe(refs, row.changer_node_id),
                convertible=row.convertible,
                volume=row.volume,
                updated_epoch=row.updated_epoch,
                locked=row.locked,
            )
            for row in rates
        ],
        bills=[
            BillView(
                id=row.id,
                drawer=ref(refs, row.drawer_node_id),
                payee=ref(refs, row.payee_node_id),
                from_market=ref(refs, row.from_entity_id),
                to_market=ref(refs, row.to_entity_id),
                amount=row.amount,
                issued_epoch=row.issued_epoch,
                settled=row.settled,
                locked=row.locked,
            )
            for row in bills
        ],
        putting_out=[
            PuttingOutView(
                id=row.id,
                merchant=ref(refs, row.merchant_entity_id),
                village=ref(refs, row.town_entity_id),
                raw=row.raw,
                product=row.product,
                volume=row.volume,
                active=row.active,
                since_epoch=row.since_epoch,
                locked=row.locked,
            )
            for row in put_out
        ],
        chains=[
            ChainView(
                holder=ref(refs, row.holder_entity_id),
                town=ref(refs, row.town_entity_id),
                product=row.product,
                share_pct=row.share_pct,
                since_epoch=row.since_epoch,
                locked=row.locked,
            )
            for row in chains
        ],
        flows=[
            TouristFlowView(
                id=row.id,
                origin=ref(refs, row.origin_entity_id),
                sight_node=ref(refs, row.sight_entity_id),
                sight=row.sight,
                visitors=row.visitors,
                income=row.income,
                epoch=row.epoch,
                locked=row.locked,
            )
            for row in flows
        ],
    )


@router.get("/honours/of/{node_id}", response_model=HonoursNodeView)
async def node_honours(services: ServicesDep, node_id: NodeId) -> HonoursNodeView:
    async with reader(services) as session:
        await exists(session, node_id)
        entity = await session.get(EntityRow, node_id)
        town = await home_town(session, entity)
        realm = await realm_of(session, entity, town)
        army = await session.get(ArmyRow, node_id)
        units = (
            list(await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == node_id).order_by(ArmyUnitRow.id))) if army is not None else []
        )
        unit_ids = [row.id for row in units]
        owners = [item for item in (node_id, realm) if item is not None]
        named = list(
            await session.scalars(
                select(NamedUnitRow)
                .where(or_(NamedUnitRow.unit_id.in_(unit_ids), NamedUnitRow.owner_entity_id.in_(owners), NamedUnitRow.raised_from_entity_id == node_id))
                .order_by(NamedUnitRow.esprit.desc(), NamedUnitRow.id)
                .limit(ROWS)
            )
        )
        honours: dict[int, list[UnitHonourRow]] = {}
        for row in await session.scalars(
            select(UnitHonourRow).where(UnitHonourRow.named_unit_id.in_([item.id for item in named])).order_by(UnitHonourRow.epoch, UnitHonourRow.id)
        ):
            honours.setdefault(row.named_unit_id, []).append(row)
        grants = list(
            await session.scalars(
                select(VeteranGrantRow)
                .where(or_(VeteranGrantRow.polity_entity_id.in_(owners), VeteranGrantRow.settlement_entity_id == node_id))
                .order_by(VeteranGrantRow.epoch.desc(), VeteranGrantRow.id.desc())
                .limit(ROWS)
            )
        )
        known = {node_id, *owners}
        known |= {item for row in named for item in (row.owner_entity_id, row.raised_from_entity_id) if item is not None}
        known |= {item for row in grants for item in (row.polity_entity_id, row.settlement_entity_id, row.war_entity_id) if item is not None}
        refs = await node_refs(session, sorted(known))
        policy = await session.get(VeteranPolicyRow, realm) if realm is not None else None
    return HonoursNodeView(
        policy=policy.grant if policy is not None else None,
        policy_locked=policy is not None and "grant" in policy.locked,
        node=ref(refs, node_id),
        realm=maybe(refs, realm),
        units=[
            NamedUnitView(
                id=row.id,
                unit_id=row.unit_id,
                owner=maybe(refs, row.owner_entity_id),
                name=row.name,
                nickname=row.nickname,
                raised_from=maybe(refs, row.raised_from_entity_id),
                esprit=row.esprit,
                battles=row.battles,
                formed_epoch=row.formed_epoch,
                disbanded_epoch=row.disbanded_epoch,
                honours=[UnitHonourView(id=item.id, kind=item.kind, note=item.note, epoch=item.epoch, locked=item.locked) for item in honours.get(row.id, [])],
                locked=row.locked,
            )
            for row in named
        ],
        choices=[ArmyUnitChoice(id=row.id, label=UNITS[row.kind].label, count=row.count) for row in units],
        grants=[
            VeteranGrantView(
                id=row.id,
                polity=ref(refs, row.polity_entity_id),
                kind=row.kind,
                veterans=row.veterans,
                settlement=maybe(refs, row.settlement_entity_id),
                war=maybe(refs, row.war_entity_id),
                epoch=row.epoch,
                locked=row.locked,
            )
            for row in grants
        ],
    )
