from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.economy import ResourceProfileRow, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.society import Commodity
from aerona.engine.demography.labour import jobs_for
from aerona.engine.economy.routes import LIVE_STATUSES
from aerona.engine.economy.stocks import aggregate_index
from aerona.engine.gods.queries import community_of
from aerona.prompts.contexts.mortal import StoresLine
from aerona.rules.registry import Rules
from aerona.tools.framework.economy_lines import Names, commodity_lines, currency_line, debt_lines, loan_lines, route_line

SHORT_INDEX = 50


async def job_of(session: AsyncSession, rules: Rules, me: EntityRow, home: EntityRow) -> str:
    parts: list[str] = []
    if me.mortal_role is not None:
        parts.append(me.mortal_role.value.replace("_", " "))
    if me.social_class is not None:
        shares = jobs_for(rules, me.social_class)
        work = max(shares, key=lambda job: (shares[job], job.value))
        row = await session.get(LabourRow, (home.id, work))
        crew = f", one of {row.workers} hands working at {row.output_pct}%" if row is not None and row.workers > 0 else ""
        parts.append(f"works at {work.value.replace('_', ' ')} like most of the {me.social_class.value.replace('_', ' ')} class{crew}")
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
        currency=f"{coin.name} of {coin.metal}, purity {coin.purity}, trust {coin.trust}" if coin is not None else "",
        debts=debts,
        loans=loans,
        job=await job_of(session, rules, me, home) if me.id != home.id else "",
    )


async def resource_yield(session: AsyncSession, resource_id: int) -> str:
    profile = await session.get(ResourceProfileRow, resource_id)
    if profile is None:
        return ""
    material = profile.material.value.replace("_", " ") + " " if profile.material is not None else ""
    return f"{material}{COMMODITIES[profile.commodity].label.lower()}, reserve {profile.reserve}"
