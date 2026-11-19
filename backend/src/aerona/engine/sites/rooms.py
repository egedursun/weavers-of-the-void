from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.gatherings import GUARDED_ROOMS, ITEM_ROOMS, ROOM_PLACES, ROOM_SETTLEMENTS, ROOM_STRUCTURES
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import RelicRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sites import RoomContentRow, SiteHolderRow, SiteRoomRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.domain.enums.site import RoomContentKind, SiteChallenge, SiteRoomKind
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore import items
from aerona.engine.mortal.standing import add_renown
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import StepDraft
from aerona.engine.recording.record import record as record_incident
from aerona.engine.renown.currencies import realm_of_community

CHALLENGES = (SiteChallenge.TRAP, SiteChallenge.GUARDIAN, SiteChallenge.PUZZLE, SiteChallenge.HAZARD)
LAYOUT_ENDS = 3


@dataclass
class RoomTally:
    furnished: int = 0
    rooms: int = 0
    holders: int = 0
    cleared: int = 0


@dataclass
class Walk:
    cleared: int = 0
    reached_heart: bool = False
    harmed: bool = False
    loot: list[int] = field(default_factory=list)


def grown(layout: tuple[SiteRoomKind, ...], level: int) -> tuple[SiteRoomKind, ...]:
    if len(layout) < LAYOUT_ENDS:
        return layout
    return (layout[0], *layout[1:-1] * (1 + max(0, level - 1) // 2), layout[-1])


async def layout_of(ctx: TickContext, site: EntityRow) -> tuple[SiteRoomKind, ...] | None:
    if site.entity_type is EntityType.PLACE:
        place = await ctx.session.get(PlaceProfileRow, site.id)
        return ROOM_PLACES.get(place.kind) if place is not None else None
    if site.entity_type is EntityType.STRUCTURE:
        work = await ctx.session.get(StructureProfileRow, site.id)
        layout = ROOM_STRUCTURES.get(work.kind) if work is not None else None
        return grown(layout, work.level) if layout is not None and work is not None else None
    if site.entity_type is EntityType.SETTLEMENT:
        town = await ctx.session.get(SettlementProfileRow, site.id)
        return ROOM_SETTLEMENTS.get(town.size_tier) if town is not None else None
    return None


async def rooms_of(ctx: TickContext, site_id: int) -> list[SiteRoomRow]:
    return list(await ctx.session.scalars(select(SiteRoomRow).where(SiteRoomRow.site_entity_id == site_id).order_by(SiteRoomRow.position, SiteRoomRow.id)))


async def dwellers(ctx: TickContext, site_id: int, kind: EntityType) -> list[int]:
    found = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.location_id == site_id, EntityRow.entity_type == kind, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [int(node) for node in found]


async def furnish(ctx: TickContext, site: EntityRow, layout: tuple[SiteRoomKind, ...]) -> list[SiteRoomRow]:
    table = ctx.rules.sites
    draw = ctx.rng(f"site.rooms.{site.id}")
    rooms: list[SiteRoomRow] = []
    for position, kind in enumerate(layout):
        challenge = SiteChallenge.GUARDIAN if kind in GUARDED_ROOMS else draw.pick(list(CHALLENGES))
        if kind is SiteRoomKind.GATE or not draw.chance(table.challenge_pct):
            challenge = SiteChallenge.NONE if kind not in GUARDED_ROOMS else challenge
        room = SiteRoomRow(
            site_entity_id=site.id,
            position=position,
            kind=kind,
            challenge=challenge,
            difficulty=clamp_int(table.difficulty_base + table.difficulty_step * position, 0, PERCENT),
            locked=[],
        )
        ctx.session.add(room)
        rooms.append(room)
    await ctx.session.flush()
    last = rooms[-1]
    for beast in await dwellers(ctx, site.id, EntityType.BEAST):
        lair = next((room for room in rooms if room.kind in (SiteRoomKind.LAIR, SiteRoomKind.HEART)), last)
        ctx.session.add(RoomContentRow(room_id=lair.id, kind=RoomContentKind.BEAST, entity_id=beast))
    for spirit in await dwellers(ctx, site.id, EntityType.SPIRIT):
        crypt = next((room for room in rooms if room.kind in (SiteRoomKind.CRYPT, SiteRoomKind.SHRINE, SiteRoomKind.HEART)), last)
        ctx.session.add(RoomContentRow(room_id=crypt.id, kind=RoomContentKind.SPIRIT, entity_id=spirit))
    hoards = [room for room in rooms if room.kind in ITEM_ROOMS] or [last]
    relics = set(await ctx.session.scalars(select(RelicRow.item_entity_id)))
    for item in await dwellers(ctx, site.id, EntityType.ITEM):
        if draw.chance(table.room_item_pct):
            found = RoomContentKind.RELIC if item in relics else RoomContentKind.ITEM
            ctx.session.add(RoomContentRow(room_id=draw.pick(hoards).id, kind=found, entity_id=item))
    here = select(EntityRow.id).where(EntityRow.location_id == site.id, EntityRow.status == EntityStatus.CANON)
    for mind in await ctx.session.scalars(select(MindProfileRow.node_id).where(MindProfileRow.node_id.in_(here), MindProfileRow.seat != MindSeat.BODY)):
        ctx.session.add(RoomContentRow(room_id=last.id, kind=RoomContentKind.MIND, entity_id=mind))
    for realm in await ctx.session.scalars(select(MadeRealmRow.dimension_id).where(MadeRealmRow.host_node_id == site.id)):
        if await ctx.session.get(EntityRow, realm) is not None:
            ctx.session.add(RoomContentRow(room_id=last.id, kind=RoomContentKind.REALM_GATE, entity_id=realm))
    for room in rooms:
        if room.challenge is SiteChallenge.TRAP:
            ctx.session.add(RoomContentRow(room_id=room.id, kind=RoomContentKind.TRAP, strength=table.trap_strength))
    await ctx.session.flush()
    return rooms


async def holder_of(ctx: TickContext, site: EntityRow) -> int | None:
    beasts = await dwellers(ctx, site.id, EntityType.BEAST)
    if beasts:
        return beasts[0]
    if site.entity_type is EntityType.STRUCTURE:
        work = await ctx.session.get(StructureProfileRow, site.id)
        host = work.host_entity_id if work is not None else None
        return (await realm_of_community(ctx.session, host)) or host if host is not None else None
    if site.entity_type is EntityType.SETTLEMENT:
        return await realm_of_community(ctx.session, site.id) or site.id
    return None


async def track_holder(ctx: TickContext, site: EntityRow, tally: RoomTally) -> None:
    if not ctx.rules.sites.holder_shift:
        return
    holder = await holder_of(ctx, site)
    current = await ctx.session.scalar(
        select(SiteHolderRow)
        .where(SiteHolderRow.site_entity_id == site.id, SiteHolderRow.to_epoch.is_(None))
        .order_by(SiteHolderRow.from_epoch.desc())
        .limit(1)
    )
    if (current.holder_node_id if current is not None else None) == holder:
        return
    if current is not None:
        current.to_epoch = ctx.epoch
    if holder is not None and not held(holder):
        ctx.session.add(SiteHolderRow(site_entity_id=site.id, holder_node_id=holder, from_epoch=ctx.epoch, how="engine"))
        tally.holders += 1


async def sites(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type.in_([EntityType.PLACE, EntityType.STRUCTURE, EntityType.SETTLEMENT]), EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
    )


async def keep_sites(ctx: TickContext, tally: RoomTally) -> None:
    for site in await sites(ctx):
        if held(site.id):
            continue
        layout = await layout_of(ctx, site)
        if layout is None:
            continue
        if not await rooms_of(ctx, site.id):
            tally.rooms += len(await furnish(ctx, site, layout))
            tally.furnished += 1
        await track_holder(ctx, site, tally)


async def contents_of(ctx: TickContext, room_id: int) -> list[RoomContentRow]:
    return list(await ctx.session.scalars(select(RoomContentRow).where(RoomContentRow.room_id == room_id).order_by(RoomContentRow.id)))


async def claim_relic(ctx: TickContext, delver: EntityRow, relic: EntityRow, room: SiteRoomRow) -> None:
    await items.profile_of(ctx, relic)
    await items.give(ctx, relic, delver.id, ItemDeed.CAPTURED, f"a relic carried out of {spoken(room.kind)} by {delver.name}")
    shift_stat(delver, "piety", ctx.rules.sites.relic_piety, 0)


async def wake_mind(ctx: TickContext, delver: EntityRow, mind: EntityRow, room: SiteRoomRow) -> None:
    await connect(ctx.session, delver.id, mind.id, BondKind.KNOWS, ctx.epoch, description="woke it in the depths")
    mind.location_id = delver.location_id
    await record_incident(ctx, "site.mind_woken", roles={IncidentRole.ACTOR: delver.id, IncidentRole.TARGET: mind.id, IncidentRole.PLACE: room.site_entity_id})


async def find_gate(ctx: TickContext, delver: EntityRow, realm: EntityRow, room: SiteRoomRow) -> None:
    await connect(ctx.session, delver.id, realm.id, BondKind.KNOWS, ctx.epoch, description="found the way into it")
    await record_incident(
        ctx,
        "site.realm_gate",
        roles={
            IncidentRole.ACTOR: delver.id,
            IncidentRole.DESTINATION: realm.id,
            IncidentRole.PLACE: room.site_entity_id,
        },
    )


FOUND: Mapping[RoomContentKind, Callable[[TickContext, EntityRow, EntityRow, SiteRoomRow], Awaitable[None]]] = {
    RoomContentKind.RELIC: claim_relic,
    RoomContentKind.MIND: wake_mind,
    RoomContentKind.REALM_GATE: find_gate,
}


async def loot(ctx: TickContext, delver: EntityRow, room: SiteRoomRow, walk: Walk) -> None:
    table = ctx.rules.sites
    for content in await contents_of(ctx, room.id):
        if content.locked:
            continue
        target = await ctx.session.get(EntityRow, content.entity_id) if content.entity_id is not None else None
        if content.kind in FOUND and target is not None and not held(target.id):
            walk.loot.append(target.id)
            await FOUND[content.kind](ctx, delver, target, room)
            await ctx.session.delete(content)
        elif content.kind is RoomContentKind.ITEM and target is not None and not held(target.id):
            await items.profile_of(ctx, target)
            await items.give(ctx, target, delver.id, ItemDeed.CAPTURED, f"carried out of {spoken(room.kind)} by {delver.name}")
            walk.loot.append(target.id)
            await ctx.session.delete(content)
        elif content.kind is RoomContentKind.BEAST and target is not None and not held(target.id):
            await apply_hits(
                ctx, target, Harm(table.beast_wound, HarmCause.QUEST, f"fell to {delver.name} in its lair", source_node_id=delver.id, killer_id=delver.id)
            )
        elif (
            content.kind is RoomContentKind.SPIRIT and target is not None and ctx.rng(f"site.rest.{content.id}.{ctx.epoch}").chance(table.spirit_rest_pct)
        ) or content.kind is RoomContentKind.TRAP:
            await ctx.session.delete(content)


async def walk_room(ctx: TickContext, delver: EntityRow, room: SiteRoomRow, company: int, walk: Walk) -> bool:
    table = ctx.rules.sites
    if room.challenge is SiteChallenge.NONE:
        return True
    draw = ctx.rng(f"site.walk.{room.id}.{delver.id}.{ctx.epoch}")
    wits = (stat_or(delver, "strength", 0) + stat_or(delver, "cunning", 0)) / 2 * table.delve_skill_pct / PERCENT
    if wits + company * table.delve_company_pct + draw.die(PERCENT) >= room.difficulty + draw.die(PERCENT):
        return True
    beasts = [content for content in await contents_of(ctx, room.id) if content.kind is RoomContentKind.BEAST]
    harm = table.guardian_hp if room.challenge is SiteChallenge.GUARDIAN or beasts else table.delve_hp
    await apply_hits(ctx, delver, Harm(harm, HarmCause.QUEST, f"fell in the {spoken(room.kind)} of a site it walked"))
    walk.harmed = True
    return False


async def delve(ctx: TickContext, delver: EntityRow, site: EntityRow, companions: int = 0) -> Walk:
    walk = Walk()
    if held(delver.id) or held(site.id):
        return walk
    rooms = await rooms_of(ctx, site.id)
    layout = await layout_of(ctx, site) if not rooms else None
    if layout is not None:
        rooms = await furnish(ctx, site, layout)
    steps: list[StepDraft] = []
    for room in rooms:
        if room.cleared_epoch is not None:
            continue
        passed = await walk_room(ctx, delver, room, companions, walk)
        steps.append(
            StepDraft(
                StepAction.ENTER,
                actor=delver.id,
                locus_kind=StepLocus.ROOM,
                locus_key=room.kind.value,
                outcome=StepOutcome.SUCCESS if passed else StepOutcome.WOUNDED,
                record_table="site_rooms",
                record_key=str(room.id),
            )
        )
        if not passed:
            break
        if "cleared_epoch" not in room.locked:
            room.cleared_epoch, room.cleared_by_entity_id = ctx.epoch, delver.id
        await loot(ctx, delver, room, walk)
        walk.cleared += 1
        await add_renown(ctx.session, delver.id, ctx.rules.sites.delve_renown, ctx.epoch, rules=ctx.rules)
    walk.reached_heart = bool(rooms) and all(room.cleared_epoch is not None for room in rooms)
    if rooms:
        await record_incident(
            ctx,
            "site.delved",
            roles={IncidentRole.ACTOR: delver.id, IncidentRole.PLACE: site.id, IncidentRole.PRODUCT: list(walk.loot)},
            facts={"cleared": walk.cleared, "rooms": len(rooms), "heart": int(walk.reached_heart)},
            steps=steps,
            place=site.id,
        )
    return walk
