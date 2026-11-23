from sqlalchemy import or_, select

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.season_shape import season_of_index

BATTLE_FIXUP = "environment.battle_ground"


async def backfill_battle_ground(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, BATTLE_FIXUP) is not None:
        return 0
    statement = select(BattleRow).where(
        or_(BattleRow.terrain.is_(None), BattleRow.year.is_(None), BattleRow.season_name.is_(None), BattleRow.weather.is_(None))
    )
    battles = list(await ctx.session.scalars(statement.order_by(BattleRow.id)))
    book = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    years = ctx.rules.time.years_per_epoch
    filled = 0
    for battle in battles:
        place = book.place_of(battle.place_entity_id)
        region = book.region_of(battle.place_entity_id or battle.winner_entity_id)
        if battle.year is None:
            battle.year = epoch_start_year(battle.epoch, years) + ctx.environment.rng(f"battle_year.{battle.id}").below(years)
        if region is None:
            continue
        seasons = book.seasons_of(region.world_id)
        season = season_of_index(seasons, battle.year)
        if battle.terrain is None:
            battle.terrain = place.terrain if place is not None and place.terrain is not None else region.dominant_terrain
        if battle.season_name is None and season is not None:
            battle.season_name = season.name
        if battle.weather is None:
            battle.weather = book.weather(ctx.environment.world_seed, battle.epoch, region, season, f"battle.{battle.id}").kind
        filled += 1
    ctx.session.add(AppliedFixupRow(key=BATTLE_FIXUP, result={"battles": filled}))
    await ctx.session.flush()
    return filled
