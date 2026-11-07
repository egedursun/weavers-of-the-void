from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.affairs import CourtPositionRow, CourtRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.statecraft import CourtPosition
from aerona.engine.context import TickContext
from aerona.engine.mortal.standing import add_honour, add_renown
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.polity.mandates import units_of
from aerona.engine.polity.regard import shift_regard
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat

POSITION_STATS: dict[CourtPosition, str] = {
    CourtPosition.STEWARD: "intellect",
    CourtPosition.CHAMPION: "strength",
    CourtPosition.PHYSICIAN: "wisdom",
    CourtPosition.TUTOR: "intellect",
    CourtPosition.CHRONICLER: "creativity",
    CourtPosition.MASTER_OF_REVELS: "charisma",
}
GRANDEUR = "grandeur"
COURTIERS = "courtiers"
TEN = 10


@dataclass
class CourtTally:
    courts: int = 0
    appointed: int = 0
    drawn: int = 0


@dataclass(frozen=True)
class Seat:
    realm: Realm
    ruler: EntityRow
    holder: EntityRow


async def courtiers_of(ctx: TickContext, ruler: EntityRow, capital: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(RelationshipRow, RelationshipRow.holder_node_id == EntityRow.id)
        .where(
            RelationshipRow.subject_node_id == ruler.id,
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == capital,
            EntityRow.id != ruler.id,
        )
        .order_by(EntityRow.id)
    )
    return list(dict.fromkeys(rows))


async def dwelling_of(ctx: TickContext, ruler: EntityRow) -> int:
    quality = await ctx.session.scalar(
        select(DwellingRow.quality)
        .join(HouseholdMemberRow, HouseholdMemberRow.household_id == DwellingRow.household_id)
        .where(HouseholdMemberRow.member_node_id == ruler.id)
    )
    return int(quality or 0)


async def artworks_at(ctx: TickContext, capital: int) -> int:
    rows = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.ARTWORK, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == capital)
    )
    return len(list(rows))


async def positions_of(ctx: TickContext, realm_id: int) -> dict[CourtPosition, CourtPositionRow]:
    rows = await ctx.session.scalars(select(CourtPositionRow).where(CourtPositionRow.polity_entity_id == realm_id))
    return {row.position: row for row in rows}


async def appoint(ctx: TickContext, realm: Realm, courtiers: list[EntityRow], tally: CourtTally) -> dict[CourtPosition, CourtPositionRow]:
    seats = await positions_of(ctx, realm.entity.id)
    present = {courtier.id for courtier in courtiers}
    taken = {row.holder_entity_id for row in seats.values() if row.holder_entity_id in present}
    for position, key in POSITION_STATS.items():
        row = seats.get(position)
        if row is not None and (row.locked or row.holder_entity_id in present):
            continue
        free = [courtier for courtier in courtiers if courtier.id not in taken and not held(courtier.id)]
        if not free:
            continue
        best = max(free, key=lambda courtier: (stat(courtier, key) or 0, -courtier.id))
        if row is None:
            row = CourtPositionRow(polity_entity_id=realm.entity.id, position=position)
            ctx.session.add(row)
            seats[position] = row
        row.holder_entity_id, row.since_epoch = best.id, ctx.epoch
        taken.add(best.id)
        tally.appointed += 1
    await ctx.session.flush()
    return seats


async def steward(ctx: TickContext, seat: Seat) -> None:
    if "treasury" not in seat.realm.profile.locked:
        spend(ctx, seat.realm, ctx.rules.affairs.steward_gain, TreasuryEntry.TAX, "saved by the court steward")


async def champion(ctx: TickContext, seat: Seat) -> None:
    await add_honour(ctx.session, seat.ruler.id, ctx.rules.affairs.champion_honour, ctx.epoch)


async def physician(ctx: TickContext, seat: Seat) -> None:
    if stat(seat.ruler, "hp") is not None:
        shift_stat(seat.ruler, "hp", ctx.rules.affairs.physician_heal, high=max(PERCENT, stat(seat.ruler, "hp") or 0))


async def tutor(ctx: TickContext, seat: Seat) -> None:
    heir_id = await ctx.session.scalar(select(DesignatedHeirRow.heir_entity_id).where(DesignatedHeirRow.ruler_entity_id == seat.ruler.id))
    heir = await ctx.session.get(EntityRow, heir_id) if heir_id is not None else None
    if heir is not None and not held(heir.id) and stat(heir, "intellect") is not None:
        shift_stat(heir, "intellect", ctx.rules.affairs.tutor_gain)


async def chronicler(ctx: TickContext, seat: Seat) -> None:
    await add_renown(ctx.session, seat.ruler.id, ctx.rules.affairs.chronicler_renown, ctx.epoch, rules=ctx.rules)


DUTIES: dict[CourtPosition, Callable[[TickContext, Seat], Awaitable[None]]] = {
    CourtPosition.STEWARD: steward,
    CourtPosition.CHAMPION: champion,
    CourtPosition.PHYSICIAN: physician,
    CourtPosition.TUTOR: tutor,
    CourtPosition.CHRONICLER: chronicler,
}


async def grandeur_parts(ctx: TickContext, ruler: EntityRow, capital: int, courtiers: int, seats: dict[CourtPosition, CourtPositionRow]) -> dict[str, int]:
    table = ctx.rules.affairs
    revelry = seats.get(CourtPosition.MASTER_OF_REVELS)
    return {
        "dwelling": round_half_up(await dwelling_of(ctx, ruler) * table.court_dwelling_pct / PERCENT),
        "artworks": await artworks_at(ctx, capital) * table.court_artwork,
        "fine_goods": await units_of(ctx, capital, CommodityKind.LUXURIES) // TEN * table.court_goods,
        "courtiers": courtiers * table.court_courtier,
        "revels": table.revels_grandeur if revelry is not None and revelry.holder_entity_id is not None else 0,
    }


async def draw_talent(ctx: TickContext, realm: Realm, capital: int, grandeur: int, tally: CourtTally) -> None:
    if not ctx.rng(f"court.talent.{realm.entity.id}.{ctx.epoch}").chance(ctx.rules.affairs.talent_pct * grandeur / PERCENT):
        return
    towns = [member for member in realm.members if member != capital]
    if not towns:
        return
    gifted = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(towns))
        .order_by(EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )
    if gifted is None or held(gifted.id):
        return
    gifted.location_id = capital
    tally.drawn += 1
    await note(
        ctx,
        f"{gifted.name} was drawn to the court of {realm.entity.name}.",
        key="affairs.court_talent",
        ids=[gifted.id, realm.entity.id],
        kind=ChronicleKind.CIVILIZATION,
    )


async def hold_court(ctx: TickContext, book: RealmBook, realm: Realm, tally: CourtTally) -> None:
    table = ctx.rules.affairs
    capital = realm.profile.capital_entity_id
    ruler = book.entities.get(realm.ruler_id or -1) or (await ctx.session.get(EntityRow, realm.ruler_id) if realm.ruler_id is not None else None)
    if capital is None or ruler is None or ruler.status is not EntityStatus.CANON:
        return
    courtiers = await courtiers_of(ctx, ruler, capital)
    seats = await appoint(ctx, realm, courtiers, tally)
    row = await ctx.session.get(CourtRow, realm.entity.id)
    if row is None:
        row = CourtRow(polity_entity_id=realm.entity.id, locked=[])
        ctx.session.add(row)
    parts = await grandeur_parts(ctx, ruler, capital, len(courtiers), seats)
    if GRANDEUR not in row.locked:
        row.grandeur = clamp_int(sum(parts.values()), 0, PERCENT)
        row.parts = parts
    if COURTIERS not in row.locked:
        row.courtiers = len(courtiers)
    row.epoch = ctx.epoch
    tally.courts += 1
    if not held(ruler.id):
        await add_renown(ctx.session, ruler.id, row.grandeur * table.court_renown_pct / PERCENT, ctx.epoch, rules=ctx.rules)
        for position, seat in seats.items():
            holder = await ctx.session.get(EntityRow, seat.holder_entity_id) if seat.holder_entity_id is not None else None
            duty = DUTIES.get(position)
            if duty is not None and holder is not None and holder.status is EntityStatus.CANON:
                await duty(ctx, Seat(realm, ruler, holder))
    welcome = round_half_up(row.grandeur * table.court_trust_pct / PERCENT)
    if welcome:
        for other in book.realms.values():
            if other.entity.id != realm.entity.id and other.entity.world_id == realm.entity.world_id:
                await shift_regard(ctx, other.entity.id, realm.entity.id, trust=welcome)
    await draw_talent(ctx, realm, capital, row.grandeur, tally)


async def tend_courts(ctx: TickContext, tally: CourtTally) -> None:
    book = await RealmBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if not held(realm.entity.id):
            await hold_court(ctx, book, realm, tally)
