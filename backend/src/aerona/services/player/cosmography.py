from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.cosmography import (
    ApocalypseVariant,
    BeingKind,
    ClusterKind,
    DimensionalEventKind,
    DimensionElement,
    DimensionKind,
    GalacticEventKind,
    GalacticStructureKind,
    GalaxyType,
    OmenReading,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
    SkyObject,
)
from aerona.domain.models.records import CargoLine, PassengerLine
from aerona.engine.cosmos import control
from aerona.engine.cosmos.climate import ClimateTurn
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

Edit = dict[str, int | float | str | bool | None]


class Edited(Command):
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class DimensionDraft(Command):
    name: str
    kind: DimensionKind
    parent_dimension_id: int | None = None
    element: DimensionElement | None = None
    description: str | None = None


class DimensionEdit(Edited):
    dimension_id: int


class DimensionTarget(Command):
    dimension_id: int


class ClusterDraft(Command):
    name: str
    kind: ClusterKind
    dimension_id: int | None = None
    parent_cluster_id: int | None = None
    x: float = 0.0
    y: float = 0.0
    radius: float = 1000.0


class ClusterEdit(Edited):
    cluster_id: int


class ClusterTarget(Command):
    cluster_id: int


class GalaxyDraft(Command):
    name: str
    galaxy_type: GalaxyType
    cluster_id: int | None = None
    dimension_id: int | None = None
    x: float = 0.0
    y: float = 0.0
    radius: float = 900.0


class GalaxyEdit(Edited):
    galaxy_id: int


class GalaxyTarget(Command):
    galaxy_id: int


class StructureDraft(Command):
    galaxy_id: int
    kind: GalacticStructureKind
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    radius: float = 60.0
    intensity: int = 50


class StructureEdit(Edited):
    structure_id: int


class StructureTarget(Command):
    structure_id: int


class GalacticEventDraft(Command):
    galaxy_id: int
    kind: GalacticEventKind
    intensity: int = 50
    other_galaxy_id: int | None = None
    star_id: int | None = None


class GalacticEventEdit(Edited):
    event_id: int


class GalacticEventTarget(Command):
    event_id: int


class DimensionalEventDraft(Command):
    dimension_id: int
    kind: DimensionalEventKind
    intensity: int = 50
    other_dimension_id: int | None = None
    world_id: int | None = None


class DimensionalEventEdit(Edited):
    event_id: int


class DimensionalEventTarget(Command):
    event_id: int


class RiftDraft(Command):
    world_id: int
    dimension_id: int
    region_id: int | None = None
    target_world_id: int | None = None


class RiftEdit(Edited):
    rift_id: int


class RiftTarget(Command):
    rift_id: int


class BeingDraft(Command):
    kind: BeingKind
    world_id: int
    region_id: int | None = None
    home_dimension_id: int | None = None
    name: str | None = None


class BeingEdit(Edited):
    being_id: int


class BeingTarget(Command):
    being_id: int


class PhenomenonDraft(Command):
    kind: PhenomenonKind
    region_id: int
    intensity: int = 50


class PhenomenonEdit(Edited):
    phenomenon_id: int


class Footprint(Command):
    phenomenon_id: int
    region_id: int
    intensity: int | None = None


class Containment(Command):
    phenomenon_id: int
    amount: int = 40


class StarLifeEdit(Edited):
    star_id: int


class WorldLifeEdit(Edited):
    world_id: int


class RouteFlowEdit(Edited):
    route_id: int


class JourneyLoad(Command):
    journey_id: int
    convoy: int | None = None
    escorts: int | None = None
    cargo: list[CargoLine] | None = None
    passengers: list[PassengerLine] | None = None


class JourneyRelease(Command):
    journey_id: int
    fields: list[str] = Field(default_factory=list)


class Reading(Command):
    celestial_id: int
    people_id: int
    reading: OmenReading | None = None


class Variant(Command):
    variant: ApocalypseVariant | None = None


class ClimateOrder(Command):
    region_id: int
    turn: ClimateTurn


@player_action("dimension:create", ActionKind.CREATE_ENTITY)
async def create_dimension(scope: PlayerScope, command: DimensionDraft) -> Effect:
    row = await control.new_dimension(
        await scope.context("dimension_create"),
        command.name,
        command.kind,
        parent_id=command.parent_dimension_id,
        element=command.element,
        description=command.description,
    )
    return Effect(f"{row.name} came into being.", row.id, created_ids=(row.id,))


@player_action("dimension:edit", ActionKind.EDIT_RECORD)
async def edit_dimension(scope: PlayerScope, command: DimensionEdit) -> Effect:
    row = await control.edit_dimension(await scope.context("dimension_edit"), command.dimension_id, command.values, command.release)
    return Effect(f"{row.name} is reshaped.", row.id)


@player_action("dimension:delete", ActionKind.EDIT_RECORD)
async def delete_dimension(scope: PlayerScope, command: DimensionTarget) -> Effect:
    await control.remove_dimension(await scope.context("dimension_delete"), command.dimension_id)
    return Effect("The dimension is unmade; what lay in it falls into its parent.")


class DimensionLaw(Command):
    dimension_id: int
    law_id: int


class LawTarget(Command):
    law_id: int


@player_action("dimension:bind_law", ActionKind.EDIT_RECORD)
async def bind_dimension_law(scope: PlayerScope, command: DimensionLaw) -> Effect:
    profile = await control.bind_law(await scope.context("dimension_law"), command.dimension_id, command.law_id)
    return Effect("The law now holds across the whole dimension.", profile.law_entity_id)


@player_action("dimension:release_law", ActionKind.EDIT_RECORD)
async def release_dimension_law(scope: PlayerScope, command: LawTarget) -> Effect:
    profile = await control.release_law(await scope.context("dimension_law"), command.law_id)
    return Effect("The law holds only on its own world again.", profile.law_entity_id)


class SkyWorship(Command):
    community_id: int
    sky: SkyObject
    worships: bool = True
    dimension_id: int | None = None


@player_action("heavens:worship", ActionKind.EDIT_RECORD)
async def sky_worship(scope: PlayerScope, command: SkyWorship) -> Effect:
    name = await control.set_sky_worship(await scope.context("sky_worship"), command.community_id, command.sky, command.worships, command.dimension_id)
    return Effect(f"They now worship {name}." if command.worships else f"They no longer worship {name}.", command.community_id)


@player_action("cluster:create", ActionKind.CREATE_ENTITY)
async def create_cluster(scope: PlayerScope, command: ClusterDraft) -> Effect:
    row = await control.new_cluster(
        await scope.context("cluster_create"),
        command.name,
        command.kind,
        dimension_id=command.dimension_id,
        parent_id=command.parent_cluster_id,
        position=(command.x, command.y, command.radius),
    )
    return Effect(f"{row.name} gathered.", row.id, created_ids=(row.id,))


@player_action("cluster:edit", ActionKind.EDIT_RECORD)
async def edit_cluster(scope: PlayerScope, command: ClusterEdit) -> Effect:
    row = await control.edit_cluster(await scope.context("cluster_edit"), command.cluster_id, command.values, command.release)
    return Effect(f"{row.name} is reshaped.", row.id)


@player_action("cluster:delete", ActionKind.EDIT_RECORD)
async def delete_cluster(scope: PlayerScope, command: ClusterTarget) -> Effect:
    await control.remove_cluster(await scope.context("cluster_delete"), command.cluster_id)
    return Effect("The cluster scatters; its galaxies stay where they are.")


@player_action("galaxy:create", ActionKind.CREATE_ENTITY)
async def create_galaxy(scope: PlayerScope, command: GalaxyDraft) -> Effect:
    row = await control.new_galaxy(
        await scope.context("galaxy_create"),
        command.name,
        command.galaxy_type,
        cluster_id=command.cluster_id,
        dimension_id=command.dimension_id,
        position=(command.x, command.y, command.radius),
    )
    return Effect(f"{row.name} was set among the galaxies.", row.id, created_ids=(row.id,))


@player_action("galaxy:edit", ActionKind.EDIT_RECORD)
async def edit_galaxy(scope: PlayerScope, command: GalaxyEdit) -> Effect:
    row = await control.edit_galaxy(await scope.context("galaxy_edit"), command.galaxy_id, command.values, command.release)
    return Effect(f"{row.name} is reshaped.", row.id)


@player_action("galaxy:delete", ActionKind.EDIT_RECORD)
async def delete_galaxy(scope: PlayerScope, command: GalaxyTarget) -> Effect:
    await control.remove_galaxy(await scope.context("galaxy_delete"), command.galaxy_id)
    return Effect("The galaxy is unmade; its stars drift between the galaxies.")


@player_action("galactic_structure:create", ActionKind.EDIT_RECORD)
async def create_structure(scope: PlayerScope, command: StructureDraft) -> Effect:
    row = await control.new_structure(
        await scope.context("galactic_structure_create"),
        command.galaxy_id,
        command.kind,
        name=command.name,
        position=(command.x, command.y, command.radius),
        intensity=command.intensity,
    )
    return Effect(f"{row.name} took shape.", command.galaxy_id, values={"structure_id": row.id})


@player_action("galactic_structure:edit", ActionKind.EDIT_RECORD)
async def edit_structure(scope: PlayerScope, command: StructureEdit) -> Effect:
    row = await control.edit_structure(await scope.context("galactic_structure_edit"), command.structure_id, command.values, command.release)
    return Effect(f"{row.name} is reshaped.", row.galaxy_id)


@player_action("galactic_structure:delete", ActionKind.EDIT_RECORD)
async def delete_structure(scope: PlayerScope, command: StructureTarget) -> Effect:
    await control.remove_structure(await scope.context("galactic_structure_delete"), command.structure_id)
    return Effect("The structure is gone.")


@player_action("galactic_event:trigger", ActionKind.EDIT_RECORD)
async def trigger_galactic_event(scope: PlayerScope, command: GalacticEventDraft) -> Effect:
    row = await control.galactic_event(
        await scope.context("galactic_event_trigger"),
        command.galaxy_id,
        command.kind,
        intensity=command.intensity,
        other_id=command.other_galaxy_id,
        star_id=command.star_id,
    )
    return Effect(row.text or "The galaxy stirs.", command.galaxy_id, values={"event_id": row.id})


@player_action("galactic_event:edit", ActionKind.EDIT_RECORD)
async def edit_galactic_event(scope: PlayerScope, command: GalacticEventEdit) -> Effect:
    row = await control.edit_galactic_event(await scope.context("galactic_event_edit"), command.event_id, command.values)
    return Effect("The galactic event is reshaped.", row.galaxy_id)


@player_action("galactic_event:delete", ActionKind.EDIT_RECORD)
async def delete_galactic_event(scope: PlayerScope, command: GalacticEventTarget) -> Effect:
    await control.remove_galactic_event(await scope.context("galactic_event_delete"), command.event_id)
    return Effect("The galactic event is struck from the record.")


@player_action("dimensional_event:trigger", ActionKind.EDIT_RECORD)
async def trigger_dimensional_event(scope: PlayerScope, command: DimensionalEventDraft) -> Effect:
    row = await control.dimensional_event(
        await scope.context("dimensional_event_trigger"),
        command.dimension_id,
        command.kind,
        intensity=command.intensity,
        other_id=command.other_dimension_id,
        world_id=command.world_id,
    )
    return Effect(row.text or "The dimension stirs.", command.dimension_id, values={"event_id": row.id})


@player_action("dimensional_event:edit", ActionKind.EDIT_RECORD)
async def edit_dimensional_event(scope: PlayerScope, command: DimensionalEventEdit) -> Effect:
    row = await control.edit_dimensional_event(await scope.context("dimensional_event_edit"), command.event_id, command.values)
    return Effect("The dimensional event is reshaped.", row.dimension_id)


@player_action("dimensional_event:delete", ActionKind.EDIT_RECORD)
async def delete_dimensional_event(scope: PlayerScope, command: DimensionalEventTarget) -> Effect:
    await control.remove_dimensional_event(await scope.context("dimensional_event_delete"), command.event_id)
    return Effect("The dimensional event is struck from the record.")


@player_action("rift:open", ActionKind.EDIT_RECORD)
async def open_rift(scope: PlayerScope, command: RiftDraft) -> Effect:
    creator = await scope.creator()
    row = await control.tear_rift(
        await scope.context("rift_open"),
        command.world_id,
        command.region_id,
        dimension_id=command.dimension_id,
        target_world_id=command.target_world_id,
        by_node_id=creator.id,
        cause=RiftCause.CREATOR,
    )
    return Effect("A rift opened.", command.world_id, values={"rift_id": row.id})


@player_action("rift:edit", ActionKind.EDIT_RECORD)
async def edit_rift(scope: PlayerScope, command: RiftEdit) -> Effect:
    row = await control.edit_rift(await scope.context("rift_edit"), command.rift_id, command.values, command.release)
    return Effect("The rift is reshaped.", row.world_id)


@player_action("rift:seal", ActionKind.EDIT_RECORD)
async def seal_rift(scope: PlayerScope, command: RiftTarget) -> Effect:
    creator = await scope.creator()
    row = await control.close_rift(await scope.context("rift_seal"), command.rift_id, creator.name)
    return Effect("The rift is sealed.", row.world_id)


@player_action("rift:delete", ActionKind.EDIT_RECORD)
async def delete_rift(scope: PlayerScope, command: RiftTarget) -> Effect:
    await control.remove_rift(await scope.context("rift_delete"), command.rift_id)
    return Effect("The rift is gone as if it had never been.")


@player_action("cosmic_being:call", ActionKind.CREATE_ENTITY)
async def call_being(scope: PlayerScope, command: BeingDraft) -> Effect:
    being = await control.call_being(
        await scope.context("cosmic_being_call"),
        command.kind,
        command.world_id,
        region_id=command.region_id,
        home_dimension_id=command.home_dimension_id,
        name=command.name,
    )
    return Effect(f"{being.name} came.", being.id, created_ids=(being.id,))


@player_action("cosmic_being:edit", ActionKind.EDIT_RECORD)
async def edit_being(scope: PlayerScope, command: BeingEdit) -> Effect:
    await control.edit_being(await scope.context("cosmic_being_edit"), command.being_id, command.values, command.release)
    return Effect("The being is reshaped.", command.being_id)


@player_action("cosmic_being:bind", ActionKind.EDIT_RECORD)
async def bind_being(scope: PlayerScope, command: BeingTarget) -> Effect:
    creator = await scope.creator()
    await control.bind(await scope.context("cosmic_being_bind"), command.being_id, creator.id, creator.name)
    return Effect("The being is bound to the Creator.", command.being_id)


@player_action("cosmic_being:banish", ActionKind.EDIT_RECORD)
async def banish_being(scope: PlayerScope, command: BeingTarget) -> Effect:
    creator = await scope.creator()
    await control.banish(await scope.context("cosmic_being_banish"), command.being_id, creator.name)
    return Effect("The being is banished.", command.being_id)


@player_action("phenomenon:create", ActionKind.CREATE_ENTITY)
async def create_phenomenon(scope: PlayerScope, command: PhenomenonDraft) -> Effect:
    made = await control.new_phenomenon(await scope.context("phenomenon_create"), command.kind, command.region_id, command.intensity, PhenomenonCause.DIVINE)
    return Effect(f"{made.name} formed.", made.id, created_ids=(made.id,))


@player_action("phenomenon:edit", ActionKind.EDIT_RECORD)
async def edit_phenomenon(scope: PlayerScope, command: PhenomenonEdit) -> Effect:
    await control.edit_phenomenon(await scope.context("phenomenon_edit"), command.phenomenon_id, command.values, command.release)
    return Effect("The phenomenon is reshaped.", command.phenomenon_id)


@player_action("phenomenon:footprint", ActionKind.EDIT_RECORD)
async def set_footprint(scope: PlayerScope, command: Footprint) -> Effect:
    row = await control.set_footprint(await scope.context("phenomenon_footprint"), command.phenomenon_id, command.region_id, command.intensity)
    return Effect("The phenomenon covers that region." if row is not None else "The phenomenon leaves that region.", command.phenomenon_id)


@player_action("phenomenon:contain", ActionKind.EDIT_RECORD)
async def contain_phenomenon(scope: PlayerScope, command: Containment) -> Effect:
    creator = await scope.creator()
    row = await control.ward_phenomenon(await scope.context("phenomenon_contain"), command.phenomenon_id, command.amount, creator.name)
    return Effect(f"The phenomenon is held back ({row.containment}%).", command.phenomenon_id)


@player_action("star_life:edit", ActionKind.EDIT_RECORD)
async def edit_star_life(scope: PlayerScope, command: StarLifeEdit) -> Effect:
    row = await control.edit_star_life(await scope.context("star_life_edit"), command.star_id, command.values, command.release)
    return Effect(f"The life of {row.name} is reshaped.", row.id)


@player_action("world_life:edit", ActionKind.EDIT_RECORD)
async def edit_world_life(scope: PlayerScope, command: WorldLifeEdit) -> Effect:
    row = await control.edit_world_life(await scope.context("world_life_edit"), command.world_id, command.values, command.release)
    return Effect(f"The life of {row.name} is reshaped.", row.id)


@player_action("route_flow:edit", ActionKind.EDIT_RECORD)
async def edit_route_flow(scope: PlayerScope, command: RouteFlowEdit) -> Effect:
    row = await control.edit_route_flow(await scope.context("route_flow_edit"), command.route_id, command.values, command.release)
    return Effect("The traffic of the route is reshaped.", row.world_a_id)


@player_action("journey:load", ActionKind.EDIT_RECORD)
async def load_journey(scope: PlayerScope, command: JourneyLoad) -> Effect:
    row = await control.load_journey(
        await scope.context("journey_load"),
        command.journey_id,
        convoy=command.convoy,
        escorts=command.escorts,
        cargo=command.cargo,
        passengers=command.passengers,
    )
    return Effect("The journey's load is set and held.", row.traveller_entity_id)


@player_action("journey:release", ActionKind.EDIT_RECORD)
async def release_journey(scope: PlayerScope, command: JourneyRelease) -> Effect:
    row = await control.release_journey(await scope.context("journey_release"), command.journey_id, command.fields)
    return Effect("The journey's load follows the road again.", row.traveller_entity_id)


@player_action("celestial_reading:set", ActionKind.EDIT_RECORD)
async def set_reading(scope: PlayerScope, command: Reading) -> Effect:
    row = await control.set_reading(await scope.context("celestial_reading_set"), command.celestial_id, command.people_id, command.reading)
    return Effect("The people's reading of the body is set." if row is not None else "The people will read the body again.", command.people_id)


@player_action("apocalypse:variant", ActionKind.EDIT_RECORD)
async def set_variant(scope: PlayerScope, command: Variant) -> Effect:
    await control.set_variant(await scope.context("apocalypse_variant"), command.variant)
    return Effect("The shape of the end is chosen." if command.variant is not None else "The end will take the shape its causes give it.")


@player_action("region_climate:turn", ActionKind.EDIT_RECORD)
async def turn_climate(scope: PlayerScope, command: ClimateOrder) -> Effect:
    creator = await scope.creator()
    await control.turn_climate(await scope.context("region_climate_turn"), command.region_id, command.turn, creator.name)
    return Effect(f"The region turns {command.turn.value}.", command.region_id)
