from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.engine.settlement import control
from aerona.engine.urban.planning import move
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 80
HEX_SPAN = 60
DESCRIPTION_MAX = 2000


class EditSettlement(Command):
    settlement_id: int
    values: dict[str, int | str | bool] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class BuildDistrict(Command):
    settlement_id: int
    kind: DistrictKind | None = None
    material: BuildMaterial = BuildMaterial.TIMBER
    design_id: int | None = None


class EditDistrict(Command):
    district_id: int
    level: int | None = Field(default=None, ge=1, le=5)
    condition: int | None = Field(default=None, ge=0, le=100)
    material: BuildMaterial | None = None
    kind: DistrictKind | None = None
    design_id: int | None = None
    clear_design: bool = False
    world_material_id: int | None = None
    clear_world_material: bool = False
    release: list[str] = Field(default_factory=list)


class MoveDistrict(Command):
    district_id: int
    q: int = Field(ge=-HEX_SPAN, le=HEX_SPAN)
    r: int = Field(ge=-HEX_SPAN, le=HEX_SPAN)


class SetForeigners(Command):
    settlement_id: int
    shares: dict[int, int] = Field(default_factory=dict)


class DesignDistrict(Command):
    world_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX)
    base_kind: DistrictKind
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    values: dict[str, int] = Field(default_factory=dict)


class EditDesign(Command):
    design_id: int
    values: dict[str, int | None] = Field(default_factory=dict)
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    base_kind: DistrictKind | None = None


class DesignTarget(Command):
    design_id: int


class DistrictTarget(Command):
    district_id: int


class SetTax(Command):
    settlement_id: int
    rate: int = Field(ge=0, le=100)


class FreeCity(Command):
    settlement_id: int
    free: bool = True


class Charter(Command):
    settlement_id: int
    name: str | None = Field(default=None, max_length=NAME_MAX)


@player_action("settlement:edit", ActionKind.EDIT_RECORD)
async def edit_settlement(scope: PlayerScope, command: EditSettlement) -> Effect:
    town = await control.edit_settlement(await scope.context("settlement_edit"), command.settlement_id, command.values, release=command.release)
    return Effect(f"{town.entity.name}: order {town.profile.public_order}, crime {town.profile.crime}, unrest {town.profile.unrest}.", command.settlement_id)


@player_action("district:build", ActionKind.BUILD)
async def build_district(scope: PlayerScope, command: BuildDistrict) -> Effect:
    district = await control.build_district(
        await scope.context("district_build"), command.settlement_id, command.kind, material=command.material, son_id=None, design_id=command.design_id
    )
    return Effect(f"The {district.kind.value.replace('_', ' ')} stands at level {district.level}.", command.settlement_id)


@player_action("district:edit", ActionKind.EDIT_RECORD)
async def edit_district(scope: PlayerScope, command: EditDistrict) -> Effect:
    change = control.DistrictChange(
        level=command.level,
        condition=command.condition,
        material=command.material,
        kind=command.kind,
        design_id=command.design_id,
        clear_design=command.clear_design,
        release=tuple(command.release),
        world_material_id=command.world_material_id,
        clear_world_material=command.clear_world_material,
    )
    district = await control.edit_district(await scope.context("district_edit"), command.district_id, change)
    return Effect(f"The district is now level {district.level} at condition {district.condition}.", district.settlement_entity_id)


@player_action("district:move", ActionKind.EDIT_RECORD)
async def move_district(scope: PlayerScope, command: MoveDistrict) -> Effect:
    district = await move(await scope.context("district_move"), command.district_id, (command.q, command.r))
    return Effect(f"The district now stands at hex {district.hex_q}, {district.hex_r} of its town.", district.settlement_entity_id)


@player_action("settlement:foreigners", ActionKind.EDIT_RECORD)
async def set_foreigners(scope: PlayerScope, command: SetForeigners) -> Effect:
    town = await control.set_foreigners(await scope.context("settlement_foreigners"), command.settlement_id, command.shares)
    return Effect(f"{town.entity.name} now counts {sum(town.profile.foreigners.values())}% foreigners.", command.settlement_id)


@player_action("district:design", ActionKind.CREATE_ENTITY)
async def design_district(scope: PlayerScope, command: DesignDistrict) -> Effect:
    design = await control.create_design(
        await scope.context("district_design"), command.world_id, command.name, command.base_kind, command.values, description=command.description, son_id=None
    )
    return Effect(f"The {design.name} can now be raised in this world.")


@player_action("district:design_edit", ActionKind.EDIT_RECORD)
async def edit_design(scope: PlayerScope, command: EditDesign) -> Effect:
    change = control.DesignChange(values=command.values, name=command.name, description=command.description, base_kind=command.base_kind)
    design = await control.edit_design(await scope.context("district_design_edit"), command.design_id, change)
    return Effect(f"The {design.name} design was reworked.")


@player_action("district:design_delete", ActionKind.OTHER)
async def delete_design(scope: PlayerScope, command: DesignTarget) -> Effect:
    await control.delete_design(await scope.context("district_design_delete"), command.design_id)
    return Effect("The district design was struck from the world's plans.")


@player_action("district:raze", ActionKind.OTHER)
async def raze_district(scope: PlayerScope, command: DistrictTarget) -> Effect:
    settlement_id = await control.raze_district(await scope.context("district_raze"), command.district_id)
    return Effect("The district was pulled down to bare ground.", settlement_id)


@player_action("settlement:tax", ActionKind.EDIT_RECORD)
async def set_tax(scope: PlayerScope, command: SetTax) -> Effect:
    await control.set_tax(await scope.context("settlement_tax"), command.settlement_id, command.rate)
    return Effect(f"The tax is set at {command.rate}%.", command.settlement_id)


@player_action("settlement:free_city", ActionKind.OTHER)
async def free_city(scope: PlayerScope, command: FreeCity) -> Effect:
    town = await control.free_city(await scope.context("settlement_free_city"), command.settlement_id, command.free)
    return Effect(f"{town.entity.name} is {'a free city' if command.free else 'bound to its overlord again'}.", command.settlement_id)


@player_action("settlement:charter", ActionKind.CREATE_ENTITY)
async def grant_charter(scope: PlayerScope, command: Charter) -> Effect:
    charter = await control.grant_charter(await scope.context("settlement_charter"), command.settlement_id, name=command.name, son_id=None)
    return Effect(f"{charter.name} was granted.", command.settlement_id, created_ids=(charter.id,))
