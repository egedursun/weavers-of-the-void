from pydantic import BaseModel, Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.grammar import an
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.gathering import AttendanceReason, CollectionKind, CollectionRole, GatheringKind, GuestRole, Milestone
from aerona.domain.enums.site import BattlefieldFeature, RoomContentKind, SiteChallenge, SiteRoomKind
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.engine.gatherings import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class Convene(Command):
    host_id: int
    kind: GatheringKind
    place_id: int | None = None
    honoured_id: int | None = None
    milestone: Milestone | None = None
    guests: list[int] = Field(default_factory=list)
    hold_now: bool = True


class GatheringTarget(Command):
    gathering_id: int


class GatheringEdit(Edited):
    gathering_id: int


class GuestSet(Command):
    gathering_id: int
    node_id: int
    role: GuestRole = GuestRole.GUEST
    reason: AttendanceReason = AttendanceReason.SUMMONED
    attended: bool | None = None
    hold: bool = True


class GuestTarget(Command):
    gathering_id: int
    node_id: int


class Member(BaseModel):
    node_id: int
    role: CollectionRole = CollectionRole.MEMBER


class CollectionDraft(Command):
    kind: CollectionKind
    name: str = Field(default="", max_length=NAME_MAX_LENGTH)
    world_id: int | None = None
    members: list[Member] = Field(min_length=1)
    places: list[int] = Field(default_factory=list)
    parent_id: int | None = None


class CollectionTarget(Command):
    collection_id: int


class CollectionEdit(Edited):
    collection_id: int


class MemberSet(Command):
    collection_id: int
    node_id: int
    role: CollectionRole = CollectionRole.MEMBER


class MemberTarget(Command):
    collection_id: int
    node_id: int


class PlaceSet(Command):
    collection_id: int
    place_id: int
    present: bool = True


class StorytellerSet(Edited):
    world_id: int
    profile: StorytellerProfile | None = None


class RoomDraft(Command):
    site_id: int
    kind: SiteRoomKind
    challenge: SiteChallenge = SiteChallenge.NONE
    difficulty: int = Field(default=30, ge=0, le=SPAN)
    position: int | None = Field(default=None, ge=0)


class RoomTarget(Command):
    room_id: int


class RoomEdit(Edited):
    room_id: int


class ContentDraft(Command):
    room_id: int
    kind: RoomContentKind
    entity_id: int | None = None
    strength: int = Field(default=40, ge=0, le=SPAN)


class ContentTarget(Command):
    content_id: int


class DelveOrder(Command):
    delver_id: int
    site_id: int


class HolderSet(Command):
    site_id: int
    holder_id: int


class HolderTarget(Command):
    holder_row_id: int


class DigDraft(Command):
    site_id: int
    leader_id: int
    sponsor_id: int | None = None


class DigTarget(Command):
    dig_id: int


class DigEdit(Edited):
    dig_id: int


class StageEdit(Edited):
    stage_id: int


class FeatureDraft(Command):
    place_id: int
    feature: BattlefieldFeature
    strength: int = Field(default=50, ge=0, le=SPAN)


class FeatureTarget(Command):
    feature_id: int


class FeatureEdit(Edited):
    feature_id: int


@player_action("gathering:convene", ActionKind.EDIT_RECORD)
async def convene(scope: PlayerScope, command: Convene) -> Effect:
    row = await control.convene(
        await scope.context("gathering_convene"),
        command.host_id,
        command.kind,
        place_id=command.place_id,
        honoured_id=command.honoured_id,
        milestone=command.milestone,
        guests=command.guests,
        hold_now=command.hold_now,
    )
    told = "is held" if command.hold_now else "is planned for this epoch"
    return Effect(f"The {row.kind.value.replace('_', ' ')} {told}.", row.host_node_id, values={"gathering_id": row.id})


@player_action("gathering:hold", ActionKind.EDIT_RECORD)
async def hold_now(scope: PlayerScope, command: GatheringTarget) -> Effect:
    row = await control.hold_planned(await scope.context("gathering_hold"), command.gathering_id)
    return Effect(f"The {row.kind.value.replace('_', ' ')} was held.", row.host_node_id)


@player_action("gathering:edit", ActionKind.EDIT_RECORD)
async def edit_gathering(scope: PlayerScope, command: GatheringEdit) -> Effect:
    row = await control.edit_gathering(await scope.context("gathering_edit"), command.gathering_id, command.values, command.release)
    return Effect("The gathering is set so.", row.host_node_id)


@player_action("gathering:delete", ActionKind.EDIT_RECORD)
async def delete_gathering(scope: PlayerScope, command: GatheringTarget) -> Effect:
    await control.delete_gathering(await scope.context("gathering_delete"), command.gathering_id)
    return Effect("The gathering is struck from memory.")


@player_action("gathering_guest:set", ActionKind.EDIT_RECORD)
async def set_guest(scope: PlayerScope, command: GuestSet) -> Effect:
    row = await control.set_guest(
        await scope.context("gathering_guest_set"),
        command.gathering_id,
        command.node_id,
        role=command.role,
        reason=command.reason,
        attended=command.attended,
        hold_it=command.hold,
    )
    return Effect("The guest is set at the gathering.", row.node_id)


@player_action("gathering_guest:remove", ActionKind.EDIT_RECORD)
async def remove_guest(scope: PlayerScope, command: GuestTarget) -> Effect:
    await control.remove_guest(await scope.context("gathering_guest_remove"), command.gathering_id, command.node_id)
    return Effect("The guest is sent away.", command.node_id)


@player_action("collection:create", ActionKind.EDIT_RECORD)
async def create_collection(scope: PlayerScope, command: CollectionDraft) -> Effect:
    row = await control.create_collection(
        await scope.context("collection_create"),
        command.kind,
        name=command.name,
        world_id=command.world_id,
        members={member.node_id: member.role for member in command.members},
        places=command.places,
        parent_id=command.parent_id,
    )
    return Effect(f"{row.name} is set down in history.", values={"collection_id": row.id})


@player_action("collection:edit", ActionKind.EDIT_RECORD)
async def edit_collection(scope: PlayerScope, command: CollectionEdit) -> Effect:
    row = await control.edit_collection(await scope.context("collection_edit"), command.collection_id, command.values, command.release)
    return Effect(f"{row.name} is rewritten.")


@player_action("collection:delete", ActionKind.EDIT_RECORD)
async def delete_collection(scope: PlayerScope, command: CollectionTarget) -> Effect:
    await control.delete_collection(await scope.context("collection_delete"), command.collection_id)
    return Effect("The history is unwritten.")


@player_action("collection_member:set", ActionKind.EDIT_RECORD)
async def set_member(scope: PlayerScope, command: MemberSet) -> Effect:
    row = await control.set_member(await scope.context("collection_member_set"), command.collection_id, command.node_id, command.role)
    return Effect("The part it played is set down.", row.node_id)


@player_action("collection_member:remove", ActionKind.EDIT_RECORD)
async def remove_member(scope: PlayerScope, command: MemberTarget) -> Effect:
    await control.remove_member(await scope.context("collection_member_remove"), command.collection_id, command.node_id)
    return Effect("It is struck from that history.", command.node_id)


@player_action("collection:place", ActionKind.EDIT_RECORD)
async def set_place(scope: PlayerScope, command: PlaceSet) -> Effect:
    await control.set_place(await scope.context("collection_place"), command.collection_id, command.place_id, present=command.present)
    return Effect("The place is set in that history." if command.present else "The place is struck from that history.", command.place_id)


@player_action("storyteller:set", ActionKind.EDIT_RECORD)
async def set_storyteller(scope: PlayerScope, command: StorytellerSet) -> Effect:
    row = await control.set_storyteller(await scope.context("storyteller_set"), command.world_id, command.profile, command.values, command.release)
    return Effect(f"The storyteller of this world is {row.profile.value}.", command.world_id)


@player_action("site_room:create", ActionKind.EDIT_RECORD)
async def create_room(scope: PlayerScope, command: RoomDraft) -> Effect:
    row = await control.create_room(
        await scope.context("site_room_create"),
        command.site_id,
        command.kind,
        challenge=command.challenge,
        difficulty=command.difficulty,
        position=command.position,
    )
    return Effect(f"{an(row.kind.value, capital=True)} opens in the site.", command.site_id, values={"room_id": row.id})


@player_action("site_room:edit", ActionKind.EDIT_RECORD)
async def edit_room(scope: PlayerScope, command: RoomEdit) -> Effect:
    row = await control.edit_room(await scope.context("site_room_edit"), command.room_id, command.values, command.release)
    return Effect("The room is reshaped.", row.site_entity_id)


@player_action("site_room:delete", ActionKind.EDIT_RECORD)
async def delete_room(scope: PlayerScope, command: RoomTarget) -> Effect:
    await control.delete_room(await scope.context("site_room_delete"), command.room_id)
    return Effect("The room is sealed for good.")


@player_action("room_content:add", ActionKind.EDIT_RECORD)
async def add_content(scope: PlayerScope, command: ContentDraft) -> Effect:
    row = await control.add_content(await scope.context("room_content_add"), command.room_id, command.kind, command.entity_id, command.strength)
    return Effect(f"{an(row.kind.value, capital=True)} now waits in the room.", values={"content_id": row.id})


@player_action("room_content:remove", ActionKind.EDIT_RECORD)
async def remove_content(scope: PlayerScope, command: ContentTarget) -> Effect:
    await control.remove_content(await scope.context("room_content_remove"), command.content_id)
    return Effect("The room is emptied of it.")


@player_action("site:delve", ActionKind.EDIT_RECORD)
async def delve(scope: PlayerScope, command: DelveOrder) -> Effect:
    walk = await control.force_delve(await scope.context("site_delve"), command.delver_id, command.site_id)
    told = "reached the heart of the site" if walk.reached_heart else f"cleared {walk.cleared} rooms"
    return Effect(f"The delver {told}.", command.site_id, values={"cleared": walk.cleared})


@player_action("site_holder:set", ActionKind.EDIT_RECORD)
async def set_holder(scope: PlayerScope, command: HolderSet) -> Effect:
    row = await control.set_holder(await scope.context("site_holder_set"), command.site_id, command.holder_id)
    return Effect("The site passes into new hands.", command.site_id, values={"holder_row_id": row.id})


@player_action("site_holder:delete", ActionKind.EDIT_RECORD)
async def delete_holder(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.delete_holder(await scope.context("site_holder_delete"), command.holder_row_id)
    return Effect("That holding is struck from the site's history.")


@player_action("excavation:begin", ActionKind.EDIT_RECORD)
async def begin_dig(scope: PlayerScope, command: DigDraft) -> Effect:
    row = await control.begin_dig(await scope.context("excavation_begin"), command.site_id, command.leader_id, command.sponsor_id)
    return Effect("The dig begins.", command.site_id, values={"dig_id": row.id})


@player_action("excavation:edit", ActionKind.EDIT_RECORD)
async def edit_dig(scope: PlayerScope, command: DigEdit) -> Effect:
    row = await control.edit_dig(await scope.context("excavation_edit"), command.dig_id, command.values, command.release)
    return Effect("The dig is set so.", row.site_entity_id)


@player_action("excavation:advance", ActionKind.EDIT_RECORD)
async def advance_dig(scope: PlayerScope, command: DigTarget) -> Effect:
    row = await control.advance_dig(await scope.context("excavation_advance"), command.dig_id)
    return Effect(f"The dig reaches its {row.stage.value.replace('_', ' ')}.", row.site_entity_id)


@player_action("excavation:delete", ActionKind.EDIT_RECORD)
async def delete_dig(scope: PlayerScope, command: DigTarget) -> Effect:
    await control.delete_dig(await scope.context("excavation_delete"), command.dig_id)
    return Effect("The dig is filled in and forgotten.")


@player_action("excavation_stage:edit", ActionKind.EDIT_RECORD)
async def edit_stage(scope: PlayerScope, command: StageEdit) -> Effect:
    await control.edit_stage(await scope.context("excavation_stage_edit"), command.stage_id, command.values, command.release)
    return Effect("The stage of the dig is set so.")


@player_action("battlefield_feature:create", ActionKind.EDIT_RECORD)
async def create_feature(scope: PlayerScope, command: FeatureDraft) -> Effect:
    row = await control.create_feature(await scope.context("battlefield_feature_create"), command.place_id, command.feature, command.strength)
    return Effect(f"{an(row.feature.value.replace('_', ' '), capital=True)} marks the battlefield.", command.place_id, values={"feature_id": row.id})


@player_action("battlefield_feature:edit", ActionKind.EDIT_RECORD)
async def edit_feature(scope: PlayerScope, command: FeatureEdit) -> Effect:
    row = await control.edit_feature(await scope.context("battlefield_feature_edit"), command.feature_id, command.values, command.release)
    return Effect("The battlefield is reshaped.", row.place_entity_id)


@player_action("battlefield_feature:delete", ActionKind.EDIT_RECORD)
async def delete_feature(scope: PlayerScope, command: FeatureTarget) -> Effect:
    await control.delete_feature(await scope.context("battlefield_feature_delete"), command.feature_id)
    return Effect("The battlefield is cleared of it.")
