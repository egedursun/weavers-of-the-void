from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.ages import IrregularSeasonRow, WinterForecastRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import SeasonCause, SeasonSpell
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import Commodity
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.society import shift_stock, stock

HUNDREDTHS = 100


@dataclass
class SeasonTally:
    turned: int = 0
    winters: int = 0
    starved: int = 0
    forecasts: int = 0
    heeded: int = 0


def chaotic(ctx: TickContext, physics: WorldPhysicsRow | None) -> bool:
    if physics is None:
        return False
    table = ctx.rules.long_seasons
    threshold = table.chaos_eccentricity / HUNDREDTHS
    return physics.eccentricity >= threshold or (physics.circumbinary and physics.eccentricity >= threshold / 2)


def roll_length(ctx: TickContext, row: IrregularSeasonRow) -> int:
    table = ctx.rules.long_seasons
    return ctx.rng(f"season.length.{row.world_id}.{ctx.epoch}").integer(table.shortest_spell, table.longest_spell)


async def begin(ctx: TickContext, world: WorldRow, cause: SeasonCause, by_node_id: int | None) -> IrregularSeasonRow:
    row = IrregularSeasonRow(world_id=world.id, cause=cause, spell=SeasonSpell.SUMMER, spell_started_epoch=ctx.epoch, by_node_id=by_node_id, locked=[])
    row.spell_length = roll_length(ctx, row)
    row.severity = ctx.rng(f"season.severity.{world.id}").integer(ctx.rules.long_seasons.mildest, PERCENT)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def find_irregular(ctx: TickContext, tally: SeasonTally) -> None:
    known = set(await ctx.session.scalars(select(IrregularSeasonRow.world_id)))
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if world.id in known or held(world.id):
            continue
        if chaotic(ctx, await ctx.session.get(WorldPhysicsRow, world.id)):
            await begin(ctx, world, SeasonCause.ORBIT, None)
            tally.turned += 1
            await note(
                ctx,
                f"The seasons of {world.name} lost their measure; its summers and winters now run for years of no set length.",
                key="seasons.irregular",
                world_id=world.id,
            )


async def turn(ctx: TickContext, world: WorldRow, row: IrregularSeasonRow, tally: SeasonTally) -> None:
    if ctx.epoch - row.spell_started_epoch < row.spell_length or "spell" in row.locked:
        return
    row.spell = SeasonSpell.WINTER if row.spell is SeasonSpell.SUMMER else SeasonSpell.SUMMER
    row.spell_started_epoch = ctx.epoch
    if "spell_length" not in row.locked:
        row.spell_length = roll_length(ctx, row)
    tally.turned += 1
    if row.spell is SeasonSpell.WINTER:
        tally.winters += 1
        await note(ctx, f"A long winter fell on {world.name}.", key="seasons.winter", world_id=world.id)
    else:
        await note(ctx, f"The long winter of {world.name} broke.", key="seasons.summer", world_id=world.id)


async def scholar_of(ctx: TickContext, people_id: int) -> tuple[EntityRow, int] | None:
    found = await ctx.session.execute(
        select(EntityRow, SkillRow.level)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, SkillRow.skill == SkillKind.ASTRONOMY)
        .order_by(SkillRow.level.desc(), EntityRow.id)
    )
    for mortal, level in found:
        town = await ctx.session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
        if town is not None and town.affiliated_entity_id == people_id and level >= ctx.rules.long_seasons.scholar_skill:
            return mortal, int(level)
    return None


async def forecast(ctx: TickContext, world: WorldRow, row: IrregularSeasonRow, tally: SeasonTally) -> None:
    table = ctx.rules.long_seasons
    peoples = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world.id)
        .order_by(EntityRow.id)
    )
    end = row.spell_started_epoch + row.spell_length
    for people in list(peoples):
        if held(people.id):
            continue
        found = await scholar_of(ctx, people.id)
        if found is None:
            continue
        scholar, level = found
        rng = ctx.rng(f"season.forecast.{people.id}.{ctx.epoch}")
        error = max(0, table.scholar_error - level)
        predicted = end + rng.integer(-error, error)
        heeded = rng.chance(clamp_int(table.heed_base + level * table.heed_per_level, 0, PERCENT))
        existing = await ctx.session.scalar(
            select(WinterForecastRow).where(WinterForecastRow.world_id == world.id, WinterForecastRow.people_entity_id == people.id)
        )
        if existing is None:
            existing = WinterForecastRow(world_id=world.id, people_entity_id=people.id, locked=[])
            ctx.session.add(existing)
        if "predicted_end_epoch" not in existing.locked:
            existing.predicted_end_epoch = max(ctx.epoch, predicted)
        if "scholar_entity_id" not in existing.locked:
            existing.scholar_entity_id = scholar.id
        if "heeded" not in existing.locked:
            existing.heeded = heeded
        existing.made_epoch = ctx.epoch
        tally.forecasts += 1
        tally.heeded += heeded
    await ctx.session.flush()


async def prepared(ctx: TickContext, world_id: int, town: EntityRow) -> bool:
    if town.affiliated_entity_id is None:
        return False
    row = await ctx.session.scalar(
        select(WinterForecastRow).where(WinterForecastRow.world_id == world_id, WinterForecastRow.people_entity_id == town.affiliated_entity_id)
    )
    return row is not None and row.heeded


async def bite(ctx: TickContext, world: WorldRow, row: IrregularSeasonRow, tally: SeasonTally) -> None:
    table = ctx.rules.long_seasons
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world.id)
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        food = await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD)
        loss_pct = row.severity * table.winter_loss_pct // PERCENT
        if await prepared(ctx, world.id, town):
            loss_pct = loss_pct * table.prepared_share // PERCENT
        loss = round_half_up(food * loss_pct / PERCENT)
        if loss > 0 and await shift_stock(ctx.session, ctx.rules, town.id, Commodity.FOOD, -loss, epoch=ctx.epoch, flow=GoodsFlow.LOSS):
            tally.starved += 1


async def keep_seasons(ctx: TickContext, tally: SeasonTally) -> None:
    await find_irregular(ctx, tally)
    for row in list(await ctx.session.scalars(select(IrregularSeasonRow).order_by(IrregularSeasonRow.world_id))):
        world = await ctx.session.get(WorldRow, row.world_id)
        if world is None or held(world.id):
            continue
        await turn(ctx, world, row, tally)
        await forecast(ctx, world, row, tally)
        if row.spell is SeasonSpell.WINTER:
            await bite(ctx, world, row, tally)
    await ctx.session.flush()
