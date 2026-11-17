from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.grammar import spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.dominion import CreatureDeed, CreatureLesson, DivineScale, MagicSiteKind
from aerona.engine.dominion import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
DESCRIPTION_MAX = 2000


class DominionSet(Command):
    god_id: int
    region_id: int
    strength: int = Field(ge=0, le=SPAN)
    hold: bool = True


class DominionTarget(Command):
    god_id: int
    region_id: int


class ScaleSet(Command):
    god_id: int
    scale: DivineScale
    value: int = Field(ge=-3, le=3)
    hold: bool = True


class ScaleTarget(Command):
    god_id: int
    scale: DivineScale


class GodEdit(Edited):
    god_id: int


class GodTarget(Command):
    god_id: int


class MiracleEdit(Edited):
    miracle_id: int


class MiracleTarget(Command):
    miracle_id: int


class SiteDraft(Command):
    place_id: int
    kind: MagicSiteKind
    school: MagicSchool
    strength: int = Field(default=50, ge=0, le=SPAN)
    found_now: bool = False


class SiteEdit(Edited):
    site_id: int


class SiteReveal(Command):
    site_id: int
    finder_id: int | None = None


class SiteTarget(Command):
    site_id: int


class ThroneDraft(Command):
    place_id: int
    power: int = Field(default=60, ge=0, le=SPAN)
    holder_id: int | None = None


class ThroneEdit(Edited):
    throne_id: int


class ThroneTarget(Command):
    throne_id: int


class CreatureDraft(Command):
    god_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=DESCRIPTION_MAX)
    home_id: int


class CreatureEdit(Edited):
    creature_id: int


class CreatureLessonOrder(Command):
    creature_id: int
    deed: CreatureDeed
    lesson: CreatureLesson


class CreatureWeight(Command):
    creature_id: int
    deed: CreatureDeed
    weight: int = Field(ge=0, le=1000)
    hold: bool = True


class CreatureTarget(Command):
    creature_id: int


@player_action("dominion:set", ActionKind.EDIT_RECORD)
async def set_dominion(scope: PlayerScope, command: DominionSet) -> Effect:
    row = await control.set_dominion(await scope.context("dominion_set"), command.god_id, command.region_id, command.strength, hold=command.hold)
    return Effect(f"The dominion stands at {row.strength}.", command.god_id)


@player_action("dominion:delete", ActionKind.EDIT_RECORD)
async def delete_dominion(scope: PlayerScope, command: DominionTarget) -> Effect:
    await control.delete_dominion(await scope.context("dominion_delete"), command.god_id, command.region_id)
    return Effect("The dominion is lifted from the land.", command.god_id)


@player_action("god_scale:set", ActionKind.EDIT_RECORD)
async def set_scale(scope: PlayerScope, command: ScaleSet) -> Effect:
    row = await control.set_scale(await scope.context("god_scale_set"), command.god_id, command.scale, command.value, hold=command.hold)
    return Effect(f"The {spoken(row.scale)} scale stands at {row.value:d}.", command.god_id)


@player_action("god_scale:delete", ActionKind.EDIT_RECORD)
async def delete_scale(scope: PlayerScope, command: ScaleTarget) -> Effect:
    await control.delete_scale(await scope.context("god_scale_delete"), command.god_id, command.scale)
    return Effect("The scale is set back to the middle.", command.god_id)


@player_action("god_design:edit", ActionKind.EDIT_RECORD)
async def edit_design(scope: PlayerScope, command: GodEdit) -> Effect:
    await control.edit_design(await scope.context("god_design_edit"), command.god_id, command.values, command.release)
    return Effect("The god's design is set so.", command.god_id)


@player_action("god_design:delete", ActionKind.EDIT_RECORD)
async def delete_design(scope: PlayerScope, command: GodTarget) -> Effect:
    await control.delete_design(await scope.context("god_design_delete"), command.god_id)
    return Effect("The god's design will be weighed anew.", command.god_id)


@player_action("god_image:edit", ActionKind.EDIT_RECORD)
async def edit_image(scope: PlayerScope, command: GodEdit) -> Effect:
    await control.edit_image(await scope.context("god_image_edit"), command.god_id, command.values, command.release)
    return Effect("The image the peoples hold is set so.", command.god_id)


@player_action("god_image:delete", ActionKind.EDIT_RECORD)
async def delete_image(scope: PlayerScope, command: GodTarget) -> Effect:
    await control.delete_image(await scope.context("god_image_delete"), command.god_id)
    return Effect("The image will be read anew from the peoples.", command.god_id)


@player_action("miracle_record:edit", ActionKind.EDIT_RECORD)
async def edit_miracle(scope: PlayerScope, command: MiracleEdit) -> Effect:
    row = await control.edit_miracle(await scope.context("miracle_record_edit"), command.miracle_id, command.values, command.release)
    return Effect("The miracle is remembered so.", row.god_node_id)


@player_action("miracle_record:delete", ActionKind.EDIT_RECORD)
async def delete_miracle(scope: PlayerScope, command: MiracleTarget) -> Effect:
    await control.delete_miracle(await scope.context("miracle_record_delete"), command.miracle_id)
    return Effect("The miracle is struck from memory.")


@player_action("magic_site:create", ActionKind.EDIT_RECORD)
async def create_site(scope: PlayerScope, command: SiteDraft) -> Effect:
    row = await control.create_site(
        await scope.context("magic_site_create"), command.place_id, command.kind, command.school, command.strength, found_now=command.found_now
    )
    return Effect("A magic site is laid in the land.", command.place_id, values={"site_id": row.id})


@player_action("magic_site:edit", ActionKind.EDIT_RECORD)
async def edit_site(scope: PlayerScope, command: SiteEdit) -> Effect:
    row = await control.edit_site(await scope.context("magic_site_edit"), command.site_id, command.values, command.release)
    return Effect("The magic site is set so.", row.place_entity_id)


@player_action("magic_site:reveal", ActionKind.EDIT_RECORD)
async def reveal_site(scope: PlayerScope, command: SiteReveal) -> Effect:
    row = await control.reveal_site(await scope.context("magic_site_reveal"), command.site_id, command.finder_id)
    return Effect("The magic site is found.", row.place_entity_id)


@player_action("magic_site:delete", ActionKind.EDIT_RECORD)
async def delete_site(scope: PlayerScope, command: SiteTarget) -> Effect:
    await control.delete_site(await scope.context("magic_site_delete"), command.site_id)
    return Effect("The magic site fades from the land.")


@player_action("throne:create", ActionKind.EDIT_RECORD)
async def create_throne(scope: PlayerScope, command: ThroneDraft) -> Effect:
    row = await control.create_throne(await scope.context("throne_create"), command.place_id, command.power, command.holder_id)
    return Effect("A throne of power rises.", command.place_id, values={"throne_id": row.id})


@player_action("throne:edit", ActionKind.EDIT_RECORD)
async def edit_throne(scope: PlayerScope, command: ThroneEdit) -> Effect:
    row = await control.edit_throne(await scope.context("throne_edit"), command.throne_id, command.values, command.release)
    return Effect("The throne is set so.", row.place_entity_id)


@player_action("throne:delete", ActionKind.EDIT_RECORD)
async def delete_throne(scope: PlayerScope, command: ThroneTarget) -> Effect:
    await control.delete_throne(await scope.context("throne_delete"), command.throne_id)
    return Effect("The throne of power is cast down.")


@player_action("divine_creature:raise", ActionKind.EDIT_RECORD)
async def raise_creature(scope: PlayerScope, command: CreatureDraft) -> Effect:
    row = await control.raise_divine_creature(
        await scope.context("divine_creature_raise"), command.god_id, name=command.name, description=command.description, home_id=command.home_id
    )
    return Effect(f"{command.name} rises as a divine creature.", row.creature_entity_id, values={"creature_id": row.creature_entity_id})


@player_action("divine_creature:edit", ActionKind.EDIT_RECORD)
async def edit_creature(scope: PlayerScope, command: CreatureEdit) -> Effect:
    row = await control.edit_creature(await scope.context("divine_creature_edit"), command.creature_id, command.values, command.release)
    return Effect("The divine creature is set so.", row.creature_entity_id)


@player_action("divine_creature:teach", ActionKind.EDIT_RECORD)
async def teach_creature(scope: PlayerScope, command: CreatureLessonOrder) -> Effect:
    await control.teach_creature(await scope.context("divine_creature_teach"), command.creature_id, command.deed, command.lesson)
    told = "rewarded" if command.lesson is CreatureLesson.REWARD else "punished"
    return Effect(f"The creature was {told} for {spoken(command.deed)}.", command.creature_id)


@player_action("divine_creature:weight", ActionKind.EDIT_RECORD)
async def weight_creature(scope: PlayerScope, command: CreatureWeight) -> Effect:
    await control.set_creature_weight(await scope.context("divine_creature_weight"), command.creature_id, command.deed, command.weight, hold=command.hold)
    return Effect("The creature's leaning is set so.", command.creature_id)


@player_action("divine_creature:release", ActionKind.EDIT_RECORD)
async def release_creature(scope: PlayerScope, command: CreatureTarget) -> Effect:
    await control.release_creature(await scope.context("divine_creature_release"), command.creature_id)
    return Effect("The creature goes free of its god.", command.creature_id)
