from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.nature import FermentKind, SenseKind, SymbiosisKind
from aerona.engine.nature import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class SoilMicrobiotaDraft(Command):
    region_id: int
    life: int = 50
    sterile_epochs: int = 0


class SoilMicrobiotaTarget(Command):
    region_id: int


class SoilMicrobiotaEdit(Edited):
    region_id: int


class FermentCultureDraft(Command):
    holder_entity_id: int
    kind: FermentKind = FermentKind.YEAST
    quality: int = 30


class FermentCultureTarget(Command):
    record_id: int


class FermentCultureEdit(Edited):
    record_id: int


class SpeciesRelationDraft(Command):
    first_species_id: int
    second_species_id: int
    kind: SymbiosisKind = SymbiosisKind.MUTUALISM
    strength: int = 40


class SpeciesRelationTarget(Command):
    record_id: int


class SpeciesRelationEdit(Edited):
    record_id: int


class SenseDraft(Command):
    holder_id: int
    sense: SenseKind
    acuity: int = 50


class SenseTarget(Command):
    holder_id: int
    sense: SenseKind


class SenseEdit(Edited):
    holder_id: int
    sense: SenseKind


@player_action("soil_microbiota:set", ActionKind.EDIT_RECORD)
async def soil_microbiota_set(scope: PlayerScope, command: SoilMicrobiotaDraft) -> Effect:
    row = await control.set_record(
        await scope.context("soil_microbiota_set"),
        "soil_microbiota",
        {"region_entity_id": command.region_id},
        {"life": command.life, "sterile_epochs": command.sterile_epochs},
    )
    return Effect("The life of the soil is set.", values={"record_id": getattr(row, "id", 0)})


@player_action("soil_microbiota:edit", ActionKind.EDIT_RECORD)
async def soil_microbiota_edit(scope: PlayerScope, command: SoilMicrobiotaEdit) -> Effect:
    await control.edit_record(await scope.context("soil_microbiota_edit"), "soil_microbiota", command.region_id, command.values, command.release)
    return Effect("The life of the soil is set so.")


@player_action("soil_microbiota:delete", ActionKind.EDIT_RECORD)
async def soil_microbiota_delete(scope: PlayerScope, command: SoilMicrobiotaTarget) -> Effect:
    await control.delete_record(await scope.context("soil_microbiota_delete"), "soil_microbiota", command.region_id)
    return Effect("The soil is left to itself.")


@player_action("ferment_culture:create", ActionKind.EDIT_RECORD)
async def ferment_culture_create(scope: PlayerScope, command: FermentCultureDraft) -> Effect:
    row = await control.set_record(
        await scope.context("ferment_culture_create"),
        "ferment_culture",
        {},
        {"holder_entity_id": command.holder_entity_id, "kind": command.kind, "quality": command.quality},
    )
    return Effect("The culture is kept.", values={"record_id": getattr(row, "id", 0)})


@player_action("ferment_culture:edit", ActionKind.EDIT_RECORD)
async def ferment_culture_edit(scope: PlayerScope, command: FermentCultureEdit) -> Effect:
    await control.edit_record(await scope.context("ferment_culture_edit"), "ferment_culture", command.record_id, command.values, command.release)
    return Effect("The culture is set so.")


@player_action("ferment_culture:delete", ActionKind.EDIT_RECORD)
async def ferment_culture_delete(scope: PlayerScope, command: FermentCultureTarget) -> Effect:
    await control.delete_record(await scope.context("ferment_culture_delete"), "ferment_culture", command.record_id)
    return Effect("The culture is lost.")


@player_action("species_relation:create", ActionKind.EDIT_RECORD)
async def species_relation_create(scope: PlayerScope, command: SpeciesRelationDraft) -> Effect:
    row = await control.set_record(
        await scope.context("species_relation_create"),
        "species_relation",
        {},
        {"first_species_id": command.first_species_id, "second_species_id": command.second_species_id, "kind": command.kind, "strength": command.strength},
    )
    return Effect("The two kinds are bound.", values={"record_id": getattr(row, "id", 0)})


@player_action("species_relation:edit", ActionKind.EDIT_RECORD)
async def species_relation_edit(scope: PlayerScope, command: SpeciesRelationEdit) -> Effect:
    await control.edit_record(await scope.context("species_relation_edit"), "species_relation", command.record_id, command.values, command.release)
    return Effect("The bond between kinds is set so.")


@player_action("species_relation:delete", ActionKind.EDIT_RECORD)
async def species_relation_delete(scope: PlayerScope, command: SpeciesRelationTarget) -> Effect:
    await control.delete_record(await scope.context("species_relation_delete"), "species_relation", command.record_id)
    return Effect("The bond between kinds is broken.")


@player_action("sense:set", ActionKind.EDIT_RECORD)
async def sense_set(scope: PlayerScope, command: SenseDraft) -> Effect:
    row = await control.set_record(
        await scope.context("sense_set"), "sense", {"holder_entity_id": command.holder_id, "sense": command.sense}, {"acuity": command.acuity}
    )
    return Effect("The sense is given.", values={"record_id": getattr(row, "id", 0)})


@player_action("sense:edit", ActionKind.EDIT_RECORD)
async def sense_edit(scope: PlayerScope, command: SenseEdit) -> Effect:
    await control.edit_record(await scope.context("sense_edit"), "sense", (command.holder_id, command.sense), command.values, command.release)
    return Effect("The sense is set so.")


@player_action("sense:delete", ActionKind.EDIT_RECORD)
async def sense_delete(scope: PlayerScope, command: SenseTarget) -> Effect:
    await control.delete_record(await scope.context("sense_delete"), "sense", (command.holder_id, command.sense))
    return Effect("The sense is taken away.")


@player_action("nature:run", ActionKind.EDIT_RECORD)
async def nature_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_nature(await scope.context("nature_run"))
    told = [
        several(tally.microbes.soils, "soil", "soils") + " read for their life",
        several(tally.microbes.founded, "culture", "cultures") + " founded",
        several(tally.symbiosis.formed, "bond between kinds", "bonds between kinds") + " formed",
        several(tally.sleepers.woken, "sleeper", "sleepers") + " woken",
        several(tally.islands.drifted, "island kind", "island kinds") + " changed in size",
    ]
    return Effect("; ".join(told) + ".")
