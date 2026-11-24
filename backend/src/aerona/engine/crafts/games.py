from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.crafts import GameRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kind_crafts import GameCategory
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.mortal.learning import practise_subject
from aerona.engine.primitives.folk import present_among, towns_of_people
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import StepDraft, record
from aerona.language.generator import NameKind


@dataclass(frozen=True)
class GameShape:
    skill: SkillKind | None
    chance_share: int
    violence: int
    team_size: int
    betting: int
    spectators: int


C = GameCategory
SHAPES: Mapping[GameCategory, GameShape] = total(
    GameCategory,
    {
        C.BOARD: GameShape(SkillKind.STRATEGY, 10, 0, 1, 20, 10),
        C.CHANCE: GameShape(None, 90, 0, 1, 70, 10),
        C.CARD: GameShape(SkillKind.DECEPTION, 50, 0, 1, 60, 10),
        C.BALL: GameShape(SkillKind.LEADERSHIP, 20, 30, 7, 30, 60),
        C.RACING: GameShape(SkillKind.RIDING, 30, 20, 1, 50, 70),
        C.COMBAT_SPORT: GameShape(SkillKind.UNARMED, 10, 70, 1, 40, 60),
        C.ATHLETIC: GameShape(None, 10, 10, 1, 20, 50),
        C.HUNTING_SPORT: GameShape(SkillKind.BOW, 20, 40, 4, 10, 20),
        C.WIT: GameShape(SkillKind.ORATORY, 10, 0, 1, 10, 30),
        C.TEAM: GameShape(SkillKind.TACTICS, 20, 30, 11, 30, 70),
        C.SPECTACLE: GameShape(None, 30, 40, 2, 50, 90),
        C.GAMBLING: GameShape(None, 95, 0, 1, 95, 20),
        C.NETWORK: GameShape(SkillKind.STRATEGY, 20, 0, 4, 20, 40),
        C.PUZZLE: GameShape(SkillKind.CRYPTOGRAPHY, 5, 0, 1, 5, 10),
        C.ANIMAL_CONTEST: GameShape(SkillKind.BEAST_HANDLING, 40, 50, 1, 60, 80),
    },
)


@dataclass
class GameTally:
    invented: int = 0
    shaped: int = 0
    trained: int = 0
    gambled: int = 0
    played: int = 0


async def towns_of(ctx: TickContext, people_id: int) -> list[EntityRow]:
    return list(await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(await towns_of_people(ctx.session, people_id))).order_by(EntityRow.id)))


def shaped(name: str, category: GameCategory, origin: EntityRow, epoch: int) -> GameRow:
    shape = SHAPES[category]
    return GameRow(
        name=name,
        category=category,
        origin_node_id=origin.id,
        world_id=origin.world_id,
        skill=shape.skill,
        chance_share=shape.chance_share,
        violence=shape.violence,
        team_size=shape.team_size,
        betting=shape.betting,
        spectators=shape.spectators,
        created_epoch=epoch,
        locked=[],
    )


def made_by(game: GameRow, people_id: int, epoch: int) -> KindHoldingRow:
    return KindHoldingRow(
        concept=KindConcept.GAME,
        kind_id=game.id,
        holder_node_id=people_id,
        stance=KindStance.MAKES,
        strength=PERCENT // 2,
        spread=KindSpread.INVENTED,
        since_epoch=epoch,
        locked=[],
    )


async def invent(ctx: TickContext, people: EntityRow, tally: GameTally) -> None:
    if await ctx.session.scalar(select(GameRow.id).where(GameRow.origin_node_id == people.id).limit(1)) is not None:
        return
    rng = ctx.rng(seed_of("game", people.id, ctx.epoch))
    if not rng.chance(ctx.rules.games.invent_chance):
        return
    name = await Namer(ctx.session, ctx.rules).from_speaker(people.id, seed_of("game.name", people.id, ctx.epoch), NameKind.GENERAL)
    if name is None:
        return
    game = shaped(name, rng.pick(list(GameCategory)), people, ctx.epoch)
    ctx.session.add(game)
    await ctx.session.flush()
    ctx.session.add(made_by(game, people.id, ctx.epoch))
    tally.invented += 1
    await record(
        ctx,
        "games.invented",
        roles={IncidentRole.MAKER: people.id},
        facts={"game": name, "category": game.category},
        steps=(StepDraft(StepAction.SHAPE, actor=people.id),),
    )


async def neighbours(ctx: TickContext, people_id: int) -> list[int]:
    regions = {town.location_id for town in await towns_of(ctx, people_id) if town.location_id is not None}
    if not regions:
        return []
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(sorted(regions)))
        .order_by(EntityRow.id)
    )
    folks = {await people_id_of(ctx.session, town) for town in list(found)}
    return sorted(item for item in folks if item is not None and item != people_id)


async def players_of(ctx: TickContext, towns: list[EntityRow]) -> list[int]:
    ids = [town.id for town in towns]
    nobles = list(
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
    return sorted(set(nobles) | seats)


async def play(ctx: TickContext, row: KindHoldingRow, game: GameRow, tally: GameTally) -> None:
    table = ctx.rules.games
    share = row.strength / PERCENT
    towns = [town for town in await towns_of(ctx, row.holder_node_id) if not held(town.id)]
    skilled = share * (PERCENT - game.chance_share) / PERCENT
    if game.skill is not None and skilled > 0:
        for player in await players_of(ctx, towns):
            if held(player):
                continue
            if await practise_subject(ctx.session, ctx.rules, player, game.skill, subject_id=game.id, xp=table.strategy_xp * skilled, epoch=ctx.epoch):
                tally.trained += 1
    wager = share * game.chance_share * game.betting / PERCENT / PERCENT
    crowd = share * game.spectators / PERCENT
    for town in towns:
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if wager > 0:
            shift_stat(town, "prosperity", -table.gamble_loss * wager, low=0, high=PERCENT)
            if profile is not None and "crime" not in profile.locked:
                profile.crime = clamp_int(profile.crime + round_half_up(table.gamble_crime * wager), 0, PERCENT)
            tally.gambled += 1
        if crowd > 0 and profile is not None and "unrest" not in profile.locked:
            profile.unrest = clamp_int(profile.unrest - round_half_up(table.ball_contentment * crowd), 0, PERCENT)
            tally.played += 1


async def played_games(ctx: TickContext) -> list[tuple[KindHoldingRow, GameRow]]:
    found = await ctx.session.execute(
        select(KindHoldingRow, GameRow)
        .join(GameRow, GameRow.id == KindHoldingRow.kind_id)
        .where(KindHoldingRow.concept == KindConcept.GAME, KindHoldingRow.stance.in_([KindStance.MAKES, KindStance.USES, KindStance.FAVOURS]))
        .where(GameRow.retired.is_(False))
        .order_by(KindHoldingRow.holder_node_id, KindHoldingRow.kind_id)
    )
    return [(row, game) for row, game in found.all()]


LEGACY_SHAPES = "games.legacy_shapes"
DEFAULT_SHAPE = (30, 0, 1, 10, 20)


async def shape_legacy_games(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, LEGACY_SHAPES) is not None:
        return 0
    shaped_count = 0
    for game in list(await ctx.session.scalars(select(GameRow).order_by(GameRow.id))):
        if (game.chance_share, game.violence, game.team_size, game.betting, game.spectators) != DEFAULT_SHAPE or game.locked:
            continue
        shape = SHAPES[game.category]
        game.skill, game.chance_share, game.violence = shape.skill, shape.chance_share, shape.violence
        game.team_size, game.betting, game.spectators = shape.team_size, shape.betting, shape.spectators
        shaped_count += 1
    ctx.session.add(AppliedFixupRow(key=LEGACY_SHAPES, result={"shaped": shaped_count}))
    await ctx.session.flush()
    return shaped_count


async def keep_games(ctx: TickContext, tally: GameTally) -> None:
    tally.shaped += await shape_legacy_games(ctx)
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if not held(people.id):
            await invent(ctx, people, tally)
    await ctx.session.flush()
    for row, game in await played_games(ctx):
        if held(row.holder_node_id) or await ctx.session.get(EntityRow, row.holder_node_id) is None:
            continue
        await play(ctx, row, game, tally)
    await ctx.session.flush()
