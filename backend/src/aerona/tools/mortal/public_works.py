from typing import Any

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.works import PublicWorksRow, StateEnterpriseRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.works import EnterpriseForm, EnterpriseManagement, LabourRegime, WorksKind, WorksStatus
from aerona.engine.economy.purse import take_coin
from aerona.engine.numbers.book import towns_in
from aerona.engine.works.building import take_treasury, towns_of_place
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.population import realm_ruled_by

BUDGET_MAX = 100_000
STAGES = 3
QUALITY = {LabourRegime.PAID: 70, LabourRegime.CORVEE: 50, LabourRegime.BOUND: 40, LabourRegime.MADE_MINDS: 80, LabourRegime.CONSTRUCTS: 75}


class BeginWorksInput(ToolInput):
    kind: WorksKind
    route_or_region_id: int
    labour: LabourRegime
    budget: int = Field(ge=0, le=BUDGET_MAX)


class FundWorksInput(ToolInput):
    works_id: int
    amount: int = Field(ge=1, le=BUDGET_MAX)


class FoundEnterpriseInput(ToolInput):
    sector: CommodityKind | None = None
    form: EnterpriseForm
    manager_id: int | None = None


async def in_realm(call: MortalCall, realm: int, place_id: int) -> bool:
    route = await call.session.get(TradeRouteProfileRow, place_id)
    mine = set(await towns_in(call.session, realm))
    if route is not None:
        return bool({route.first_market_id, route.second_market_id} & mine)
    return bool(set(await towns_of_place(call.session, place_id)) & mine)


async def begin_works(call: MortalCall, args: BeginWorksInput) -> str:
    realm = await realm_ruled_by(call)
    if realm is None:
        fail(MortalResult.WORKS_REFUSED, why="only one who rules a realm begins its public works")
    if held(realm) or held(args.route_or_region_id):
        fail(MortalResult.WORKS_REFUSED, why="a god holds it as it is")
    if not await in_realm(call, realm, args.route_or_region_id):
        fail(MortalResult.WORKS_REFUSED, why="the works must lie on a route, region or town of your realm")
    if not await take_treasury(call.session, realm, args.budget):
        fail(MortalResult.WORKS_REFUSED, why="your treasury cannot set that much aside")
    call.session.add(
        PublicWorksRow(
            polity_entity_id=realm,
            place_node_id=args.route_or_region_id,
            kind=args.kind,
            labour=args.labour,
            stages=STAGES,
            budget=args.budget,
            quality=QUALITY[args.labour],
            begun_epoch=call.epoch,
            locked=[],
        )
    )
    call.target(realm)
    await call.record(
        "works.begun",
        roles={IncidentRole.ACTOR: realm, IncidentRole.PLACE: args.route_or_region_id},
        facts={"kind": args.kind, "labour": args.labour},
    )
    return result(MortalResult.WORKS_BEGUN, kind=spoken(args.kind), labour=spoken(args.labour), budget=args.budget)


async def fund_works(call: MortalCall, args: FundWorksInput) -> str:
    works = await call.session.get(PublicWorksRow, args.works_id)
    if works is None or works.status is not WorksStatus.BUILDING:
        fail(MortalResult.WORKS_REFUSED, why="there are no such works being built")
    if held(works.polity_entity_id) or "budget" in (works.locked or []):
        fail(MortalResult.WORKS_REFUSED, why="a god holds those works as they are")
    if not await take_coin(call.session, call.rules, call.me, args.amount):
        fail(MortalResult.WORKS_REFUSED, why="you cannot spare that much")
    works.budget += args.amount
    call.target(works.polity_entity_id)
    return result(MortalResult.WORKS_FUNDED, kind=spoken(works.kind), amount=args.amount, budget=works.budget)


async def found_enterprise(call: MortalCall, args: FoundEnterpriseInput) -> str:
    realm = await realm_ruled_by(call)
    if realm is None:
        fail(MortalResult.WORKS_REFUSED, why="only one who rules a realm founds its enterprises")
    if held(realm):
        fail(MortalResult.WORKS_REFUSED, why="a god holds your realm as it is")
    manager = await call.session.get(EntityRow, args.manager_id) if args.manager_id is not None else None
    if args.manager_id is not None and (manager is None or manager.status is not EntityStatus.CANON):
        fail(MortalResult.WORKS_REFUSED, why="there is no such manager")
    management = EnterpriseManagement.OFFICIAL
    if manager is not None and manager.entity_type is EntityType.FACTION:
        management = EnterpriseManagement.COMPANY
    call.session.add(
        StateEnterpriseRow(
            polity_entity_id=realm,
            sector=args.sector,
            form=args.form,
            management=management,
            manager_node_id=manager.id if manager is not None else None,
            output=PERCENT // 10,
            founded_epoch=call.epoch,
            locked=[],
        )
    )
    call.target(realm)
    await call.record(
        "enterprise.founded",
        roles={IncidentRole.ACTOR: realm, **({IncidentRole.TARGET: manager.id} if manager is not None else {})},
        facts={"form": args.form},
    )
    return result(MortalResult.ENTERPRISE_FOUNDED, form=spoken(args.form), sector=spoken(args.sector) if args.sector is not None else "no single good")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.ENACT_LAW, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.BEGIN_WORKS, AgentKind.MORTAL, BeginWorksInput, meta, begin_works),
        ToolSpec(MortalToolId.FUND_WORKS, AgentKind.MORTAL, FundWorksInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), fund_works),
        ToolSpec(MortalToolId.FOUND_ENTERPRISE, AgentKind.MORTAL, FoundEnterpriseInput, meta, found_enterprise),
    ]
