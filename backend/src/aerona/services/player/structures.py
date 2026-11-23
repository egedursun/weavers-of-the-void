from pydantic import Field

from aerona.core.grammar import spoken
from aerona.db.tables.structures import StructureDesignRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.structure import STRUCTURE_LEVEL_MAX, StructureKind
from aerona.engine.structures import control
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 120
REASON_MAX = 200
Value = int | str | bool | None


class Commission(Command):
    site_id: int
    kind: StructureKind
    level: int = Field(default=1, ge=1, le=STRUCTURE_LEVEL_MAX)
    design_id: int | None = None
    material: MaterialKind | None = None
    world_material_id: int | None = None
    name: str | None = Field(default=None, max_length=NAME_MAX)
    builder_id: int | None = None
    architect_id: int | None = None
    dedicated_son_id: int | None = None
    funds: int = Field(default=0, ge=0)


class StructureTarget(Command):
    structure_id: int


class Fund(Command):
    structure_id: int
    amount: int = Field(ge=1)


class Abandon(Command):
    structure_id: int
    reason: str = Field(default="", max_length=REASON_MAX)


class Staff(Command):
    structure_id: int
    allocated: int | None = Field(default=None, ge=0)
    hold: bool = True


class Damage(Command):
    structure_id: int
    amount: int = Field(ge=1, le=100)
    cause: str = Field(default="", max_length=REASON_MAX)


class EditStructure(Command):
    structure_id: int
    values: dict[str, Value] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)
    world_material_id: int | None = None


class CreateDesign(Command):
    world_id: int | None = None
    values: dict[str, Value] = Field(default_factory=dict)


class EditDesign(Command):
    design_id: int
    values: dict[str, Value] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class RetireDesign(Command):
    design_id: int
    retired: bool = True


def label(kind: StructureKind) -> str:
    return spoken(kind)


@player_action("structure:commission", ActionKind.BUILD)
async def commission(scope: PlayerScope, command: Commission) -> Effect:
    ctx = await scope.context("structure_commission")
    design = await ctx.session.get(StructureDesignRow, command.design_id) if command.design_id is not None else None
    work, construction = await control.commission(
        ctx,
        command.site_id,
        command.kind,
        level=command.level,
        design=design,
        material=command.material,
        world_material_id=command.world_material_id,
        name=guards.optional_text(command.name),
        son_id=command.dedicated_son_id,
        builder_id=command.builder_id,
        architect_id=command.architect_id,
        funds=command.funds,
        player=True,
    )
    return Effect(f"Work began on {work.name}; it needs {construction.cost} labour.", work.id, created_ids=(work.id,))


@player_action("structure:fund", ActionKind.EDIT_RECORD)
async def fund(scope: PlayerScope, command: Fund) -> Effect:
    row = await control.fund(await scope.context("structure_fund"), command.structure_id, command.amount)
    return Effect(f"The builders hold {row.funds} coin for the work.", command.structure_id)


@player_action("structure:finish", ActionKind.BUILD)
async def finish(scope: PlayerScope, command: StructureTarget) -> Effect:
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.construction.finish_cost, "construction.finish_cost")
    work = await control.finish_now(await scope.context("structure_finish"), command.structure_id)
    return Effect(f"{work.name} stands finished.", work.id, essence_spent=spent)


@player_action("structure:abandon", ActionKind.OTHER)
async def abandon(scope: PlayerScope, command: Abandon) -> Effect:
    await control.abandon_now(await scope.context("structure_abandon"), command.structure_id, guards.clip(command.reason, REASON_MAX))
    return Effect("The work was abandoned half-raised.", command.structure_id)


@player_action("structure:staff", ActionKind.EDIT_RECORD)
async def staff(scope: PlayerScope, command: Staff) -> Effect:
    profile = await control.set_staff(await scope.context("structure_staff"), command.structure_id, command.allocated, hold=command.hold)
    held = "held" if command.hold else "left to the world"
    return Effect(f"The staff now fills {profile.staff_pct}% of its posts ({held}).", command.structure_id)


@player_action("structure:damage", ActionKind.OTHER)
async def damage(scope: PlayerScope, command: Damage) -> Effect:
    profile = await control.damage(await scope.context("structure_damage"), command.structure_id, command.amount, guards.clip(command.cause, REASON_MAX))
    return Effect(f"The structure stands at condition {profile.condition}.", command.structure_id)


@player_action("structure:repair", ActionKind.EDIT_RECORD)
async def repair(scope: PlayerScope, command: StructureTarget) -> Effect:
    profile = await control.repair(await scope.context("structure_repair"), command.structure_id)
    return Effect(f"The structure was restored to condition {profile.condition}.", command.structure_id)


@player_action("structure:edit", ActionKind.EDIT_RECORD)
async def edit(scope: PlayerScope, command: EditStructure) -> Effect:
    profile = await control.edit_structure(
        await scope.context("structure_edit"), command.structure_id, command.values, release=command.release, world_material_id=command.world_material_id
    )
    return Effect(f"The {label(profile.kind)} works at {profile.effect_pct}% (condition {profile.condition}).", command.structure_id)


@player_action("structure_design:create", ActionKind.CREATE_ENTITY)
async def create_design(scope: PlayerScope, command: CreateDesign) -> Effect:
    row = await control.create_design(await scope.context("structure_design_create"), command.values, world_id=command.world_id)
    return Effect(f"The design {row.name} was drawn up.", values={"design_id": row.id})


@player_action("structure_design:edit", ActionKind.EDIT_RECORD)
async def edit_design(scope: PlayerScope, command: EditDesign) -> Effect:
    row = await control.edit_design(await scope.context("structure_design_edit"), command.design_id, command.values, release=command.release)
    return Effect(f"The design {row.name} was redrawn.", values={"design_id": row.id})


@player_action("structure_design:retire", ActionKind.OTHER)
async def retire_design(scope: PlayerScope, command: RetireDesign) -> Effect:
    row = await control.retire_design(await scope.context("structure_design_retire"), command.design_id, command.retired)
    return Effect(f"The design {row.name} was {'retired' if command.retired else 'restored'}.", values={"design_id": row.id})
