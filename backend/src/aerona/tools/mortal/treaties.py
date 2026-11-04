from typing import Any

from sqlalchemy import select

from aerona.db.tables.polity import OfficeRow, PolityProfileRow, TreatyPartyRow, TreatyProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.polity import OfficeKind, PartyRole, TreatyKind, TreatyStatus
from aerona.engine.polity.accords import Clause, accept, propose
from aerona.engine.polity.treaties import breach
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.treaty_inputs import ClauseInput
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import require_target


class ProposeTreatyInput(ToolInput):
    target_id: int
    kind: TreatyKind
    clauses: list[ClauseInput] | None = None
    epochs: int | None = None


class TreatyTargetInput(ToolInput):
    treaty_id: int


async def voice_of(call: MortalCall) -> int:
    if call.me.entity_type in COMMUNITY_TYPES:
        return call.me.id
    if call.me.entity_type is EntityType.MORTAL:
        realm = await call.session.scalar(
            select(OfficeRow.polity_entity_id)
            .where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind.in_([OfficeKind.RULER, OfficeKind.REGENT]))
            .limit(1)
        )
        profile = await call.session.get(PolityProfileRow, realm) if realm is not None else None
        if profile is not None and profile.core_entity_id is not None:
            return profile.core_entity_id
    fail(MortalResult.NO_TREATY_VOICE)


async def propose_treaty(call: MortalCall, args: ProposeTreatyInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.TREATIES_PROPOSED, tools.propose_treaty_per_epoch, "mortal_tools.propose_treaty_per_epoch", MortalResult.TREATY_LIMIT)
    me = await voice_of(call)
    target = await require_target(call, args.target_id)
    if target.id == me:
        fail(MortalResult.NO_TREATY_VOICE)
    roles = (
        [(me, PartyRole.VASSAL), (target.id, PartyRole.OVERLORD)]
        if args.kind is TreatyKind.VASSALAGE
        else [(me, PartyRole.SIGNATORY), (target.id, PartyRole.SIGNATORY)]
    )
    clauses = [Clause(item.kind, item.obligor_id, item.beneficiary_id, item.params or {}) for item in args.clauses or []]
    epochs = max(1, min(tools.treaty_max_epochs, args.epochs)) if args.epochs else None
    treaty = await propose(call.tick, args.kind, roles, proposer_id=me, clauses=clauses, epochs=epochs)
    await call.bump(TurnCounter.TREATIES_PROPOSED)
    call.target(treaty.id)
    return result(MortalResult.TREATY_PROPOSED, name=treaty.name, target=target.name)


async def mine(call: MortalCall, treaty_id: int, status: TreatyStatus) -> tuple[TreatyProfileRow, int]:
    me = await voice_of(call)
    profile = await call.session.get(TreatyProfileRow, treaty_id)
    member = await call.session.get(TreatyPartyRow, (treaty_id, me))
    if profile is None or member is None or profile.status is not status:
        fail(MortalResult.NO_SUCH_TREATY)
    return profile, me


async def accept_treaty(call: MortalCall, args: TreatyTargetInput) -> str:
    profile, me = await mine(call, args.treaty_id, TreatyStatus.PROPOSED)
    if profile.proposed_by_node_id == me:
        fail(MortalResult.NO_SUCH_TREATY)
    treaty = await accept(call.tick, profile)
    call.target(profile.treaty_entity_id)
    return result(MortalResult.TREATY_ACCEPTED, name=treaty.name if treaty is not None else "the treaty")


async def break_treaty(call: MortalCall, args: TreatyTargetInput) -> str:
    profile, me = await mine(call, args.treaty_id, TreatyStatus.IN_FORCE)
    await breach(call.tick, profile, me, clause=None, reason="its rulers chose to break faith")
    call.target(profile.treaty_entity_id)
    return result(MortalResult.TREATY_BROKEN)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.PROPOSE_TREATY, mortal, ProposeTreatyInput, ToolMeta(ActionKind.PROPOSE_TREATY, mortal_standard_action), propose_treaty),
        ToolSpec(MortalToolId.ACCEPT_TREATY, mortal, TreatyTargetInput, ToolMeta(ActionKind.ACCEPT_TREATY, no_cost), accept_treaty),
        ToolSpec(MortalToolId.BREAK_TREATY, mortal, TreatyTargetInput, ToolMeta(ActionKind.BREAK_TREATY, mortal_standard_action), break_treaty),
    ]
