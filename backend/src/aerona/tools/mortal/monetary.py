from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.monetary import RATE_MAX, MonetaryAuthorityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.monetary import MonetaryAim
from aerona.engine.monetary.authorities import authority_of, establish
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred.places import ruler_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class SetMonetaryPolicyInput(ToolInput):
    authority_id: int
    rate: int = Field(ge=0, le=RATE_MAX)
    aim: MonetaryAim
    peg_currency_id: int | None = None
    peg_goods_kind: CommodityKind | None = None


class FoundMonetaryAuthorityInput(ToolInput):
    currency_id: int
    holder_id: int
    independence: int = Field(ge=0, le=PERCENT)
    aim: MonetaryAim


async def controls(call: MortalCall, node_id: int | None) -> bool:
    if node_id is None:
        return False
    me = call.me.id
    if node_id == me or await ruler_of(call.session, node_id) == me:
        return True
    head = await call.session.scalar(select(OrgGovernanceRow.head_node_id).where(OrgGovernanceRow.org_node_id == node_id))
    if head == me:
        return True
    leader = await call.session.scalar(select(FactionProfileRow.leader_entity_id).where(FactionProfileRow.faction_entity_id == node_id))
    if leader == me:
        return True
    rules = select(BondRow.id).where(
        BondRow.source_node_id == me, BondRow.target_node_id == node_id, BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE
    )
    return await call.session.scalar(rules.limit(1)) is not None


async def checked_peg(call: MortalCall, currency_id: int, args: SetMonetaryPolicyInput) -> None:
    if args.aim is not MonetaryAim.PEG:
        return
    if (args.peg_currency_id is None) == (args.peg_goods_kind is None):
        fail(MortalResult.MONEY_REFUSED, why="a peg names either another currency or a good, and only one")
    if args.peg_currency_id is not None and (args.peg_currency_id == currency_id or await call.session.get(CurrencyRow, args.peg_currency_id) is None):
        fail(MortalResult.MONEY_REFUSED, why="a currency is pegged to another currency that exists")


async def set_monetary_policy_tool(call: MortalCall, args: SetMonetaryPolicyInput) -> str:
    authority = await call.session.get(MonetaryAuthorityRow, args.authority_id)
    currency = await call.session.get(CurrencyRow, authority.currency_id) if authority is not None else None
    if authority is None or currency is None:
        fail(MortalResult.MONEY_REFUSED, why="there is no such monetary authority")
    if not await controls(call, authority.holder_node_id):
        fail(MortalResult.MONEY_REFUSED, why="only those who hold the authority set its policy")
    if (authority.holder_node_id is not None and held(authority.holder_node_id)) or currency.held:
        fail(MortalResult.MONEY_REFUSED, why="a god holds that money as it is")
    await checked_peg(call, currency.id, args)
    locked = authority.locked or []
    if "rate" not in locked:
        authority.rate = args.rate
    if "aim" not in locked:
        authority.aim = args.aim
    if args.aim is MonetaryAim.PEG:
        authority.peg_currency_id, authority.peg_good, authority.peg_reserves = args.peg_currency_id, args.peg_goods_kind, authority.reserves
    await call.record(
        "money.rate_set",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"currency": currency.name, "rate": authority.rate, "before": authority.effective_rate, "aim": authority.aim},
    )
    return result(MortalResult.MONEY_POLICY_SET, currency=currency.name, rate=authority.rate, aim=spoken(authority.aim))


async def found_monetary_authority_tool(call: MortalCall, args: FoundMonetaryAuthorityInput) -> str:
    currency = await call.session.get(CurrencyRow, args.currency_id)
    if currency is None:
        fail(MortalResult.MONEY_REFUSED, why="there is no such currency")
    if not await controls(call, currency.issuer_entity_id):
        fail(MortalResult.MONEY_REFUSED, why="only those who rule its issuer found an authority for a currency")
    if await authority_of(call.session, currency.id) is not None:
        fail(MortalResult.MONEY_REFUSED, why="that currency already has an authority")
    holder = await living_entity(call.session, args.holder_id)
    if holder is None or held(holder.id) or held(currency.issuer_entity_id):
        fail(MortalResult.MONEY_REFUSED, why="the holder must be a living one that no god holds")
    authority = await establish(call.tick, currency)
    authority.holder_node_id, authority.independence, authority.aim = holder.id, args.independence, args.aim
    call.target(holder.id)
    await call.record(
        "money.authority_founded",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OWNER: holder.id, IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"currency": currency.name, "independence": authority.independence, "aim": authority.aim},
    )
    return result(MortalResult.MONEY_AUTHORITY_FOUNDED, currency=currency.name, holder=holder.name, independence=args.independence, aim=spoken(args.aim))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    money = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SET_MONETARY_POLICY, AgentKind.MORTAL, SetMonetaryPolicyInput, money, set_monetary_policy_tool),
        ToolSpec(MortalToolId.FOUND_MONETARY_AUTHORITY, AgentKind.MORTAL, FoundMonetaryAuthorityInput, money, found_monetary_authority_tool),
    ]
