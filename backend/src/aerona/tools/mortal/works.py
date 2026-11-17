from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.finance import POLICY_LABELS
from aerona.catalog.methods import METHODS, PROCESS_LABELS
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.db.tables.economy import MarketPriceRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.economy.book import EconomyBook
from aerona.engine.finance.policy import lay
from aerona.engine.finance.speculation import hunger_at, open_hoard
from aerona.engine.industry.methods import MethodTally, adopt, allowed
from aerona.engine.industry.owners import buy
from aerona.engine.renown.currencies import realm_ruled_by
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, require_canon


class MethodInput(ToolInput):
    method: MethodKind


class BuyInput(ToolInput):
    kind: WorkshopKind


class PolicyInput(ToolInput):
    kind: TradePolicyKind
    commodity: CommodityKind | None = None
    partner_id: int | None = None
    rate_pct: int = Field(default=20, ge=0, le=100)


class SpeculateInput(ToolInput):
    commodity: CommodityKind


async def works_of(call: MortalCall) -> EntityRow | None:
    if call.me.entity_type in SOCIETY_TYPES:
        return call.me
    for home_id in (call.me.affiliated_entity_id, call.me.location_id):
        home = await call.session.get(EntityRow, home_id) if home_id is not None else None
        if home is not None and home.entity_type in SOCIETY_TYPES:
            return home
    return None


async def choose_method(call: MortalCall, args: MethodInput) -> str:
    spec = METHODS[args.method]
    community = await works_of(call)
    if community is None:
        fail(MortalResult.METHOD_REFUSED, name=call.me.name, method=spec.label.lower(), why="you belong to no community with works")
    book = await EconomyBook.load(call.tick)
    row = book.methods.get(community.id, {}).get(spec.process)
    if row is not None and "method" in row.locked:
        fail(MortalResult.METHOD_REFUSED, name=community.name, method=spec.label.lower(), why="a god holds the way it is done")
    why = allowed(book, community, spec)
    if why is not None:
        fail(MortalResult.METHOD_REFUSED, name=community.name, method=spec.label.lower(), why=why)
    await adopt(call.tick, book, community, spec, MethodTally())
    call.target(community.id)
    await call.record(
        "tools.mortal.method_chosen",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.BENEFICIARY: community.id},
        facts={"method": args.method, "process": spec.process},
    )
    return result(MortalResult.METHOD_CHOSEN, name=community.name, method=spec.label.lower(), process=PROCESS_LABELS[spec.process].lower())


async def buy_workshop(call: MortalCall, args: BuyInput) -> str:
    label = WORKSHOP_LABELS[args.kind].lower()
    community = await works_of(call)
    if community is None:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why="you belong to no community with works")
    workshop = await call.session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == community.id, WorkshopRow.kind == args.kind))
    if workshop is None:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why=f"{community.name} has none")
    if workshop.held:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why="a god holds who owns it")
    price = await buy(call.tick, workshop, call.me.id)
    if price is None:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why="you own it already or cannot pay its price")
    call.target(community.id)
    await call.record(
        "tools.mortal.workshop_bought",
        roles={IncidentRole.BUYER: call.me.id, IncidentRole.PLACE: community.id},
        facts={"workshop": args.kind, "price": price},
        place=community.id,
    )
    return result(MortalResult.WORKSHOP_BOUGHT, workshop=label, place=community.name, price=price)


async def lay_trade_policy(call: MortalCall, args: PolicyInput) -> str:
    realm = call.me.id if call.me.entity_type is EntityType.POLITY else await realm_ruled_by(call.session, call.me.id)
    label = POLICY_LABELS[args.kind].lower()
    if realm is None:
        fail(MortalResult.POLICY_REFUSED, policy=label, why="you rule no realm")
    if args.kind is TradePolicyKind.EMBARGO and args.partner_id is None and args.commodity is None:
        fail(MortalResult.POLICY_REFUSED, policy=label, why="an embargo needs a partner or a good")
    if args.partner_id is not None:
        await require_canon(call.session, args.partner_id)
    held_row = await call.session.scalar(
        select(TradePolicyRow).where(TradePolicyRow.issuer_node_id == realm, TradePolicyRow.kind == args.kind, TradePolicyRow.commodity == args.commodity)
    )
    if held_row is not None and held_row.locked:
        fail(MortalResult.POLICY_REFUSED, policy=label, why="a god holds it")
    row = held_row or await lay(
        call.tick, realm, args.kind, commodity=args.commodity, partner=args.partner_id, rate=args.rate_pct, reason=f"laid by {call.me.name}"
    )
    row.rate_pct = 100 if args.kind is TradePolicyKind.EMBARGO else args.rate_pct
    good = COMMODITIES[args.commodity].label.lower() if args.commodity is not None else "every good"
    call.target(realm)
    await call.record(
        "tools.mortal.policy_laid",
        roles={IncidentRole.AUTHORITY: call.me.id, IncidentRole.OWNER: realm, IncidentRole.TARGET: args.partner_id},
        facts={"policy": args.kind, "good": args.commodity, "rate": row.rate_pct},
    )
    return result(MortalResult.POLICY_LAID, policy=label, good=good, rate=row.rate_pct)


async def speculate(call: MortalCall, args: SpeculateInput) -> str:
    label = COMMODITIES[args.commodity].label.lower()
    market = await works_of(call)
    if market is None:
        fail(MortalResult.HOARD_REFUSED, good=label, why="you trade in no market")
    price = await call.session.scalar(
        select(MarketPriceRow.price)
        .where(MarketPriceRow.market_entity_id == market.id, MarketPriceRow.commodity == args.commodity)
        .order_by(MarketPriceRow.epoch.desc())
        .limit(1)
    )
    if price is None:
        fail(MortalResult.HOARD_REFUSED, good=label, why=f"{market.name} keeps no price for it")
    famine = await hunger_at(call.tick, market.id) >= call.rules.speculation.famine_hunger
    row = await open_hoard(call.tick, call.me.id, market, args.commodity, price, famine=famine)
    if row is None:
        fail(MortalResult.HOARD_REFUSED, good=label, why="there is too little to buy or you cannot pay")
    call.target(market.id)
    await call.record(
        "tools.mortal.hoard_opened",
        roles={IncidentRole.BUYER: call.me.id, IncidentRole.PLACE: market.id},
        facts={"good": args.commodity, "units": row.units, "price": price, "famine": int(famine)},
        place=market.id,
    )
    return result(MortalResult.HOARD_OPENED, units=row.units, good=label, place=market.name, price=price)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.LAY_TRADE_POLICY, AgentKind.MORTAL, PolicyInput, ToolMeta(ActionKind.BARTER, mortal_standard_action), lay_trade_policy),
        ToolSpec(MortalToolId.SPECULATE, AgentKind.MORTAL, SpeculateInput, ToolMeta(ActionKind.BARTER, mortal_standard_action), speculate),
        ToolSpec(MortalToolId.BUY_WORKSHOP, AgentKind.MORTAL, BuyInput, ToolMeta(ActionKind.BARTER, mortal_standard_action), buy_workshop),
        ToolSpec(MortalToolId.CHOOSE_METHOD, AgentKind.MORTAL, MethodInput, ToolMeta(ActionKind.PRODUCE, mortal_standard_action), choose_method),
    ]
