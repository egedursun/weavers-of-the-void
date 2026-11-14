from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import GameFollowingRow, GameRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import GameKind, GameRule
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.mortal.learning import practise_subject
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.language.generator import NameKind

RULE_OF = {GameKind.BOARD: GameRule.STRATEGY, GameKind.DICE: GameRule.CHANCE, GameKind.BALL: GameRule.PHYSICAL, GameKind.WRESTLING: GameRule.PHYSICAL}


@dataclass
class GameTally:
    invented: int = 0
    spread: int = 0
    trained: int = 0
    gambled: int = 0
    played: int = 0


async def towns_of(ctx: TickContext, people_id: int) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.affiliated_entity_id == people_id)
            .order_by(EntityRow.id)
        )
    )


async def invent(ctx: TickContext, people: EntityRow, tally: GameTally) -> None:
    if await ctx.session.scalar(select(GameRow.id).where(GameRow.origin_entity_id == people.id).limit(1)) is not None:
        return
    rng = ctx.rng(seed_of("game", people.id, ctx.epoch))
    if not rng.chance(ctx.rules.games.invent_chance):
        return
    name = await Namer(ctx.session, ctx.rules).from_speaker(people.id, seed_of("game.name", people.id, ctx.epoch), NameKind.GENERAL)
    if name is None:
        return
    kind = rng.pick(list(GameKind))
    rule = RULE_OF.get(kind) or rng.pick([GameRule.STRATEGY, GameRule.CHANCE])
    game = GameRow(name=name, kind=kind, rule=rule, origin_entity_id=people.id, created_epoch=ctx.epoch, locked=[])
    ctx.session.add(game)
    await ctx.session.flush()
    ctx.session.add(GameFollowingRow(people_entity_id=people.id, game_id=game.id, adopted_epoch=ctx.epoch, locked=[]))
    tally.invented += 1
    await note(ctx, f"The {people.name} took to a new game, {name}.", key="games.invented", ids=[people.id])


async def neighbours(ctx: TickContext, people_id: int) -> list[int]:
    regions = {town.location_id for town in await towns_of(ctx, people_id) if town.location_id is not None}
    if not regions:
        return []
    found = await ctx.session.scalars(
        select(EntityRow.affiliated_entity_id)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(sorted(regions)))
        .order_by(EntityRow.affiliated_entity_id)
    )
    return sorted({item for item in found if item is not None and item != people_id})


async def spread(ctx: TickContext, row: GameFollowingRow, tally: GameTally) -> None:
    rng = ctx.rng(seed_of("game.spread", row.people_entity_id, row.game_id, ctx.epoch))
    if not rng.chance(ctx.rules.games.spread_chance):
        return
    targets = [item for item in await neighbours(ctx, row.people_entity_id) if not held(item)]
    targets = [item for item in targets if await ctx.session.get(GameFollowingRow, (item, row.game_id)) is None]
    if not targets:
        return
    ctx.session.add(GameFollowingRow(people_entity_id=rng.pick(targets), game_id=row.game_id, popularity=10, adopted_epoch=ctx.epoch, locked=[]))
    tally.spread += 1


async def play(ctx: TickContext, row: GameFollowingRow, game: GameRow, tally: GameTally) -> None:
    table = ctx.rules.games
    share = row.popularity / PERCENT
    towns = [town for town in await towns_of(ctx, row.people_entity_id) if not held(town.id)]
    if game.rule is GameRule.STRATEGY:
        ids = [town.id for town in towns]
        players = list(
            await ctx.session.scalars(
                select(EntityRow.id)
                .where(
                    EntityRow.entity_type == EntityType.MORTAL,
                    EntityRow.status == EntityStatus.CANON,
                    await present_among(ctx.session, ids),
                    EntityRow.social_class == SocialClass.NOBLE,
                )
                .order_by(EntityRow.id)
            )
        )
        officers = list(await ctx.session.scalars(select(OfficeRow.holder_entity_id).where(OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id)))
        seats = set(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.id.in_(officers), await present_among(ctx.session, ids))))
        for player in sorted(set(players) | seats):
            if held(player):
                continue
            for skill in (SkillKind.TACTICS, SkillKind.STRATEGY):
                if await practise_subject(ctx.session, ctx.rules, player, skill, subject_id=game.id, xp=table.strategy_xp * share, epoch=ctx.epoch):
                    tally.trained += 1
        return
    for town in towns:
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if game.rule is GameRule.CHANCE:
            shift_stat(town, "prosperity", -table.gamble_loss * share, low=0, high=PERCENT)
            if profile is not None and "crime" not in profile.locked:
                profile.crime = clamp_int(profile.crime + round_half_up(table.gamble_crime * share), 0, PERCENT)
            tally.gambled += 1
        elif profile is not None and "unrest" not in profile.locked:
            profile.unrest = clamp_int(profile.unrest - round_half_up(table.ball_contentment * share), 0, PERCENT)
            tally.played += 1


async def keep_games(ctx: TickContext, tally: GameTally) -> None:
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if not held(people.id):
            await invent(ctx, people, tally)
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(GameFollowingRow).order_by(GameFollowingRow.people_entity_id, GameFollowingRow.game_id))):
        game = await ctx.session.get(GameRow, row.game_id)
        if game is None or held(row.people_entity_id):
            continue
        if "popularity" not in row.locked:
            row.popularity = clamp_int(row.popularity + ctx.rules.games.popularity_gain, 0, PERCENT)
        await spread(ctx, row, tally)
        await play(ctx, row, game, tally)
    await ctx.session.flush()
