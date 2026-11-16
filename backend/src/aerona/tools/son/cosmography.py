from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, REASON_MAX, REASON_MIN, SHORT_DESCRIPTION_MAX, SHORT_DESCRIPTION_MIN
from aerona.core.errors import AeronaError
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, CosmicBeingProfileRow, DimensionRow, GalaxyRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.physics import ImpactEventRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, BeingKind, ClusterKind, DimensionElement, DimensionKind, GalaxyType, RiftCause
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.physics import ImpactOutcome, TerraformAim
from aerona.engine.cosmos import control, physics_control
from aerona.engine.cosmos.climate import ClimateTurn
from aerona.engine.cosmos.ladder import NEW_CLUSTER_RADIUS, NEW_GALAXY_RADIUS
from aerona.engine.cosmos.placement import Cosmography
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
Description = Annotated[str, Field(min_length=SHORT_DESCRIPTION_MIN, max_length=SHORT_DESCRIPTION_MAX)]


class OpenRiftInput(ToolInput):
    region_id: int
    dimension_id: int
    target_world_id: int | None = None
    reason: Reason


class RiftInput(ToolInput):
    rift_id: int
    reason: Reason


class CallBeingInput(ToolInput):
    kind: BeingKind
    region_id: int
    reason: Reason


class BeingInput(ToolInput):
    being_id: int
    reason: Reason


class PhenomenonInput(ToolInput):
    phenomenon_id: int
    reason: Reason


class TurnClimateInput(ToolInput):
    region_id: int
    turn: ClimateTurn
    reason: Reason


class GalaxyInput(ToolInput):
    galaxy_id: int
    reason: Reason


class DimensionInput(ToolInput):
    dimension_id: int
    reason: Reason


class CreateGalaxyInput(ToolInput):
    name: Name
    galaxy_type: GalaxyType
    cluster_id: int | None = None
    dimension_id: int | None = None
    description: Description


class CreateClusterInput(ToolInput):
    name: Name
    kind: ClusterKind
    dimension_id: int | None = None
    parent_cluster_id: int | None = None
    description: Description


class CreateDimensionInput(ToolInput):
    name: Name
    kind: DimensionKind
    element: DimensionElement | None = None
    form: SpellForm | None = None
    parent_dimension_id: int | None = None
    description: Description


class CallImpactInput(ToolInput):
    region_id: int
    reason: Reason


class ImpactInput(ToolInput):
    impact_id: int
    reason: Reason


class TerraformInput(ToolInput):
    world_id: int
    aim: TerraformAim
    reason: Reason


class MoonInput(ToolInput):
    moon_id: int
    reason: Reason


class StarPatronInput(ToolInput):
    star_id: int
    reason: Reason


async def reaches_galaxy(call: SonCall, galaxy_id: int) -> bool:
    cosmography = await Cosmography.load(call.session)
    return any([await call.reachable_world(world.id) for world in cosmography.worlds_in_galaxy(galaxy_id)])


async def reaches_dimension(call: SonCall, dimension_id: int) -> bool:
    cosmography = await Cosmography.load(call.session)
    return any([await call.reachable_world(world.id) for world in cosmography.worlds_in_dimension(dimension_id)])


async def open_rift(call: SonCall, args: OpenRiftInput) -> str:
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name="region")
    await ensure_in_reach(call, region)
    dimension = await call.session.get(DimensionRow, args.dimension_id)
    if dimension is None:
        fail(SonResult.NO_SUCH_DIMENSION, id=args.dimension_id)
    cost = call.rules.rifts.open_essence
    require_essence(call, cost)
    world = await call.session.get(WorldRow, region.world_id)
    try:
        await control.tear_rift(
            call.tick, region.world_id, region.id, dimension_id=dimension.id, target_world_id=args.target_world_id, by_node_id=call.son.id, cause=RiftCause.GOD
        )
    except AeronaError as error:
        fail(SonResult.RIFT_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(region.id)
    await call.chronicle(
        ChronicleKind.COSMIC, lines.OPEN_RIFT, entity_ids=[region.id], son=call.son.name, place=region.name, dimension=dimension.name, reason=args.reason
    )
    return result(SonResult.RIFT_OPENED, place=region.name, dimension=dimension.name, world=world.name if world is not None else "")


async def seal_rift(call: SonCall, args: RiftInput) -> str:
    rift = await call.session.get(RiftRow, args.rift_id)
    if rift is None or rift.state not in OPEN_RIFT_STATES:
        fail(SonResult.NO_SUCH_RIFT, id=args.rift_id)
    if not await call.reachable_world(rift.world_id):
        fail(SonResult.RIFT_OUT_OF_REACH, id=rift.id)
    cost = call.rules.rifts.seal_essence
    require_essence(call, cost)
    await control.close_rift(call.tick, rift.id, call.son.name)
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.MIRACLE, lines.SEAL_RIFT, son=call.son.name, reason=args.reason)
    return result(SonResult.RIFT_SEALED)


async def call_being(call: SonCall, args: CallBeingInput) -> str:
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name="region")
    await ensure_in_reach(call, region)
    cost = call.rules.cosmic_beings.call_essence
    require_essence(call, cost)
    being = await control.call_being(call.tick, args.kind, region.world_id, region_id=region.id, home_dimension_id=None, name=None)
    call.spend_essence(cost)
    call.target(being.id)
    await call.chronicle(ChronicleKind.COSMIC, lines.CALL_BEING, entity_ids=[being.id], son=call.son.name, being=being.name, reason=args.reason)
    return result(SonResult.BEING_CALLED, name=being.name)


async def being_of(call: SonCall, being_id: int) -> CosmicBeingProfileRow:
    profile = await call.session.get(CosmicBeingProfileRow, being_id)
    entity = await require_canon(call.session, being_id)
    if profile is None or entity.entity_type is not EntityType.COSMIC_BEING:
        fail(SonResult.NOT_A_COSMIC_BEING, id=being_id)
    await ensure_in_reach(call, entity)
    return profile


async def bind_being(call: SonCall, args: BeingInput) -> str:
    await being_of(call, args.being_id)
    cost = call.rules.cosmic_beings.bind_essence
    require_essence(call, cost)
    try:
        await control.bind(call.tick, args.being_id, call.son.id, call.son.name)
    except AeronaError as error:
        fail(SonResult.BEING_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(args.being_id)
    await call.chronicle(ChronicleKind.MIRACLE, lines.BIND_BEING, entity_ids=[args.being_id], son=call.son.name, reason=args.reason)
    return result(SonResult.BEING_BOUND)


async def banish_being(call: SonCall, args: BeingInput) -> str:
    await being_of(call, args.being_id)
    cost = call.rules.cosmic_beings.banish_essence
    require_essence(call, cost)
    await control.banish(call.tick, args.being_id, call.son.name)
    call.spend_essence(cost)
    call.target(args.being_id)
    await call.chronicle(ChronicleKind.MIRACLE, lines.BANISH_BEING, entity_ids=[args.being_id], son=call.son.name, reason=args.reason)
    return result(SonResult.BEING_BANISHED)


async def contain_phenomenon(call: SonCall, args: PhenomenonInput) -> str:
    entity = await require_canon(call.session, args.phenomenon_id)
    if entity.entity_type is not EntityType.PHENOMENON or await call.session.get(PhenomenonProfileRow, entity.id) is None:
        fail(SonResult.NOT_A_PHENOMENON, id=args.phenomenon_id)
    await ensure_in_reach(call, entity)
    cost = call.rules.phenomena.contain_essence
    require_essence(call, cost)
    await control.ward_phenomenon(call.tick, entity.id, call.rules.phenomena.contain_amount, call.son.name)
    call.spend_essence(cost)
    call.target(entity.id)
    await call.chronicle(ChronicleKind.MIRACLE, lines.CONTAIN_PHENOMENON, entity_ids=[entity.id], son=call.son.name, phenomenon=entity.name, reason=args.reason)
    return result(SonResult.PHENOMENON_CONTAINED, name=entity.name)


async def turn_climate(call: SonCall, args: TurnClimateInput) -> str:
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name="region")
    await ensure_in_reach(call, region)
    cost = call.rules.world_life.son_climate_essence
    require_essence(call, cost)
    try:
        await control.turn_climate(call.tick, region.id, args.turn, call.son.name)
    except AeronaError as error:
        fail(SonResult.CLIMATE_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(region.id)
    return result(SonResult.CLIMATE_TURNED, place=region.name, turn=args.turn.value)


async def claim_galaxy(call: SonCall, args: GalaxyInput) -> str:
    galaxy = await call.session.get(GalaxyRow, args.galaxy_id)
    if galaxy is None:
        fail(SonResult.NO_SUCH_GALAXY, id=args.galaxy_id)
    if not await reaches_galaxy(call, galaxy.id):
        fail(SonResult.GALAXY_OUT_OF_REACH, name=galaxy.name)
    cost = call.rules.galaxies.claim_essence
    require_essence(call, cost)
    galaxy.patron_son_id = call.son.id
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.ASCENSION, lines.CLAIM_GALAXY, son=call.son.name, galaxy=galaxy.name, reason=args.reason)
    return result(SonResult.GALAXY_CLAIMED, name=galaxy.name)


async def rule_dimension(call: SonCall, args: DimensionInput) -> str:
    dimension = await call.session.get(DimensionRow, args.dimension_id)
    if dimension is None:
        fail(SonResult.NO_SUCH_DIMENSION, id=args.dimension_id)
    if not await reaches_dimension(call, dimension.id):
        fail(SonResult.DIMENSION_OUT_OF_REACH, name=dimension.name)
    cost = call.rules.dimensions.rule_essence
    require_essence(call, cost)
    dimension.ruler_node_id = call.son.id
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.ASCENSION, lines.RULE_DIMENSION, son=call.son.name, dimension=dimension.name, reason=args.reason)
    return result(SonResult.DIMENSION_RULED, name=dimension.name)


async def fresh_name(call: SonCall, name: str) -> str:
    cleaned = " ".join(name.split())
    if await NameRepository(call.session).is_taken(cleaned):
        fail(SonResult.NAME_IN_USE)
    return cleaned


async def home_of(call: SonCall, cluster_id: int | None, dimension_id: int | None) -> DimensionRow | None:
    if cluster_id is not None and dimension_id is not None:
        fail(SonResult.ONE_HOME_ONLY)
    cosmography = await Cosmography.load(call.session)
    if cluster_id is not None:
        cluster = await call.session.get(ClusterRow, cluster_id)
        if cluster is None:
            fail(SonResult.NO_SUCH_CLUSTER, id=cluster_id)
        return cosmography.dimension_of_cluster(cluster)
    if dimension_id is not None:
        dimension = await call.session.get(DimensionRow, dimension_id)
        if dimension is None:
            fail(SonResult.NO_SUCH_DIMENSION, id=dimension_id)
        return dimension
    return cosmography.prime


async def ensure_reaches(call: SonCall, dimension: DimensionRow | None) -> None:
    if dimension is not None and not await reaches_dimension(call, dimension.id):
        fail(SonResult.DIMENSION_OUT_OF_REACH, name=dimension.name)


async def create_galaxy(call: SonCall, args: CreateGalaxyInput) -> str:
    name = await fresh_name(call, args.name)
    await ensure_reaches(call, await home_of(call, args.cluster_id, args.dimension_id))
    cost = call.rules.galaxies.create_essence
    require_essence(call, cost)
    galaxy = await control.new_galaxy(
        call.tick, name, args.galaxy_type, cluster_id=args.cluster_id, dimension_id=args.dimension_id, position=(None, None, NEW_GALAXY_RADIUS)
    )
    galaxy.description = args.description
    galaxy.patron_son_id = call.son.id
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.COSMIC, lines.CREATE_GALAXY, son=call.son.name, galaxy=galaxy.name, description=args.description)
    return result(SonResult.GALAXY_CREATED, id=galaxy.id, name=galaxy.name)


async def create_cluster(call: SonCall, args: CreateClusterInput) -> str:
    name = await fresh_name(call, args.name)
    await ensure_reaches(call, await home_of(call, args.parent_cluster_id, args.dimension_id))
    cost = call.rules.clusters.create_essence
    require_essence(call, cost)
    cluster = await control.new_cluster(
        call.tick, name, args.kind, dimension_id=args.dimension_id, parent_id=args.parent_cluster_id, position=(None, None, NEW_CLUSTER_RADIUS)
    )
    cluster.description = args.description
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.COSMIC, lines.CREATE_CLUSTER, son=call.son.name, cluster=cluster.name, description=args.description)
    return result(SonResult.CLUSTER_CREATED, id=cluster.id, name=cluster.name)


async def create_dimension(call: SonCall, args: CreateDimensionInput) -> str:
    name = await fresh_name(call, args.name)
    if args.parent_dimension_id is not None:
        await ensure_reaches(call, await home_of(call, None, args.parent_dimension_id))
    cost = call.rules.dimensions.create_essence
    require_essence(call, cost)
    dimension = await control.new_dimension(
        call.tick, name, args.kind, parent_id=args.parent_dimension_id, element=args.element, description=args.description, form=args.form
    )
    dimension.ruler_node_id = call.son.id
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.COSMIC, lines.CREATE_DIMENSION, son=call.son.name, dimension=dimension.name, description=args.description)
    return result(SonResult.DIMENSION_CREATED, id=dimension.id, name=dimension.name)


async def claim_star(call: SonCall, args: StarPatronInput) -> str:
    star = await call.session.get(StarRow, args.star_id)
    if star is None:
        fail(SonResult.NO_SUCH_STAR)
    cost = call.rules.star_life.claim_essence
    require_essence(call, cost)
    star.patron_son_id = call.son.id
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.ASCENSION, lines.CLAIM_STAR, son=call.son.name, star=star.name, reason=args.reason)
    return result(SonResult.STAR_CLAIMED, name=star.name)


async def call_impact(call: SonCall, args: CallImpactInput) -> str:
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name="region")
    await ensure_in_reach(call, region)
    cost = call.rules.impacts.call_essence
    require_essence(call, cost)
    try:
        impact = await physics_control.call(call.tick, region.world_id or 0, region.id, call.son.id, by=call.son.name, size=None)
    except AeronaError as error:
        fail(SonResult.IMPACT_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(region.id)
    await call.chronicle(ChronicleKind.MIRACLE, lines.CALL_IMPACT, entity_ids=[region.id], son=call.son.name, place=region.name, reason=args.reason)
    return result(SonResult.IMPACT_CALLED, place=region.name, epoch=impact.due_epoch)


async def deflect_impact(call: SonCall, args: ImpactInput) -> str:
    impact = await call.session.get(ImpactEventRow, args.impact_id)
    if impact is None or impact.outcome is not ImpactOutcome.PENDING:
        fail(SonResult.NO_SUCH_IMPACT, id=args.impact_id)
    if not await call.reachable_world(impact.world_id):
        fail(SonResult.IMPACT_OUT_OF_REACH, id=impact.id)
    cost = call.rules.impacts.deflect_essence
    require_essence(call, cost)
    await physics_control.deflect(call.tick, impact.id, call.son.id, call.son.name)
    call.spend_essence(cost)
    world = await call.session.get(WorldRow, impact.world_id)
    name = world.name if world is not None else ""
    await call.chronicle(ChronicleKind.MIRACLE, lines.DEFLECT_IMPACT, son=call.son.name, world=name, reason=args.reason)
    return result(SonResult.IMPACT_DEFLECTED, world=name)


async def terraform_world(call: SonCall, args: TerraformInput) -> str:
    world = await call.session.get(WorldRow, args.world_id)
    if world is None or not await call.reachable_world(world.id):
        fail(SonResult.TERRAFORM_REFUSED, reason="that world is beyond your reach")
    cost = call.rules.terraforming.essence
    require_essence(call, cost)
    try:
        project = await physics_control.start_terraform(call.tick, world.id, args.aim, call.son.id, by=call.son.name, step=None, epochs=None)
    except AeronaError as error:
        fail(SonResult.TERRAFORM_REFUSED, reason=error.message)
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.MIRACLE, lines.TERRAFORM_WORLD, son=call.son.name, world=world.name, reason=args.reason)
    return result(SonResult.TERRAFORM_BEGUN, world=world.name, epochs=project.epochs_left)


async def break_moon(call: SonCall, args: MoonInput) -> str:
    moon = await call.session.get(WorldRow, args.moon_id)
    reached = moon is not None and (
        await call.reachable_world(moon.id) or (moon.parent_world_id is not None and await call.reachable_world(moon.parent_world_id))
    )
    if moon is None or not reached:
        fail(SonResult.MOON_REFUSED, reason="that world is beyond your reach")
    cost = call.rules.orbits.break_moon_essence
    require_essence(call, cost)
    try:
        await physics_control.break_moon(call.tick, moon.id, call.son.name)
    except AeronaError as error:
        fail(SonResult.MOON_REFUSED, reason=error.message)
    call.spend_essence(cost)
    await call.chronicle(ChronicleKind.MIRACLE, lines.BREAK_MOON, son=call.son.name, moon=moon.name, reason=args.reason)
    return result(SonResult.MOON_BROKEN, moon=moon.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    standard = son_standard_action
    return [
        ToolSpec(
            SonToolId.OPEN_RIFT,
            AgentKind.SON,
            OpenRiftInput,
            ToolMeta(ActionKind.SKY_EVENT, standard, essence_cost=lambda rules: rules.rifts.open_essence),
            open_rift,
        ),
        ToolSpec(
            SonToolId.SEAL_RIFT,
            AgentKind.SON,
            RiftInput,
            ToolMeta(ActionKind.CLEANSE_LEAK, standard, essence_cost=lambda rules: rules.rifts.seal_essence),
            seal_rift,
        ),
        ToolSpec(
            SonToolId.CALL_COSMIC_BEING,
            AgentKind.SON,
            CallBeingInput,
            ToolMeta(ActionKind.SUMMON_OUTER_BEING, standard, essence_cost=lambda rules: rules.cosmic_beings.call_essence),
            call_being,
        ),
        ToolSpec(
            SonToolId.BIND_COSMIC_BEING,
            AgentKind.SON,
            BeingInput,
            ToolMeta(ActionKind.MANIFESTATION, standard, essence_cost=lambda rules: rules.cosmic_beings.bind_essence),
            bind_being,
        ),
        ToolSpec(
            SonToolId.BANISH_COSMIC_BEING,
            AgentKind.SON,
            BeingInput,
            ToolMeta(ActionKind.CLEANSE_LEAK, standard, essence_cost=lambda rules: rules.cosmic_beings.banish_essence),
            banish_being,
        ),
        ToolSpec(
            SonToolId.CONTAIN_PHENOMENON,
            AgentKind.SON,
            PhenomenonInput,
            ToolMeta(ActionKind.CLEANSE_LEAK, standard, essence_cost=lambda rules: rules.phenomena.contain_essence),
            contain_phenomenon,
        ),
        ToolSpec(
            SonToolId.TURN_REGION_CLIMATE,
            AgentKind.SON,
            TurnClimateInput,
            ToolMeta(ActionKind.SKY_EVENT, standard, essence_cost=lambda rules: rules.world_life.son_climate_essence),
            turn_climate,
        ),
        ToolSpec(
            SonToolId.CLAIM_GALAXY,
            AgentKind.SON,
            GalaxyInput,
            ToolMeta(ActionKind.BLESS_EXISTENCE, standard, essence_cost=lambda rules: rules.galaxies.claim_essence),
            claim_galaxy,
        ),
        ToolSpec(
            SonToolId.CREATE_GALAXY,
            AgentKind.SON,
            CreateGalaxyInput,
            ToolMeta(
                ActionKind.CREATE_ENTITY,
                lambda rules: rules.son_tools.create_galaxy_ap,
                essence_cost=lambda rules: rules.galaxies.create_essence,
                rarity_gate=gate(Gate.GALAXY_CREATION),
            ),
            create_galaxy,
        ),
        ToolSpec(
            SonToolId.CREATE_CLUSTER,
            AgentKind.SON,
            CreateClusterInput,
            ToolMeta(
                ActionKind.CREATE_ENTITY,
                lambda rules: rules.son_tools.create_cluster_ap,
                essence_cost=lambda rules: rules.clusters.create_essence,
                rarity_gate=gate(Gate.CLUSTER_CREATION),
            ),
            create_cluster,
        ),
        ToolSpec(
            SonToolId.CREATE_DIMENSION,
            AgentKind.SON,
            CreateDimensionInput,
            ToolMeta(
                ActionKind.CREATE_ENTITY,
                lambda rules: rules.son_tools.create_dimension_ap,
                essence_cost=lambda rules: rules.dimensions.create_essence,
                rarity_gate=gate(Gate.DIMENSION_CREATION),
            ),
            create_dimension,
        ),
        ToolSpec(
            SonToolId.RULE_DIMENSION,
            AgentKind.SON,
            DimensionInput,
            ToolMeta(ActionKind.BLESS_EXISTENCE, standard, essence_cost=lambda rules: rules.dimensions.rule_essence),
            rule_dimension,
        ),
        ToolSpec(
            SonToolId.CALL_IMPACT,
            AgentKind.SON,
            CallImpactInput,
            ToolMeta(ActionKind.SKY_EVENT, standard, essence_cost=lambda rules: rules.impacts.call_essence),
            call_impact,
        ),
        ToolSpec(
            SonToolId.DEFLECT_IMPACT,
            AgentKind.SON,
            ImpactInput,
            ToolMeta(ActionKind.MANIFESTATION, standard, essence_cost=lambda rules: rules.impacts.deflect_essence),
            deflect_impact,
        ),
        ToolSpec(
            SonToolId.TERRAFORM_WORLD,
            AgentKind.SON,
            TerraformInput,
            ToolMeta(ActionKind.SKY_EVENT, standard, essence_cost=lambda rules: rules.terraforming.essence),
            terraform_world,
        ),
        ToolSpec(
            SonToolId.BREAK_MOON,
            AgentKind.SON,
            MoonInput,
            ToolMeta(ActionKind.SKY_EVENT, standard, essence_cost=lambda rules: rules.orbits.break_moon_essence),
            break_moon,
        ),
        ToolSpec(
            SonToolId.CLAIM_STAR,
            AgentKind.SON,
            StarPatronInput,
            ToolMeta(ActionKind.BLESS_EXISTENCE, standard, essence_cost=lambda rules: rules.star_life.claim_essence),
            claim_star,
        ),
    ]
