from sqlalchemy import select

from aerona.catalog.goods_tables import WORKSHOP_GOODS
from aerona.catalog.life_traits import ALLOCATION_MODE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.commerce import ShopGoodRow, ShopRow, SupplyTierRow
from aerona.db.tables.competition import MarketStructureRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.db.tables.orders import EconomicOrderRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.competition import CompetitionClause, EntryBarrier, MarketForm
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.life_traits import AllocationModeTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.competition.clauses import clause_strength
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of
from aerona.engine.factions.companies import realm_of
from aerona.engine.governance.seats import apportioned
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import headcount
from aerona.engine.recording.record import record

STATE_BUYERS = having(ALLOCATION_MODE_TRAITS, AllocationModeTrait.STATE_BUYERS)
SELLERS_LOCK = "sellers"
BARRIERS_LOCK = "barriers"
FORM_LOCK = "form"


async def guild_holder(ctx: TickContext, market_id: int, commodity: CommodityKind) -> int | None:
    found = await ctx.session.scalar(
        select(FactionProfileRow.faction_entity_id)
        .where(FactionProfileRow.home_entity_id == market_id, FactionProfileRow.monopoly == commodity.value)
        .order_by(FactionProfileRow.faction_entity_id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def named_sellers(ctx: TickContext, market_id: int, commodity: CommodityKind) -> tuple[dict[int, float], bool]:
    guild = await guild_holder(ctx, market_id, commodity)
    if guild is not None:
        return {guild: float(PERCENT)}, False
    found: dict[int, float] = {}
    commons = False
    for tier in await ctx.session.scalars(
        select(SupplyTierRow).where(SupplyTierRow.market_entity_id == market_id, SupplyTierRow.commodity == commodity).order_by(SupplyTierRow.id)
    ):
        if tier.holder_node_id == market_id:
            commons = True
            continue
        found[tier.holder_node_id] = found.get(tier.holder_node_id, 0.0) + max(1, tier.share)
    for keeper in await ctx.session.scalars(
        select(ShopGoodRow.keeper_node_id)
        .join(ShopRow, ShopRow.id == ShopGoodRow.shop_id)
        .where(ShopRow.settlement_entity_id == market_id, ShopGoodRow.commodity == commodity)
        .order_by(ShopGoodRow.shop_id)
    ):
        found[keeper] = found.get(keeper, 0.0) + ctx.rules.competition.shop_weight
    for owner, kind, level in await ctx.session.execute(
        select(WorkshopRow.owner_node_id, WorkshopRow.kind, WorkshopRow.level)
        .where(WorkshopRow.community_entity_id == market_id, WorkshopRow.owner_node_id.is_not(None))
        .order_by(WorkshopRow.id)
    ):
        if owner is None or WORKSHOP_GOODS.get(kind) is not commodity:
            continue
        if owner == market_id:
            commons = True
            continue
        found[owner] = found.get(owner, 0.0) + max(1, level) * ctx.rules.competition.workshop_weight
    return found, commons


async def market_goods(ctx: TickContext) -> list[tuple[int, CommodityKind]]:
    pairs: set[tuple[int, CommodityKind]] = set()
    for market, commodity, holder in await ctx.session.execute(select(SupplyTierRow.market_entity_id, SupplyTierRow.commodity, SupplyTierRow.holder_node_id)):
        if commodity is not None and holder != market:
            pairs.add((market, commodity))
    for market, commodity in await ctx.session.execute(
        select(ShopRow.settlement_entity_id, ShopGoodRow.commodity).join(ShopGoodRow, ShopGoodRow.shop_id == ShopRow.id)
    ):
        pairs.add((market, commodity))
    for market, kind, owner in await ctx.session.execute(
        select(WorkshopRow.community_entity_id, WorkshopRow.kind, WorkshopRow.owner_node_id).where(WorkshopRow.owner_node_id.is_not(None))
    ):
        good = WORKSHOP_GOODS.get(kind)
        if good is not None and owner != market:
            pairs.add((market, good))
    for home, monopoly in await ctx.session.execute(
        select(FactionProfileRow.home_entity_id, FactionProfileRow.monopoly).where(
            FactionProfileRow.monopoly.is_not(None), FactionProfileRow.home_entity_id.is_not(None)
        )
    ):
        if home is not None and monopoly in {item.value for item in CommodityKind}:
            pairs.add((home, CommodityKind(monopoly)))
    return sorted(pairs, key=lambda pair: (pair[0], pair[1].value))


def concentration_of(shares: dict[str, int]) -> int:
    return clamp_int(round_half_up(sum(share * share for share in shares.values()) / PERCENT), 0, PERCENT)


async def state_buys(ctx: TickContext, market_id: int, commodity: CommodityKind) -> bool:
    realm = await realm_of(ctx, market_id)
    if realm is None:
        return False
    orders = list(await ctx.session.scalars(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == realm).order_by(EconomicOrderRow.id)))
    sector = next((order for order in orders if order.sector is commodity), None) or next((order for order in orders if order.sector is None), None)
    return sector is not None and sector.allocation in STATE_BUYERS


async def form_of(ctx: TickContext, market: EntityRow, commodity: CommodityKind, shares: dict[str, int], concentration: int) -> MarketForm:
    table = ctx.rules.competition
    if await state_buys(ctx, market.id, commodity):
        return MarketForm.ONE_BUYER
    if shares and max(shares.values()) >= table.one_seller_share:
        return MarketForm.ONE_SELLER
    if concentration >= table.few_sellers_concentration:
        return MarketForm.FEW_SELLERS
    if headcount(market) < table.few_buyers_population:
        return MarketForm.FEW_BUYERS
    return MarketForm.MANY_SELLERS


async def derived_barriers(ctx: TickContext, market_id: int, commodity: CommodityKind, top: int | None) -> dict[EntryBarrier, int]:
    table = ctx.rules.competition
    found: dict[EntryBarrier, int] = {}
    licence = await clause_strength(ctx, market_id, CompetitionClause.LICENCE_LIMIT)
    if licence:
        found[EntryBarrier.LICENCE] = clamp_int(round_half_up(licence * table.licence_barrier_pct / PERCENT), 0, PERCENT)
    seller = await ctx.session.get(EntityRow, top) if top is not None else None
    if seller is None:
        return found
    found[EntryBarrier.CAPITAL] = clamp_int(await points_of(ctx.session, seller), 0, PERCENT)
    if await guild_holder(ctx, market_id, commodity) == seller.id:
        found[EntryBarrier.GUILD_RIGHT] = table.guild_right_barrier
    secret = await ctx.session.scalar(
        select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == seller.id, HolderTechniqueRow.secret.is_(True)).limit(1)
    )
    if secret is not None:
        found[EntryBarrier.SECRET_TECHNIQUE] = table.secret_barrier
    company = await ctx.session.get(CompanyProfileRow, seller.id)
    if company is not None and company.route_entity_id is not None:
        found[EntryBarrier.ROUTE_CONTROL] = table.route_barrier
    network = await ctx.session.scalar(
        select(NetworkProfileRow.network_entity_id)
        .join(NetworkNodeRow, NetworkNodeRow.network_entity_id == NetworkProfileRow.network_entity_id)
        .where(NetworkProfileRow.owner_node_id == seller.id, NetworkNodeRow.member_node_id == market_id)
        .limit(1)
    )
    if network is not None:
        found[EntryBarrier.NETWORK_CONTROL] = table.network_barrier
    if await active_bonds(ctx.session, [BondKind.BLESSED], targets=[seller.id]):
        found[EntryBarrier.DIVINE_FAVOUR] = table.favour_barrier
    return found


async def weigh_barriers(ctx: TickContext, row: MarketStructureRow, wanted: dict[EntryBarrier, int]) -> list[EntryBarrier]:
    if BARRIERS_LOCK in (row.locked or []):
        return []
    decay = ctx.rules.competition.barrier_decay_per_epoch
    current = dict(row.barriers or {})
    fallen: list[EntryBarrier] = []
    for barrier in EntryBarrier:
        before = int(current.get(barrier.value, 0))
        target = wanted.get(barrier, 0)
        after = target if target >= before else max(target, before - decay)
        if after > 0:
            current[barrier.value] = after
        else:
            current.pop(barrier.value, None)
        if before > 0 and after == 0:
            fallen.append(barrier)
    row.barriers = current
    return fallen


async def survey_market(ctx: TickContext, market: EntityRow, commodity: CommodityKind) -> MarketStructureRow:
    row = await ctx.session.scalar(
        select(MarketStructureRow).where(MarketStructureRow.market_entity_id == market.id, MarketStructureRow.commodity == commodity)
    )
    if row is None:
        row = MarketStructureRow(market_entity_id=market.id, commodity=commodity, sellers={}, barriers={}, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    weights, commons = await named_sellers(ctx, market.id, commodity)
    if SELLERS_LOCK not in (row.locked or []):
        small = ctx.rules.competition.small_sellers_pct if commons or not weights else 0
        row.small_sellers_pct = small
        row.sellers = {str(node): share for node, share in apportioned(weights, PERCENT - small).items() if share > 0}
    row.concentration = concentration_of(row.sellers or {})
    if FORM_LOCK not in (row.locked or []):
        row.form = await form_of(ctx, market, commodity, row.sellers or {}, row.concentration)
    top = max(row.sellers or {}, key=lambda node: (row.sellers[node], node), default=None)
    for barrier in await weigh_barriers(ctx, row, await derived_barriers(ctx, market.id, commodity, int(top) if top is not None else None)):
        await record(ctx, "market.barrier_fell", roles={IncidentRole.PLACE: market.id}, facts={"barrier": barrier, "commodity": commodity}, place=market.id)
    row.updated_epoch = ctx.epoch
    return row


async def survey_markets(ctx: TickContext) -> int:
    surveyed = 0
    for market_id, commodity in await market_goods(ctx):
        market = await ctx.session.get(EntityRow, market_id)
        if market is None or market.status is not EntityStatus.CANON or held(market.id):
            continue
        await survey_market(ctx, market, commodity)
        surveyed += 1
    await ctx.session.flush()
    return surveyed


async def structure_of(ctx: TickContext, market_id: int, commodity: CommodityKind) -> MarketStructureRow | None:
    return await ctx.session.scalar(
        select(MarketStructureRow).where(MarketStructureRow.market_entity_id == market_id, MarketStructureRow.commodity == commodity)
    )
