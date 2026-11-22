from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.polity import BASE_OF_TAX_KINDS
from aerona.catalog.life_traits import TAX_KIND_TRAITS, having
from aerona.catalog.taxes import TAXES
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.affairs import TaxPolicyRow
from aerona.db.tables.culture import IdeologyTenetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import IdeologyTenet, Technique
from aerona.domain.enums.life_traits import TaxKindTrait
from aerona.domain.enums.mind import TraitKind, ValueAxis
from aerona.domain.enums.settlement import DistrictKind, TreasuryEntry
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import TaxKind
from aerona.engine.context import TickContext
from aerona.engine.law.records import records_of
from aerona.engine.lore.civics import realm_allows
from aerona.engine.mind.book import traits_of, values_for
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.regime.book import corruption_pull, extraction_of

C = SocialClass
CLEAN_CREEDS = frozenset({IdeologyTenet.LEGALISM, IdeologyTenet.ASCETICISM})
RATE_UNIT = 10
CORRUPTION = "corruption"
EFFICIENCY = "efficiency"
TAKE = "take"


@dataclass
class RevenueTally:
    gathered: int = 0
    farmed: int = 0
    tithed: int = 0


async def policies_of(ctx: TickContext, realm: Realm) -> dict[TaxKind, TaxPolicyRow]:
    rows = {row.kind: row for row in await ctx.session.scalars(select(TaxPolicyRow).where(TaxPolicyRow.polity_entity_id == realm.entity.id))}
    for kind in TaxKind:
        if kind not in rows:
            rate = TAXES[kind].rate if kind is not TaxKind.TITHE or realm.profile.state_religion_id is not None else 0
            row = TaxPolicyRow(polity_entity_id=realm.entity.id, kind=kind, rate=rate, epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
            rows[kind] = row
    await ctx.session.flush()
    return rows


async def officers_greed(ctx: TickContext, realm: Realm) -> int:
    table = ctx.rules.affairs
    total = 0
    for office in realm.offices:
        if office.holder_entity_id is None:
            continue
        traits = await traits_of(ctx.session, office.holder_entity_id)
        total += table.greed_corruption * (TraitKind.GREEDY in traits) - table.honest_corruption * (TraitKind.HONEST in traits)
    return total


async def mean_justice(ctx: TickContext, laws: LawBook, realm: Realm) -> float:
    justices = [stat_or(laws.laws[law_id], "justice", PERCENT // 2) for law_id in laws.by_node.get(realm.entity.id, []) if law_id in laws.laws]
    return sum(justices) / len(justices) if justices else PERCENT / 2


async def breed_corruption(ctx: TickContext, laws: LawBook, realm: Realm, policies: dict[TaxKind, TaxPolicyRow]) -> None:
    table = ctx.rules.affairs
    if CORRUPTION in realm.profile.locked:
        return
    creed = realm.profile.ideology_entity_id
    tenets = set(await ctx.session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == creed))) if creed is not None else set()
    aim = (
        min(PERCENT, realm.profile.overextension) * table.overreach_pct / PERCENT
        + max(0.0, PERCENT / 2 - await mean_justice(ctx, laws, realm))
        + await officers_greed(ctx, realm)
        + sum(table.farm_corruption for row in policies.values() if row.farmed and row.rate > 0)
        - (table.creed_corruption if tenets & CLEAN_CREEDS else 0)
        + await corruption_pull(ctx.session, ctx.rules, realm.entity.id)
    )
    if await realm_allows(ctx.session, realm, Technique.BUREAUCRACY):
        aim = aim * (PERCENT - ctx.rules.technique_effects.corruption_cut_pct) / PERCENT
    aim = clamp_int(aim, 0, PERCENT)
    realm.profile.corruption = clamp_int(
        realm.profile.corruption + round_half_up((aim - realm.profile.corruption) * table.corruption_drift_pct / PERCENT), 0, PERCENT
    )


async def trade_points(ctx: TickContext, realm: Realm) -> int:
    members = list(realm.members)
    if not members:
        return 0
    routes = len(await active_bonds(ctx.session, [BondKind.TRADES_WITH], sources=members))
    markets = await market_districts(ctx.session)
    return routes + sum(markets.get(member, 0) for member in set(members))


@memoized(DistrictRow)
async def market_districts(session: AsyncSession) -> dict[int, int]:
    found: dict[int, int] = {}
    for settlement in await session.scalars(select(DistrictRow.settlement_entity_id).where(DistrictRow.kind == DistrictKind.MARKET)):
        found[settlement] = found.get(settlement, 0) + 1
    return found


@memoized(CompanyProfileRow)
async def companies_by_polity(session: AsyncSession) -> dict[int, int]:
    found: dict[int, int] = {}
    for polity in await session.scalars(select(CompanyProfileRow.polity_entity_id)):
        if polity is not None:
            found[polity] = found.get(polity, 0) + 1
    return found


async def kept_share(ctx: TickContext, realm: Realm, kind: TaxKind) -> float:
    spec = TAXES[kind]
    records = min(ctx.rules.registries.records_cap, await records_of(ctx, realm.entity.id))
    cost = spec.collection * (PERCENT - min(PERCENT, realm.profile.administration)) / PERCENT * (PERCENT - records) / PERCENT
    lawful = (await values_for(ctx.session, realm.entity.id)).get(ValueAxis.LAW, 0)
    evaded = spec.evasion * (PERCENT - lawful) / (2 * PERCENT)
    return max(0.0, (PERCENT - cost) / PERCENT * (PERCENT - evaded) / PERCENT * spec.take_pct / PERCENT)


async def company_points(ctx: TickContext, realm: Realm) -> int:
    return (await companies_by_polity(ctx.session)).get(realm.entity.id, 0)


SHARE_TAXES = having(TAX_KIND_TRAITS, TaxKindTrait.SHARE_TAXES)
HEAD_TAXES = having(TAX_KIND_TRAITS, TaxKindTrait.HEAD_TAXES)


async def base_of(ctx: TickContext, book: RealmBook, realm: Realm, kind: TaxKind) -> float:
    table = ctx.rules.affairs
    if kind in BASE_OF_TAX_KINDS:
        return float(await trade_points(ctx, realm) * table.trade_take)
    if kind is TaxKind.COMPANY:
        return float(await company_points(ctx, realm) * table.trade_take)
    if kind is TaxKind.LICENCE:
        return float((await trade_points(ctx, realm) + await company_points(ctx, realm)) * table.trade_take) / 2
    total = 0.0
    for member in book.members(realm):
        shares = await class_shares(ctx.session, ctx.rules, member.id)
        prosperity = stat_or(member, "prosperity", PERCENT // 2)
        if kind in HEAD_TAXES:
            total += (stat(member, "population") or 0) / 1000 * table.poll_take
        elif kind in SHARE_TAXES:
            payers = sum(shares.get(social_class, 0.0) for social_class in TAXES[kind].classes)
            total += prosperity * payers / PERCENT * table.consumption_take / RATE_UNIT
        elif kind is TaxKind.CONSUMPTION:
            spenders = shares.get(C.NOBLE, 0.0) + shares.get(C.MERCHANT, 0.0) + shares.get(C.PROFESSIONAL, 0.0) + shares.get(C.CITIZEN, 0.0)
            total += prosperity * spenders / PERCENT * table.consumption_take / RATE_UNIT
        elif kind is TaxKind.LAND:
            total += prosperity * (shares.get(C.FARMER, 0.0) + shares.get(C.NOBLE, 0.0)) / PERCENT * table.land_take / RATE_UNIT
        else:
            total += prosperity / RATE_UNIT
    return total


async def burden(ctx: TickContext, book: RealmBook, realm: Realm, row: TaxPolicyRow) -> None:
    loss = round_half_up(ctx.rules.affairs.tax_burden * row.rate / 5 * TAXES[row.kind].unrest / PERCENT)
    if loss <= 0:
        return
    for member in book.members(realm):
        society = await ctx.session.get(CommunitySocietyRow, member.id)
        if society is None or held(member.id):
            continue
        for social_class in TAXES[row.kind].classes:
            key = f"satisfaction_{social_class.value}"
            setattr(society, key, clamp_int(getattr(society, key) - loss, 0, PERCENT))
        if row.farmed:
            town = await ctx.session.get(SettlementProfileRow, member.id)
            if town is not None and "unrest" not in (town.locked or []):
                town.unrest = clamp_int(town.unrest + ctx.rules.affairs.farm_unrest, 0, PERCENT)


async def levy(ctx: TickContext, book: RealmBook, realm: Realm, row: TaxPolicyRow, tally: RevenueTally) -> None:
    table = ctx.rules.affairs
    if EFFICIENCY not in row.locked:
        order = [town.public_order for member in realm.members if (town := await ctx.session.get(SettlementProfileRow, member)) is not None]
        mean_order = sum(order) / len(order) if order else PERCENT / 2
        row.efficiency = clamp_int((min(PERCENT, realm.profile.administration) + mean_order + PERCENT - realm.profile.corruption) / 3, 0, PERCENT)
    rate = row.rate if "rate" in row.locked or await realm_allows(ctx.session, realm, TAXES[row.kind].gate) else 0
    take = await base_of(ctx, book, realm, row.kind) * rate / RATE_UNIT * row.efficiency / PERCENT * await extraction_of(ctx.session, realm.entity.id)
    take *= await kept_share(ctx, realm, row.kind)
    if row.farmed:
        take *= 1 + table.farm_take_pct / PERCENT
        tally.farmed += 1
    amount = round_half_up(take)
    if TAKE not in row.locked:
        row.take = max(0, amount)
    row.epoch = ctx.epoch
    if row.take <= 0:
        return
    if row.kind is TaxKind.TITHE:
        church = book.entities.get(realm.profile.state_religion_id or -1) or await ctx.session.get(EntityRow, realm.profile.state_religion_id or -1)
        if church is not None and not held(church.id):
            shift_stat(church, "wealth", row.take / RATE_UNIT)
            tally.tithed += row.take
    else:
        spend(ctx, realm, row.take, TreasuryEntry.TAX, f"{row.kind.value} tax")
        tally.gathered += row.take
    await burden(ctx, book, realm, row)


async def tend_revenue(ctx: TickContext, tally: RevenueTally) -> None:
    book = await RealmBook.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        policies = await policies_of(ctx, realm)
        await breed_corruption(ctx, laws, realm, policies)
        for kind in TaxKind:
            await levy(ctx, book, realm, policies[kind], tally)
