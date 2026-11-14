from pydantic import Field

from aerona.core.grammar import agree, several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, PlagueResponse
from aerona.domain.enums.happening import LandAct
from aerona.engine.ecology import evolution_control as control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class TraitDraft(Command):
    species_id: int
    region_id: int
    trait: EvolvedTrait
    mean: int = Field(ge=0, le=SPAN)
    variance: int | None = Field(default=None, ge=0, le=50)


class TraitEdit(Edited):
    species_id: int
    region_id: int
    trait: EvolvedTrait


class TraitTarget(Command):
    species_id: int
    region_id: int
    trait: EvolvedTrait | None = None


class MarkDraft(Command):
    species_id: int
    package: PackageKind
    blessing: bool = False
    source_node_id: int | None = None


class MarkEdit(Edited):
    species_id: int
    package: PackageKind


class MarkTarget(Command):
    species_id: int
    package: PackageKind


class SpeciesEdit(Edited):
    species_id: int


class ServiceDraft(Command):
    region_id: int
    role: KeystoneRole
    strength: int = Field(ge=0, le=SPAN)
    species_id: int | None = None


class ServiceEdit(Edited):
    region_id: int
    role: KeystoneRole


class ServiceTarget(Command):
    region_id: int
    role: KeystoneRole


class HerdTarget(Command):
    community_id: int
    species_id: int


class CarrierTarget(Command):
    mortal_id: int
    disease_id: int


class CarrierEdit(Edited):
    mortal_id: int
    disease_id: int


class ResponseDraft(Command):
    community_id: int
    disease_id: int
    response: PlagueResponse
    strength: int = Field(default=60, ge=0, le=SPAN)


class ResponseEdit(Edited):
    community_id: int
    disease_id: int
    response: PlagueResponse


class ResponseTarget(Command):
    community_id: int
    disease_id: int
    response: PlagueResponse


class ResearchTarget(Command):
    institution_id: int
    disease_id: int


class ResearchEdit(Edited):
    institution_id: int
    disease_id: int


class CycleEdit(Edited):
    world_id: int


class CycleTarget(Command):
    world_id: int


class LandDraft(Command):
    region_id: int
    act: LandAct
    target_region_id: int | None = None
    fiery: bool = False


@player_action("species_trait:set", ActionKind.EDIT_RECORD)
async def set_trait(scope: PlayerScope, command: TraitDraft) -> Effect:
    await control.set_trait(
        await scope.context("species_trait_set"), command.species_id, command.region_id, command.trait, mean=command.mean, variance=command.variance
    )
    return Effect(f"The {command.trait.value.replace('_', ' ')} of that stock is set so.", command.species_id)


@player_action("species_trait:edit", ActionKind.EDIT_RECORD)
async def edit_trait(scope: PlayerScope, command: TraitEdit) -> Effect:
    await control.edit_trait(
        await scope.context("species_trait_edit"), command.species_id, command.region_id, command.trait, values=command.values, release=command.release
    )
    return Effect("The trait is set so.", command.species_id)


@player_action("species_trait:delete", ActionKind.EDIT_RECORD)
async def delete_traits(scope: PlayerScope, command: TraitTarget) -> Effect:
    removed = await control.delete_traits(await scope.context("species_trait_delete"), command.species_id, command.region_id, command.trait)
    return Effect(f"{several(removed, 'trait', 'traits')} of that stock {agree(removed, 'is', 'are')} drawn anew from its kind.", command.species_id)


@player_action("lineage:mark", ActionKind.EDIT_RECORD)
async def mark_line(scope: PlayerScope, command: MarkDraft) -> Effect:
    await control.mark_line(
        await scope.context("lineage_mark"), command.species_id, command.package, blessing=command.blessing, source_node_id=command.source_node_id
    )
    return Effect("The line carries the mark from parent to young.", command.species_id)


@player_action("lineage:edit", ActionKind.EDIT_RECORD)
async def edit_mark(scope: PlayerScope, command: MarkEdit) -> Effect:
    await control.edit_mark(await scope.context("lineage_edit"), command.species_id, command.package, command.values, command.release)
    return Effect("The lineage mark is set so.", command.species_id)


@player_action("lineage:delete", ActionKind.EDIT_RECORD)
async def delete_mark(scope: PlayerScope, command: MarkTarget) -> Effect:
    await control.delete_mark(await scope.context("lineage_delete"), command.species_id, command.package)
    return Effect("The line is free of the mark.", command.species_id)


@player_action("species_ecology:edit", ActionKind.EDIT_RECORD)
async def edit_ecology(scope: PlayerScope, command: SpeciesEdit) -> Effect:
    await control.edit_ecology(await scope.context("species_ecology_edit"), command.species_id, command.values, command.release)
    return Effect("The species' place in its lands is set so.", command.species_id)


@player_action("ecosystem_service:set", ActionKind.EDIT_RECORD)
async def set_service(scope: PlayerScope, command: ServiceDraft) -> Effect:
    await control.set_service(await scope.context("ecosystem_service_set"), command.region_id, command.role, command.strength, command.species_id)
    return Effect(f"The land's {command.role.value.replace('_', ' ')} service is set so.", command.region_id)


@player_action("ecosystem_service:edit", ActionKind.EDIT_RECORD)
async def edit_service(scope: PlayerScope, command: ServiceEdit) -> Effect:
    await control.edit_service(await scope.context("ecosystem_service_edit"), command.region_id, command.role, command.values, command.release)
    return Effect("The land's service is set so.", command.region_id)


@player_action("ecosystem_service:delete", ActionKind.EDIT_RECORD)
async def delete_service(scope: PlayerScope, command: ServiceTarget) -> Effect:
    await control.delete_service(await scope.context("ecosystem_service_delete"), command.region_id, command.role)
    return Effect("The land's service is struck from the record.", command.region_id)


@player_action("herd:release", ActionKind.EDIT_RECORD)
async def release_herd(scope: PlayerScope, command: HerdTarget) -> Effect:
    region_id = await control.release(await scope.context("herd_release"), command.community_id, command.species_id)
    return Effect("The herd goes loose into the wild.", region_id or command.community_id)


@player_action("carrier:add", ActionKind.EDIT_RECORD)
async def add_carrier(scope: PlayerScope, command: CarrierTarget) -> Effect:
    await control.add_carrier(await scope.context("carrier_add"), command.mortal_id, command.disease_id)
    return Effect("The mortal carries the sickness unseen.", command.mortal_id)


@player_action("carrier:edit", ActionKind.EDIT_RECORD)
async def edit_carrier(scope: PlayerScope, command: CarrierEdit) -> Effect:
    await control.edit_carrier(await scope.context("carrier_edit"), command.mortal_id, command.disease_id, command.values, command.release)
    return Effect("The carrier is set so.", command.mortal_id)


@player_action("carrier:delete", ActionKind.EDIT_RECORD)
async def delete_carrier(scope: PlayerScope, command: CarrierTarget) -> Effect:
    await control.delete_carrier(await scope.context("carrier_delete"), command.mortal_id, command.disease_id)
    return Effect("The mortal no longer carries the sickness.", command.mortal_id)


@player_action("plague_response:set", ActionKind.EDIT_RECORD)
async def set_response(scope: PlayerScope, command: ResponseDraft) -> Effect:
    await control.set_response(await scope.context("plague_response_set"), command.community_id, command.disease_id, command.response, command.strength)
    return Effect(f"The community answers the sickness: {command.response.value.replace('_', ' ')}.", command.community_id)


@player_action("plague_response:edit", ActionKind.EDIT_RECORD)
async def edit_response(scope: PlayerScope, command: ResponseEdit) -> Effect:
    await control.edit_response(
        await scope.context("plague_response_edit"), command.community_id, command.disease_id, command.response, values=command.values, release=command.release
    )
    return Effect("The response is set so.", command.community_id)


@player_action("plague_response:delete", ActionKind.EDIT_RECORD)
async def delete_response(scope: PlayerScope, command: ResponseTarget) -> Effect:
    await control.delete_response(await scope.context("plague_response_delete"), command.community_id, command.disease_id, command.response)
    return Effect("The response is lifted.", command.community_id)


@player_action("cure_research:start", ActionKind.EDIT_RECORD)
async def start_research(scope: PlayerScope, command: ResearchTarget) -> Effect:
    await control.start_research(await scope.context("cure_research_start"), command.institution_id, command.disease_id)
    return Effect("The learned there take up the search for a cure.", command.institution_id)


@player_action("cure_research:edit", ActionKind.EDIT_RECORD)
async def edit_research(scope: PlayerScope, command: ResearchEdit) -> Effect:
    await control.edit_research(await scope.context("cure_research_edit"), command.institution_id, command.disease_id, command.values, command.release)
    return Effect("The research is set so.", command.institution_id)


@player_action("cure_research:delete", ActionKind.EDIT_RECORD)
async def delete_research(scope: PlayerScope, command: ResearchTarget) -> Effect:
    await control.delete_research(await scope.context("cure_research_delete"), command.institution_id, command.disease_id)
    return Effect("The search for a cure is abandoned.", command.institution_id)


@player_action("world_cycle:edit", ActionKind.EDIT_RECORD)
async def edit_cycle(scope: PlayerScope, command: CycleEdit) -> Effect:
    await control.edit_cycle(await scope.context("world_cycle_edit"), command.world_id, command.values, command.release)
    return Effect("The world's cycles are set so.")


@player_action("world_cycle:reset", ActionKind.EDIT_RECORD)
async def reset_cycle(scope: PlayerScope, command: CycleTarget) -> Effect:
    await control.reset_cycle(await scope.context("world_cycle_reset"), command.world_id)
    return Effect("The world's cycles return to balance.")


@player_action("land:reshape", ActionKind.EDIT_RECORD)
async def reshape_land(scope: PlayerScope, command: LandDraft) -> Effect:
    region = await control.shape_land(await scope.context("land_reshape"), command.region_id, command.act, command.target_region_id, fiery=command.fiery)
    return Effect(f"{region.name} is reshaped: {command.act.value.replace('_', ' ')}.", region.id)
