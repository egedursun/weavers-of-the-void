from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.evolution import SpeciesTraitRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import OuterHunger
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.engine.divine.outer import outer_profile
from aerona.engine.primitives.numbers import clamp_int
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
TRAIT_STEP = 10


class HungerInput(ToolInput):
    outer_id: int
    hunger: OuterHunger
    reason: Reason


class TraitInput(ToolInput):
    species_id: int
    trait: EvolvedTrait
    raise_it: bool = True
    reason: Reason


async def turn_hunger(call: SonCall, args: HungerInput) -> str:
    being = await living_entity(call.session, args.outer_id)
    if being is None or being.entity_type is not EntityType.OUTER_BEING or held(being.id):
        fail(SonResult.WAY_REFUSED, why="there is no such being from outside")
    await ensure_in_reach(call, being)
    row = await outer_profile(call.tick, being)
    if "hunger" in row.locked:
        fail(SonResult.WAY_REFUSED, why="the Creator holds that hunger as it is")
    row.hunger = args.hunger
    row.updated_epoch = call.tick.epoch
    await call.session.flush()
    call.target(being.id)
    what = f"the hunger of {being.name} turned to {spoken(args.hunger)}"
    await call.chronicle(ChronicleKind.MIRACLE, lines.TURN_HUNGER, entity_ids=[being.id], son=call.son.name, what=what, reason=args.reason)
    return result(SonResult.WAY_TAKEN, what=what)


async def shape_trait(call: SonCall, args: TraitInput) -> str:
    species = await living_entity(call.session, args.species_id)
    if species is None or species.entity_type is not EntityType.SPECIES or held(species.id):
        fail(SonResult.WAY_REFUSED, why="there is no such living kind of creature")
    await ensure_in_reach(call, species)
    if species.location_id is None:
        fail(SonResult.WAY_REFUSED, why=f"{species.name} has no home ground")
    row = await call.session.get(SpeciesTraitRow, (species.id, species.location_id, args.trait))
    if row is None:
        row = SpeciesTraitRow(species_entity_id=species.id, region_entity_id=species.location_id, trait=args.trait, updated_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    elif "mean" in row.locked:
        fail(SonResult.WAY_REFUSED, why="the Creator holds that trait as it is")
    row.mean = clamp_int((row.mean or PERCENT // 2) + (TRAIT_STEP if args.raise_it else -TRAIT_STEP), 0, PERCENT)
    row.updated_epoch = call.tick.epoch
    await call.session.flush()
    call.target(species.id)
    what = f"{spoken(args.trait)} {'raised' if args.raise_it else 'lowered'} in {species.name}"
    await call.chronicle(ChronicleKind.MIRACLE, lines.SHAPE_TRAIT, entity_ids=[species.id], son=call.son.name, what=what, reason=args.reason)
    return result(SonResult.WAY_TAKEN, what=what)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.TURN_HUNGER, AgentKind.SON, HungerInput, meta, turn_hunger),
        ToolSpec(SonToolId.SHAPE_TRAIT, AgentKind.SON, TraitInput, meta, shape_trait),
    ]
