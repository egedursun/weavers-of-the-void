from typing import Annotated

from pydantic import Field

from aerona.catalog.flora import BIOCHEMISTRY_LABELS
from aerona.core.grammar import spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.ecology import Biochemistry
from aerona.engine.ecology import flora_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

Edit = dict[str, int | str | bool | None]
Percent = Annotated[int, Field(ge=0, le=100)]


class EditPlant(Command):
    species_id: int
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class SetCrop(Command):
    region_id: int
    plant_id: int
    share: Percent | None = None
    hold: bool = True
    release: list[str] = Field(default_factory=list)


class CropTarget(Command):
    region_id: int
    plant_id: int


class CropPest(Command):
    plant_id: int
    pest_id: int
    present: bool = True


class WorldLife(Command):
    world_id: int
    biochemistry: Biochemistry
    present: bool = True


@player_action("plant:edit", ActionKind.EDIT_RECORD)
async def edit_plant(scope: PlayerScope, command: EditPlant) -> Effect:
    row = await flora_control.edit_plant(await scope.context("plant_edit"), command.species_id, command.values, release=command.release)
    return Effect(f"The plant is reshaped; it is {spoken(row.cultivation)} now.", command.species_id)


@player_action("crop:set", ActionKind.EDIT_RECORD)
async def set_crop(scope: PlayerScope, command: SetCrop) -> Effect:
    row = await flora_control.set_crop(
        await scope.context("crop_set"), command.region_id, command.plant_id, command.share, hold=command.hold, release=command.release
    )
    return Effect(f"It is sown on {row.share}% of the fields there.", command.region_id)


@player_action("crop:drop", ActionKind.OTHER)
async def drop_crop(scope: PlayerScope, command: CropTarget) -> Effect:
    await flora_control.drop_crop(await scope.context("crop_drop"), command.region_id, command.plant_id)
    return Effect("The crop is no longer sown there.", command.region_id)


@player_action("crop_pest:set", ActionKind.EDIT_RECORD)
async def set_crop_pest(scope: PlayerScope, command: CropPest) -> Effect:
    row = await flora_control.set_crop_pest(await scope.context("crop_pest"), command.plant_id, command.pest_id, present=command.present)
    return Effect("The pest now feeds on that crop." if row is not None else "The pest no longer feeds on that crop.", command.plant_id)


@player_action("world:life", ActionKind.EDIT_RECORD)
async def set_world_life(scope: PlayerScope, command: WorldLife) -> Effect:
    kinds = await flora_control.set_world_life(await scope.context("world_life"), command.world_id, command.biochemistry, present=command.present)
    names = ", ".join(BIOCHEMISTRY_LABELS[kind].lower() for kind in kinds) or "no life of any kind"
    return Effect(f"The world now bears {names}.", command.world_id)
