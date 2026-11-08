from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.titles import FAITH_RANKS, RANK_WORDS, SEAT_RANKS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import GUILD_KINDS, FactionKind, FactionRank
from aerona.domain.enums.renown import Currency
from aerona.domain.enums.titles import TitleRank, TitleTenure
from aerona.domain.models.entity_stats import TitleStats
from aerona.engine.context import TickContext
from aerona.engine.faith.doctrine import CLERGY_ROLES
from aerona.engine.notes import note
from aerona.engine.polity.titles import HOLDER, POWER, RANK, emblem_of, record_holder
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat
from aerona.engine.renown.currencies import bump, purse_of

FOLLOWERS = "followers"


@dataclass
class SeatTally:
    founded: int = 0
    passed: int = 0
    raised: int = 0
    vacant: int = 0


@dataclass(frozen=True)
class Seat:
    institution: EntityRow
    rank: TitleRank
    home_id: int | None
    holder_id: int | None


async def foremost_cleric(ctx: TickContext, cult: EntityRow) -> int | None:
    if cult.location_id is None:
        return None
    found: int | None = await ctx.session.scalar(
        select(EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_among(ctx.session, [cult.location_id]),
            EntityRow.mortal_role.in_(list(CLERGY_ROLES)),
        )
        .order_by(EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )
    return found


async def faction_leader(ctx: TickContext, faction_id: int) -> int | None:
    found: int | None = await ctx.session.scalar(
        select(FactionMembershipRow.mortal_entity_id)
        .join(EntityRow, EntityRow.id == FactionMembershipRow.mortal_entity_id)
        .where(FactionMembershipRow.faction_entity_id == faction_id, FactionMembershipRow.rank == FactionRank.LEADER, EntityRow.status == EntityStatus.CANON)
        .order_by(FactionMembershipRow.mortal_entity_id)
        .limit(1)
    )
    return found


async def faith_seats(ctx: TickContext) -> list[Seat]:
    table = ctx.rules.titles
    cults = [
        cult
        for cult in await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
        if (stat(cult, FOLLOWERS) or 0) >= table.see_followers
    ]
    largest: dict[int, EntityRow] = {}
    for cult in cults:
        best = largest.get(cult.world_id or 0)
        if (stat(cult, FOLLOWERS) or 0) >= table.archsee_followers and (best is None or (stat(cult, FOLLOWERS) or 0) > (stat(best, FOLLOWERS) or 0)):
            largest[cult.world_id or 0] = cult
    seats: list[Seat] = []
    for cult in cults:
        if largest.get(cult.world_id or 0) is cult:
            rank = TitleRank.HIGH_SEAT
        elif (stat(cult, FOLLOWERS) or 0) >= table.archsee_followers:
            rank = TitleRank.ARCHSEE
        else:
            rank = TitleRank.SEE
        seats.append(Seat(cult, rank, cult.location_id, await foremost_cleric(ctx, cult)))
    return seats


async def company_seats(ctx: TickContext) -> list[Seat]:
    rows = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_([FactionKind.MERCENARY_COMPANY, *GUILD_KINDS]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    seats: list[Seat] = []
    for faction, profile in list(rows):
        rank = TitleRank.CAPTAINCY if profile.kind is FactionKind.MERCENARY_COMPANY else TitleRank.GUILDMASTERSHIP
        seats.append(Seat(faction, rank, profile.home_entity_id or faction.location_id, await faction_leader(ctx, faction.id)))
    return seats


async def seat_of(ctx: TickContext, institution_id: int) -> TitleProfileRow | None:
    found: TitleProfileRow | None = await ctx.session.scalar(
        select(TitleProfileRow)
        .join(EntityRow, EntityRow.id == TitleProfileRow.title_entity_id)
        .where(EntityRow.affiliated_entity_id == institution_id, EntityRow.entity_type == EntityType.TITLE, TitleProfileRow.destroyed_epoch.is_(None))
        .order_by(TitleProfileRow.title_entity_id)
        .limit(1)
    )
    return found


def seat_prestige(ctx: TickContext, rank: TitleRank) -> int:
    step = FAITH_RANKS.index(rank) + 1 if rank in FAITH_RANKS else 1
    return min(PERCENT, ctx.rules.titles.rank_prestige * step)


async def found_seat(ctx: TickContext, seat: Seat) -> TitleProfileRow:
    entity = await create_title_record(ctx, seat)
    row = TitleProfileRow(
        title_entity_id=entity.id,
        rank=seat.rank,
        capital_entity_id=seat.home_id,
        emblem=emblem_of(ctx, seed_of("title.emblem", entity.id)),
        prestige=seat_prestige(ctx, seat.rank),
        regalia=[],
        drift={},
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await record_holder(ctx, row, seat.holder_id, TitleTenure.CREATED)
    await ctx.session.flush()
    return row


async def create_title_record(ctx: TickContext, seat: Seat) -> EntityRow:
    words = RANK_WORDS[seat.rank]
    return await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TITLE,
            name=f"the {words} of {seat.institution.name.removeprefix('the ')}",
            body=f"The {words.lower()} of {seat.institution.name.removeprefix('the ')}, held by whoever leads it.",
            stats=TitleStats(prestige=seat_prestige(ctx, seat.rank), territory=0),
            power=POWER,
            world_id=seat.institution.world_id,
            location_id=seat.home_id,
            subtype=words.lower(),
            affiliated_entity_id=seat.institution.id,
        ),
    )


async def keep_seat(ctx: TickContext, title: TitleProfileRow, seat: Seat, tally: SeatTally) -> None:
    locked = set(title.locked or [])
    if RANK not in locked and title.rank is not seat.rank:
        title.rank = seat.rank
        title.prestige = seat_prestige(ctx, seat.rank)
        tally.raised += 1
    if HOLDER not in locked and title.holder_node_id != seat.holder_id:
        await record_holder(ctx, title, seat.holder_id, TitleTenure.INHERITED)
        tally.passed += 1


async def reward_holder(ctx: TickContext, title: TitleProfileRow) -> None:
    if title.holder_node_id is None:
        return
    purse = await purse_of(ctx.session, title.holder_node_id, ctx.epoch)
    if purse is not None:
        step = FAITH_RANKS.index(title.rank) + 1 if title.rank in FAITH_RANKS else 1
        bump(purse, Currency.PRESTIGE, ctx.rules.titles.seat_prestige * step)


async def vacate_lost(ctx: TickContext, live: set[int], tally: SeatTally) -> None:
    rows = await ctx.session.execute(
        select(TitleProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == TitleProfileRow.title_entity_id)
        .where(EntityRow.affiliated_entity_id.is_not(None), TitleProfileRow.destroyed_epoch.is_(None), TitleProfileRow.holder_node_id.is_not(None))
        .order_by(TitleProfileRow.title_entity_id)
    )
    for title, entity in list(rows):
        if title.rank not in SEAT_RANKS or entity.affiliated_entity_id in live or held(entity.id) or HOLDER in (title.locked or []):
            continue
        if title.polity_entity_id is not None:
            continue
        await record_holder(ctx, title, None, TitleTenure.INHERITED)
        tally.vacant += 1


async def tend_seats(ctx: TickContext, tally: SeatTally) -> None:
    seats = [*await faith_seats(ctx), *await company_seats(ctx)]
    for seat in seats:
        if held(seat.institution.id):
            continue
        title = await seat_of(ctx, seat.institution.id)
        if title is None:
            title = await found_seat(ctx, seat)
            tally.founded += 1
            await note(
                ctx,
                f"{seat.institution.name} raised a seat: the {RANK_WORDS[seat.rank].lower()}.",
                key="titles.seat_founded",
                ids=[seat.institution.id, title.title_entity_id],
                kind=ChronicleKind.WORLD,
            )
        elif not held(title.title_entity_id):
            await keep_seat(ctx, title, seat, tally)
        await reward_holder(ctx, title)
    await vacate_lost(ctx, {seat.institution.id for seat in seats}, tally)
