from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.finance import CREDIT_LABELS, POLICY_LABELS
from aerona.catalog.methods import ENERGY_LABELS, METHODS, PROCESS_LABELS, TIER_LABELS
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.economy import ResourceProfileRow, TradeRouteProfileRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import CreditProfileRow, SpeculationRow, TradePolicyRow
from aerona.db.tables.industry import CommunityIndustryRow, CommunityMethodRow, RegionPollutionRow
from aerona.db.tables.ownership import SiteProfitRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.finance import SpeculationStatus, TradePolicyKind
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.society import Commodity
from aerona.engine.demography.labour import jobs_for
from aerona.engine.economy.routes import LIVE_STATUSES
from aerona.engine.economy.stocks import aggregate_index
from aerona.engine.gods.queries import community_of
from aerona.engine.industry.quality import tier_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.prompts.contexts.mortal import StoresLine
from aerona.rules.registry import Rules
from aerona.tools.framework.economy_lines import Names, commodity_lines, currency_line, debt_lines, loan_lines, route_line

SHORT_INDEX = 50
PROFITS_SHOWN = 3


async def job_of(session: AsyncSession, rules: Rules, me: EntityRow, home: EntityRow) -> str:
    parts: list[str] = []
    if me.mortal_role is not None:
        parts.append(spoken(me.mortal_role))
    if me.social_class is not None:
        shares = jobs_for(rules, me.social_class)
        work = max(shares, key=lambda job: (shares[job], job.value))
        row = await session.get(LabourRow, (home.id, work))
        crew = f", one of {several(row.workers, 'hand', 'hands')} working at {row.output_pct}%" if row is not None and row.workers > 0 else ""
        parts.append(f"works at {spoken(work)} like most of the {spoken(me.social_class)} class{crew}")
    return "; ".join(parts)


async def stores_for(session: AsyncSession, rules: Rules, me: EntityRow) -> StoresLine | None:
    home = me if me.entity_type in SOCIETY_TYPES else await community_of(session, me)
    if home is None or home.entity_type not in SOCIETY_TYPES:
        return None
    names = Names(session)
    goods = await commodity_lines(session, home)
    short = [aggregate.value for aggregate in Commodity if await aggregate_index(session, rules, home, aggregate) < SHORT_INDEX]
    statement = select(TradeRouteProfileRow).where(
        TradeRouteProfileRow.status.in_(list(LIVE_STATUSES)),
        (TradeRouteProfileRow.first_market_id == home.id) | (TradeRouteProfileRow.second_market_id == home.id),
    )
    routes: list[str] = []
    for profile in await session.scalars(statement.order_by(TradeRouteProfileRow.route_entity_id)):
        line = await route_line(session, profile, names, viewpoint=home.id)
        if line is None:
            continue
        flags = [flag for flag, on in (("blockaded", line.blockaded_by != ""), ("a chokepoint", line.chokepoint)) if on]
        routes.append(
            f"{line.name} to {line.partner} by {line.mode}, danger {line.danger} "
            f"(bandits {line.bandits}, beasts {line.beasts}, weather {line.weather}, sea {line.sea}){', ' + ', '.join(flags) if flags else ''}"
        )
    coin = await currency_line(session, home.id, names)
    debts = [
        f"{debt.role} {debt.other} {debt.amount} {debt.what}".strip() + (f", due age {debt.due_epoch}" if debt.due_epoch is not None else "")
        for debt in await debt_lines(session, me.id, names)
    ]
    if home.id != me.id:
        debts += [f"your people {debt.role} {debt.other} {debt.amount} {debt.what}".strip() for debt in await debt_lines(session, home.id, names)]
    loans = [
        f"{loan.role} {loan.other}: {loan.owed} still owed at {loan.interest_pct}%, due age {loan.due_epoch} ({loan.status})"
        for loan in await loan_lines(session, home.id, names)
    ]
    return StoresLine(
        community=home.name,
        materials=[f"{line.label.lower()}: {'; '.join(line.lots)}" for line in goods if line.lots],
        short=short,
        routes=routes,
        prices=[f"{line.label.lower()} {line.price} (supply {line.supply}, need {line.demand})" for line in goods if line.price is not None],
        currency=f"{coin.name} of {coin.metal or 'no metal backing'}, purity {coin.purity}, trust {coin.trust}" if coin is not None else "",
        debts=debts,
        loans=loans,
        works=await works_lines(session, rules, home, me),
        job=await job_of(session, rules, me, home) if me.id != home.id else "",
    )


async def finance_lines(session: AsyncSession, home: EntityRow, me: EntityRow) -> list[str]:
    lines: list[str] = []
    row = await session.get(CommunityIndustryRow, home.id)
    if row is not None:
        lines.append(f"market access {row.market_access} of 100" + (f", {several(row.black_market, 'load', 'loads')} smuggled in" if row.black_market else ""))
    realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == home.id).limit(1))
    for subject in dict.fromkeys(item for item in (me.id, home.id, realm) if item is not None):
        credit = await session.get(CreditProfileRow, subject)
        if credit is not None:
            whose = "your" if subject == me.id else "your people's" if subject == home.id else "your realm's"
            lines.append(f"{whose} credit {credit.rating} ({CREDIT_LABELS[credit.state].lower()}), borrowing at {credit.interest_pct}%")
    if realm is not None:
        laid = list(await session.scalars(select(TradePolicyRow).where(TradePolicyRow.issuer_node_id == realm).order_by(TradePolicyRow.id)))
        if laid:
            lines.append(
                "your realm keeps "
                + ", ".join(
                    f"{an(POLICY_LABELS[row.kind].lower())} on {COMMODITIES[row.commodity].label.lower() if row.commodity else 'every good'}"
                    + (f" at {row.rate_pct}%" if row.kind is not TradePolicyKind.EMBARGO else "")
                    for row in laid
                )
            )
    hoards = list(
        await session.scalars(select(SpeculationRow).where(SpeculationRow.merchant_node_id == me.id, SpeculationRow.status == SpeculationStatus.HOARDING))
    )
    if hoards:
        lines.append("you hoard " + ", ".join(f"{row.units} {COMMODITIES[row.commodity].label.lower()} bought at {row.price}" for row in hoards))
    return lines


async def works_lines(session: AsyncSession, rules: Rules, home: EntityRow, me: EntityRow) -> list[str]:
    methods = list(
        await session.scalars(select(CommunityMethodRow).where(CommunityMethodRow.community_node_id == home.id).order_by(CommunityMethodRow.process))
    )
    lines = [f"{PROCESS_LABELS[row.process].lower()} by {METHODS[row.method].label.lower()}" for row in methods]
    row = await session.get(CommunityIndustryRow, home.id)
    if row is not None:
        power = [f"{ENERGY_LABELS[kind].lower()} {getattr(row, kind.value)}" for kind in EnergyKind if getattr(row, kind.value)]
        if power:
            lines.append("power: " + ", ".join(power))
        short = [ENERGY_LABELS[EnergyKind(key)].lower() for key, value in sorted(row.short.items()) if value > 0]
        if short:
            lines.append("short of " + ", ".join(short) + " power")
        lines.append(
            f"meals {TIER_LABELS[tier_of(rules, row.meal_quality)].lower()}; spoiled {row.spoiled}, preserved {row.preserved}, tools worn {row.tools_worn}"
        )
    owned = list(await session.scalars(select(WorkshopRow).where(WorkshopRow.owner_node_id.in_([home.id, me.id])).order_by(WorkshopRow.id)))
    if owned:
        lines.append("owns " + ", ".join(f"the {WORKSHOP_LABELS[row.kind].lower()} of level {row.level}" for row in owned))
    recent = select(SiteProfitRow).where(SiteProfitRow.owner_node_id.in_([home.id, me.id])).order_by(SiteProfitRow.epoch.desc())
    gains = list(await session.scalars(recent.limit(PROFITS_SHOWN)))
    if gains:
        lines.append("last profits: " + ", ".join(f"{row.site.replace('_', ' ')} {row.profit} (taxes {row.taxes})" for row in gains))
    lines.extend(await finance_lines(session, home, me))
    top = (await RegionAtlas.load(session)).top_region(home.id)
    fouled = await session.get(RegionPollutionRow, top) if top is not None else None
    if fouled is not None and max(fouled.air, fouled.water, fouled.soil) > 0:
        lines.append(f"the land is fouled: air {fouled.air}, water {fouled.water}, soil {fouled.soil}")
    return lines


async def resource_yield(session: AsyncSession, resource_id: int) -> str:
    profile = await session.get(ResourceProfileRow, resource_id)
    if profile is None:
        return ""
    material = spoken(profile.material) + " " if profile.material is not None else ""
    return f"{material}{COMMODITIES[profile.commodity].label.lower()}, reserve {profile.reserve}"
