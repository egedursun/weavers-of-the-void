from typing import Any

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.endowments import EndowmentPurpose, EndowmentState
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.economy.purse import take_coin
from aerona.engine.endowments.trust import CAPITAL_YIELD_PCT
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

CAPITAL_MAX = 1_000_000


class EndowInput(ToolInput):
    beneficiary_id: int
    purpose: EndowmentPurpose
    capital: int = Field(ge=1, le=CAPITAL_MAX)


class AuditEndowmentInput(ToolInput):
    endowment_id: int


async def endow(call: MortalCall, args: EndowInput) -> str:
    beneficiary = await call.session.get(EntityRow, args.beneficiary_id)
    if beneficiary is None or not beneficiary.living:
        fail(MortalResult.ENDOWMENT_REFUSED, why="there is no such living beneficiary")
    if held(beneficiary.id):
        fail(MortalResult.ENDOWMENT_REFUSED, why="a god holds that beneficiary as it is")
    if not await take_coin(call.session, call.rules, call.me, args.capital):
        fail(MortalResult.ENDOWMENT_REFUSED, why=f"you cannot spare {args.capital}")
    row = EndowmentRow(
        founder_node_id=call.me.id,
        beneficiary_node_id=beneficiary.id,
        trustee_node_id=call.me.id,
        purpose=args.purpose,
        capital=args.capital,
        founded_epoch=call.epoch,
        locked=[],
    )
    call.session.add(row)
    call.target(beneficiary.id)
    await call.record(
        "endowment.founded",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.BENEFICIARY: beneficiary.id},
        facts={"capital": args.capital, "purpose": args.purpose},
        place=call.me.location_id,
    )
    income = round_half_up(args.capital * call.rules.endowments.income_pct / PERCENT * CAPITAL_YIELD_PCT[row.capital_kind] / PERCENT)
    return result(MortalResult.ENDOWED, beneficiary=beneficiary.name, capital=args.capital, purpose=spoken(args.purpose), income=income)


async def audit_endowment(call: MortalCall, args: AuditEndowmentInput) -> str:
    row = await call.session.get(EndowmentRow, args.endowment_id)
    if row is None or row.state is not EndowmentState.SERVING:
        fail(MortalResult.ENDOWMENT_REFUSED, why="there is no such endowment serving")
    if held(row.beneficiary_node_id) or held(row.founder_node_id):
        fail(MortalResult.ENDOWMENT_REFUSED, why="a god holds that endowment as it is")
    beneficiary = await call.session.get(EntityRow, row.beneficiary_node_id)
    trustee = await call.session.get(EntityRow, row.trustee_node_id) if row.trustee_node_id is not None else None
    name = beneficiary.name if beneficiary is not None else "its beneficiary"
    call.target(row.beneficiary_node_id)
    found = row.skimmed
    await call.record(
        "endowment.audited",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.BENEFICIARY: row.beneficiary_node_id, **({IncidentRole.TARGET: trustee.id} if trustee else {})},
        facts={"amount": found},
        place=call.me.location_id,
    )
    if not found or trustee is None or trustee.id == call.me.id:
        return result(MortalResult.AUDITED_CLEAN, beneficiary=name)
    profile = await call.session.get(MortalProfileRow, trustee.id)
    if profile is not None and not held(trustee.id) and "honour" not in (profile.locked or []):
        profile.honour = clamp_int(profile.honour - call.rules.endowments.audit_honour, 0, PERCENT)
    if "trustee_node_id" not in (row.locked or []):
        row.trustee_node_id = call.me.id
    if "skimmed" not in (row.locked or []):
        row.skimmed = 0
    return result(MortalResult.AUDITED_FOUND, beneficiary=name, trustee=trustee.name, amount=found)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.ENDOW, AgentKind.MORTAL, EndowInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), endow),
        ToolSpec(MortalToolId.AUDIT_ENDOWMENT, AgentKind.MORTAL, AuditEndowmentInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), audit_endowment),
    ]
