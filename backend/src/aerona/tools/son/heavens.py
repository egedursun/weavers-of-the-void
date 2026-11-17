from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, REASON_MAX, REASON_MIN
from aerona.core.errors import AeronaError
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import DimensionRow, GalaxyRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import DimensionalEventKind, GalacticEventKind, GalacticStructureKind, PhenomenonCause, PhenomenonKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.physics import CosmicFeatureKind
from aerona.engine.cosmos import control, physics_control
from aerona.engine.divine.control import open_breach as engine_open_breach
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.cosmography import fresh_name, reaches_dimension, reaches_galaxy
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]


class ShapeStructureInput(ToolInput):
    galaxy_id: int
    kind: GalacticStructureKind
    name: Name
    reason: Reason


class StirGalaxyInput(ToolInput):
    galaxy_id: int
    kind: GalacticEventKind
    other_galaxy_id: int | None = None
    star_id: int | None = None
    reason: Reason


class StirDimensionInput(ToolInput):
    dimension_id: int
    kind: DimensionalEventKind
    other_dimension_id: int | None = None
    world_id: int | None = None
    reason: Reason


class DimensionLawInput(ToolInput):
    dimension_id: int
    law_id: int
    reason: Reason


class CosmicFeatureInput(ToolInput):
    kind: CosmicFeatureKind
    name: Name
    star_id: int | None = None
    galaxy_id: int | None = None
    world_id: int | None = None
    world_b_id: int | None = None
    reason: Reason


class StarSystemInput(ToolInput):
    name: Name
    star_ids: list[int] = Field(min_length=2)
    reason: Reason


class PhenomenonDraftInput(ToolInput):
    kind: PhenomenonKind
    region_id: int
    reason: Reason


class BreachInput(ToolInput):
    being_id: int
    region_id: int
    reason: Reason


async def galaxy_in_hand(call: SonCall, galaxy_id: int) -> GalaxyRow:
    galaxy = await call.session.get(GalaxyRow, galaxy_id)
    if galaxy is None:
        fail(SonResult.NO_SUCH_GALAXY, id=galaxy_id)
    if galaxy.patron_son_id != call.son.id and not await reaches_galaxy(call, galaxy.id):
        fail(SonResult.GALAXY_OUT_OF_REACH, name=galaxy.name)
    return galaxy


async def dimension_in_hand(call: SonCall, dimension_id: int) -> DimensionRow:
    dimension = await call.session.get(DimensionRow, dimension_id)
    if dimension is None:
        fail(SonResult.NO_SUCH_DIMENSION, id=dimension_id)
    if dimension.ruler_node_id != call.son.id and not await reaches_dimension(call, dimension.id):
        fail(SonResult.DIMENSION_OUT_OF_REACH, name=dimension.name)
    return dimension


async def star_in_hand(call: SonCall, star_id: int) -> StarRow:
    star = await call.session.get(StarRow, star_id)
    if star is None:
        fail(SonResult.NO_SUCH_STAR_ID, id=star_id)
    if star.patron_son_id == call.son.id:
        return star
    for world_id in await call.session.scalars(select(WorldRow.id).where(WorldRow.star_id == star.id)):
        if await call.reachable_world(world_id):
            return star
    if star.galaxy_id is not None:
        galaxy = await call.session.get(GalaxyRow, star.galaxy_id)
        if galaxy is not None and (galaxy.patron_son_id == call.son.id or await reaches_galaxy(call, galaxy.id)):
            return star
    fail(SonResult.STAR_OUT_OF_REACH, name=star.name)


async def world_in_hand(call: SonCall, world_id: int) -> WorldRow:
    world = await call.session.get(WorldRow, world_id)
    if world is None:
        fail(SonResult.NO_SUCH_WORLD)
    if not await call.reachable_world(world.id):
        fail(SonResult.WORLD_OUT_OF_REACH, name=world.name)
    return world


async def shape_galactic_structure(call: SonCall, args: ShapeStructureInput) -> str:
    galaxy = await galaxy_in_hand(call, args.galaxy_id)
    name = await fresh_name(call, args.name)
    cost = call.rules.son_tools.shape_structure_essence
    require_essence(call, cost)
    try:
        structure = await control.new_structure(
            call.tick,
            galaxy.id,
            args.kind,
            name=name,
            position=(0.0, 0.0, galaxy.radius * call.rules.galaxies.inner_reach_pct / 100),
            intensity=call.rules.galaxies.layout_intensity,
        )
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    await call.record(
        "tools.son.shape_galactic_structure",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: galaxy.id},
        facts={"structure": structure.name, "reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.STRUCTURE_SHAPED, name=structure.name, galaxy=galaxy.name)


async def stir_galaxy(call: SonCall, args: StirGalaxyInput) -> str:
    galaxy = await galaxy_in_hand(call, args.galaxy_id)
    if args.other_galaxy_id is not None:
        await galaxy_in_hand(call, args.other_galaxy_id)
    if args.star_id is not None:
        await star_in_hand(call, args.star_id)
    cost = call.rules.son_tools.stir_galaxy_essence
    require_essence(call, cost)
    try:
        event = await control.galactic_event(
            call.tick, galaxy.id, args.kind, intensity=call.rules.son_tools.cosmic_event_intensity, other_id=args.other_galaxy_id, star_id=args.star_id
        )
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    await call.record(
        "tools.son.stir_galaxy",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: galaxy.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.GALAXY_STIRRED, name=galaxy.name, text=event.text or "")


async def stir_dimension(call: SonCall, args: StirDimensionInput) -> str:
    dimension = await dimension_in_hand(call, args.dimension_id)
    if args.other_dimension_id is not None:
        await dimension_in_hand(call, args.other_dimension_id)
    if args.world_id is not None:
        await world_in_hand(call, args.world_id)
    cost = call.rules.son_tools.stir_dimension_essence
    require_essence(call, cost)
    try:
        event = await control.dimensional_event(
            call.tick, dimension.id, args.kind, intensity=call.rules.son_tools.cosmic_event_intensity, other_id=args.other_dimension_id, world_id=args.world_id
        )
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    await call.record(
        "tools.son.stir_dimension",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: dimension.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.DIMENSION_STIRRED, name=dimension.name, text=event.text or "")


async def bind_law_across_dimension(call: SonCall, args: DimensionLawInput) -> str:
    dimension = await call.session.get(DimensionRow, args.dimension_id)
    if dimension is None:
        fail(SonResult.NO_SUCH_DIMENSION, id=args.dimension_id)
    if dimension.ruler_node_id != call.son.id:
        fail(SonResult.NOT_YOUR_DIMENSION, name=dimension.name)
    law = require_type(await require_canon(call.session, args.law_id), {EntityType.NATURAL_LAW}, SonResult.NOT_A_NATURAL_LAW, id=args.law_id)
    await ensure_in_reach(call, law)
    cost = call.rules.son_tools.dimension_law_essence
    require_essence(call, cost)
    try:
        await control.bind_law(call.tick, dimension.id, law.id)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(law.id)
    await call.record(
        "tools.son.bind_law_across_dimension",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [law.id, dimension.id]},
        facts={"reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.DIMENSION_LAW_BOUND, law=law.name, dimension=dimension.name)


async def set_cosmic_feature(call: SonCall, args: CosmicFeatureInput) -> str:
    if args.star_id is not None:
        await star_in_hand(call, args.star_id)
    if args.galaxy_id is not None:
        await galaxy_in_hand(call, args.galaxy_id)
    for world_id in (args.world_id, args.world_b_id):
        if world_id is not None:
            await world_in_hand(call, world_id)
    name = await fresh_name(call, args.name)
    cost = call.rules.son_tools.cosmic_feature_essence
    require_essence(call, cost)
    values = {"star_id": args.star_id, "galaxy_id": args.galaxy_id, "world_id": args.world_id, "world_b_id": args.world_b_id}
    try:
        feature = await physics_control.create_feature(call.tick, args.kind, name, values)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    await call.record(
        "tools.son.set_cosmic_feature",
        roles={IncidentRole.ACTOR: call.son.id},
        facts={"feature": feature.name, "reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.FEATURE_SET, name=feature.name)


async def gather_star_system(call: SonCall, args: StarSystemInput) -> str:
    for star_id in args.star_ids:
        await star_in_hand(call, star_id)
    name = await fresh_name(call, args.name)
    cost = call.rules.son_tools.star_system_essence
    require_essence(call, cost)
    try:
        system = await physics_control.create_system(call.tick, name, list(args.star_ids), 0.0)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(args.star_ids[0])
    await call.record(
        "tools.son.gather_star_system", roles={IncidentRole.ACTOR: call.son.id}, facts={"system": system.name, "reason": args.reason}, kind=ChronicleKind.COSMIC
    )
    return result(SonResult.STAR_SYSTEM_GATHERED, name=system.name, count=len(args.star_ids))


async def raise_phenomenon(call: SonCall, args: PhenomenonDraftInput) -> str:
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name=f"#{args.region_id}")
    await ensure_in_reach(call, region)
    cost = call.rules.son_tools.phenomenon_essence
    require_essence(call, cost)
    try:
        made = await control.new_phenomenon(call.tick, args.kind, region.id, call.rules.son_tools.phenomenon_intensity, PhenomenonCause.DIVINE)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.remember_creation(made.id)
    call.target(made.id)
    await call.record(
        "tools.son.raise_phenomenon",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: made.id, IncidentRole.PLACE: region.id},
        facts={"reason": args.reason},
        place=region.id,
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.PHENOMENON_RAISED, name=made.name, place=region.name)


async def open_breach(call: SonCall, args: BreachInput) -> str:
    being = require_type(await require_canon(call.session, args.being_id), {EntityType.OUTER_BEING}, SonResult.NOT_AN_OUTER_BEING, id=args.being_id)
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name=f"#{args.region_id}")
    await ensure_in_reach(call, region)
    cost = call.rules.son_tools.breach_essence
    require_essence(call, cost)
    try:
        await engine_open_breach(call.tick, being.id, region.id, call.rules.son_tools.breach_strength)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(region.id)
    await call.record(
        "tools.son.open_breach",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: being.id, IncidentRole.PLACE: region.id},
        facts={"reason": args.reason},
        place=region.id,
        kind=ChronicleKind.DISASTER,
    )
    return result(SonResult.BREACH_OPENED, being=being.name, place=region.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    galactic = gate(Gate.GALACTIC_WORKS)
    dimensional = gate(Gate.DIMENSIONAL_WORKS)
    cosmic = gate(Gate.COSMIC_WORKS)
    return [
        ToolSpec(
            SonToolId.SHAPE_GALACTIC_STRUCTURE,
            son,
            ShapeStructureInput,
            ToolMeta(
                ActionKind.SKY_EVENT,
                lambda rules: rules.son_tools.shape_structure_ap,
                essence_cost=lambda rules: rules.son_tools.shape_structure_essence,
                rarity_gate=galactic,
            ),
            shape_galactic_structure,
        ),
        ToolSpec(
            SonToolId.STIR_GALAXY,
            son,
            StirGalaxyInput,
            ToolMeta(
                ActionKind.SKY_EVENT,
                lambda rules: rules.son_tools.stir_galaxy_ap,
                essence_cost=lambda rules: rules.son_tools.stir_galaxy_essence,
                rarity_gate=galactic,
            ),
            stir_galaxy,
        ),
        ToolSpec(
            SonToolId.SET_COSMIC_FEATURE,
            son,
            CosmicFeatureInput,
            ToolMeta(
                ActionKind.SKY_EVENT,
                lambda rules: rules.son_tools.cosmic_feature_ap,
                essence_cost=lambda rules: rules.son_tools.cosmic_feature_essence,
                rarity_gate=galactic,
            ),
            set_cosmic_feature,
        ),
        ToolSpec(
            SonToolId.GATHER_STAR_SYSTEM,
            son,
            StarSystemInput,
            ToolMeta(
                ActionKind.SKY_EVENT,
                lambda rules: rules.son_tools.star_system_ap,
                essence_cost=lambda rules: rules.son_tools.star_system_essence,
                rarity_gate=galactic,
            ),
            gather_star_system,
        ),
        ToolSpec(
            SonToolId.STIR_DIMENSION,
            son,
            StirDimensionInput,
            ToolMeta(
                ActionKind.SKY_EVENT,
                lambda rules: rules.son_tools.stir_dimension_ap,
                essence_cost=lambda rules: rules.son_tools.stir_dimension_essence,
                rarity_gate=dimensional,
            ),
            stir_dimension,
        ),
        ToolSpec(
            SonToolId.BIND_LAW_ACROSS_DIMENSION,
            son,
            DimensionLawInput,
            ToolMeta(
                ActionKind.BLESS_EXISTENCE,
                lambda rules: rules.son_tools.dimension_law_ap,
                essence_cost=lambda rules: rules.son_tools.dimension_law_essence,
                rarity_gate=dimensional,
            ),
            bind_law_across_dimension,
        ),
        ToolSpec(
            SonToolId.RAISE_PHENOMENON,
            son,
            PhenomenonDraftInput,
            ToolMeta(
                ActionKind.CREATE_ENTITY,
                lambda rules: rules.son_tools.phenomenon_ap,
                essence_cost=lambda rules: rules.son_tools.phenomenon_essence,
                rarity_gate=cosmic,
            ),
            raise_phenomenon,
        ),
        ToolSpec(
            SonToolId.OPEN_BREACH,
            son,
            BreachInput,
            ToolMeta(
                ActionKind.CURSE,
                lambda rules: rules.son_tools.breach_ap,
                essence_cost=lambda rules: rules.son_tools.breach_essence,
                rarity_gate=cosmic,
            ),
            open_breach,
        ),
    ]
