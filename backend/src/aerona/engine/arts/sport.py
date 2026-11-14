from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.arts import BetRow, ClubRow, LeagueRow, MatchRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.arts import ClubKind, FandomLine
from aerona.domain.enums.collective import CollectiveTrigger
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.engine.collective.crowds import CrowdTally, spark
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.notes import note
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.sacred.places import church_of, realm_of_town, ruler_of
from aerona.engine.structures.readers import working

ARENAS = (StructureKind.ARENA, StructureKind.STADIUM)
MIDDLING = 50


@dataclass
class SportTally:
    clubs: int = 0
    leagues: int = 0
    matches: int = 0
    wagered: int = 0
    riots: int = 0
    bought: int = 0
    champions: int = 0


async def home_of(ctx: TickContext, club_id: int) -> EntityRow | None:
    profile = await ctx.session.get(FactionProfileRow, club_id)
    return await living_entity(ctx.session, profile.home_entity_id) if profile is not None else None


async def found_club(ctx: TickContext, town: EntityRow, kind: ClubKind | None) -> ClubRow:
    faction = await found_faction(ctx, town, FactionKind.CLUB)
    arenas = await working(ctx.session, ARENAS, host_id=town.id)
    row = ClubRow(
        faction_entity_id=faction.id,
        kind=kind or ctx.rng(f"club.kind.{town.id}.{faction.id}").pick(list(ClubKind)),
        arena_entity_id=arenas[0].structure.id if arenas else None,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def found_clubs(ctx: TickContext, tally: SportTally) -> None:
    table = ctx.rules.sports
    homed = set(await ctx.session.scalars(select(FactionProfileRow.home_entity_id).where(FactionProfileRow.kind == FactionKind.CLUB)))
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if tally.clubs >= table.clubs_per_epoch:
            return
        if held(town.id) or town.id in homed or stat_or(town, "population", 0) < table.club_population:
            continue
        if not await working(ctx.session, ARENAS, host_id=town.id) or not ctx.rng(f"club.{town.id}").chance(table.club_chance):
            continue
        club = await found_club(ctx, town, None)
        tally.clubs += 1
        await note(ctx, f"A club formed in {town.name}.", key="sport.club", ids=[club.faction_entity_id, town.id])


async def form_leagues(ctx: TickContext, tally: SportTally) -> None:
    table = ctx.rules.sports
    by_realm: dict[int, list[ClubRow]] = defaultdict(list)
    for club in await ctx.session.scalars(select(ClubRow).where(ClubRow.league_entity_id.is_(None)).order_by(ClubRow.faction_entity_id)):
        home = await home_of(ctx, club.faction_entity_id)
        realm = await realm_of_town(ctx.session, home.id) if home is not None else None
        if realm is not None:
            by_realm[realm].append(club)
    for realm_id, clubs in sorted(by_realm.items()):
        league = await ctx.session.scalar(select(LeagueRow).where(LeagueRow.polity_entity_id == realm_id).limit(1))
        if league is None:
            if len(clubs) < table.league_clubs:
                continue
            home = await home_of(ctx, clubs[0].faction_entity_id)
            if home is None or held(home.id):
                continue
            faction = await found_faction(ctx, home, FactionKind.LEAGUE)
            league = LeagueRow(faction_entity_id=faction.id, polity_entity_id=realm_id, season_epoch=ctx.epoch, locked=[])
            ctx.session.add(league)
            tally.leagues += 1
            await note(ctx, f"The clubs of the realm formed {faction.name}.", key="sport.league", ids=[faction.id, realm_id])
        for club in clubs:
            if "league_entity_id" not in club.locked:
                club.league_entity_id = league.faction_entity_id
    await ctx.session.flush()


async def read_line(ctx: TickContext, club: ClubRow, home: EntityRow) -> None:
    table = ctx.rules.circus_factions
    if "line" in club.locked:
        return
    society = await ctx.session.get(CommunitySocietyRow, home.id)
    shares = {item: society.share(item) for item in SocialClass} if society is not None else {}
    top = max(shares.items(), key=lambda item: (item[1], item[0].value), default=None)
    church = await church_of(ctx.session, home)
    if top is not None and top[1] >= table.line_share:
        club.line, club.line_entity_id = FandomLine.CLASS, None
    elif church is not None:
        club.line, club.line_entity_id = FandomLine.FAITH, church.id
    elif home.location_id is not None:
        club.line, club.line_entity_id = FandomLine.DISTRICT, home.id
    else:
        club.line, club.line_entity_id = FandomLine.NONE, None
    if "leverage" not in club.locked:
        club.leverage = 0 if club.line is FandomLine.NONE else round_half_up(club.fandom * table.leverage_pct / PERCENT)


async def wager(ctx: TickContext, match: MatchRow, club: ClubRow, home: EntityRow) -> BetRow | None:
    table = ctx.rules.sports
    wealth = stat_or(home, "wealth", 0)
    stake = round_half_up(wealth * table.stake_pct / PERCENT * club.fandom / PERCENT)
    if stake <= 0:
        return None
    row = BetRow(match_id=match.id, settlement_entity_id=home.id, club_entity_id=club.faction_entity_id, stake=stake, locked=[])
    ctx.session.add(row)
    match.stake += stake
    return row


async def settle_bets(ctx: TickContext, match: MatchRow) -> None:
    for bet in await ctx.session.scalars(select(BetRow).where(BetRow.match_id == match.id)):
        town = await living_entity(ctx.session, bet.settlement_entity_id)
        bet.won = bet.club_entity_id == match.winner_entity_id
        if town is None or held(town.id):
            continue
        shift = bet.stake if bet.won else -bet.stake
        set_stats(town, wealth=clamp_int(stat_or(town, "wealth", 0) + shift, 0, PERCENT))


async def play(ctx: TickContext, league_id: int | None, home: ClubRow, away: ClubRow, tally: SportTally, *, fixed: int | None = None) -> MatchRow:
    table = ctx.rules.sports
    rng = ctx.rng(f"match.{home.faction_entity_id}.{away.faction_entity_id}.{ctx.epoch}")
    home_wins = rng.integer(0, home.rating + away.rating) < home.rating + rng.integer(0, MIDDLING // 5) if fixed is None else fixed == home.faction_entity_id
    winner, loser = (home, away) if home_wins else (away, home)
    match = MatchRow(
        league_entity_id=league_id,
        home_entity_id=home.faction_entity_id,
        away_entity_id=away.faction_entity_id,
        winner_entity_id=winner.faction_entity_id,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(match)
    await ctx.session.flush()
    for club in (home, away):
        town = await home_of(ctx, club.faction_entity_id)
        if town is not None and not held(town.id):
            await wager(ctx, match, club, town)
    await ctx.session.flush()
    await settle_bets(ctx, match)
    for club, won in ((winner, True), (loser, False)):
        if "wins" not in club.locked and won:
            club.wins += 1
        if "losses" not in club.locked and not won:
            club.losses += 1
        if "rating" not in club.locked:
            club.rating = clamp_int(club.rating + (table.rating_step if won else -table.rating_step), 0, PERCENT)
        if "fandom" not in club.locked:
            club.fandom = clamp_int(club.fandom + (table.fandom_step if won else -table.fandom_step), 0, PERCENT)
    tally.matches += 1
    tally.wagered += match.stake
    await riot_after(ctx, match, loser, tally)
    return match


async def riot_after(ctx: TickContext, match: MatchRow, loser: ClubRow, tally: SportTally) -> None:
    table = ctx.rules.circus_factions
    town = await home_of(ctx, loser.faction_entity_id)
    if town is None or held(town.id) or loser.leverage < table.riot_leverage:
        return
    if not ctx.rng(f"riot.{match.id}").chance(table.riot_chance):
        return
    cascade = await spark(ctx, town, CollectiveTrigger.LOST_MATCH, CrowdTally(), forced=True)
    match.riot = cascade is not None
    if match.riot:
        tally.riots += 1


async def play_seasons(ctx: TickContext, tally: SportTally) -> None:
    table = ctx.rules.sports
    for league in list(await ctx.session.scalars(select(LeagueRow).order_by(LeagueRow.faction_entity_id))):
        if held(league.faction_entity_id):
            continue
        clubs = list(await ctx.session.scalars(select(ClubRow).where(ClubRow.league_entity_id == league.faction_entity_id).order_by(ClubRow.faction_entity_id)))
        for club in clubs:
            home = await home_of(ctx, club.faction_entity_id)
            if home is not None:
                await read_line(ctx, club, home)
        live = [club for club in clubs if not held(club.faction_entity_id)]
        ctx.rng(f"draw.{league.faction_entity_id}.{ctx.epoch}").shuffle(live)
        for hosts, guests in zip(live[::2], live[1::2], strict=False):
            await play(ctx, league.faction_entity_id, hosts, guests, tally)
        if ctx.epoch - league.season_epoch >= table.season_epochs and clubs:
            champion = max(clubs, key=lambda club: (club.wins - club.losses, club.rating, -club.faction_entity_id))
            if "champion_entity_id" not in league.locked:
                league.champion_entity_id = champion.faction_entity_id
            league.season_epoch = ctx.epoch
            tally.champions += 1
            await note(ctx, "A champion was named in the league.", key="sport.champion", ids=[league.faction_entity_id, champion.faction_entity_id])


async def buy_favour(ctx: TickContext, tally: SportTally) -> None:
    table = ctx.rules.circus_factions
    for club in list(
        await ctx.session.scalars(select(ClubRow).where(ClubRow.bought_by_entity_id.is_(None), ClubRow.leverage > 0).order_by(ClubRow.faction_entity_id))
    ):
        home = await home_of(ctx, club.faction_entity_id)
        realm_id = await realm_of_town(ctx.session, home.id) if home is not None else None
        ruler = await living_entity(ctx.session, await ruler_of(ctx.session, realm_id))
        realm = await living_entity(ctx.session, realm_id)
        if ruler is None or realm is None or held(ruler.id) or "bought_by_entity_id" in club.locked:
            continue
        profile = await ctx.session.get(MortalProfileRow, ruler.id)
        if profile is None or (profile.legitimacy or 0) >= table.buy_legitimacy:
            continue
        if not await take_coin(ctx.session, ctx.rules, realm, table.buy_cost):
            continue
        club.bought_by_entity_id = realm.id
        tally.bought += 1
        await note(ctx, f"{ruler.name} bought the favour of a club of {realm.name}.", key="sport.bought", ids=[ruler.id, club.faction_entity_id])
    for club in list(await ctx.session.scalars(select(ClubRow).where(ClubRow.bought_by_entity_id.is_not(None)).order_by(ClubRow.faction_entity_id))):
        ruler = await living_entity(ctx.session, await ruler_of(ctx.session, club.bought_by_entity_id))
        profile = await ctx.session.get(MortalProfileRow, ruler.id) if ruler is not None else None
        if profile is not None and not held(profile.entity_id) and "legitimacy" not in profile.locked:
            profile.legitimacy = clamp_int((profile.legitimacy or 0) + table.buy_gain * club.leverage // PERCENT, 0, PERCENT)


async def keep_sport(ctx: TickContext, tally: SportTally) -> None:
    await found_clubs(ctx, tally)
    await form_leagues(ctx, tally)
    await play_seasons(ctx, tally)
    await buy_favour(ctx, tally)
    await ctx.session.flush()
