from sqlalchemy import select

from aerona.catalog.market_kinds import FORGERIES
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.arts import (
    BET_FIELDS,
    CANON_FIELDS,
    CLUB_FIELDS,
    COLLECTOR_FIELDS,
    FORGERY_FIELDS,
    LEAGUE_FIELDS,
    MATCH_FIELDS,
    MOVEMENT_FIELDS,
    PRICE_FIELDS,
    SALE_FIELDS,
    ArtMovementRow,
    ArtPriceRow,
    ArtSaleRow,
    BetRow,
    CanonWorkRow,
    ClubRow,
    CollectorRow,
    ForgeryRow,
    LeagueRow,
    MatchRow,
)
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.arts import ArtMarketRole, CanonPath, ClubKind, ForgeryKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.arts.forgery import expose, forge
from aerona.engine.arts.market import appraise, owner_of, sell, start_collection
from aerona.engine.arts.market_roles import critic_of, review
from aerona.engine.arts.movements import PATH_WEIGHT, found_movement, makers_by_town
from aerona.engine.arts.sport import SportTally, found_club, play, wager
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.numbers import clamp_int

ARTWORKS = frozenset({EntityType.ARTWORK})
MORTALS = frozenset({EntityType.MORTAL})
TOWNS = frozenset({EntityType.SETTLEMENT})
PEOPLES = frozenset({EntityType.PEOPLE})
REALMS = frozenset({EntityType.POLITY})
HOLDERS = frozenset({EntityType.MORTAL, EntityType.POLITY, EntityType.CULT, EntityType.FACTION, EntityType.SETTLEMENT})
FORGED = frozenset({EntityType.ARTWORK, EntityType.ITEM, EntityType.TITLE, EntityType.LAW, EntityType.TREATY, EntityType.SETTLEMENT})
TITLES = frozenset({EntityType.TITLE})


async def artwork_profile(ctx: TickContext, artwork_id: int) -> tuple[EntityRow, ArtworkProfileRow]:
    artwork = await of_type(ctx, artwork_id, ARTWORKS, "a work of art")
    profile = await ctx.session.get(ArtworkProfileRow, artwork.id)
    if profile is None:
        raise ValidationFailedError(f"{artwork.name} has no record as a work.")
    return artwork, profile


async def price_work(ctx: TickContext, artwork_id: int, price: int | None) -> ArtPriceRow:
    artwork, profile = await artwork_profile(ctx, artwork_id)
    row = await appraise(ctx, artwork, profile)
    if price is not None:
        apply(row, {"price": price}, [])
    await ctx.session.flush()
    return row


async def sell_work(ctx: TickContext, artwork_id: int, buyer_id: int, price: int | None) -> ArtSaleRow:
    artwork, profile = await artwork_profile(ctx, artwork_id)
    buyer = await of_type(ctx, buyer_id, HOLDERS, "a buyer who can hold a work")
    seller = await owner_of(ctx, artwork.id)
    if seller == buyer.id:
        raise ValidationFailedError(f"{buyer.name} already holds {artwork.name}.")
    row = await appraise(ctx, artwork, profile)
    if price is not None:
        row.price = price
    sale = await sell(ctx, artwork, row, buyer, seller_id=seller, fair_place_id=None)
    if sale is None:
        raise ValidationFailedError(f"{buyer.name} cannot pay {row.price} for {artwork.name}.")
    return sale


async def add_collector(ctx: TickContext, holder_id: int, role: ArtMarketRole | None, taste_id: int | None) -> CollectorRow:
    holder = await of_type(ctx, holder_id, HOLDERS, "a mortal, realm, church, faction or town")
    if await ctx.session.get(CollectorRow, holder.id) is not None:
        raise ValidationFailedError(f"{holder.name} already collects.")
    if taste_id is not None:
        await of_type(ctx, taste_id, frozenset({EntityType.ART_FORM}), "an art form")
    row = await start_collection(ctx, holder, taste_id)
    if role is not None:
        apply(row, {"role": role}, [])
    await ctx.session.flush()
    return row


async def forge_work(ctx: TickContext, original_id: int, forger_id: int, kind: ForgeryKind | None = None) -> ForgeryRow:
    forger = await of_type(ctx, forger_id, MORTALS, "a mortal")
    against = FORGERIES[kind].against if kind is not None else "work"
    if kind is not None and against == "realm":
        return await forge(ctx, await of_type(ctx, original_id, REALMS, "a realm"), forger, kind=kind)
    if kind is not None and against == "title":
        return await forge(ctx, await of_type(ctx, original_id, TITLES, "a title"), forger, kind=kind)
    original = await of_type(ctx, original_id, FORGED, "a work, relic, document or a town with a brand")
    brand = None
    if original.entity_type is EntityType.SETTLEMENT:
        brand = await ctx.session.scalar(select(BrandRow).where(BrandRow.community_entity_id == original.id).order_by(BrandRow.reputation.desc()).limit(1))
        if brand is None:
            raise ValidationFailedError(f"{original.name} has no brand to counterfeit.")
    return await forge(ctx, original, forger, brand=brand)


async def review_work(ctx: TickContext, artwork_id: int, critic_id: int) -> int:
    critic = await of_type(ctx, critic_id, MORTALS, "a mortal")
    work, profile = await artwork_profile(ctx, artwork_id)
    judge = await critic_of(ctx, critic)
    if judge is None:
        raise ValidationFailedError("Only a critic, or one of enough renown to become one, can judge a work before the market.")
    price = await appraise(ctx, work, profile)
    swing = await review(ctx, judge, profile, price)
    await ctx.session.flush()
    return swing


async def expose_forgery(ctx: TickContext, forgery_id: int, expert_id: int | None) -> ForgeryRow:
    row = await found(ctx, ForgeryRow, forgery_id, "forgery")
    if expert_id is not None:
        await of_type(ctx, expert_id, HOLDERS, "an expert")
    await expose(ctx, row, expert_id)
    await ctx.session.flush()
    return row


async def canonise(ctx: TickContext, people_id: int, artwork_id: int, path: CanonPath) -> CanonWorkRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    _, profile = await artwork_profile(ctx, artwork_id)
    if await ctx.session.get(CanonWorkRow, (people_id, artwork_id)) is not None:
        raise ValidationFailedError("That work is already in the canon of that people.")
    row = await saved(
        ctx, CanonWorkRow(people_entity_id=people_id, artwork_entity_id=artwork_id, path=path, weight=PATH_WEIGHT[path], since_epoch=ctx.epoch, locked=[])
    )
    profile.canon = True
    await ctx.session.flush()
    return row


async def drop_canon(ctx: TickContext, people_id: int, artwork_id: int) -> None:
    row = await found(ctx, CanonWorkRow, (people_id, artwork_id), "canon work")
    await ctx.session.delete(row)
    others = await ctx.session.scalar(
        select(CanonWorkRow.people_entity_id).where(CanonWorkRow.artwork_entity_id == artwork_id, CanonWorkRow.people_entity_id != people_id).limit(1)
    )
    profile = await ctx.session.get(ArtworkProfileRow, artwork_id)
    if profile is not None and others is None:
        profile.canon = False
    await ctx.session.flush()


async def start_movement(ctx: TickContext, town_id: int) -> ArtMovementRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    makers = (await makers_by_town(ctx)).get(town.id, [])
    if not makers:
        raise ValidationFailedError(f"No maker of works lives in {town.name}.")
    return await found_movement(ctx, town, makers)


async def start_club(ctx: TickContext, town_id: int, kind: ClubKind | None) -> ClubRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    return await found_club(ctx, town, kind)


async def fix_contest(ctx: TickContext, fixer_id: int, match_id: int, side_id: int) -> ClubRow:
    await of_type(ctx, fixer_id, HOLDERS, "one who can fix a contest")
    match = await found(ctx, MatchRow, match_id, "match")
    if side_id not in {match.home_entity_id, match.away_entity_id}:
        raise ValidationFailedError("The side to win must be one of the two clubs of that match.")
    club = await found(ctx, ClubRow, side_id, "club")
    if "fixed_by_entity_id" in club.locked:
        raise ValidationFailedError("A god holds who fixes that club's contests.")
    club.fixed_by_entity_id, club.fixed_winner_entity_id = fixer_id, side_id
    await ctx.session.flush()
    return club


async def start_league(ctx: TickContext, realm_id: int, town_id: int | None) -> LeagueRow:
    realm = await of_type(ctx, realm_id, REALMS, "a realm")
    if await ctx.session.scalar(select(LeagueRow.faction_entity_id).where(LeagueRow.polity_entity_id == realm.id).limit(1)) is not None:
        raise ValidationFailedError(f"{realm.name} already has a league.")
    seat = await of_type(ctx, town_id, TOWNS, "a town") if town_id is not None else realm
    faction = await found_faction(ctx, seat, FactionKind.LEAGUE)
    return await saved(ctx, LeagueRow(faction_entity_id=faction.id, polity_entity_id=realm.id, season_epoch=ctx.epoch, locked=[]))


async def stage_match(ctx: TickContext, home_id: int, away_id: int, winner_id: int | None) -> MatchRow:
    if home_id == away_id:
        raise ValidationFailedError("A club cannot play itself.")
    if winner_id is not None and winner_id not in (home_id, away_id):
        raise ValidationFailedError("The winner must be one of the two clubs.")
    home = await found(ctx, ClubRow, home_id, "home club")
    away = await found(ctx, ClubRow, away_id, "away club")
    league = home.league_entity_id if home.league_entity_id == away.league_entity_id else None
    return await play(ctx, league, home, away, SportTally(), fixed=winner_id)


async def place_bet(ctx: TickContext, match_id: int, town_id: int, club_id: int, stake: int | None) -> BetRow:
    match = await found(ctx, MatchRow, match_id, "match")
    if club_id not in (match.home_entity_id, match.away_entity_id):
        raise ValidationFailedError("A bet backs one of the two clubs that played.")
    town = await of_type(ctx, town_id, TOWNS, "a town")
    club = await found(ctx, ClubRow, club_id, "club")
    row = (
        await wager(ctx, match, club, town)
        if stake is None
        else await saved(ctx, BetRow(match_id=match.id, settlement_entity_id=town.id, club_entity_id=club.faction_entity_id, stake=stake, locked=[]))
    )
    if row is None:
        raise ValidationFailedError(f"{town.name} has nothing to wager; name a stake.")
    if stake is not None:
        match.stake += stake
    row.won = None if match.winner_entity_id is None else match.winner_entity_id == club_id
    await ctx.session.flush()
    return row


async def set_manifesto(ctx: TickContext, faction_id: int, axis: ValueAxis, value: int | None) -> ArtMovementRow:
    row = await found(ctx, ArtMovementRow, faction_id, "art movement")
    manifesto = {key: amount for key, amount in row.manifesto.items() if key != axis.value}
    if value is not None:
        manifesto[axis.value] = clamp_int(value, -PERCENT, PERCENT)
    row.manifesto = dict(sorted(manifesto.items()))
    row.locked = sorted({*row.locked, "manifesto"})
    await ctx.session.flush()
    return row


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "art_price": (ArtPriceRow, PRICE_FIELDS, "price of a work"),
    "art_sale": (ArtSaleRow, SALE_FIELDS, "sale"),
    "collector": (CollectorRow, COLLECTOR_FIELDS, "collector"),
    "forgery": (ForgeryRow, FORGERY_FIELDS, "forgery"),
    "canon_work": (CanonWorkRow, CANON_FIELDS, "canon work"),
    "art_movement": (ArtMovementRow, MOVEMENT_FIELDS, "art movement"),
    "club": (ClubRow, CLUB_FIELDS, "club"),
    "league": (LeagueRow, LEAGUE_FIELDS, "league"),
    "match": (MatchRow, MATCH_FIELDS, "match"),
    "bet": (BetRow, BET_FIELDS, "bet"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
