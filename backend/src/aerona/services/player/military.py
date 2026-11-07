from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.military import CaptiveFate, CommanderTrait, Stance, UnitKind, WarAimKind
from aerona.engine.military import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditArmy(Command):
    army_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class CommandArmy(Command):
    army_id: int
    stance: Stance | None = None
    target_region_id: int | None = None
    forced_march: bool | None = None


class EditStack(Command):
    unit_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class AddStack(Command):
    army_id: int
    kind: UnitKind
    count: int = Field(ge=1, le=10_000_000)


class StackTarget(Command):
    unit_id: int


class EditSiege(Command):
    siege_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)


class SetAim(Command):
    war_id: int
    side_id: int
    kind: WarAimKind
    target_id: int | None = None
    achieved: int = Field(default=0, ge=0, le=100)


class AimTarget(Command):
    aim_id: int


class ImposePeace(Command):
    war_id: int
    victor_id: int
    terms: list[WarAimKind] = Field(default_factory=list)


class CallAllies(Command):
    war_id: int
    side_id: int


class Weariness(Command):
    war_id: int
    side_id: int
    weariness: int = Field(ge=0, le=100)


class EditSide(Command):
    war_id: int
    side_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class SideTarget(Command):
    war_id: int
    side_id: int


class EditOccupation(Command):
    region_id: int
    control: int | None = Field(default=None, ge=0, le=100)
    resistance: int | None = Field(default=None, ge=0, le=100)
    end: bool = False


class SettleCaptives(Command):
    cohort_id: int
    fate: CaptiveFate
    count: int | None = Field(default=None, ge=0)


class CommanderTraitOrder(Command):
    mortal_id: int
    trait: CommanderTrait
    held: bool = True


class EditNetwork(Command):
    network_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)
    dismantle: bool = False


@player_action("army:edit", ActionKind.EDIT_RECORD)
async def edit_army(scope: PlayerScope, command: EditArmy) -> Effect:
    profile = await control.edit_army(await scope.context("army_edit"), command.army_id, command.values, release=command.release)
    return Effect(f"The army now stands at {profile.stance.value} with {profile.supply_days} days of food.", command.army_id)


@player_action("army:command", ActionKind.EDIT_RECORD)
async def command_army(scope: PlayerScope, command: CommandArmy) -> Effect:
    values: dict[str, int | str | bool | None] = {}
    if command.stance is not None:
        values["stance"] = command.stance.value
    if command.target_region_id is not None:
        values["target_id"] = command.target_region_id
    if command.forced_march is not None:
        values["forced_march"] = command.forced_march
    profile = await control.edit_army(await scope.context("army_command"), command.army_id, values, release=[])
    return Effect(f"The army obeys: {profile.stance.value}" + (", by forced marches." if profile.forced_march else "."), command.army_id)


@player_action("army:edit_stack", ActionKind.EDIT_RECORD)
async def edit_stack(scope: PlayerScope, command: EditStack) -> Effect:
    row = await control.edit_stack(await scope.context("army_stack"), command.unit_id, command.values, release=command.release)
    return Effect(f"The {row.kind.value.replace('_', ' ')} now number {row.count}.", row.army_entity_id)


@player_action("army:add_stack", ActionKind.EDIT_RECORD)
async def add_stack(scope: PlayerScope, command: AddStack) -> Effect:
    row = await control.add_stack(await scope.context("army_stack"), command.army_id, command.kind, command.count)
    return Effect(f"{row.count} {row.kind.value.replace('_', ' ')} join the army.", command.army_id)


@player_action("army:remove_stack", ActionKind.EDIT_RECORD)
async def remove_stack(scope: PlayerScope, command: StackTarget) -> Effect:
    army_id = await control.remove_stack(await scope.context("army_stack"), command.unit_id)
    return Effect("The stack is struck from the rolls.", army_id)


@player_action("siege:edit", ActionKind.EDIT_RECORD)
async def edit_siege(scope: PlayerScope, command: EditSiege) -> Effect:
    row = await control.edit_siege(await scope.context("siege_edit"), command.siege_id, command.values)
    return Effect(f"The siege stands {row.status.value}: {row.supplies} days of food, {row.water} of water inside.", row.besieged_entity_id)


@player_action("war:aim", ActionKind.EDIT_RECORD)
async def set_aim(scope: PlayerScope, command: SetAim) -> Effect:
    ctx = await scope.context("war_aim")
    row = await control.set_aim(ctx, command.war_id, command.side_id, command.kind, target_id=command.target_id, achieved=command.achieved)
    return Effect(f"War aim {row.kind.value.replace('_', ' ')} at {row.achieved}.", command.side_id)


@player_action("war:drop_aim", ActionKind.EDIT_RECORD)
async def drop_aim(scope: PlayerScope, command: AimTarget) -> Effect:
    await control.drop_aim(await scope.context("war_aim"), command.aim_id)
    return Effect("The war aim is abandoned.", None)


@player_action("war:impose_peace", ActionKind.OTHER)
async def impose_peace(scope: PlayerScope, command: ImposePeace) -> Effect:
    settlement = await control.impose_peace(await scope.context("war_peace"), command.war_id, command.victor_id, command.terms)
    notes = " ".join(settlement.notes)
    return Effect(f"Peace is imposed. {notes}".strip(), command.victor_id)


@player_action("war:call_allies", ActionKind.OTHER)
async def call_allies(scope: PlayerScope, command: CallAllies) -> Effect:
    joined = await control.call_allies(await scope.context("war_allies"), command.war_id, command.side_id)
    return Effect(f"{joined} allies answered the call to arms.", command.side_id)


@player_action("war:weariness", ActionKind.EDIT_RECORD)
async def set_weariness(scope: PlayerScope, command: Weariness) -> Effect:
    row = await control.set_weariness(await scope.context("war_weariness"), command.war_id, command.side_id, command.weariness)
    return Effect(f"War weariness set to {row.weariness}.", command.side_id)


@player_action("war:edit_side", ActionKind.EDIT_RECORD)
async def edit_side(scope: PlayerScope, command: EditSide) -> Effect:
    row = await control.edit_side(await scope.context("war_side"), command.war_id, command.side_id, command.values, release=command.release)
    return Effect(f"The side stands at weariness {row.weariness} and war support {row.support}.", command.side_id)


@player_action("war:separate_peace", ActionKind.OTHER)
async def separate_peace(scope: PlayerScope, command: SideTarget) -> Effect:
    await control.force_separate_peace(await scope.context("war_separate_peace"), command.war_id, command.side_id)
    return Effect("The ally made a separate peace and left the war.", command.side_id)


@player_action("occupation:edit", ActionKind.EDIT_RECORD)
async def edit_occupation(scope: PlayerScope, command: EditOccupation) -> Effect:
    row = await control.edit_occupation(
        await scope.context("occupation"), command.region_id, control=command.control, resistance=command.resistance, end=command.end
    )
    text = "The occupation ends." if row is None else f"Occupation: control {row.control}, resistance {row.resistance}."
    return Effect(text, command.region_id)


@player_action("captives:settle", ActionKind.OTHER)
async def settle_captives(scope: PlayerScope, command: SettleCaptives) -> Effect:
    row = await control.settle_cohort(await scope.context("captives"), command.cohort_id, command.fate, command.count)
    return Effect(f"{row.count} captives: {row.fate.value}.", row.captor_entity_id)


@player_action("commander:trait", ActionKind.EDIT_RECORD)
async def commander_trait(scope: PlayerScope, command: CommanderTraitOrder) -> Effect:
    await control.set_trait(await scope.context("commander_trait"), command.mortal_id, command.trait, held=command.held)
    label = command.trait.value.replace("_", " ")
    return Effect(f"They are now known as {label}." if command.held else f"They are no longer {label}.", command.mortal_id)


@player_action("spy:edit_network", ActionKind.EDIT_RECORD)
async def edit_network(scope: PlayerScope, command: EditNetwork) -> Effect:
    row = await control.edit_network(await scope.context("spy_network"), command.network_id, command.values, dismantle=command.dismantle)
    text = "The network is rolled up." if row is None else f"The network runs {row.agents} agents at depth {row.depth}."
    return Effect(text, row.owner_entity_id if row is not None else None)
