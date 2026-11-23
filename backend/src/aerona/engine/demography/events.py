from sqlalchemy import select

from aerona.catalog.mobility import MOBILITY_EVENTS
from aerona.core.grammar import several
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.tables.society_depth import MobilityEventRow
from aerona.domain.enums.cycles import ManumissionPath
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society_depth import MobilityEvent
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.indenture import bought_freedom
from aerona.engine.mind.memories import remember
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.houses import HouseBook, found_house
from aerona.engine.recording.record import record as record_incident


async def log_event(
    ctx: TickContext,
    event: MobilityEvent,
    *,
    community: EntityRow | None,
    count: int,
    mortal: EntityRow | None = None,
    house: EntityRow | None = None,
    other: EntityRow | None = None,
    by_hand: bool = False,
) -> MobilityEventRow:
    row = MobilityEventRow(
        community_entity_id=community.id if community is not None else None,
        event=event,
        count=count,
        mortal_entity_id=mortal.id if mortal is not None else None,
        house_entity_id=house.id if house is not None else None,
        other_entity_id=other.id if other is not None else None,
        by_hand=by_hand,
        epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def captive_origins(ctx: TickContext, community_id: int) -> list[EntityRow]:
    statement = select(CaptiveCohortRow.origin_entity_id).where(
        CaptiveCohortRow.captor_entity_id == community_id, CaptiveCohortRow.origin_entity_id.is_not(None)
    )
    ids = sorted({origin for origin in await ctx.session.scalars(statement) if origin is not None})
    found: list[EntityRow] = []
    for origin_id in ids:
        origin = await ctx.session.get(EntityRow, origin_id)
        if origin is not None:
            found.append(origin)
    return found


async def kin_of(ctx: TickContext, community: EntityRow) -> list[EntityRow]:
    origins = await captive_origins(ctx, community.id)
    if origins:
        return origins
    people = await people_of(ctx.session, community)
    return [people] if people is not None and people.id != community.id else []


async def enslaved(ctx: TickContext, community: EntityRow, count: int, *, by_hand: bool = False) -> None:
    if count <= 0:
        return
    kin = await kin_of(ctx, community)
    await log_event(ctx, MobilityEvent.ENSLAVED, community=community, count=count, other=kin[0] if kin else None, by_hand=by_hand)
    for holder in kin:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=holder.id,
            subject_id=community.id,
            kind=MemoryKind.HELD_CAPTIVE,
            magnitude=-ctx.rules.mobility.enslaved_memory,
            epoch=ctx.epoch,
            note=f"{several(count, 'was', 'were')} put in chains",
        )
    await record_incident(
        ctx,
        "society.enslaved",
        roles={IncidentRole.ACTOR: community.id, IncidentRole.VICTIM: [item.id for item in kin]},
        facts={
            "captives": count,
        },
    )


async def freed(ctx: TickContext, community: EntityRow, count: int, *, by_hand: bool = False, path: ManumissionPath | None = None) -> None:
    if count <= 0:
        return
    kin = await kin_of(ctx, community)
    await log_event(ctx, MobilityEvent.FREED, community=community, count=count, other=kin[0] if kin else None, by_hand=by_hand)
    for holder in kin:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=holder.id,
            subject_id=community.id,
            kind=MemoryKind.FREED_US,
            magnitude=ctx.rules.mobility.freed_memory,
            epoch=ctx.epoch,
            note=f"{count} of our kin were set free",
        )
    await record_incident(
        ctx,
        "society.freed",
        roles={IncidentRole.ACTOR: community.id, IncidentRole.BENEFICIARY: [item.id for item in kin]},
        facts={"freed": count, "path": path},
        steps=bought_freedom(community.id, count, path),
    )


async def raise_house(ctx: TickContext, hero: EntityRow) -> EntityRow | None:
    if await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == hero.id).limit(1)) is not None:
        return None
    realms = await RealmBook.load(ctx.session)
    return await found_house(ctx, await HouseBook.load(ctx), hero, polity_id=realms.member_of.get(hero.location_id or -1))


async def ennobled(ctx: TickContext, hero: EntityRow, benefactor: EntityRow | None, *, by_hand: bool = False) -> EntityRow | None:
    house = await raise_house(ctx, hero)
    await log_event(ctx, MobilityEvent.ENNOBLED, community=benefactor, count=1, mortal=hero, house=house, by_hand=by_hand)
    if benefactor is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=hero.id,
            subject_id=benefactor.id,
            kind=MemoryKind.GIFTED_ME,
            magnitude=ctx.rules.mobility.ennobled_memory,
            epoch=ctx.epoch,
            note="raised me among the nobles",
        )
    await record_incident(
        ctx,
        "society.ennobled",
        roles={
            IncidentRole.SUBJECT: hero.id,
            IncidentRole.PRODUCT: house.id if house is not None else None,
            IncidentRole.PATRON: benefactor.id if benefactor else None,
        },
    )
    return house


async def ruined(ctx: TickContext, member: EntityRow, guild: EntityRow | None, *, by_hand: bool = False) -> None:
    community = await ctx.session.get(EntityRow, member.location_id) if member.location_id is not None else None
    await log_event(ctx, MobilityEvent.RUINED, community=community, count=1, mortal=member, other=guild, by_hand=by_hand)
    if guild is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=member.id,
            subject_id=guild.id,
            kind=MemoryKind.CHEATED_US,
            magnitude=-ctx.rules.mobility.ruined_memory,
            epoch=ctx.epoch,
            note="their debts ruined me",
        )
    await record_incident(
        ctx,
        "society.ruined",
        roles={IncidentRole.VICTIM: member.id, IncidentRole.BORROWER: guild.id if guild else None},
        facts={
            "fell_to": member.social_class,
        },
    )


async def moved_class(ctx: TickContext, mortal: EntityRow, event: MobilityEvent, *, cause: str, by_hand: bool = False) -> bool:
    spec = MOBILITY_EVENTS[event]
    target = spec.lands_in
    if target is None or mortal.social_class is target:
        return False
    before = mortal.social_class
    mortal.social_class = target
    community = await ctx.session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
    await log_event(ctx, event, community=community, count=1, mortal=mortal, by_hand=by_hand)
    await record_incident(
        ctx,
        "life.class_changed",
        roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.PLACE: community.id if community is not None else None},
        facts={"event": event, "from_class": before, "to_class": target, "cause": cause},
    )
    return True
