from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.thin_sections import (
    COMPONENT_FIELDS,
    CONSTITUTION_FIELDS,
    ENCOUNTER_FIELDS,
    ConstitutionRow,
    JourneyEncounterRow,
    RelationComponentRow,
)
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.mind import RelationComponent
from aerona.domain.enums.travel import EncounterEffect, RouteEnvironment
from aerona.engine.lore.creed_change import merge_creeds, split_creed, write_constitution
from aerona.engine.powers.control import edit_fields
from aerona.engine.services.community_relations import pair_key
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class ComponentSet(Command):
    first_id: int
    second_id: int
    component: RelationComponent
    value: int = Field(ge=-100, le=100)


class ComponentEdit(Edited):
    first_id: int
    second_id: int
    component: RelationComponent
    hold: bool = True


class PartKey(Command):
    first_id: int
    second_id: int
    component: RelationComponent


class ConstitutionWrite(Command):
    polity_id: int
    ideology_id: int | None = None


class ConstitutionEdit(Edited):
    polity_id: int
    hold: bool = True


class CharterKey(Command):
    polity_id: int


class EncounterMake(Command):
    environment: RouteEnvironment
    effect: EncounterEffect
    world_id: int | None = None
    name: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    weight: int = Field(default=50, ge=0, le=100)
    loss_pct: int = Field(default=10, ge=0, le=100)


class EncounterEdit(Edited):
    encounter_id: int
    hold: bool = True


class EncounterKey(Command):
    encounter_id: int


class CreedSplit(Command):
    ideology_id: int
    community_id: int
    dropped: IdeologyTenet | None = None
    added: IdeologyTenet | None = None


class CreedMerge(Command):
    keeper_id: int
    absorbed_id: int


async def a_pair(scope: PlayerScope, first_id: int, second_id: int) -> tuple[int, int]:
    if first_id == second_id:
        raise ValidationFailedError("A relation joins two different communities.")
    for node in (first_id, second_id):
        if await scope.session.get(EntityRow, node) is None:
            raise NotFoundError("No such community.")
    return pair_key(first_id, second_id)


@player_action("relation_component:set", ActionKind.EDIT_RECORD)
async def component_set(scope: PlayerScope, command: ComponentSet) -> Effect:
    low, high = await a_pair(scope, command.first_id, command.second_id)
    ctx = await scope.context("relation_component_set")
    row = await ctx.session.get(RelationComponentRow, (low, high, command.component))
    if row is None:
        row = RelationComponentRow(entity_a_id=low, entity_b_id=high, component=command.component, locked=[])
        ctx.session.add(row)
    row.value, row.updated_epoch, row.locked = command.value, ctx.epoch, ["value"]
    return Effect("That part of the relation is set and held.", command.first_id)


async def component_of(scope: PlayerScope, first_id: int, second_id: int, component: RelationComponent) -> RelationComponentRow:
    low, high = await a_pair(scope, first_id, second_id)
    row = await scope.session.get(RelationComponentRow, (low, high, component))
    if row is None:
        raise NotFoundError("That part of the relation is not reckoned yet.")
    return row


@player_action("relation_component:edit", ActionKind.EDIT_RECORD)
async def component_edit(scope: PlayerScope, command: ComponentEdit) -> Effect:
    row = await component_of(scope, command.first_id, command.second_id, command.component)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(COMPONENT_FIELDS))
    return Effect(f"The part of the relation: {', '.join(changed) or 'nothing'} set.", command.first_id)


@player_action("relation_component:delete", ActionKind.EDIT_RECORD)
async def component_delete(scope: PlayerScope, command: PartKey) -> Effect:
    row = await component_of(scope, command.first_id, command.second_id, command.component)
    await scope.session.delete(row)
    return Effect("That part of the relation is struck out.", command.first_id)


@player_action("constitution:write", ActionKind.EDIT_RECORD)
async def constitution_write(scope: PlayerScope, command: ConstitutionWrite) -> Effect:
    if await scope.session.get(PolityProfileRow, command.polity_id) is None:
        raise NotFoundError("No such realm.")
    row = await write_constitution(await scope.context("constitution_write"), command.polity_id, command.ideology_id)
    return Effect("The realm has a constitution.", row.polity_entity_id)


async def constitution_of(scope: PlayerScope, polity_id: int) -> ConstitutionRow:
    row = await scope.session.get(ConstitutionRow, polity_id)
    if row is None:
        raise NotFoundError("That realm has no constitution.")
    return row


@player_action("constitution:edit", ActionKind.EDIT_RECORD)
async def constitution_edit(scope: PlayerScope, command: ConstitutionEdit) -> Effect:
    row = await constitution_of(scope, command.polity_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(CONSTITUTION_FIELDS))
    return Effect(f"The constitution: {', '.join(changed) or 'nothing'} set.", command.polity_id)


@player_action("constitution:delete", ActionKind.EDIT_RECORD)
async def constitution_delete(scope: PlayerScope, command: CharterKey) -> Effect:
    row = await constitution_of(scope, command.polity_id)
    await scope.session.delete(row)
    return Effect("The constitution is torn up.", command.polity_id)


@player_action("journey_encounter:create", ActionKind.EDIT_RECORD)
async def encounter_create(scope: PlayerScope, command: EncounterMake) -> Effect:
    row = JourneyEncounterRow(
        environment=command.environment, effect=command.effect, world_id=command.world_id, name=command.name, weight=command.weight, loss_pct=command.loss_pct
    )
    row.locked = []
    scope.session.add(row)
    await scope.session.flush()
    return Effect("A new kind of encounter waits on the roads.", command.world_id, values={"encounter_id": row.id})


async def encounter_of(scope: PlayerScope, encounter_id: int) -> JourneyEncounterRow:
    row = await scope.session.get(JourneyEncounterRow, encounter_id)
    if row is None:
        raise NotFoundError("No such encounter.")
    return row


@player_action("journey_encounter:edit", ActionKind.EDIT_RECORD)
async def encounter_edit(scope: PlayerScope, command: EncounterEdit) -> Effect:
    row = await encounter_of(scope, command.encounter_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(ENCOUNTER_FIELDS))
    return Effect(f"The encounter: {', '.join(changed) or 'nothing'} set.", row.world_id)


@player_action("journey_encounter:delete", ActionKind.EDIT_RECORD)
async def encounter_delete(scope: PlayerScope, command: EncounterKey) -> Effect:
    row = await encounter_of(scope, command.encounter_id)
    await scope.session.delete(row)
    return Effect("The encounter is struck from the roads.", row.world_id)


@player_action("ideology:split", ActionKind.EDIT_RECORD)
async def creed_split(scope: PlayerScope, command: CreedSplit) -> Effect:
    splinter = await split_creed(await scope.context("ideology_split"), command.ideology_id, command.community_id, command.dropped, command.added)
    return Effect(f"{splinter.name} split away.", splinter.id, created_ids=(splinter.id,))


@player_action("ideology:merge", ActionKind.EDIT_RECORD)
async def creed_merge(scope: PlayerScope, command: CreedMerge) -> Effect:
    keeper = await merge_creeds(await scope.context("ideology_merge"), command.keeper_id, command.absorbed_id)
    return Effect(f"The two creeds are one: {keeper.name}.", keeper.id)
