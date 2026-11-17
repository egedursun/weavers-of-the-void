from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import NAME_MAX
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import ReincarnationGate, TenetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.faith import control
from aerona.engine.faith.book import FaithBook
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach

REFUSALS = (ConflictError, NotFoundError, ValidationFailedError)


class RevealTenetInput(ToolInput):
    cult_id: int
    tenet: TenetKind
    name: Annotated[str, Field(max_length=NAME_MAX)] | None = None
    target: Annotated[str, Field(max_length=NAME_MAX)] | None = None


class RebirthGateInput(ToolInput):
    spirit_id: int
    community_id: int | None = None


async def reveal_tenet(call: SonCall, args: RevealTenetInput) -> str:
    table = call.rules.doctrine
    cult = require_type(await require_canon(call.session, args.cult_id), {EntityType.CULT}, SonResult.NOT_A_CULT)
    await ensure_in_reach(call, cult)
    church = (await FaithBook.load(call.session)).churches.get(cult.id)
    if church is None or church.god is None or church.god.id != call.son.id:
        fail(SonResult.NOT_YOUR_FAITHFUL, name=cult.name)
    if await call.target_uses(ActionKind.REVELATION, cult.id):
        fail(SonResult.TENET_ALREADY_REVEALED, name=cult.name)
    if call.son.essence < table.reveal_cost:
        fail(SonResult.TENET_TOO_COSTLY, cost=table.reveal_cost, have=call.son.essence)
    try:
        row = await control.set_tenet(call.tick, cult.id, args.tenet, held=True, target=args.target, son_id=call.son.id, name=args.name)
    except REFUSALS as error:
        fail(SonResult.TENET_REFUSED, reason=str(error))
    call.spend_essence(table.reveal_cost)
    call.target(cult.id)
    label = (row.name if row is not None and row.name else None) or args.tenet.value.replace("_", " ")
    await call.record(
        "tools.son.tenet", roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: cult.id}, facts={"tenet": str(label)}, kind=ChronicleKind.WORSHIP
    )
    return result(SonResult.TENET_REVEALED, cult=cult.name, tenet=label, cost=table.reveal_cost)


async def open_rebirth_gate(call: SonCall, args: RebirthGateInput) -> str:
    table = call.rules.necromancy
    spirit = require_type(await require_canon(call.session, args.spirit_id), {EntityType.SPIRIT}, SonResult.NOT_A_SPIRIT)
    await ensure_in_reach(call, spirit)
    _, profile = await control.spirit_profile(call.tick, spirit.id)
    death_god = await call.tick.god_share(call.son.id, DomainHook.SOUL_HOLD) > 0
    if profile.patron_son_id != call.son.id and not death_god:
        fail(SonResult.NOT_YOUR_SOUL, name=spirit.name)
    if call.son.essence < table.rebirth_gate_cost:
        fail(SonResult.REBIRTH_TOO_COSTLY, cost=table.rebirth_gate_cost, have=call.son.essence)
    try:
        child = await control.reincarnate_soul(call.tick, spirit.id, args.community_id, gate=ReincarnationGate.GOD)
    except REFUSALS as error:
        fail(SonResult.REBIRTH_REFUSED, reason=str(error))
    call.spend_essence(table.rebirth_gate_cost)
    call.target(child.id)
    await call.record(
        "tools.son.reborn", roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: spirit.id, IncidentRole.CHILD: child.id}, kind=ChronicleKind.WORSHIP
    )
    return result(SonResult.REBIRTH_DONE, spirit=spirit.name, child=child.name, cost=table.rebirth_gate_cost)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(
            SonToolId.REVEAL_TENET,
            son,
            RevealTenetInput,
            ToolMeta(ActionKind.REVELATION, son_standard_action, essence_cost=lambda rules: rules.doctrine.reveal_cost),
            reveal_tenet,
        ),
        ToolSpec(
            SonToolId.OPEN_REBIRTH_GATE,
            son,
            RebirthGateInput,
            ToolMeta(ActionKind.RESURRECT_MORTAL, son_standard_action, essence_cost=lambda rules: rules.necromancy.rebirth_gate_cost),
            open_rebirth_gate,
        ),
    ]
