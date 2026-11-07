from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select

from aerona.catalog.finance import ILLEGAL_GOODS
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import MarketPriceRow, ProductionRunRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.mind import PressureRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.mind import PressureKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import goods_of
from aerona.engine.industry.energy import industry_row
from aerona.engine.notes import note
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.services.war import ongoing_wars

OUTLAW_KINDS = (FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.VOID_PIRATES)
MERCHANT_GUILDS = (FactionKind.MERCHANT_GUILD, FactionKind.WANDERING_MARKET)
NOTE_CAP = 4


@dataclass(frozen=True)
class Terms:
    tariff_pct: int = 0
    subsidy_pct: int = 0
    embargo: bool = False
    illegal: bool = False
    access: float = 1.0
    informed: float = 1.0
    seller_realm: int | None = None
    buyer_realm: int | None = None

    @property
    def blocked(self) -> bool:
        return self.embargo or self.illegal


@dataclass
class PolicyTally:
    laid: int = 0
    lifted: int = 0
    smuggled: int = 0
    tariffs: int = 0
    subsidies: int = 0
    noted: int = 0


@dataclass
class PolicyBook:
    policies: dict[int, list[TradePolicyRow]] = field(default_factory=lambda: defaultdict(list))
    member_of: dict[int, int] = field(default_factory=dict)
    illegal: dict[int, set[CommodityKind]] = field(default_factory=dict)
    outlaws: dict[int, int] = field(default_factory=dict)
    access: dict[int, int] = field(default_factory=dict)
    informed: dict[int, float] = field(default_factory=dict)

    @classmethod
    async def load(cls, ctx: TickContext, book: EconomyBook) -> "PolicyBook":
        found = cls()
        for row in await ctx.session.scalars(select(TradePolicyRow).order_by(TradePolicyRow.id)):
            found.policies[row.issuer_node_id].append(row)
        for member in await ctx.session.scalars(select(PolityMemberRow)):
            found.member_of[member.member_entity_id] = member.polity_entity_id
        laws = await LawBook.load(ctx.session)
        table = ctx.rules.arbitrage
        guilds = {
            row.home_entity_id
            for row in await ctx.session.scalars(select(FactionProfileRow).where(FactionProfileRow.kind.in_(list(MERCHANT_GUILDS))))
            if row.home_entity_id
        }
        gangs = select(FactionProfileRow).where(FactionProfileRow.kind.in_(list(OUTLAW_KINDS))).order_by(FactionProfileRow.faction_entity_id)
        for gang in await ctx.session.scalars(gangs):
            if gang.home_entity_id is not None:
                found.outlaws.setdefault(gang.home_entity_id, gang.faction_entity_id)
        for community in book.communities:
            banned = {good for law, goods in ILLEGAL_GOODS.items() if laws.in_force(community.id, law) is not None for good in goods}
            if banned:
                found.illegal[community.id] = banned
            industry = book.industry.get(community.id)
            found.access[community.id] = industry.market_access if industry is not None else PERCENT
            society = book.societies.get(community.id)
            merchants = society.share(SocialClass.MERCHANT) if society is not None else 0.0
            found.informed[community.id] = 1 + merchants / PERCENT * table.merchant_pct / PERCENT + (table.guild_pct / PERCENT if community.id in guilds else 0)
        return found

    def realm_of(self, node_id: int) -> int | None:
        return self.member_of.get(node_id)

    def rate(self, issuer: int | None, kind: TradePolicyKind, commodity: CommodityKind, partner: int | None) -> int:
        if issuer is None:
            return 0
        rates = [
            row.rate_pct if kind is not TradePolicyKind.EMBARGO else PERCENT
            for row in self.policies.get(issuer, [])
            if row.kind is kind and row.commodity in (None, commodity) and row.partner_node_id in (None, partner)
        ]
        return max(rates, default=0)

    def terms(self, seller: int, buyer: int, commodity: CommodityKind) -> Terms:
        seller_realm, buyer_realm = self.realm_of(seller), self.realm_of(buyer)
        foreign = seller_realm != buyer_realm
        tariff = self.rate(buyer_realm, TradePolicyKind.TARIFF, commodity, seller_realm) if foreign else 0
        embargo = foreign and (
            self.rate(buyer_realm, TradePolicyKind.EMBARGO, commodity, seller_realm) > 0
            or self.rate(seller_realm, TradePolicyKind.EMBARGO, commodity, buyer_realm) > 0
        )
        return Terms(
            tariff_pct=tariff,
            subsidy_pct=self.rate(seller_realm, TradePolicyKind.SUBSIDY, commodity, None),
            embargo=embargo,
            illegal=commodity in self.illegal.get(buyer, set()),
            access=self.access.get(seller, PERCENT) / PERCENT,
            informed=(self.informed.get(seller, 1.0) + self.informed.get(buyer, 1.0)) / 2,
            seller_realm=seller_realm,
            buyer_realm=buyer_realm,
        )


async def smuggle(
    ctx: TickContext,
    book: EconomyBook,
    policies: PolicyBook,
    *,
    seller: int,
    buyer: int,
    commodity: CommodityKind,
    volume: int,
    landed: float,
    tally: PolicyTally,
) -> int:
    table = ctx.rules.trade_policy
    outlaw = policies.outlaws.get(buyer) or policies.outlaws.get(seller)
    units = round_half_up(volume * table.smuggle_share_pct / PERCENT)
    if outlaw is None or units <= 0 or held(buyer) or held(seller):
        return 0
    ledger = goods_of(ctx.session, ctx.epoch)
    moved = 0
    for lot in await ledger.take(seller, commodity, units, GoodsFlow.TRADE):
        moved += await ledger.add(
            buyer, commodity, lot.quantity, GoodsFlow.TRADE, material=lot.material, world_material_id=lot.world_material_id, quality=lot.quality
        )
    if moved <= 0:
        return 0
    value = round_half_up(landed * moved / PERCENT * (1 + table.smuggle_premium_pct / PERCENT))
    gang = await ctx.session.get(FactionProfileRow, outlaw)
    if gang is not None and not held(outlaw):
        gang.treasury += value
    town = await ctx.session.get(SettlementProfileRow, buyer)
    if town is not None and "crime" not in (town.locked or []):
        town.crime = clamp_int(town.crime + moved * table.crime_per_10_units / 10, 0, PERCENT)
    row = industry_row(ctx, book, buyer)
    if "black_market" not in row.locked:
        row.black_market += moved
    tally.smuggled += moved
    if tally.noted < NOTE_CAP:
        tally.noted += 1
        gang_entity = book.entities.get(outlaw)
        target = book.entities.get(buyer)
        await note(
            ctx,
            f"{gang_entity.name if gang_entity else 'Smugglers'} slipped {moved} loads of forbidden goods into {target.name if target else 'the market'}.",
            key="trade_policy.smuggled",
            ids=[item for item in (outlaw, buyer) if item],
            kind=ChronicleKind.TRADE,
        )
    return moved


async def lay(
    ctx: TickContext, realm_id: int, kind: TradePolicyKind, *, commodity: CommodityKind | None, partner: int | None, rate: int, reason: str
) -> TradePolicyRow:
    row = TradePolicyRow(
        issuer_node_id=realm_id, kind=kind, commodity=commodity, partner_node_id=partner, rate_pct=rate, since_epoch=ctx.epoch, reason=reason[:120], locked=[]
    )
    ctx.session.add(row)
    return row


def existing(policies: PolicyBook, realm_id: int, kind: TradePolicyKind, commodity: CommodityKind | None, partner: int | None) -> TradePolicyRow | None:
    return next(
        (row for row in policies.policies.get(realm_id, []) if row.kind is kind and row.commodity == commodity and row.partner_node_id == partner), None
    )


async def imported_made(ctx: TickContext, members: list[int]) -> set[CommodityKind]:
    table = ctx.rules.trade_policy
    made = set(
        await ctx.session.scalars(
            select(ProductionRunRow.output).where(ProductionRunRow.community_entity_id.in_(members), ProductionRunRow.epoch >= ctx.epoch - 1)
        )
    )
    owned = set(
        await ctx.session.scalars(
            select(WorkshopRow.community_entity_id).where(WorkshopRow.community_entity_id.in_(members), WorkshopRow.owner_node_id.is_not(None))
        )
    )
    if not owned:
        return set()
    flooded: set[CommodityKind] = set()
    statement = select(MarketPriceRow.commodity, func.sum(MarketPriceRow.imported), func.sum(MarketPriceRow.supply)).where(
        MarketPriceRow.market_entity_id.in_(members), MarketPriceRow.epoch == ctx.epoch - 1
    )
    for commodity, imported, supply in await ctx.session.execute(statement.group_by(MarketPriceRow.commodity)):
        if commodity in made and supply and int(imported or 0) * PERCENT >= int(supply) * table.import_share_pct:
            flooded.add(commodity)
    return flooded


async def hungry_members(ctx: TickContext, members: list[int]) -> bool:
    found = await ctx.session.scalar(
        select(PressureRow.entity_id)
        .where(PressureRow.entity_id.in_(members), PressureRow.pressure == PressureKind.HUNGER, PressureRow.value >= ctx.rules.trade_policy.subsidy_hunger)
        .limit(1)
    )
    return found is not None


async def enemies_of(ctx: TickContext, realm: EntityRow, policies: PolicyBook) -> set[int]:
    enemies: set[int] = set()
    for war in await ongoing_wars(ctx.session, realm.id):
        other = war.defender_id if war.attacker_id == realm.id else war.attacker_id
        enemies.add(policies.realm_of(other) or other)
    return enemies


async def tend_policies(ctx: TickContext, book: EconomyBook, policies: PolicyBook, tally: PolicyTally) -> None:
    table = ctx.rules.trade_policy
    members_of: dict[int, list[int]] = defaultdict(list)
    for member, realm_id in policies.member_of.items():
        members_of[realm_id].append(member)
    for profile in await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id)):
        realm = book.entities.get(profile.polity_entity_id)
        if realm is None or held(realm.id):
            continue
        rng = ctx.rng(f"trade_policy.{realm.id}.{ctx.epoch}")
        members = members_of.get(realm.id, [])
        flooded = await imported_made(ctx, members)
        for commodity in sorted(flooded, key=lambda item: item.value):
            if existing(policies, realm.id, TradePolicyKind.TARIFF, commodity, None) is None and rng.chance(table.tariff_chance):
                policies.policies[realm.id].append(
                    await lay(
                        ctx,
                        realm.id,
                        TradePolicyKind.TARIFF,
                        commodity=commodity,
                        partner=None,
                        rate=table.tariff_rate,
                        reason="its owners pressed against cheap imports",
                    )
                )
                tally.laid += 1
        enemies = await enemies_of(ctx, realm, policies)
        for enemy in sorted(enemies):
            if existing(policies, realm.id, TradePolicyKind.EMBARGO, None, enemy) is None and rng.chance(table.embargo_chance):
                policies.policies[realm.id].append(
                    await lay(ctx, realm.id, TradePolicyKind.EMBARGO, commodity=None, partner=enemy, rate=PERCENT, reason="at war")
                )
                tally.laid += 1
        hungry = await hungry_members(ctx, members)
        if hungry and profile.treasury >= table.subsidy_treasury and existing(policies, realm.id, TradePolicyKind.SUBSIDY, CommodityKind.GRAIN, None) is None:
            policies.policies[realm.id].append(
                await lay(
                    ctx,
                    realm.id,
                    TradePolicyKind.SUBSIDY,
                    commodity=CommodityKind.GRAIN,
                    partner=None,
                    rate=table.subsidy_rate,
                    reason="its people went hungry",
                )
            )
            tally.laid += 1
        for row in list(policies.policies.get(realm.id, [])):
            if row.locked:
                continue
            passed = (
                (row.kind is TradePolicyKind.TARIFF and row.commodity not in flooded)
                or (row.kind is TradePolicyKind.EMBARGO and row.partner_node_id not in enemies)
                or (row.kind is TradePolicyKind.SUBSIDY and not hungry)
            )
            if passed and row.since_epoch < ctx.epoch and rng.chance(table.lift_chance):
                policies.policies[realm.id].remove(row)
                await ctx.session.delete(row)
                tally.lifted += 1


async def subsidy_paid(
    ctx: TickContext, policies: PolicyBook, community_id: int, commodity: CommodityKind, revenue: float, *, tally: PolicyTally | None
) -> int:
    realm_id = policies.realm_of(community_id)
    rate = policies.rate(realm_id, TradePolicyKind.SUBSIDY, commodity, None)
    if realm_id is None or rate <= 0:
        return 0
    profile = await ctx.session.get(PolityProfileRow, realm_id)
    paid = min(round_half_up(revenue * rate / PERCENT), profile.treasury if profile is not None else 0)
    if profile is None or paid <= 0 or held(realm_id):
        return 0
    profile.treasury -= paid
    if tally is not None:
        tally.subsidies += paid
    return paid
