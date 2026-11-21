from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.competition import CartelRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.competition import CartelAim, CompetitionClause
from aerona.domain.enums.economy import CommodityKind
from aerona.engine.competition.cartels import cartel_over, expose, form_cartel
from aerona.engine.competition.clauses import clause_strength
from aerona.engine.competition.structure import structure_of
from aerona.engine.competition.wars import start_war, war_over
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

MEMBERS_MAX = 12
CUT_MAX = 90
TERMS_MAX = 100000


class FormCartelInput(ToolInput):
    member_ids: list[int] = Field(min_length=2, max_length=MEMBERS_MAX)
    goods_kind: CommodityKind
    market_id: int
    aim: CartelAim
    terms: int = Field(default=0, ge=0, le=TERMS_MAX)


class StartPriceWarInput(ToolInput):
    market_id: int
    goods_kind: CommodityKind
    cut: int = Field(ge=1, le=CUT_MAX)


class ReportCartelInput(ToolInput):
    cartel_id: int


async def my_orgs(call: MortalCall) -> set[int]:
    return set(await call.session.scalars(select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.head_node_id == call.me.id)))


async def sellers_at(call: MortalCall, market_id: int, commodity: CommodityKind) -> dict[int, int]:
    structure = await structure_of(call.tick, market_id, commodity)
    if structure is None:
        fail(MortalResult.MARKET_REFUSED, why=f"no one is counted as selling {spoken(commodity)} in that market")
    if held(market_id):
        fail(MortalResult.MARKET_REFUSED, why="a god holds that market as it is")
    return {int(node): share for node, share in (structure.sellers or {}).items()}


async def form_cartel_tool(call: MortalCall, args: FormCartelInput) -> str:
    sellers = await sellers_at(call, args.market_id, args.goods_kind)
    mine = await my_orgs(call) & set(args.member_ids)
    if not mine:
        fail(MortalResult.MARKET_REFUSED, why="a compact is made by the head of one of its members")
    strangers = [node for node in args.member_ids if node not in sellers]
    if strangers:
        fail(MortalResult.MARKET_REFUSED, why=f"only those who sell {spoken(args.goods_kind)} there can join")
    if await cartel_over(call.tick, args.market_id, args.goods_kind) is not None:
        fail(MortalResult.MARKET_REFUSED, why="a compact already rules that market")
    cartel = await form_cartel(call.tick, args.member_ids, args.goods_kind, markets=[args.market_id], aim=args.aim, terms=args.terms, leader=min(mine))
    call.target(args.market_id)
    return result(MortalResult.CARTEL_FORMED, cartel=cartel.name, commodity=spoken(args.goods_kind), aim=spoken(args.aim))


async def start_price_war_tool(call: MortalCall, args: StartPriceWarInput) -> str:
    sellers = await sellers_at(call, args.market_id, args.goods_kind)
    mine = sorted(await my_orgs(call) & set(sellers))
    if not mine:
        fail(MortalResult.MARKET_REFUSED, why=f"only the head of one who sells {spoken(args.goods_kind)} there can start one")
    if await war_over(call.tick, args.market_id, args.goods_kind) is not None:
        fail(MortalResult.MARKET_REFUSED, why="a price war already runs in that market")
    rivals = [node for node in sellers if node not in mine]
    if not rivals:
        fail(MortalResult.MARKET_REFUSED, why="no rival sells there to drive out")
    war = await start_war(call.tick, mine[0], args.market_id, args.goods_kind, cut=args.cut, targets=rivals)
    call.target(args.market_id)
    names = [entity.name for entity in [await call.session.get(EntityRow, node) for node in war.targets] if entity is not None]
    return result(MortalResult.PRICE_WAR_BEGUN, commodity=spoken(args.goods_kind), cut=args.cut, rivals=", ".join(names) or "your rivals")


async def report_cartel_tool(call: MortalCall, args: ReportCartelInput) -> str:
    cartel = await call.session.get(CartelRow, args.cartel_id)
    if cartel is None or cartel.broken_epoch is not None:
        fail(MortalResult.MARKET_REFUSED, why="there is no such compact still in force")
    if any(held(node) for node in [*(cartel.members or []), *(cartel.markets or [])]):
        fail(MortalResult.MARKET_REFUSED, why="a god holds it as it is")
    ban = await clause_strength(call.tick, cartel.markets[0], CompetitionClause.CARTEL_BAN) if cartel.markets else 0
    call.target(cartel.markets[0] if cartel.markets else None)
    if ban:
        await expose(call.tick, cartel)
        return result(MortalResult.CARTEL_REPORTED, cartel=cartel.name, outcome="the law took it apart and fined its members")
    if "secrecy" not in (cartel.locked or []):
        cartel.secrecy = 0
    return result(MortalResult.CARTEL_REPORTED, cartel=cartel.name, outcome="no law forbids it, but it is no longer secret")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    trade = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FORM_CARTEL, AgentKind.MORTAL, FormCartelInput, trade, form_cartel_tool),
        ToolSpec(MortalToolId.START_PRICE_WAR, AgentKind.MORTAL, StartPriceWarInput, trade, start_price_war_tool),
        ToolSpec(MortalToolId.REPORT_CARTEL, AgentKind.MORTAL, ReportCartelInput, trade, report_cartel_tool),
    ]
