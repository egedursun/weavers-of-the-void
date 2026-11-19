from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.ages import ArcRow, IrregularSeasonRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.ages import ArcOutcome, SeasonSpell, SetupKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.queries import living_entity
from aerona.engine.storyteller import control
from aerona.engine.storyteller.ages import current_age
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
MORTALS = frozenset({EntityType.MORTAL})
LONGEST = 20


class UnsettleSeasonsInput(ToolInput):
    world_id: int
    reason: Reason


class LengthenWinterInput(ToolInput):
    world_id: int
    epochs: int = Field(ge=1, le=LONGEST)
    reason: Reason


class PressTaleInput(ToolInput):
    arc_id: int
    reason: Reason


class ForeshadowInput(ToolInput):
    subject_id: int
    reason: Reason


class EchoLifeInput(ToolInput):
    mortal_id: int
    reason: Reason


def reason_of(error: ValidationFailedError) -> str:
    return str(error).rstrip(".")


async def world_in_reach(call: SonCall, world_id: int, refused: SonResult) -> WorldRow:
    world = await call.session.get(WorldRow, world_id)
    if world is None:
        fail(refused, why="there is no such world")
    if held(world.id):
        fail(refused, why="a stronger hand holds it")
    if call.son.current_world_id != world.id:
        fail(refused, why="you do not walk that world")
    return world


async def unsettle_seasons(call: SonCall, args: UnsettleSeasonsInput) -> str:
    world = await world_in_reach(call, args.world_id, SonResult.SEASONS_REFUSED)
    try:
        row = await control.unsettle_seasons(call.tick, world.id, call.son.id)
    except ValidationFailedError as error:
        fail(SonResult.SEASONS_REFUSED, why=reason_of(error))
    call.target(world.id)
    await call.record(
        "tools.son.unsettle_seasons",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: world.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.CLIMATE,
    )
    return result(SonResult.SEASONS_UNSETTLED, world=world.name, length=row.spell_length)


async def lengthen_winter(call: SonCall, args: LengthenWinterInput) -> str:
    world = await world_in_reach(call, args.world_id, SonResult.WINTER_REFUSED)
    row = await call.session.get(IrregularSeasonRow, world.id)
    if row is None or row.spell is not SeasonSpell.WINTER:
        fail(SonResult.WINTER_REFUSED, why="no long winter holds that world")
    await control.edit_record(call.tick, "irregular_season", world.id, {"spell_length": row.spell_length + args.epochs}, [])
    call.target(world.id)
    await call.record(
        "tools.son.lengthen_winter",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: world.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.CLIMATE,
    )
    return result(SonResult.WINTER_LENGTHENED, world=world.name, epochs=args.epochs)


async def press_tale(call: SonCall, args: PressTaleInput) -> str:
    arc = await call.session.get(ArcRow, args.arc_id)
    if arc is None or arc.outcome is not ArcOutcome.OPEN:
        fail(SonResult.TALE_REFUSED, why="no such tale is under way")
    subject = await living_entity(call.session, arc.subject_node_id)
    if subject is None:
        fail(SonResult.TALE_REFUSED, why="its subject is gone")
    await ensure_in_reach(call, subject)
    if held(subject.id):
        fail(SonResult.TALE_REFUSED, why="a stronger hand holds it")
    await control.press_arc(call.tick, arc.id, PERCENT)
    call.target(subject.id)
    told = spoken(arc.template)
    await call.record(
        "tools.son.press_tale",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: subject.id},
        facts={"tale": str(told), "reason": args.reason},
        kind=ChronicleKind.FATE,
    )
    return result(SonResult.TALE_PRESSED, subject=subject.name, tale=told)


async def foreshadow(call: SonCall, args: ForeshadowInput) -> str:
    subject = await living_entity(call.session, args.subject_id)
    if subject is None:
        fail(SonResult.FORESHADOW_REFUSED, why="there is no such subject")
    await ensure_in_reach(call, subject)
    if held(subject.id):
        fail(SonResult.FORESHADOW_REFUSED, why="a stronger hand holds it")
    row = await control.add_setup(call.tick, SetupKind.PORTENT, call.son.id, subject.id)
    call.target(subject.id)
    await call.record(
        "tools.son.foreshadow",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: subject.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.FORESHADOWED, subject=subject.name, lapse=row.opened_epoch + call.tick.rules.arcs.lapse_epochs)


async def echo_life(call: SonCall, args: EchoLifeInput) -> str:
    mortal = await call.session.get(EntityRow, args.mortal_id)
    if mortal is None or mortal.entity_type not in MORTALS:
        fail(SonResult.ECHO_REFUSED, why="there is no such mortal")
    if held(mortal.id):
        fail(SonResult.ECHO_REFUSED, why="a stronger hand holds it")
    age = await current_age(call.tick)
    if age is None:
        fail(SonResult.ECHO_REFUSED, why="the cosmos does not turn in ages")
    arc = await call.session.scalar(select(ArcRow).where(ArcRow.subject_node_id == mortal.id).order_by(ArcRow.id.desc()).limit(1))
    if arc is None:
        fail(SonResult.ECHO_REFUSED, why="no tale was ever told of that life")
    await control.add_echo(call.tick, age.id, arc.template, mortal.id, call.tick.rules.ages.echo_weight)
    call.target(mortal.id)
    await call.record(
        "tools.son.echo_life", roles={IncidentRole.ACTOR: call.son.id, IncidentRole.TARGET: mortal.id}, facts={"reason": args.reason}, kind=ChronicleKind.FATE
    )
    return result(SonResult.LIFE_ECHOED, mortal=mortal.name, tale=spoken(arc.template))


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.UNSETTLE_SEASONS, son, UnsettleSeasonsInput, meta, unsettle_seasons),
        ToolSpec(SonToolId.LENGTHEN_WINTER, son, LengthenWinterInput, meta, lengthen_winter),
        ToolSpec(SonToolId.PRESS_TALE, son, PressTaleInput, meta, press_tale),
        ToolSpec(SonToolId.FORESHADOW, son, ForeshadowInput, meta, foreshadow),
        ToolSpec(SonToolId.ECHO_LIFE, son, EchoLifeInput, meta, echo_life),
    ]
