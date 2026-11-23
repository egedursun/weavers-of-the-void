from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete, select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import (
    COLLECTION_FIELDS,
    GATHERING_FIELDS,
    CollectionMemberRow,
    CollectionPlaceRow,
    CollectionRow,
    GatheringGuestRow,
    GatheringRow,
)
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sites import (
    EXCAVATION_FIELDS,
    FEATURE_FIELDS,
    ROOM_FIELDS,
    STAGE_FIELDS,
    BattlefieldFeatureRow,
    ExcavationRow,
    ExcavationStageRow,
    RoomContentRow,
    SiteHolderRow,
    SiteRoomRow,
)
from aerona.db.tables.storyteller import STORYTELLER_FIELDS, StorytellerRow
from aerona.domain.enums.gathering import AttendanceReason, CollectionKind, CollectionRole, GatheringKind, GatheringStatus, GuestRole, Milestone
from aerona.domain.enums.site import BattlefieldFeature, RoomContentKind, SiteChallenge, SiteRoomKind
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.hold import GatheringTally, hold, plan
from aerona.engine.gatherings.occasions import Guest, Occasion
from aerona.engine.history.collections import add_members, add_places, open_collection
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.sites.accounts import remnant_near
from aerona.engine.sites.digs import DigTally, begin, dig_on
from aerona.engine.sites.rooms import Walk, delve, rooms_of
from aerona.engine.storyteller.pace import storyteller_of

Values = Mapping[str, Any]


def allowed(values: Values, fields: tuple[str, ...], label: str) -> Values:
    unknown = sorted(set(values) - set(fields))
    if unknown:
        raise ValidationFailedError(f"{an(label, capital=True)} cannot be set by {', '.join(unknown)}.")
    return values


async def found[Row](ctx: TickContext, kind: type[Row], key: object, label: str) -> Row:
    row = await ctx.session.get(kind, key)
    if row is None:
        raise NotFoundError(f"No such {label}.")
    return row


async def node(ctx: TickContext, node_id: int, label: str) -> NodeRow:
    return await found(ctx, NodeRow, node_id, label)


async def entity(ctx: TickContext, entity_id: int, label: str) -> EntityRow:
    return await found(ctx, EntityRow, entity_id, label)


async def convene(
    ctx: TickContext,
    host_id: int,
    kind: GatheringKind,
    *,
    place_id: int | None,
    honoured_id: int | None,
    milestone: Milestone | None,
    guests: list[int],
    hold_now: bool,
) -> GatheringRow:
    host = await node(ctx, host_id, "host")
    place = await entity(ctx, place_id, "place") if place_id is not None else None
    world = place.world_id if place is not None else (host_entity.world_id if (host_entity := await ctx.session.get(EntityRow, host_id)) is not None else None)
    occasion = Occasion(
        kind,
        host.id,
        world,
        place.id if place is not None else None,
        honoured_id,
        milestone,
        guests=[Guest(guest, GuestRole.GUEST, AttendanceReason.SUMMONED) for guest in guests],
    )
    row = await plan(ctx, occasion, by_player=True)
    if row is None:
        raise ValidationFailedError(f"{host.name} is held against change.")
    if hold_now:
        await hold(ctx, row, await RegionAtlas.load(ctx.session), GatheringTally())
    await ctx.session.flush()
    return row


async def hold_planned(ctx: TickContext, gathering_id: int) -> GatheringRow:
    row = await found(ctx, GatheringRow, gathering_id, "gathering")
    if row.status is not GatheringStatus.PLANNED:
        raise ValidationFailedError("Only a planned gathering can be held.")
    await hold(ctx, row, await RegionAtlas.load(ctx.session), GatheringTally())
    await ctx.session.flush()
    return row


async def edit_gathering(ctx: TickContext, gathering_id: int, values: Values, release: list[str]) -> GatheringRow:
    row = apply(await found(ctx, GatheringRow, gathering_id, "gathering"), allowed(values, GATHERING_FIELDS, "gathering"), release)
    await ctx.session.flush()
    return row


async def delete_gathering(ctx: TickContext, gathering_id: int) -> None:
    await ctx.session.delete(await found(ctx, GatheringRow, gathering_id, "gathering"))
    await ctx.session.flush()


async def set_guest(
    ctx: TickContext, gathering_id: int, node_id: int, *, role: GuestRole, reason: AttendanceReason, attended: bool | None, hold_it: bool
) -> GatheringGuestRow:
    await found(ctx, GatheringRow, gathering_id, "gathering")
    await node(ctx, node_id, "guest")
    row = await ctx.session.get(GatheringGuestRow, (gathering_id, node_id))
    if row is None:
        row = GatheringGuestRow(gathering_id=gathering_id, node_id=node_id, role=role, reason=reason, attended=attended)
        ctx.session.add(row)
    row.role, row.reason, row.attended, row.locked = role, reason, attended, hold_it
    await ctx.session.flush()
    return row


async def remove_guest(ctx: TickContext, gathering_id: int, node_id: int) -> None:
    await ctx.session.delete(await found(ctx, GatheringGuestRow, (gathering_id, node_id), "guest"))
    await ctx.session.flush()


async def create_collection(
    ctx: TickContext, kind: CollectionKind, *, name: str, world_id: int | None, members: Mapping[int, CollectionRole], places: list[int], parent_id: int | None
) -> CollectionRow:
    if world_id is not None:
        await found(ctx, WorldRow, world_id, "world")
    for member in members:
        await node(ctx, member, "member")
    row = await open_collection(ctx, kind, world_id=world_id, members=members, places=places, name=name.strip() or None, source_key="player")
    if row is None:
        raise ValidationFailedError("A history needs at least one free member.")
    if parent_id is not None:
        await found(ctx, CollectionRow, parent_id, "history")
        row.parent_id = parent_id
    row.locked = sorted({*row.locked, "name", "kind", "parent_id"})
    await ctx.session.flush()
    return row


async def edit_collection(ctx: TickContext, collection_id: int, values: Values, release: list[str]) -> CollectionRow:
    row = await found(ctx, CollectionRow, collection_id, "history")
    if values.get("parent_id") == collection_id:
        raise ValidationFailedError("A history cannot hold itself.")
    apply(row, allowed(values, COLLECTION_FIELDS, "history"), release)
    await ctx.session.flush()
    return row


async def delete_collection(ctx: TickContext, collection_id: int) -> None:
    await ctx.session.delete(await found(ctx, CollectionRow, collection_id, "history"))
    await ctx.session.flush()


async def set_member(ctx: TickContext, collection_id: int, node_id: int, role: CollectionRole) -> CollectionMemberRow:
    collection = await found(ctx, CollectionRow, collection_id, "history")
    await node(ctx, node_id, "member")
    row = await ctx.session.get(CollectionMemberRow, (collection_id, node_id))
    if row is None:
        await add_members(ctx, collection, {node_id: role})
        await ctx.session.flush()
        row = await found(ctx, CollectionMemberRow, (collection_id, node_id), "member")
    row.role = role
    await ctx.session.flush()
    return row


async def remove_member(ctx: TickContext, collection_id: int, node_id: int) -> None:
    await ctx.session.delete(await found(ctx, CollectionMemberRow, (collection_id, node_id), "member"))
    await ctx.session.flush()


async def set_place(ctx: TickContext, collection_id: int, place_id: int, *, present: bool) -> None:
    collection = await found(ctx, CollectionRow, collection_id, "history")
    await entity(ctx, place_id, "place")
    if present:
        await add_places(ctx, collection, [place_id])
    else:
        await ctx.session.execute(
            delete(CollectionPlaceRow).where(CollectionPlaceRow.collection_id == collection_id, CollectionPlaceRow.place_entity_id == place_id)
        )
    await ctx.session.flush()


async def set_storyteller(ctx: TickContext, world_id: int, profile: StorytellerProfile | None, values: Values, release: list[str]) -> StorytellerRow:
    await found(ctx, WorldRow, world_id, "world")
    row = await storyteller_of(ctx, world_id)
    if profile is not None:
        row.profile = profile
    apply(row, allowed(values, STORYTELLER_FIELDS, "storyteller"), release)
    await ctx.session.flush()
    return row


async def create_room(ctx: TickContext, site_id: int, kind: SiteRoomKind, *, challenge: SiteChallenge, difficulty: int, position: int | None) -> SiteRoomRow:
    await entity(ctx, site_id, "site")
    rooms = await rooms_of(ctx, site_id)
    row = SiteRoomRow(
        site_entity_id=site_id,
        kind=kind,
        challenge=challenge,
        difficulty=difficulty,
        position=position if position is not None else len(rooms),
        locked=["kind", "challenge", "difficulty", "position"],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_room(ctx: TickContext, room_id: int, values: Values, release: list[str]) -> SiteRoomRow:
    row = apply(await found(ctx, SiteRoomRow, room_id, "room"), allowed(values, ROOM_FIELDS, "room"), release)
    await ctx.session.flush()
    return row


async def delete_room(ctx: TickContext, room_id: int) -> None:
    await ctx.session.delete(await found(ctx, SiteRoomRow, room_id, "room"))
    await ctx.session.flush()


async def add_content(ctx: TickContext, room_id: int, kind: RoomContentKind, entity_id: int | None, strength: int) -> RoomContentRow:
    await found(ctx, SiteRoomRow, room_id, "room")
    if entity_id is not None:
        await entity(ctx, entity_id, "thing")
    elif kind is not RoomContentKind.TRAP:
        raise ValidationFailedError("Only a trap stands in a room without a thing.")
    row = RoomContentRow(room_id=room_id, kind=kind, entity_id=entity_id, strength=strength, locked=True)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def remove_content(ctx: TickContext, content_id: int) -> None:
    await ctx.session.delete(await found(ctx, RoomContentRow, content_id, "content"))
    await ctx.session.flush()


async def force_delve(ctx: TickContext, delver_id: int, site_id: int) -> Walk:
    delver = await entity(ctx, delver_id, "delver")
    site = await entity(ctx, site_id, "site")
    walk = await delve(ctx, delver, site)
    await ctx.session.flush()
    return walk


async def set_holder(ctx: TickContext, site_id: int, holder_id: int) -> SiteHolderRow:
    await entity(ctx, site_id, "site")
    await node(ctx, holder_id, "holder")
    for row in await ctx.session.scalars(select(SiteHolderRow).where(SiteHolderRow.site_entity_id == site_id, SiteHolderRow.to_epoch.is_(None))):
        row.to_epoch = ctx.epoch
    row = SiteHolderRow(site_entity_id=site_id, holder_node_id=holder_id, from_epoch=ctx.epoch, how="given by the gods")
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def delete_holder(ctx: TickContext, holder_row_id: int) -> None:
    await ctx.session.delete(await found(ctx, SiteHolderRow, holder_row_id, "holder"))
    await ctx.session.flush()


async def begin_dig(ctx: TickContext, site_id: int, leader_id: int, sponsor_id: int | None) -> ExcavationRow:
    site = await entity(ctx, site_id, "site")
    leader = await entity(ctx, leader_id, "leader")
    if sponsor_id is not None:
        await node(ctx, sponsor_id, "sponsor")
    row = await begin(ctx, site, leader, sponsor_id, by_player=True)
    await ctx.session.flush()
    return row


async def edit_dig(ctx: TickContext, dig_id: int, values: Values, release: list[str]) -> ExcavationRow:
    row = apply(await found(ctx, ExcavationRow, dig_id, "dig"), allowed(values, EXCAVATION_FIELDS, "dig"), release)
    await ctx.session.flush()
    return row


async def advance_dig(ctx: TickContext, dig_id: int) -> ExcavationRow:
    row = await found(ctx, ExcavationRow, dig_id, "dig")
    row.progress = 100
    await dig_on(ctx, row, DigTally())
    await ctx.session.flush()
    return row


async def delete_dig(ctx: TickContext, dig_id: int) -> None:
    await ctx.session.delete(await found(ctx, ExcavationRow, dig_id, "dig"))
    await ctx.session.flush()


async def edit_stage(ctx: TickContext, stage_id: int, values: Values, release: list[str]) -> ExcavationStageRow:
    row = apply(await found(ctx, ExcavationStageRow, stage_id, "stage"), allowed(values, STAGE_FIELDS, "stage"), release)
    await ctx.session.flush()
    return row


async def create_feature(ctx: TickContext, place_id: int, feature: BattlefieldFeature, strength: int, remnant_id: int | None = None) -> BattlefieldFeatureRow:
    place = await entity(ctx, place_id, "battlefield")
    if feature is BattlefieldFeature.ORDNANCE and remnant_id is None:
        remnant = await remnant_near(ctx, place)
        if remnant is None:
            raise ValidationFailedError("No arms of a war remain in this land to lie on its field.")
        remnant_id = remnant.id
    row = BattlefieldFeatureRow(
        place_entity_id=place_id,
        feature=feature,
        strength=strength,
        remnant_id=remnant_id if feature is BattlefieldFeature.ORDNANCE else None,
        epoch=ctx.epoch,
        locked=["strength"],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_feature(ctx: TickContext, feature_id: int, values: Values, release: list[str]) -> BattlefieldFeatureRow:
    row = apply(await found(ctx, BattlefieldFeatureRow, feature_id, "feature"), allowed(values, FEATURE_FIELDS, "feature"), release)
    await ctx.session.flush()
    return row


async def delete_feature(ctx: TickContext, feature_id: int) -> None:
    await ctx.session.delete(await found(ctx, BattlefieldFeatureRow, feature_id, "feature"))
    await ctx.session.flush()
