from typing import Any

from pydantic import Field

from aerona.catalog.intimacy_shapes import PATH_COST_PCT
from aerona.constants.units import PERCENT
from aerona.core.grammar import several, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intimacy import ChildRecognitionRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.intimacy import ChildLegitimacy, LegitimacyPath, RestraintVow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathKind
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.intimacy.legitimacy import legitimacy_of, rule_for
from aerona.engine.mortal.kin import parents_of
from aerona.engine.polity.oaths import oaths_of, swear
from aerona.engine.primitives.numbers import round_half_up
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

VOW_OATHS = {RestraintVow.CELIBACY: OathKind.CELIBACY, RestraintVow.FIDELITY: OathKind.FIDELITY}
TERM_MAX = 10


class SeekRecognitionInput(ToolInput):
    child_id: int
    path: LegitimacyPath


class TakeRestraintVowInput(ToolInput):
    kind: RestraintVow
    term: int = Field(default=0, ge=0, le=TERM_MAX)


async def seek_recognition(call: MortalCall, args: SeekRecognitionInput) -> str:
    child = await call.session.get(EntityRow, args.child_id)
    if child is None or child.status is not EntityStatus.CANON or call.me.id not in await parents_of(call.session, child.id):
        fail(MortalResult.UNIONS_REFUSED, why="only a parent of a living child seeks its recognition")
    if held(child.id):
        fail(MortalResult.UNIONS_REFUSED, why="a god holds this child as it is")
    if await legitimacy_of(call.session, child) is ChildLegitimacy.FULL:
        fail(MortalResult.UNIONS_REFUSED, why=f"{child.name} already stands in full")
    rule = await rule_for(call.session, child)
    if rule is None or rule.path is LegitimacyPath.NONE or args.path is LegitimacyPath.NONE:
        fail(MortalResult.UNIONS_REFUSED, why="your people know no way to change this child's standing")
    if args.path is not rule.path:
        fail(MortalResult.UNIONS_REFUSED, why=f"your people change a child's standing only by {spoken(rule.path)}")
    cost = round_half_up(rule.cost * PATH_COST_PCT[args.path] / PERCENT) + (
        call.rules.unions_and_birth.recognition_cost if args.path is LegitimacyPath.PAYMENT else 0
    )
    if await points_of(call.session, call.me) < cost:
        fail(MortalResult.UNIONS_REFUSED, why=f"it costs {cost} of wealth and you have less")
    await shift_points(call.session, call.me, -cost)
    call.session.add(ChildRecognitionRow(child_node_id=child.id, path=args.path, sponsor_node_id=call.me.id, recognized_epoch=call.epoch, locked=[]))
    call.target(child.id)
    await call.record(
        "birth.recognition", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: child.id}, facts={"path": args.path}, place=call.me.location_id
    )
    return result(MortalResult.CHILD_RECOGNISED, name=child.name, path=spoken(args.path), cost=cost)


async def take_restraint_vow(call: MortalCall, args: TakeRestraintVowInput) -> str:
    oath_kind = VOW_OATHS[args.kind]
    if await oaths_of(call.tick, call.me.id, oath_kind):
        fail(MortalResult.UNIONS_REFUSED, why=f"you already keep a vow of {spoken(args.kind)}")
    oath = await swear(call.tick, call.me, oath_kind, recipient_id=None, note_text="a vow taken of your own will")
    oath.deadline_epoch = call.epoch + args.term if args.term else None
    call.target(call.me.id)
    await call.record("unions.vow_taken", roles={IncidentRole.ACTOR: call.me.id}, facts={"vow": oath_kind}, place=call.me.location_id)
    span = f"for {several(args.term, 'epoch', 'epochs')}" if args.term else "for life"
    return result(MortalResult.RESTRAINT_VOWED, vow=spoken(args.kind), span=span)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(
            MortalToolId.SEEK_RECOGNITION, AgentKind.MORTAL, SeekRecognitionInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), seek_recognition
        ),
        ToolSpec(
            MortalToolId.TAKE_RESTRAINT_VOW,
            AgentKind.MORTAL,
            TakeRestraintVowInput,
            ToolMeta(ActionKind.INFLUENCE, mortal_standard_action),
            take_restraint_vow,
        ),
    ]
