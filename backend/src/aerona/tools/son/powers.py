from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.concealment import HiddenTruthRow
from aerona.db.tables.powers import PowerRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.concealment import ConcealScope, HiddenTruthKind
from aerona.domain.enums.powers import (
    Learnability,
    PowerOrigin,
    PowerState,
    PowerStructure,
    PowerVisibility,
    SourceAccess,
    SourceLocus,
    SourceRenewal,
)
from aerona.engine.powers import control
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Name = Annotated[str, Field(min_length=1, max_length=120)]
PERCENT = 100


class ShapeSourceInput(ToolInput):
    name: Name
    place_id: int
    locus: SourceLocus
    renewal: SourceRenewal = SourceRenewal.TIME
    access: SourceAccess = SourceAccess.ANYONE
    visibility: PowerVisibility = PowerVisibility.SUBTLE
    reason: Reason


class ShapeMagicInput(ToolInput):
    name: Name
    world_id: int
    structure: PowerStructure
    predictability: int = Field(default=50, ge=0, le=PERCENT)
    prevalence: int = Field(default=50, ge=0, le=PERCENT)
    learnability: Learnability = Learnability.ANYONE
    reason: Reason


class GrantPowerInput(ToolInput):
    holder_id: int
    technique: SpellTechnique
    form: SpellForm
    strength: int = Field(default=3, ge=1, le=10)
    reason: Reason


class RevokePowerInput(ToolInput):
    power_id: int
    reason: Reason


class UnveilInput(ToolInput):
    truth_id: int
    population_id: int
    reason: Reason


class HideTruthInput(ToolInput):
    title: Name
    subject_id: int
    kind: HiddenTruthKind
    hidden_from: ConcealScope = ConcealScope.EVERYONE
    reason: Reason


async def shape_source(call: SonCall, args: ShapeSourceInput) -> str:
    place = await living_entity(call.session, args.place_id)
    if place is None:
        fail(SonResult.SOURCE_REFUSED, why="there is no such place")
    await ensure_in_reach(call, place)
    try:
        row = await control.create_source(
            call.tick, control.SourceDraft(args.name, place.id, args.locus, args.renewal, args.access, args.visibility, PERCENT // 2)
        )
    except ValidationFailedError as error:
        fail(SonResult.SOURCE_REFUSED, why=str(error))
    call.target(place.id)
    await call.chronicle(ChronicleKind.FATE, lines.SHAPE_SOURCE, entity_ids=[place.id], son=call.son.name, name=row.name, reason=args.reason)
    return result(SonResult.SOURCE_SHAPED, name=row.name)


async def shape_magic(call: SonCall, args: ShapeMagicInput) -> str:
    if args.world_id != call.son.current_world_id:
        fail(SonResult.MAGIC_REFUSED, why="that world is beyond your reach")
    draft = control.SystemDraft(
        args.name, args.world_id, args.structure, args.predictability, args.prevalence, PERCENT // 2, SourceAccess.ANYONE, args.learnability
    )
    try:
        row = await control.create_system(call.tick, draft)
    except (ValidationFailedError, NotFoundError) as error:
        fail(SonResult.MAGIC_REFUSED, why=str(error))
    await call.chronicle(ChronicleKind.FATE, lines.SHAPE_MAGIC, entity_ids=[], son=call.son.name, name=row.name, reason=args.reason)
    return result(SonResult.MAGIC_SHAPED, name=row.name)


async def grant_power(call: SonCall, args: GrantPowerInput) -> str:
    holder = await living_entity(call.session, args.holder_id)
    if holder is None:
        fail(SonResult.POWER_GRANT_REFUSED, why="there is no one there")
    await ensure_in_reach(call, holder)
    draft = control.PowerDraft(
        holder.id, args.technique, args.form, args.strength, PERCENT // 2, PowerOrigin.GRANTED, PowerState.ACTIVE, PowerVisibility.SUBTLE
    )
    try:
        await control.grant_power(call.tick, call.son.id, draft)
    except ValidationFailedError as error:
        fail(SonResult.POWER_GRANT_REFUSED, why=str(error))
    call.target(holder.id)
    await call.chronicle(ChronicleKind.FATE, lines.GRANT_POWER, entity_ids=[holder.id], son=call.son.name, name=holder.name, reason=args.reason)
    return result(SonResult.POWER_GRANTED, name=holder.name)


async def revoke_power(call: SonCall, args: RevokePowerInput) -> str:
    power = await call.session.get(PowerRow, args.power_id)
    if power is None:
        fail(SonResult.POWER_REVOKE_REFUSED, why="there is no such power")
    try:
        await control.revoke_power(call.tick, call.son.id, power.id)
    except ValidationFailedError as error:
        fail(SonResult.POWER_REVOKE_REFUSED, why=str(error))
    call.target(power.holder_node_id)
    await call.chronicle(ChronicleKind.FATE, lines.REVOKE_POWER, entity_ids=[power.holder_node_id], son=call.son.name, reason=args.reason)
    return result(SonResult.POWER_REVOKED)


async def unveil_truth(call: SonCall, args: UnveilInput) -> str:
    truth = await call.session.get(HiddenTruthRow, args.truth_id)
    population = await living_entity(call.session, args.population_id)
    if truth is None or population is None:
        fail(SonResult.UNVEIL_REFUSED, why="there is no such truth or people")
    await ensure_in_reach(call, population)
    await control.reveal(call.tick, truth.id, population.id)
    call.target(population.id)
    await call.chronicle(ChronicleKind.FATE, lines.UNVEIL_TRUTH, entity_ids=[population.id], son=call.son.name, name=population.name, reason=args.reason)
    return result(SonResult.TRUTH_UNVEILED, title=truth.title, name=population.name)


async def hide_truth(call: SonCall, args: HideTruthInput) -> str:
    subject = await living_entity(call.session, args.subject_id)
    if subject is None:
        fail(SonResult.HIDING_REFUSED, why="there is no such thing")
    await ensure_in_reach(call, subject)
    draft = control.TruthDraft(args.title, subject.id, args.kind, args.hidden_from, None, PERCENT * 3 // 4, ("by_nature",), 0, call.son.id)
    row = await control.create_truth(call.tick, draft)
    call.target(subject.id)
    await call.chronicle(ChronicleKind.FATE, lines.HIDE_TRUTH, entity_ids=[subject.id], son=call.son.name, name=subject.name, reason=args.reason)
    return result(SonResult.TRUTH_HIDDEN, title=row.title)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.SHAPE_SOURCE, son, ShapeSourceInput, meta, shape_source),
        ToolSpec(SonToolId.SHAPE_MAGIC, son, ShapeMagicInput, meta, shape_magic),
        ToolSpec(SonToolId.GRANT_POWER, son, GrantPowerInput, meta, grant_power),
        ToolSpec(SonToolId.REVOKE_POWER, son, RevokePowerInput, meta, revoke_power),
        ToolSpec(SonToolId.UNVEIL_TRUTH, son, UnveilInput, meta, unveil_truth),
        ToolSpec(SonToolId.HIDE_TRUTH, son, HideTruthInput, meta, hide_truth),
    ]
