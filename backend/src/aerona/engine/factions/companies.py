from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow, CompanyShareRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import GovernmentKind
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import found_polity, refresh_realms
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, close
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.renames import rename_everywhere
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import StepDraft, record

POWER = 3
WEALTH = "wealth"
STRENGTH = "strength"
FOUNDER_SHARE = 60


@dataclass
class CompanyTally:
    chartered: int = 0
    dividends: int = 0
    conquered: int = 0
    guarded: int = 0
    dominions: int = 0


async def realm_of(ctx: TickContext, community_id: int | None) -> int | None:
    found: int | None = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return found


async def foreign_route(ctx: TickContext, home_id: int) -> TradeRouteProfileRow | None:
    home_realm = await realm_of(ctx, home_id)
    routes = await ctx.session.scalars(
        select(TradeRouteProfileRow)
        .where(or_(TradeRouteProfileRow.first_market_id == home_id, TradeRouteProfileRow.second_market_id == home_id))
        .order_by(TradeRouteProfileRow.route_entity_id)
    )
    for route in routes:
        far = route.second_market_id if route.first_market_id == home_id else route.first_market_id
        taken = await ctx.session.scalar(select(CompanyProfileRow.faction_entity_id).where(CompanyProfileRow.route_entity_id == route.route_entity_id).limit(1))
        if taken is None and await realm_of(ctx, far) != home_realm:
            return route
    return None


async def charter(ctx: TickContext, guild: EntityRow, profile: FactionProfileRow, route: TradeRouteProfileRow) -> CompanyProfileRow:
    home = await ctx.session.get(EntityRow, profile.home_entity_id)
    name = home.name if home is not None else guild.name
    company = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.FACTION,
            name=f"the Chartered Company of {name}",
            body=f"A company chartered to hold the trade of a far route, owned in shares by the merchants of {name}.",
            stats=FactionStats(strength=PERCENT // 5, wealth=PERCENT // 3, sway=PERCENT // 5),
            power=POWER,
            location_id=profile.home_entity_id,
            world_id=guild.world_id,
            subtype="chartered company",
        ),
    )
    ctx.session.add(
        FactionProfileRow(
            faction_entity_id=company.id, kind=FactionKind.CHARTERED_COMPANY, home_entity_id=profile.home_entity_id, influence_over={}, armed=True, locked=[]
        )
    )
    row = CompanyProfileRow(
        faction_entity_id=company.id,
        polity_entity_id=await realm_of(ctx, profile.home_entity_id),
        route_entity_id=route.route_entity_id,
        dividend_pct=PERCENT // 3,
        value=PERCENT // 3,
        chartered_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    ctx.session.add(CompanyShareRow(company_entity_id=company.id, holder_node_id=guild.id, share=FOUNDER_SHARE))
    if row.polity_entity_id is not None:
        ctx.session.add(CompanyShareRow(company_entity_id=company.id, holder_node_id=row.polity_entity_id, share=PERCENT - FOUNDER_SHARE))
    await ctx.session.flush()
    return row


async def found_companies(ctx: TickContext, tally: CompanyTally) -> None:
    table = ctx.rules.companies
    guilds = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind == FactionKind.MERCHANT_GUILD, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for guild, profile in list(guilds):
        if held(guild.id) or profile.home_entity_id is None or (stat(guild, WEALTH) or 0) < table.found_wealth:
            continue
        if not ctx.rng(seed_of("company.found", guild.id, ctx.epoch)).chance(table.found_pct):
            continue
        route = await foreign_route(ctx, profile.home_entity_id)
        if route is not None:
            await charter(ctx, guild, profile, route)
            tally.chartered += 1


async def pay_dividends(ctx: TickContext, company: EntityRow, row: CompanyProfileRow, tally: CompanyTally) -> None:
    table = ctx.rules.companies
    purse = stat(company, WEALTH) or 0
    for share in await ctx.session.scalars(
        select(CompanyShareRow).where(CompanyShareRow.company_entity_id == row.faction_entity_id).order_by(CompanyShareRow.holder_node_id)
    ):
        holder = await ctx.session.get(EntityRow, share.holder_node_id)
        if holder is None or held(holder.id):
            continue
        paid = min(purse, round_half_up(table.dividend_wealth * share.share / PERCENT * row.dividend_pct / PERCENT * PERCENT / 10))
        if paid:
            purse -= paid
            await shift_points(ctx.session, holder, paid)
            tally.dividends += 1
    set_stats(company, wealth=purse)


async def hire_guards(ctx: TickContext, company: EntityRow, tally: CompanyTally) -> None:
    table = ctx.rules.companies
    wealth = stat(company, WEALTH) or 0
    strength = stat(company, STRENGTH) or 0
    if wealth < table.guard_wealth or strength >= PERCENT:
        return
    set_stats(company, wealth=wealth - table.guard_wage, strength=clamp_int(strength + table.guard_strength, 0, PERCENT))
    tally.guarded += 1


async def conquer(ctx: TickContext, company: EntityRow, row: CompanyProfileRow, tally: CompanyTally) -> None:
    route = await ctx.session.get(TradeRouteProfileRow, row.route_entity_id) if row.route_entity_id is not None else None
    profile = await ctx.session.get(FactionProfileRow, company.id)
    if route is None or profile is None or row.region_entity_id is not None:
        return
    far = route.second_market_id if route.first_market_id == profile.home_entity_id else route.first_market_id
    market = await ctx.session.get(EntityRow, far)
    region = market.location_id if market is not None else None
    if region is None or await ctx.session.get(OccupationRow, region) is not None or held(region):
        return
    ctx.session.add(OccupationRow(region_entity_id=region, occupier_entity_id=company.id, since_epoch=ctx.epoch))
    row.region_entity_id = region
    await record(
        ctx,
        "companies.conquest",
        roles={IncidentRole.ACTOR: company.id, IncidentRole.PLACE: region, IncidentRole.INSTRUMENT: row.route_entity_id},
        steps=(StepDraft(StepAction.SEIZE_GOODS, actor=company.id, target=region, locus_kind=StepLocus.REGION, locus_node=region),),
        place=region,
    )
    tally.conquered += 1


async def far_market(ctx: TickContext, row: CompanyProfileRow, home_id: int | None) -> EntityRow | None:
    route = await ctx.session.get(TradeRouteProfileRow, row.route_entity_id) if row.route_entity_id is not None else None
    if route is None:
        return None
    return await ctx.session.get(EntityRow, route.second_market_id if route.first_market_id == home_id else route.first_market_id)


async def found_dominion(ctx: TickContext, company: EntityRow, row: CompanyProfileRow, tally: CompanyTally) -> bool:
    occupation = await ctx.session.get(OccupationRow, row.region_entity_id) if row.region_entity_id is not None else None
    if occupation is None or occupation.occupier_entity_id != company.id or ctx.epoch - occupation.since_epoch < ctx.rules.companies.dominion_epochs:
        return False
    profile = await ctx.session.get(FactionProfileRow, company.id)
    market = await far_market(ctx, row, profile.home_entity_id if profile is not None else None)
    if market is None or market.status is not EntityStatus.CANON or market.entity_type is not EntityType.SETTLEMENT or held(market.id):
        return False
    book = await RealmBook.load(ctx.session)
    current = book.realm_of(market.id)
    if current is not None and current.profile.core_entity_id == market.id:
        return False
    for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[market.id]):
        await close(ctx.session, bond, ctx.epoch, f"ruled now by {company.name}")
    await add_flag(ctx.session, market.id, EntityFlag.INDEPENDENT, ctx.epoch)
    realm = await found_polity(ctx, book, market)
    await rename_everywhere(ctx.session, realm.entity.id, f"the dominion of {company.name.removeprefix('the ')}", ctx.epoch, free=True)
    realm.profile.government = GovernmentKind.OLIGARCHY
    await refresh_realms(ctx, book)
    await ctx.session.delete(occupation)
    row.region_entity_id = None
    await retire_in(ctx, company, f"the company became {realm.entity.name}", close_bonds=True)
    await record(
        ctx,
        "companies.dominion",
        roles={IncidentRole.PREDECESSOR: company.id, IncidentRole.SUCCESSOR: realm.entity.id, IncidentRole.PLACE: market.id},
        facts={"government": realm.profile.government},
        place=market.id,
    )
    tally.dominions += 1
    return True


async def tend_companies(ctx: TickContext, tally: CompanyTally) -> None:
    table = ctx.rules.companies
    await found_companies(ctx, tally)
    for row in list(await ctx.session.scalars(select(CompanyProfileRow).order_by(CompanyProfileRow.faction_entity_id))):
        company = await ctx.session.get(EntityRow, row.faction_entity_id)
        if company is None or company.status is not EntityStatus.CANON or held(company.id):
            continue
        if row.route_entity_id is not None and WEALTH not in (row.locked or []):
            set_stats(company, wealth=clamp_int((stat(company, WEALTH) or 0) + table.route_profit, 0, PERCENT))
        row.value = stat(company, WEALTH) or 0
        if row.value < table.collapse_wealth:
            continue
        await pay_dividends(ctx, company, row, tally)
        await hire_guards(ctx, company, tally)
        if await found_dominion(ctx, company, row, tally):
            continue
        if (stat(company, STRENGTH) or 0) >= table.conquest_strength:
            await conquer(ctx, company, row, tally)
