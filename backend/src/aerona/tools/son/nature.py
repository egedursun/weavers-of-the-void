from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.nature import SenseProfileRow, SpeciesRelationRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.nature import SenseKind, SymbiosisKind
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class BindSpeciesInput(ToolInput):
    first_species_id: int
    second_species_id: int
    kind: SymbiosisKind
    reason: Reason


class SharpenSenseInput(ToolInput):
    holder_id: int
    sense: SenseKind
    reason: Reason


async def bind_species(call: SonCall, args: BindSpeciesInput) -> str:
    first = await living_entity(call.session, args.first_species_id)
    second = await living_entity(call.session, args.second_species_id)
    if first is None or second is None or first.id == second.id:
        fail(SonResult.SPECIES_UNBOUND, why="you need two different living kinds")
    if await call.session.get(SpeciesProfileRow, first.id) is None or await call.session.get(SpeciesProfileRow, second.id) is None:
        fail(SonResult.SPECIES_UNBOUND, why="only kinds of creature or plant can be bound")
    if call.son.current_world_id not in {first.world_id, second.world_id}:
        fail(SonResult.SPECIES_UNBOUND, why="you can bind only kinds of the world you stand on")
    if held(first.id) or held(second.id):
        fail(SonResult.SPECIES_UNBOUND, why="a stronger hand holds them")
    paired = await call.session.scalar(
        select(SpeciesRelationRow.id).where(
            ((SpeciesRelationRow.first_species_id == first.id) & (SpeciesRelationRow.second_species_id == second.id))
            | ((SpeciesRelationRow.first_species_id == second.id) & (SpeciesRelationRow.second_species_id == first.id))
        )
    )
    if paired is not None:
        fail(SonResult.SPECIES_UNBOUND, why="those kinds are bound already")
    row = SpeciesRelationRow(
        first_species_id=first.id, second_species_id=second.id, kind=args.kind, strength=call.tick.rules.symbiosis.start_strength, since_epoch=call.tick.epoch
    )
    row.locked = []
    call.session.add(row)
    await call.session.flush()
    call.target(first.id)
    kind = args.kind.value
    await call.chronicle(
        ChronicleKind.CREATION,
        lines.BIND_SPECIES,
        entity_ids=[first.id, second.id],
        son=call.son.name,
        first=first.name,
        second=second.name,
        kind=kind,
        reason=args.reason,
    )
    return result(SonResult.SPECIES_BOUND, first=first.name, second=second.name, kind=kind)


async def sharpen_sense(call: SonCall, args: SharpenSenseInput) -> str:
    holder = await living_entity(call.session, args.holder_id)
    if holder is None:
        fail(SonResult.SENSE_UNSHARPENED, why="no such living kind or people")
    if holder.entity_type is not EntityType.PEOPLE and await call.session.get(SpeciesProfileRow, holder.id) is None:
        fail(SonResult.SENSE_UNSHARPENED, why="only a kind of creature or a people holds senses")
    if holder.world_id != call.son.current_world_id:
        fail(SonResult.SENSE_UNSHARPENED, why="you can sharpen only the senses of the world you stand on")
    row = await call.session.get(SenseProfileRow, (holder.id, args.sense))
    if held(holder.id) or (row is not None and "acuity" in row.locked):
        fail(SonResult.SENSE_UNSHARPENED, why="a stronger hand holds it")
    if row is None:
        row = SenseProfileRow(holder_entity_id=holder.id, sense=args.sense, acuity=0)
        row.locked = []
        call.session.add(row)
    row.acuity = clamp_int(row.acuity + call.tick.rules.senses.sharpened, 0, PERCENT)
    await call.session.flush()
    call.target(holder.id)
    sense = args.sense.value.replace("_", " ")
    await call.chronicle(
        ChronicleKind.CREATION, lines.SHARPEN_SENSE, entity_ids=[holder.id], son=call.son.name, sense=sense, holder=holder.name, reason=args.reason
    )
    return result(SonResult.SENSE_SHARPENED, sense=sense, holder=holder.name, acuity=row.acuity)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.BIND_SPECIES, son, BindSpeciesInput, meta, bind_species),
        ToolSpec(SonToolId.SHARPEN_SENSE, son, SharpenSenseInput, meta, sharpen_sense),
    ]
