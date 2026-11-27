from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.arts import FIELD_GAMES
from aerona.catalog.market_kinds import ANIMAL_CLUBS, CLUBS, MIND_CLUBS
from aerona.constants.units import PERCENT
from aerona.db.tables.arts import BetRow, ClubRow, LeagueRow, MatchRow
from aerona.db.tables.crafts import GameRow
from aerona.db.tables.ecology import HerdRow, SpeciesUseRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.arts import ClubKind, FandomLine
from aerona.domain.enums.collective import CollectiveTrigger
from aerona.domain.enums.cycles import GiftOccasion
from aerona.domain.enums.ecology import AnimalRole
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.customs import people_id_of
from aerona.engine.collective.crowds import CrowdTally, spark
from aerona.engine.context import TickContext
from aerona.engine.cycles.gifts import occasion_gift
from aerona.engine.ecology.domestication import kept_for
from aerona.engine.economy.purse import coin_of, held_coin, receive_coin, take_coin
from aerona.engine.mind.ethics import conscience
from aerona.engine.phases.factions import found_faction
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.quota import WorldQuota
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import church_of, realm_of_town, ruler_of
from aerona.engine.structures.readers import working

ARENAS = (StructureKind.ARENA, StructureKind.STADIUM)
MIDDLING = 50
PAIR = 2


@dataclass
class SportTally:
    clubs: int = 0
    leagues: int = 0
    matches: int = 0
    wagered: int = 0
    riots: int = 0
    bought: int = 0
    champions: int = 0
    friendlies: int = 0
    fixed: int = 0
    exposed: int = 0
    bred: int = 0
    patrons: int = 0


async def home_of(ctx: TickContext, club_id: int) -> EntityRow | None:
    profile = await ctx.session.get(FactionProfileRow, club_id)
    return await living_entity(ctx.session, profile.home_entity_id) if profile is not None else None


async def found_club(ctx: TickContext, town: EntityRow, kind: ClubKind | None) -> ClubRow:
    faction = await found_faction(ctx, town, FactionKind.CLUB)
    arenas = await working(ctx.session, ARENAS, host_id=town.id)
    open_kinds = [item for item in ClubKind if item not in ANIMAL_CLUBS or await kept_for(ctx, town.id, AnimalRole.SPORT) > 0]
    row = ClubRow(
        faction_entity_id=faction.id,
        kind=kind or ctx.rng(f"club.kind.{town.id}.{faction.id}").pick(open_kinds),
        arena_entity_id=arenas[0].structure.id if arenas else None,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await sign_athletes(ctx, row, town)
    return row


async def sign_athletes(ctx: TickContext, club: ClubRow, town: EntityRow) -> int:
    clubs = select(ClubRow.faction_entity_id)
    signed = select(FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id.in_(clubs))
    found = await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_among(ctx.session, [town.id]),
            EntityRow.id.not_in(signed),
        )
    )
    athletes = sorted(found, key=lambda mortal: (-(stat_or(mortal, "strength", 0) + stat_or(mortal, "agility", 0)), mortal.id))
    chosen = [mortal for mortal in athletes if not held(mortal.id)][: ctx.rules.sports.athletes]
    for mortal in chosen:
        ctx.session.add(FactionMembershipRow(faction_entity_id=club.faction_entity_id, mortal_entity_id=mortal.id, joined_epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()
    return len(chosen)


async def prowess(ctx: TickContext, club: ClubRow) -> int:
    members = await ctx.session.scalars(
        select(EntityRow)
        .join(FactionMembershipRow, FactionMembershipRow.mortal_entity_id == EntityRow.id)
        .where(FactionMembershipRow.faction_entity_id == club.faction_entity_id, EntityRow.status == EntityStatus.CANON)
    )
    scores = [(stat_or(mortal, "strength", 0) + stat_or(mortal, "agility", 0)) // 2 for mortal in members]
    return sum(scores) // len(scores) if scores else 0


async def field_game(ctx: TickContext, town: EntityRow) -> ClubKind | None:
    folk = await people_id_of(ctx.session, town)
    if folk is None:
        return None
    found = await ctx.session.scalar(
        select(GameRow.category)
        .join(KindHoldingRow, KindHoldingRow.kind_id == GameRow.id)
        .where(KindHoldingRow.concept == KindConcept.GAME, KindHoldingRow.holder_node_id == folk)
        .where(GameRow.category.in_(list(FIELD_GAMES)), KindHoldingRow.strength >= ctx.rules.sports.field_following)
        .order_by((KindHoldingRow.strength * GameRow.spectators).desc(), GameRow.id)
        .limit(1)
    )
    return FIELD_GAMES[found] if found is not None else None


async def found_clubs(ctx: TickContext, tally: SportTally) -> None:
    table = ctx.rules.sports
    homed = set(await ctx.session.scalars(select(FactionProfileRow.home_entity_id).where(FactionProfileRow.kind == FactionKind.CLUB)))
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    quota = WorldQuota(table.clubs_per_epoch)
    for town in ctx.rng("club.order").shuffled(towns):
        if quota.full(town.world_id):
            continue
        if held(town.id) or town.id in homed or stat_or(town, "population", 0) < table.club_population:
            continue
        arena = bool(await working(ctx.session, ARENAS, host_id=town.id))
        kind = None if arena else await field_game(ctx, town)
        if not arena and kind is None and await kept_for(ctx, town.id, AnimalRole.SPORT) > 0:
            kind = next(iter(sorted(ANIMAL_CLUBS)))
        if (not arena and kind is None) or not ctx.rng(f"club.{town.id}").chance(table.club_chance):
            continue
        club = await found_club(ctx, town, kind)
        quota.take(town.world_id)
        tally.clubs += 1
        await record(
            ctx,
            "sport.club",
            roles={IncidentRole.PRODUCT: club.faction_entity_id, IncidentRole.PLACE: town.id},
            facts={"game": kind},
            steps=(StepDraft(StepAction.FOUND, target=club.faction_entity_id),),
            place=town.id,
        )


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
            await record(
                ctx,
                "sport.league",
                roles={IncidentRole.PRODUCT: faction.id, IncidentRole.AUTHORITY: realm_id, IncidentRole.MEMBER: [club.faction_entity_id for club in clubs]},
                facts={"clubs": len(clubs)},
                steps=(StepDraft(StepAction.FOUND, target=faction.id),),
            )
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
    stake = round_half_up(held_coin(await coin_of(ctx.session, ctx.rules, home)) * table.stake_pct / PERCENT * club.fandom / PERCENT)
    if stake <= 0:
        return None
    row = BetRow(match_id=match.id, settlement_entity_id=home.id, club_entity_id=club.faction_entity_id, stake=stake, locked=[])
    ctx.session.add(row)
    match.stake += stake
    return row


async def settle_bets(ctx: TickContext, match: MatchRow) -> None:
    bets = list(await ctx.session.scalars(select(BetRow).where(BetRow.match_id == match.id).order_by(BetRow.id)))
    for bet in bets:
        bet.won = bet.club_entity_id == match.winner_entity_id
    staked_on_winner = sum(bet.stake for bet in bets if bet.won)
    pool = 0
    for bet in bets:
        town = await living_entity(ctx.session, bet.settlement_entity_id)
        if bet.won or town is None or held(town.id):
            continue
        if await take_coin(ctx.session, ctx.rules, town, bet.stake):
            pool += bet.stake
    for bet in bets:
        town = await living_entity(ctx.session, bet.settlement_entity_id)
        if not bet.won or town is None or held(town.id) or not staked_on_winner:
            continue
        await receive_coin(ctx.session, ctx.rules, town, round_half_up(pool * bet.stake / staked_on_winner))


async def play(ctx: TickContext, league_id: int | None, home: ClubRow, away: ClubRow, tally: SportTally, *, fixed: int | None = None) -> MatchRow:
    table = ctx.rules.sports
    rng = ctx.rng(f"match.{home.faction_entity_id}.{away.faction_entity_id}.{ctx.epoch}")
    strength = home.rating + await prowess(ctx, home)
    against = away.rating + await prowess(ctx, away)
    fixer, fixed = await fixing_of(ctx, home, away, fixed)
    home_wins = rng.integer(0, strength + against) < strength + rng.integer(0, MIDDLING // 5) if fixed is None else fixed == home.faction_entity_id
    winner, loser = (home, away) if home_wins else (away, home)
    match = MatchRow(
        league_entity_id=league_id,
        home_entity_id=home.faction_entity_id,
        away_entity_id=away.faction_entity_id,
        winner_entity_id=winner.faction_entity_id,
        fixed_by_entity_id=fixer,
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
    if fixer is not None:
        tally.fixed += 1
        await expose_fixing(ctx, match, (home, away), tally)
    if not match.fixing_exposed:
        await settle_bets(ctx, match)
    await record(
        ctx,
        "club.match",
        roles={IncidentRole.ACTOR: winner.faction_entity_id, IncidentRole.OPPONENT: loser.faction_entity_id},
        facts={"kind": home.kind, "stake": match.stake},
        steps=(StepDraft(StepAction.WIN, actor=winner.faction_entity_id, target=loser.faction_entity_id),),
    )
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


async def fixing_of(ctx: TickContext, home: ClubRow, away: ClubRow, fixed: int | None) -> tuple[int | None, int | None]:
    sides = {home.faction_entity_id, away.faction_entity_id}
    for club in (home, away):
        if club.fixed_by_entity_id is not None and club.fixed_winner_entity_id in sides:
            fixer, winner = club.fixed_by_entity_id, club.fixed_winner_entity_id
            if "fixed_by_entity_id" not in club.locked:
                club.fixed_by_entity_id, club.fixed_winner_entity_id = None, None
            return fixer, winner
    return None, fixed


async def expose_fixing(ctx: TickContext, match: MatchRow, sides: tuple[ClubRow, ClubRow], tally: SportTally) -> None:
    table = ctx.rules.clubs
    if match.fixed_by_entity_id is None or not ctx.rng(f"fixing.{match.id}").chance(table.fixing_detect_pct):
        return
    match.fixing_exposed = True
    tally.exposed += 1
    for club in sides:
        if "rating" not in club.locked:
            club.rating = clamp_int(club.rating - table.fixing_standing_loss, 0, PERCENT)
        if "fandom" not in club.locked:
            club.fandom = clamp_int(club.fandom - table.fixing_standing_loss, 0, PERCENT)
    loser = sides[0] if sides[0].faction_entity_id != match.winner_entity_id else sides[1]
    town = await home_of(ctx, loser.faction_entity_id)
    fixer = await living_entity(ctx.session, match.fixed_by_entity_id)
    if town is not None and not held(town.id):
        works = await ctx.session.get(SettlementProfileRow, town.id)
        if works is not None and "unrest" not in works.locked:
            works.unrest = clamp_int(works.unrest + table.fixing_riot_push, 0, PERCENT)
        if fixer is not None:
            await report_crime(ctx, town.id, fixer.id, CrimeKind.FIXING_CONTESTS)
            await conscience(ctx, fixer.id, ActKind.FIXING_CONTESTS, loser.faction_entity_id)
        if await spark(ctx, town, CollectiveTrigger.LOST_MATCH, CrowdTally(), forced=True) is not None:
            match.riot = True
            tally.riots += 1
    await record(
        ctx,
        "club.fixing_exposed",
        roles={IncidentRole.ACTOR: match.fixed_by_entity_id, IncidentRole.VICTIM: loser.faction_entity_id},
        facts={"stake": match.stake, "unrest": table.fixing_riot_push},
        steps=(StepDraft(StepAction.REVEAL, target=loser.faction_entity_id),),
    )


async def fix_for_patrons(ctx: TickContext) -> None:
    for club in list(
        await ctx.session.scalars(
            select(ClubRow).where(ClubRow.bought_by_entity_id.is_not(None), ClubRow.fixed_by_entity_id.is_(None)).order_by(ClubRow.faction_entity_id)
        )
    ):
        if held(club.faction_entity_id) or "fixed_by_entity_id" in club.locked:
            continue
        if ctx.rng(f"fixing.patron.{club.faction_entity_id}.{ctx.epoch}").chance(ctx.rules.clubs.fixing_detect_pct):
            club.fixed_by_entity_id, club.fixed_winner_entity_id = club.bought_by_entity_id, club.faction_entity_id


async def draw_fans(ctx: TickContext) -> None:
    for club in list(await ctx.session.scalars(select(ClubRow).order_by(ClubRow.faction_entity_id))):
        if held(club.faction_entity_id) or "fandom" in club.locked:
            continue
        draw = CLUBS[club.kind].fan_draw(ctx.rules)
        club.fandom = clamp_int(club.fandom + round_half_up(draw * (PERCENT - club.fandom) / PERCENT), 0, PERCENT)


async def breed_for_sport(ctx: TickContext, tally: SportTally) -> None:
    table = ctx.rules.clubs
    sport = select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.use == AnimalRole.SPORT)
    for club in list(await ctx.session.scalars(select(ClubRow).where(ClubRow.kind.in_(list(ANIMAL_CLUBS))).order_by(ClubRow.faction_entity_id))):
        town = await home_of(ctx, club.faction_entity_id)
        if town is None or held(town.id) or not ctx.rng(f"club.breed.{club.faction_entity_id}.{ctx.epoch}").chance(table.animal_breed_pct):
            continue
        herd = await ctx.session.scalar(
            select(HerdRow).where(HerdRow.community_entity_id == town.id, HerdRow.species_entity_id.in_(sport)).order_by(HerdRow.species_entity_id).limit(1)
        )
        if herd is not None and "head" not in herd.locked:
            herd.head += 1
            tally.bred += 1


async def court_mind_patrons(ctx: TickContext, tally: SportTally) -> None:
    table = ctx.rules.clubs
    for club in list(await ctx.session.scalars(select(ClubRow).where(ClubRow.kind.in_(list(MIND_CLUBS))).order_by(ClubRow.faction_entity_id))):
        town = await home_of(ctx, club.faction_entity_id)
        realm = await realm_of_town(ctx.session, town.id) if town is not None else None
        if realm is None or held(club.faction_entity_id) or not ctx.rng(f"club.patron.{club.faction_entity_id}.{ctx.epoch}").chance(table.mind_patron_pct):
            continue
        if await occasion_gift(ctx, realm, club.faction_entity_id, GiftOccasion.PATRONAGE, ctx.rules.gifts.occasion_value) is not None:
            tally.patrons += 1


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
            await record(
                ctx,
                "sport.champion",
                roles={IncidentRole.BENEFICIARY: champion.faction_entity_id, IncidentRole.AUTHORITY: league.faction_entity_id},
                facts={"wins": champion.wins, "losses": champion.losses, "rating": champion.rating},
                steps=(StepDraft(StepAction.WIN, actor=champion.faction_entity_id),),
            )


async def play_friendlies(ctx: TickContext, tally: SportTally) -> None:
    by_world: dict[int, list[ClubRow]] = defaultdict(list)
    for club in await ctx.session.scalars(select(ClubRow).where(ClubRow.league_entity_id.is_(None)).order_by(ClubRow.faction_entity_id)):
        home = await home_of(ctx, club.faction_entity_id)
        if home is not None and not held(club.faction_entity_id):
            by_world[home.world_id].append(club)
    for world_id, clubs in sorted(by_world.items()):
        if len(clubs) < PAIR or not ctx.rng(f"friendly.{world_id}").chance(ctx.rules.sports.friendly_chance):
            continue
        ctx.rng(f"friendly.draw.{world_id}").shuffle(clubs)
        for hosts, guests in zip(clubs[::2], clubs[1::2], strict=False):
            await play(ctx, None, hosts, guests, tally)
            tally.friendlies += 1


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
        backers = await ctx.session.get(EntityRow, club.faction_entity_id)
        if backers is not None:
            await receive_coin(ctx.session, ctx.rules, backers, table.buy_cost)
        club.bought_by_entity_id = realm.id
        tally.bought += 1
        await record(
            ctx,
            "sport.bought",
            roles={IncidentRole.BUYER: ruler.id, IncidentRole.TARGET: club.faction_entity_id, IncidentRole.AUTHORITY: realm.id},
            facts={"cost": table.buy_cost},
            steps=(StepDraft(StepAction.PAY, actor=realm.id, target=club.faction_entity_id, amount=table.buy_cost, unit=FactUnit.COIN),),
        )
    for club in list(await ctx.session.scalars(select(ClubRow).where(ClubRow.bought_by_entity_id.is_not(None)).order_by(ClubRow.faction_entity_id))):
        ruler = await living_entity(ctx.session, await ruler_of(ctx.session, club.bought_by_entity_id))
        profile = await ctx.session.get(MortalProfileRow, ruler.id) if ruler is not None else None
        if profile is not None and not held(profile.entity_id) and "legitimacy" not in profile.locked:
            profile.legitimacy = clamp_int((profile.legitimacy or 0) + table.buy_gain * club.leverage // PERCENT, 0, PERCENT)


async def keep_sport(ctx: TickContext, tally: SportTally) -> None:
    await found_clubs(ctx, tally)
    await draw_fans(ctx)
    await breed_for_sport(ctx, tally)
    await court_mind_patrons(ctx, tally)
    await fix_for_patrons(ctx)
    await form_leagues(ctx, tally)
    await play_seasons(ctx, tally)
    await play_friendlies(ctx, tally)
    await buy_favour(ctx, tally)
    await ctx.session.flush()
