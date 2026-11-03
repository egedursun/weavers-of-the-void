from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.engine.settlement import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 80


class EditSettlement(Command):
    settlement_id: int
    values: dict[str, int | str | bool] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class BuildDistrict(Command):
    settlement_id: int
    kind: DistrictKind
    material: BuildMaterial = BuildMaterial.TIMBER


class EditDistrict(Command):
    district_id: int
    level: int | None = Field(default=None, ge=1, le=5)
    condition: int | None = Field(default=None, ge=0, le=100)
    material: BuildMaterial | None = None


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
    district = await control.build_district(await scope.context("district_build"), command.settlement_id, command.kind, material=command.material, son_id=None)
    return Effect(f"The {command.kind.value.replace('_', ' ')} stands at level {district.level}.", command.settlement_id)


@player_action("district:edit", ActionKind.EDIT_RECORD)
async def edit_district(scope: PlayerScope, command: EditDistrict) -> Effect:
    district = await control.edit_district(
        await scope.context("district_edit"), command.district_id, level=command.level, condition=command.condition, material=command.material
    )
    return Effect(f"The district is now level {district.level} at condition {district.condition}.", district.settlement_entity_id)


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
