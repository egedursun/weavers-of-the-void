from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.errors import AeronaError
from aerona.db.tables.divine import BreachPointRow, DivineWoundRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import GoalSource, GodGoalKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.lifecycle_end import LifecycleState
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.divine import control
from aerona.engine.divine.foreign import friendship, pact_between, seal_pact
from aerona.engine.divine.goals import GOAL_LABELS, active_goals
from aerona.engine.divine.outer import oppose_cost
from aerona.engine.divine.wounds import gather
from aerona.engine.lifecycle.states import state_of
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.stats import stat_or
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach, require_essence


class SetAimInput(ToolInput):
    kind: GodGoalKind
    target_id: int | None = None
    world_id: int | None = None
    domain: Domain | None = None
    amount: int = 0


class MortalFormInput(ToolInput):
    place_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class WardInput(ToolInput):
    outsider_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class PactInput(ToolInput):
    god_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class MendInput(ToolInput):
    wound_id: int
    essence: int


async def set_aim(call: SonCall, args: SetAimInput) -> str:
    for old in await active_goals(call.tick, call.son.id):
        if old.source is GoalSource.AGENT:
            await control.drop_goal(call.tick, old.id)
    try:
        row = await control.set_goal(
            call.tick, call.son.id, args.kind, target_id=args.target_id, world_id=args.world_id, domain=args.domain, amount=args.amount, source=GoalSource.AGENT
        )
    except AeronaError as error:
        fail(SonResult.AIM_REFUSED, reason=error.message)
    await call.record("tools.son.set_aim", roles={IncidentRole.ACTOR: call.son.id}, facts={"aim": GOAL_LABELS[row.kind].lower()}, kind=ChronicleKind.ASCENSION)
    return result(SonResult.AIM_SET, aim=GOAL_LABELS[row.kind].lower())


async def take_mortal_form(call: SonCall, args: MortalFormInput) -> str:
    place = await require_canon(call.session, args.place_id)
    await ensure_in_reach(call, place)
    cost = call.rules.avatars.essence_cost
    require_essence(call, cost)
    try:
        avatar = await control.manifest_avatar(call.tick, call.son.id, place.id)
    except AeronaError as error:
        fail(SonResult.FORM_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(avatar.id)
    await call.record(
        "tools.son.mortal_form",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: place.id, IncidentRole.SUBJECT: avatar.id},
        facts={"reason": str(args.reason)},
        place=place.id,
        kind=ChronicleKind.MIRACLE,
    )
    return result(SonResult.FORM_TAKEN, name=avatar.name, place=place.name)


async def ward_against_outer(call: SonCall, args: WardInput) -> str:
    table = call.rules.outer_beings
    being = require_type(await require_canon(call.session, args.outsider_id), {EntityType.OUTER_BEING}, SonResult.NOT_AN_OUTSIDER, name=str(args.outsider_id))
    if await state_of(call.session, being.id) is LifecycleState.DESTROYED:
        fail(SonResult.NOT_AN_OUTSIDER, name=being.name)
    await ensure_in_reach(call, being)
    cost = oppose_cost(table.oppose_cost_pct, being)
    require_essence(call, cost)
    call.spend_essence(cost)
    call.son.sanity = clamp_percent((call.son.sanity if call.son.sanity is not None else PERCENT) - table.oppose_sanity)
    being.stats = being.stats.model_copy(update={"interest": clamp_percent(stat_or(being, "interest", 0) - table.ward_interest)})
    for breach in await call.session.scalars(select(BreachPointRow).where(BreachPointRow.outer_entity_id == being.id)):
        if "strength" not in breach.locked:
            breach.strength = clamp_int(breach.strength - table.ward_breach, 1, PERCENT)
    call.target(being.id)
    await call.record(
        "tools.son.ward_outer",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: being.id},
        facts={"reason": str(args.reason)},
        kind=ChronicleKind.OUTER_BEING,
    )
    return result(SonResult.WARDED, name=being.name, cost=cost)


async def seal_divine_pact(call: SonCall, args: PactInput) -> str:
    god = await call.session.get(ForeignGodRow, args.god_id)
    if god is None:
        fail(SonResult.NO_SUCH_FOREIGN_GOD, id=args.god_id)
    if await pact_between(call.tick, call.son.id, god.id) is not None:
        fail(SonResult.PACT_EXISTS, name=god.name)
    warmth = await friendship(call.tick, god.id, call.son.id)
    if warmth < call.rules.god_relations.pact_friendship:
        fail(SonResult.PACT_REFUSED, name=god.name, warmth=warmth, needed=call.rules.god_relations.pact_friendship)
    treaty = await seal_pact(call.tick, call.son, god)
    call.target(treaty.id)
    await call.record(
        "tools.son.divine_pact",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [god.id, treaty.id]},
        facts={"reason": str(args.reason)},
        kind=ChronicleKind.FOREIGN_GOD,
    )
    return result(SonResult.PACT_SEALED, name=god.name)


async def mend_wound(call: SonCall, args: MendInput) -> str:
    row = await call.session.get(DivineWoundRow, args.wound_id)
    if row is None or row.god_node_id != call.son.id or row.healed >= PERCENT:
        fail(SonResult.NO_SUCH_WOUND, id=args.wound_id)
    spend = max(1, min(args.essence, call.son.essence))
    require_essence(call, spend)
    call.spend_essence(spend)
    if "healed" not in row.locked:
        row.healed = clamp_int(row.healed + spend * PERCENT // max(1, row.severity), 0, PERCENT)
        if row.healed >= PERCENT:
            await gather(call.session, row)
    return result(SonResult.WOUND_MENDED, healed=row.healed)


def mortal_form_cost(rules: Rules) -> int:
    return rules.avatars.essence_cost


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(SonToolId.SET_AIM, AgentKind.SON, SetAimInput, ToolMeta(ActionKind.INFLUENCE, no_cost), set_aim),
        ToolSpec(
            SonToolId.TAKE_MORTAL_FORM,
            AgentKind.SON,
            MortalFormInput,
            ToolMeta(ActionKind.MANIFESTATION, son_standard_action, essence_cost=mortal_form_cost),
            take_mortal_form,
        ),
        ToolSpec(SonToolId.WARD_AGAINST_OUTER, AgentKind.SON, WardInput, ToolMeta(ActionKind.CLEANSE_LEAK, son_standard_action), ward_against_outer),
        ToolSpec(SonToolId.SEAL_DIVINE_PACT, AgentKind.SON, PactInput, ToolMeta(ActionKind.COVENANT, son_standard_action), seal_divine_pact),
        ToolSpec(SonToolId.MEND_WOUND, AgentKind.SON, MendInput, ToolMeta(ActionKind.BLESS_EXISTENCE, no_cost), mend_wound),
    ]
