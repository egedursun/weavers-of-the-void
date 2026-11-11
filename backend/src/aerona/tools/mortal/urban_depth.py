from typing import Any

from sqlalchemy import select

from aerona.catalog.urban import MERCHANT_HOUSES
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.urban import OrderLawRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.faction import CRIME_KINDS, FactionKind
from aerona.domain.enums.urban import MarketPlay, OrderLaw
from aerona.engine.primitives.queries import living_entity
from aerona.engine.urban import control
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines

CLAIMED = 30
BRIBE = 10
CORNERED = 60


class DistrictInput(ToolInput):
    district_id: int


class OfficialInput(ToolInput):
    official_id: int


class HostInput(ToolInput):
    host_id: int


class RouteInput(ToolInput):
    route_id: int


class CornerInput(ToolInput):
    commodity: CommodityKind


class TribunalInput(ToolInput):
    accused_id: int
    law: OrderLaw


async def led(call: MortalCall, kinds: frozenset[FactionKind], refused: MortalResult, why: str) -> FactionProfileRow:
    profile = await call.session.scalar(
        select(FactionProfileRow).where(FactionProfileRow.leader_entity_id == call.me.id, FactionProfileRow.kind.in_(list(kinds))).limit(1)
    )
    if profile is None:
        fail(refused, why=why)
    return profile


async def claim_turf(call: MortalCall, args: DistrictInput) -> str:
    profile = await led(call, CRIME_KINDS, MortalResult.TURF_REFUSED, "you lead no criminal organisation")
    district = await call.session.get(DistrictRow, args.district_id)
    if district is None or district.settlement_entity_id != profile.home_entity_id:
        fail(MortalResult.TURF_REFUSED, why="that district is not in your town")
    await control.set_turf(call.tick, district.id, profile.faction_entity_id, CLAIMED)
    call.target(district.settlement_entity_id)
    await call.chronicle(ChronicleKind.WORLD, lines.CLAIM_TURF, entity_ids=[call.me.id, district.settlement_entity_id], me=call.me.name)
    return result(MortalResult.TURF_CLAIMED, kind=district.kind.value.replace("_", " "))


async def bribe_official(call: MortalCall, args: OfficialInput) -> str:
    profile = await led(call, CRIME_KINDS, MortalResult.BRIBE_REFUSED, "you lead no criminal organisation")
    official = await living_entity(call.session, args.official_id)
    if official is None or official.id == call.me.id:
        fail(MortalResult.BRIBE_REFUSED, why="there is no such official")
    await control.add_payroll(call.tick, profile.faction_entity_id, official.id, BRIBE)
    call.target(official.id)
    await call.chronicle(ChronicleKind.WORLD, lines.BRIBE_OFFICIAL, entity_ids=[call.me.id, official.id], me=call.me.name, official=official.name)
    return result(MortalResult.BRIBED, name=official.name)


async def open_trading_post(call: MortalCall, args: HostInput) -> str:
    profile = await led(call, MERCHANT_HOUSES, MortalResult.POST_REFUSED, "you lead no merchant house")
    host = await living_entity(call.session, args.host_id)
    if host is None or host.id == profile.home_entity_id:
        fail(MortalResult.POST_REFUSED, why="that is no foreign town")
    await control.open_trading_post(call.tick, profile.faction_entity_id, host.id)
    call.target(host.id)
    await call.chronicle(ChronicleKind.WORLD, lines.OPEN_POST, entity_ids=[call.me.id, host.id], me=call.me.name, town=host.name)
    return result(MortalResult.POST_OPENED, name=host.name)


async def send_convoy(call: MortalCall, args: RouteInput) -> str:
    profile = await led(call, MERCHANT_HOUSES, MortalResult.CONVOY_SEND_REFUSED, "you lead no merchant house")
    route = await call.session.get(TradeRouteProfileRow, args.route_id)
    if route is None or profile.home_entity_id not in (route.first_market_id, route.second_market_id):
        fail(MortalResult.CONVOY_SEND_REFUSED, why="that route does not touch your town")
    convoy = await control.send_convoy(call.tick, route.route_entity_id)
    call.target(route.route_entity_id)
    await call.chronicle(ChronicleKind.WORLD, lines.SEND_CONVOY, entity_ids=[call.me.id, route.route_entity_id], me=call.me.name)
    return result(MortalResult.CONVOY_SENT, capacity=convoy.capacity)


async def corner_market(call: MortalCall, args: CornerInput) -> str:
    profile = await led(call, MERCHANT_HOUSES, MortalResult.CORNER_REFUSED, "you lead no merchant house")
    if profile.home_entity_id is None:
        fail(MortalResult.CORNER_REFUSED, why="your house has no home market")
    town = await call.session.get(EntityRow, profile.home_entity_id)
    await control.set_play(call.tick, profile.faction_entity_id, profile.home_entity_id, args.commodity, MarketPlay.CORNER, strength=CORNERED)
    call.target(profile.home_entity_id)
    await call.chronicle(
        ChronicleKind.WORLD, lines.CORNER_MARKET, entity_ids=[call.me.id, profile.home_entity_id], me=call.me.name, good=args.commodity.value.replace("_", " ")
    )
    return result(MortalResult.CORNERED, good=args.commodity.value.replace("_", " "), name=town.name if town is not None else "your market")


async def call_tribunal(call: MortalCall, args: TribunalInput) -> str:
    profile = await led(call, frozenset({FactionKind.MAGE_ORDER}), MortalResult.TRIBUNAL_REFUSED, "you lead no magical order")
    if await call.session.get(OrderLawRow, (profile.faction_entity_id, args.law)) is None:
        fail(MortalResult.TRIBUNAL_REFUSED, why="your order keeps no such law")
    accused = await living_entity(call.session, args.accused_id)
    if accused is None:
        fail(MortalResult.TRIBUNAL_REFUSED, why="there is no such mortal")
    trial = await control.convene(call.tick, profile.faction_entity_id, args.law, accused.id)
    call.target(accused.id)
    await call.chronicle(ChronicleKind.WORLD, lines.CALL_TRIBUNAL, entity_ids=[call.me.id, accused.id], me=call.me.name, accused=accused.name)
    return result(MortalResult.TRIBUNAL_HELD, name=accused.name, verdict=trial.verdict.value)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.CLAIM_TURF, mortal, DistrictInput, meta, claim_turf),
        ToolSpec(MortalToolId.BRIBE_OFFICIAL, mortal, OfficialInput, meta, bribe_official),
        ToolSpec(MortalToolId.OPEN_TRADING_POST, mortal, HostInput, meta, open_trading_post),
        ToolSpec(MortalToolId.SEND_CONVOY, mortal, RouteInput, meta, send_convoy),
        ToolSpec(MortalToolId.CORNER_MARKET, mortal, CornerInput, meta, corner_market),
        ToolSpec(MortalToolId.CALL_TRIBUNAL, mortal, TribunalInput, meta, call_tribunal),
    ]
