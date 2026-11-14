from sqlalchemy import select

from aerona.core.grammar import several
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.tables.society_depth import MobilityEventRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import MobilityEvent
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.houses import HouseBook, found_house


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
    await note(
        ctx,
        f"{community.name} put {several(count, 'captive', 'captives')} in chains as slaves.",
        key="society.enslaved",
        ids=[community.id, *(item.id for item in kin)],
        kind=ChronicleKind.WORLD,
    )


async def freed(ctx: TickContext, community: EntityRow, count: int, *, by_hand: bool = False) -> None:
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
    await note(ctx, f"In {community.name}, {count} of the bound were set free.", key="society.freed", ids=[community.id, *(item.id for item in kin)])


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
    text = f"For the victory, {hero.name} was raised among the nobles" + (f" and founded {house.name}." if house is not None else ".")
    await note(ctx, text, key="society.ennobled", ids=[hero.id, *([house.id] if house is not None else []), *([benefactor.id] if benefactor else [])])
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
    fallen = "the bound" if member.social_class is SocialClass.SERF_OR_SLAVE else "the outcasts"
    owner = f"{guild.name} could not pay; " if guild is not None else ""
    await note(ctx, f"{owner}{member.name} lost everything and fell among {fallen}.", key="society.ruined", ids=[member.id, *([guild.id] if guild else [])])
