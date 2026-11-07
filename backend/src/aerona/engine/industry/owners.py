from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.ownership import GUILD_KINDS, OWNER_CLASS
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import ProductionRunRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.faith import CultDoctrineRow, CultHoldingRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.ownership import SiteProfitRow
from aerona.db.tables.polity import HouseProfileRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.faction import FactionGoalKind
from aerona.domain.enums.industry import OwnerClass
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.finance.access import sold_share
from aerona.engine.finance.policy import PolicyBook, PolicyTally, subsidy_paid
from aerona.engine.industry.methods import local_price
from aerona.engine.industry.quality import premium
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity

TENTH = 10
HARVEST_STEP = "harvest"


@dataclass
class ProfitTally:
    owned: int = 0
    sites: int = 0
    profit: int = 0
    losses: int = 0
    invested: int = 0
    taxes: int = 0
    lobbied: int = 0


@dataclass
class Ledger:
    owner: int | None
    community: int
    workshop: int | None
    resource: int | None
    site: str
    revenue: float = 0.0
    inputs: float = 0.0
    wages: float = 0.0
    upkeep: float = 0.0


async def owner_for(ctx: TickContext, community: EntityRow, owner_class: OwnerClass) -> int:
    session = ctx.session
    if owner_class in GUILD_KINDS:
        found = await session.scalar(
            select(FactionProfileRow.faction_entity_id)
            .where(FactionProfileRow.home_entity_id == community.id, FactionProfileRow.kind.in_(list(GUILD_KINDS[owner_class])))
            .order_by(FactionProfileRow.faction_entity_id)
            .limit(1)
        )
        return found if found is not None else community.id
    if owner_class is OwnerClass.CULT:
        found = await session.scalar(
            select(CultHoldingRow.cult_entity_id).where(CultHoldingRow.holding_entity_id == community.id).order_by(CultHoldingRow.cult_entity_id).limit(1)
        )
        return found if found is not None else community.id
    if owner_class is OwnerClass.REALM:
        found = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community.id).limit(1))
        return found if found is not None else community.id
    if owner_class is OwnerClass.HOUSE:
        for house in await session.scalars(select(HouseProfileRow).order_by(HouseProfileRow.house_entity_id)):
            if community.id in (house.seats or []):
                return house.house_entity_id
    return community.id


async def assign_owners(ctx: TickContext, book: EconomyBook, tally: ProfitTally) -> None:
    for community in book.communities:
        if held(community.id):
            continue
        for workshop in book.workshops.get(community.id, {}).values():
            if workshop.owner_node_id is not None or workshop.held:
                continue
            workshop.owner_node_id = await owner_for(ctx, community, OWNER_CLASS.get(workshop.kind, OwnerClass.COMMUNITY))
            tally.owned += 1


async def credit_owner(ctx: TickContext, owner_id: int | None, value: int) -> None:
    if owner_id is None or value == 0 or held(owner_id):
        return
    session = ctx.session
    table = ctx.rules.ownership
    for row_type, column in (
        (FactionProfileRow, "treasury"),
        (CultDoctrineRow, "treasury"),
        (PolityProfileRow, "treasury"),
        (SettlementProfileRow, "treasury"),
        (HouseProfileRow, "wealth"),
    ):
        row = await session.get(row_type, owner_id)
        if row is not None:
            setattr(row, column, max(0, int(getattr(row, column)) + value))
            return
    mortal = await session.get(MortalProfileRow, owner_id)
    if mortal is not None:
        if "standing" not in (mortal.locked or []):
            mortal.wealth = clamp_int(mortal.wealth + value / table.wealth_per_value, 0, PERCENT)
        return
    owner = await session.get(EntityRow, owner_id)
    if owner is not None:
        add_prosperity(ctx.rules, owner, round_half_up(value / table.prosperity_per_value))


async def purse_value(ctx: TickContext, owner_id: int) -> int:
    session = ctx.session
    for row_type, column in (
        (FactionProfileRow, "treasury"),
        (CultDoctrineRow, "treasury"),
        (PolityProfileRow, "treasury"),
        (SettlementProfileRow, "treasury"),
        (HouseProfileRow, "wealth"),
    ):
        row = await session.get(row_type, owner_id)
        if row is not None:
            return int(getattr(row, column))
    mortal = await session.get(MortalProfileRow, owner_id)
    return mortal.wealth * ctx.rules.ownership.wealth_per_value if mortal is not None else 0


async def buy(ctx: TickContext, workshop: WorkshopRow, buyer_id: int) -> int | None:
    price = workshop.level * ctx.rules.ownership.price_per_level
    if workshop.owner_node_id == buyer_id or await purse_value(ctx, buyer_id) < price:
        return None
    await credit_owner(ctx, buyer_id, -price)
    await credit_owner(ctx, workshop.owner_node_id or workshop.community_entity_id, price)
    workshop.owner_node_id = buyer_id
    return price


def run_value(book: EconomyBook, ctx: TickContext, run: ProductionRunRow) -> tuple[float, float]:
    revenue = run.quantity * local_price(book, run.community_entity_id, run.output) * premium(ctx.rules, run.quality)
    inputs = sum(
        units * local_price(book, run.community_entity_id, CommodityKind(commodity)) for commodity, units in run.inputs.items() if commodity in COMMODITY_KEYS
    )
    return revenue, inputs


COMMODITY_KEYS = frozenset(kind.value for kind in CommodityKind)


async def ledgers_of(
    ctx: TickContext, book: EconomyBook, *, policies: PolicyBook | None = None, policy_tally: PolicyTally | None = None
) -> dict[tuple[int, str], Ledger]:
    table = ctx.rules.ownership
    ledgers: dict[tuple[int, str], Ledger] = {}
    runs = await ctx.session.scalars(
        select(ProductionRunRow).where(ProductionRunRow.epoch == ctx.epoch, ProductionRunRow.quantity > 0).order_by(ProductionRunRow.id)
    )
    for run in runs:
        community = run.community_entity_id
        workshop = book.workshop(community, run.workshop) if run.workshop is not None and run.resource_entity_id is None else None
        if run.resource_entity_id is not None:
            owners = book.owners.get(run.resource_entity_id, [])
            key = (community, f"resource.{run.resource_entity_id}")
            ledger = ledgers.setdefault(key, Ledger(owners[0] if owners else community, community, None, run.resource_entity_id, run.step))
        elif run.step == HARVEST_STEP:
            key = (community, "fields")
            if key not in ledgers:
                land = book.entities.get(community)
                landlord = await owner_for(ctx, land, OwnerClass.HOUSE) if land is not None else community
                ledgers[key] = Ledger(landlord, community, None, None, "fields")
            ledger = ledgers[key]
        elif workshop is not None:
            key = (community, f"workshop.{workshop.id}")
            ledger = ledgers.setdefault(key, Ledger(workshop.owner_node_id or community, community, workshop.id, None, workshop.kind.value))
            ledger.upkeep = workshop.level * table.upkeep_per_level
        else:
            continue
        revenue, inputs = run_value(book, ctx, run)
        revenue *= sold_share(ctx.rules, book.industry.get(community))
        if policies is not None:
            revenue += await subsidy_paid(ctx, policies, community, run.output, revenue, tally=policy_tally)
        ledger.revenue += revenue
        ledger.inputs += inputs
        ledger.wages += run.workers * table.wage_per_10_workers / TENTH
    return ledgers


async def settle(ctx: TickContext, book: EconomyBook, ledger: Ledger, tally: ProfitTally) -> SiteProfitRow:
    table = ctx.rules.ownership
    settlement = await ctx.session.get(SettlementProfileRow, ledger.community)
    taxes = ledger.revenue * (settlement.tax_rate if settlement is not None else 0) / PERCENT
    profit = round_half_up(ledger.revenue - ledger.inputs - ledger.wages - ledger.upkeep - taxes)
    invested = round_half_up(profit * table.invest_pct / PERCENT) if profit > 0 and settlement is not None else 0
    row = SiteProfitRow(
        epoch=ctx.epoch,
        owner_node_id=ledger.owner,
        community_node_id=ledger.community,
        workshop_id=ledger.workshop,
        resource_node_id=ledger.resource,
        site=ledger.site,
        revenue=round_half_up(ledger.revenue),
        inputs=round_half_up(ledger.inputs),
        wages=round_half_up(ledger.wages),
        upkeep=round_half_up(ledger.upkeep),
        taxes=round_half_up(taxes),
        profit=profit,
        invested=invested,
        locked=[],
    )
    ctx.session.add(row)
    if settlement is not None and not held(ledger.community):
        settlement.treasury += row.taxes
        if "investment_pool" not in (settlement.locked or []):
            settlement.investment_pool += invested
    community = book.entities.get(ledger.community)
    if community is not None and not held(community.id):
        add_prosperity(ctx.rules, community, round_half_up(row.wages / table.prosperity_per_value))
    await credit_owner(ctx, ledger.owner, profit - invested)
    tally.sites += 1
    tally.taxes += row.taxes
    tally.invested += invested
    if profit >= 0:
        tally.profit += profit
    else:
        tally.losses -= profit
    return row


async def press(ctx: TickContext, faction_id: int, kind: FactionGoalKind, *, target: int | None, key: str | None, progress: int) -> bool:
    if held(faction_id):
        return False
    goal = await ctx.session.scalar(
        select(FactionGoalRow).where(FactionGoalRow.faction_entity_id == faction_id, FactionGoalRow.kind == kind, FactionGoalRow.achieved_epoch.is_(None))
    )
    if goal is None:
        goal = FactionGoalRow(
            faction_entity_id=faction_id,
            kind=kind,
            target_node_id=target,
            target_key=key,
            priority=PERCENT // 2,
            progress=0,
            since_epoch=ctx.epoch,
            set_by_player=False,
            locked=[],
        )
        ctx.session.add(goal)
    if "progress" not in goal.locked:
        goal.progress = clamp_int(goal.progress + progress, 0, PERCENT)
    return True


async def lobby(ctx: TickContext, book: EconomyBook, rows: list[SiteProfitRow], banned: set[int], tally: ProfitTally) -> None:
    table = ctx.rules.ownership
    revenue: dict[int, int] = defaultdict(int)
    taxes: dict[int, int] = defaultdict(int)
    homes: dict[int, int] = {}
    for row in rows:
        if row.owner_node_id is None:
            continue
        revenue[row.owner_node_id] += row.revenue
        taxes[row.owner_node_id] += row.taxes
        homes.setdefault(row.owner_node_id, row.community_node_id)
    for owner_id in sorted(revenue):
        profile = await ctx.session.get(FactionProfileRow, owner_id)
        if profile is None:
            continue
        home = homes[owner_id]
        realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == home).limit(1))
        if revenue[owner_id] > 0 and taxes[owner_id] * PERCENT >= revenue[owner_id] * table.lobby_tax_pct:
            tally.lobbied += await press(ctx, owner_id, FactionGoalKind.LOWER_TAXES, target=realm or home, key=None, progress=table.lobby_progress)
        if home in banned:
            tally.lobbied += await press(
                ctx, owner_id, FactionGoalKind.ABOLISH_LAW, target=realm or home, key=LawKind.MAGIC_BAN.value, progress=table.law_progress
            )


async def magic_banned(session: AsyncSession, book: EconomyBook) -> set[int]:
    laws = await LawBook.load(session)
    return {community.id for community in book.communities if laws.in_force(community.id, LawKind.MAGIC_BAN) is not None}


def barred_works(book: EconomyBook, banned: set[int]) -> set[int]:
    return {community_id for community_id in banned if (row := book.industry.get(community_id)) is not None and row.magic > 0}


async def owners_starved(session: AsyncSession, community_id: int) -> int:
    statement = select(WorkshopRow.owner_node_id).where(WorkshopRow.community_entity_id == community_id, WorkshopRow.owner_node_id.is_not(None))
    rows = await session.scalars(statement)
    return len({owner for owner in rows if owner is not None and owner != community_id})


async def tend_profits(ctx: TickContext, book: EconomyBook, tally: ProfitTally) -> list[SiteProfitRow]:
    await assign_owners(ctx, book, tally)
    policies = await PolicyBook.load(ctx, book)
    ledgers = await ledgers_of(ctx, book, policies=policies, policy_tally=PolicyTally())
    rows = [await settle(ctx, book, ledger, tally) for ledger in ledgers.values() if not held(ledger.community)]
    banned = barred_works(book, await magic_banned(ctx.session, book))
    await lobby(ctx, book, rows, banned, tally)
    return rows
