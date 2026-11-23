from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.long_seasons import northern
from aerona.constants.units import PERCENT
from aerona.db.tables.ages import IrregularSeasonRow, WinterForecastRow
from aerona.db.tables.agrarian import FamineLoreRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import LongSeasonReach, SeasonCause, SeasonSpell, SeasonSpellShape
from aerona.domain.enums.crafts import AssistiveAid, InsuranceCover
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import Commodity, NaturalLaw
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.crafts.aiding import aid_quality
from aerona.engine.crafts.cover import insured_loss
from aerona.engine.crafts.reckoning import fine_division, numeracy_of
from aerona.engine.environment.spells import SpellPull, SpellSources, begin_spell, pull_of, spells_of
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.recording.record import record

HUNDREDTHS = 100
CYCLING_CAUSES = (SeasonCause.NATURAL_LAW, SeasonCause.ORBIT)


@dataclass
class SeasonTally:
    turned: int = 0
    winters: int = 0
    starved: int = 0
    forecasts: int = 0
    heeded: int = 0
    settled: int = 0


def chaotic(ctx: TickContext, physics: WorldPhysicsRow | None) -> bool:
    if physics is None:
        return False
    table = ctx.rules.long_seasons
    threshold = table.chaos_eccentricity / HUNDREDTHS
    return physics.eccentricity >= threshold or (physics.circumbinary and physics.eccentricity >= threshold / 2)


def roll_length(ctx: TickContext, row: IrregularSeasonRow) -> int:
    table = ctx.rules.long_seasons
    return ctx.rng(f"season.length.{row.world_id}.{row.id}.{ctx.epoch}").integer(table.shortest_spell, table.longest_spell)


async def begin(
    ctx: TickContext, world: WorldRow, cause: SeasonCause, by_node_id: int | None, shape: SeasonSpellShape = SeasonSpellShape.CYCLING
) -> IrregularSeasonRow:
    table = ctx.rules.long_seasons
    rng = ctx.rng(f"season.begin.{world.id}.{cause.value}.{ctx.epoch}")
    return await begin_spell(
        ctx,
        world,
        cause,
        shape=shape,
        spell=SeasonSpell.SUMMER if shape is SeasonSpellShape.CYCLING else SeasonSpell.WINTER,
        length=rng.integer(table.shortest_spell, table.longest_spell),
        severity=rng.integer(table.mildest, PERCENT),
        by_node_id=by_node_id,
    )


async def find_irregular(ctx: TickContext, tally: SeasonTally) -> None:
    known = {(row.world_id, row.cause) for row in await ctx.session.scalars(select(IrregularSeasonRow).order_by(IrregularSeasonRow.id))}
    laws = await ctx.laws()
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if held(world.id):
            continue
        causes = [
            cause
            for cause, present in (
                (SeasonCause.NATURAL_LAW, laws.has(NaturalLaw.LONG_SEASONS, world.id)),
                (SeasonCause.ORBIT, chaotic(ctx, await ctx.session.get(WorldPhysicsRow, world.id))),
            )
            if present and (world.id, cause) not in known
        ]
        for cause in causes:
            row = await begin(ctx, world, cause, None)
            tally.turned += 1
            await record(
                ctx,
                "seasons.irregular",
                roles={IncidentRole.SUBJECT: world.id},
                facts={"cause": cause, "length": row.spell_length, "severity": row.severity},
                world_id=world.id,
            )


async def turn(ctx: TickContext, world: WorldRow, row: IrregularSeasonRow, tally: SeasonTally) -> None:
    if row.shape is not SeasonSpellShape.CYCLING or ctx.epoch - row.spell_started_epoch < row.spell_length or "spell" in row.locked:
        return
    row.spell = SeasonSpell.WINTER if row.spell is SeasonSpell.SUMMER else SeasonSpell.SUMMER
    row.spell_started_epoch = ctx.epoch
    if "spell_length" not in row.locked:
        row.spell_length = roll_length(ctx, row)
    tally.turned += 1
    if row.spell is SeasonSpell.WINTER:
        tally.winters += 1
    await record(
        ctx,
        "seasons.winter" if row.spell is SeasonSpell.WINTER else "seasons.summer",
        roles={IncidentRole.SUBJECT: world.id},
        facts={"length": row.spell_length, "severity": row.severity},
        world_id=world.id,
    )


async def region_spells(ctx: TickContext, env: RegionEnvironmentRow) -> SpellPull:
    region = await ctx.session.get(EntityRow, env.entity_id)
    return pull_of(ctx.rules, await spells_of(ctx, env.world_id), env.latitude, region.map_y if region is not None else None)


async def winter_share(ctx: TickContext, env: RegionEnvironmentRow) -> int:
    table = ctx.rules.long_seasons
    pull = await region_spells(ctx, env)
    share = PERCENT - pull.winter * table.winter_harvest_pct // PERCENT
    if pull.summer:
        settings = ctx.rules.weather
        if env.temperature >= settings.hot_threshold or env.rainfall < settings.dry_threshold:
            share -= pull.summer * table.summer_harvest_pct // PERCENT
        elif env.temperature < settings.cold_threshold:
            share += pull.summer * table.summer_cold_gain_pct // PERCENT
    return clamp_int(share, 0, PERCENT * 2)


async def scholar_of(ctx: TickContext, people_id: int) -> tuple[EntityRow, int] | None:
    found = await ctx.session.execute(
        select(EntityRow, SkillRow.level)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, SkillRow.skill == SkillKind.ASTRONOMY)
        .order_by(SkillRow.level.desc(), EntityRow.id)
    )
    homes = set(await towns_of_people(ctx.session, people_id))
    for mortal, level in found:
        if mortal.location_id in homes and level >= ctx.rules.long_seasons.scholar_skill:
            return mortal, int(level)
    return None


async def watched_source(ctx: TickContext, row: IrregularSeasonRow, people_id: int) -> bool:
    if row.shape is not SeasonSpellShape.SINGLE or row.source_region_id is None:
        return row.shape is SeasonSpellShape.SINGLE and (row.source_impact_id is not None or row.source_star_id is not None)
    homes = set(await towns_of_people(ctx.session, people_id))
    towns = await ctx.session.scalars(select(EntityRow.location_id).where(EntityRow.id.in_(sorted(homes))))
    return row.source_region_id in set(towns)


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
        rng = ctx.rng(f"season.forecast.{people.id}.{row.id}.{ctx.epoch}")
        sharpened = (
            1
            - await numeracy_of(ctx.session, ctx.rules, people.id)
            * ctx.rules.numeracy.forecast_pct
            / PERCENT
            / PERCENT
            * await fine_division(ctx.session, ctx.rules, people.id)
            - await aid_quality(ctx.session, scholar.id, AssistiveAid.TELESCOPE) * ctx.rules.aids.telescope_forecast_pct / PERCENT / PERCENT
        )
        if await watched_source(ctx, row, people.id):
            sharpened *= (PERCENT - table.forecast_known_source_pct) / PERCENT
        error = max(0, round_half_up((table.scholar_error - level) * max(0.0, sharpened)))
        predicted = end + rng.integer(-error, error)
        heeded = rng.chance(clamp_int(table.heed_base + level * table.heed_per_level, 0, PERCENT))
        existing = await ctx.session.scalar(
            select(WinterForecastRow).where(WinterForecastRow.long_season_id == row.id, WinterForecastRow.people_entity_id == people.id)
        )
        if existing is None:
            existing = WinterForecastRow(long_season_id=row.id, world_id=world.id, people_entity_id=people.id, locked=[])
            ctx.session.add(existing)
            await record(
                ctx,
                "seasons.forecast_made",
                roles={IncidentRole.SUBJECT: world.id, IncidentRole.ACTOR: scholar.id, IncidentRole.BENEFICIARY: people.id},
                facts={"predicted": max(ctx.epoch, predicted)},
                world_id=world.id,
            )
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


async def prepared(ctx: TickContext, row: IrregularSeasonRow, town: EntityRow) -> bool:
    folk = await people_id_of(ctx.session, town)
    if folk is None:
        return False
    found = await ctx.session.scalar(select(WinterForecastRow).where(WinterForecastRow.long_season_id == row.id, WinterForecastRow.people_entity_id == folk))
    return found is not None and found.heeded


async def eased(ctx: TickContext, town: EntityRow, loss_pct: int) -> int:
    folk = await people_id_of(ctx.session, town)
    lore = await ctx.session.get(FamineLoreRow, folk) if folk is not None else None
    if lore is None:
        return loss_pct
    table = ctx.rules.long_seasons
    loss_pct = loss_pct * (PERCENT - lore.storage * table.storage_ease_pct // PERCENT) // PERCENT
    return loss_pct * table.famine_foods_share // PERCENT if lore.famine_foods else loss_pct


async def bite(ctx: TickContext, world: WorldRow, rows: list[IrregularSeasonRow], tally: SeasonTally) -> None:
    table = ctx.rules.long_seasons
    winters = [row for row in rows if row.spell is SeasonSpell.WINTER]
    if not winters:
        return
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world.id)
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        ground = await ctx.session.get(RegionEnvironmentRow, town.location_id) if town.location_id is not None else None
        region = await ctx.session.get(EntityRow, town.location_id) if town.location_id is not None else None
        pull = pull_of(ctx.rules, winters, ground.latitude if ground is not None else 0, region.map_y if region is not None else None)
        if pull.winter <= 0:
            continue
        food = await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD)
        loss_pct = pull.winter * table.winter_loss_pct // PERCENT
        if any([await prepared(ctx, row, town) for row in winters]):
            loss_pct = loss_pct * table.prepared_share // PERCENT
        loss_pct = await eased(ctx, town, loss_pct)
        loss = round_half_up(food * loss_pct / PERCENT)
        if loss > 0 and await shift_stock(ctx.session, ctx.rules, town.id, Commodity.FOOD, -loss, epoch=ctx.epoch, flow=GoodsFlow.LOSS):
            tally.starved += 1
            await insured_loss(ctx, town.id, InsuranceCover.CROP, loss * ctx.rules.insurance.crop_payout_pct // PERCENT)


async def summer_drought(ctx: TickContext, world: WorldRow, rows: list[IrregularSeasonRow]) -> None:
    summers = [row for row in rows if row.spell is SeasonSpell.SUMMER and row.shape is SeasonSpellShape.SINGLE]
    if not summers:
        return
    lost = max(row.severity * ctx.rules.long_seasons.summer_harvest_pct // PERCENT for row in summers)
    await record(ctx, "seasons.summer_drought", roles={IncidentRole.SUBJECT: world.id}, facts={"lost": lost}, world_id=world.id)


async def lost_cause(ctx: TickContext, world: WorldRow, row: IrregularSeasonRow) -> bool:
    if "spell" in row.locked or "spell_length" in row.locked:
        return False
    if row.shape is SeasonSpellShape.SINGLE:
        return ctx.epoch - row.spell_started_epoch >= row.spell_length
    if row.spell is SeasonSpell.WINTER:
        return False
    if row.cause is SeasonCause.NATURAL_LAW:
        return not (await ctx.laws()).has(NaturalLaw.LONG_SEASONS, world.id)
    if row.cause is SeasonCause.ORBIT:
        return not chaotic(ctx, await ctx.session.get(WorldPhysicsRow, world.id))
    return False


async def end_spell(ctx: TickContext, world: WorldRow, row: IrregularSeasonRow, tally: SeasonTally) -> None:
    for forecast_row in await ctx.session.scalars(select(WinterForecastRow).where(WinterForecastRow.long_season_id == row.id).order_by(WinterForecastRow.id)):
        await ctx.session.delete(forecast_row)
    await ctx.session.flush()
    await ctx.session.delete(row)
    tally.settled += 1
    await record(ctx, "seasons.spell_ended", roles={IncidentRole.SUBJECT: world.id}, facts={"cause": row.cause, "spell": row.spell}, world_id=world.id)
    if row.cause in CYCLING_CAUSES:
        await record(ctx, "seasons.settled", roles={IncidentRole.SUBJECT: world.id}, facts={"cause": row.cause}, world_id=world.id)


async def keep_seasons(ctx: TickContext, tally: SeasonTally) -> None:
    await find_irregular(ctx, tally)
    worlds = sorted(set(await ctx.session.scalars(select(IrregularSeasonRow.world_id))))
    for world_id in worlds:
        world = await ctx.session.get(WorldRow, world_id)
        if world is None or held(world.id):
            continue
        live: list[IrregularSeasonRow] = []
        for row in await spells_of(ctx, world.id):
            if await lost_cause(ctx, world, row):
                await end_spell(ctx, world, row, tally)
                continue
            await turn(ctx, world, row, tally)
            await forecast(ctx, world, row, tally)
            live.append(row)
        await bite(ctx, world, live, tally)
        await summer_drought(ctx, world, live)
    await ctx.session.flush()


async def single_winter(
    ctx: TickContext, world: WorldRow, cause: SeasonCause, *, length: int, severity: int, reach: LongSeasonReach, sources: SpellSources
) -> IrregularSeasonRow:
    return await begin_spell(
        ctx, world, cause, shape=SeasonSpellShape.SINGLE, spell=SeasonSpell.WINTER, length=length, severity=severity, reach=reach, sources=sources
    )


async def stellar_spells(ctx: TickContext, cosmography: Cosmography, changes: dict[int, tuple[int, int]]) -> int:
    table = ctx.rules.long_seasons
    begun = 0
    for star_id, (before, after) in sorted(changes.items()):
        if before <= 0 or before == after:
            continue
        change = (after - before) * PERCENT // before
        if -change < table.stellar_dim_pct and change < table.stellar_bright_pct:
            continue
        spell = SeasonSpell.WINTER if change < 0 else SeasonSpell.SUMMER
        for world in sorted(cosmography.worlds.values(), key=lambda row: row.id):
            star = cosmography.place_world(world).star
            if star is None or star.id != star_id or held(world.id):
                continue
            ongoing = await ctx.session.scalar(
                select(IrregularSeasonRow.id)
                .where(IrregularSeasonRow.world_id == world.id, IrregularSeasonRow.source_star_id == star_id, IrregularSeasonRow.spell == spell)
                .limit(1)
            )
            if ongoing is not None:
                continue
            rng = ctx.rng(f"stellar_spell.{world.id}.{star_id}")
            await begin_spell(
                ctx,
                world,
                SeasonCause.STELLAR,
                shape=SeasonSpellShape.SINGLE,
                spell=spell,
                length=rng.integer(table.shortest_spell, table.longest_spell),
                severity=min(PERCENT, abs(change) * PERCENT // max(1, table.stellar_dim_pct if spell is SeasonSpell.WINTER else table.stellar_bright_pct) // 2),
                sources=SpellSources(star_id=star_id),
            )
            begun += 1
    return begun


async def impact_spell(ctx: TickContext, world: WorldRow, impact_id: int, size: int, epochs: int) -> IrregularSeasonRow | None:
    table = ctx.rules.long_seasons
    if size < table.impact_size_min or epochs <= 0:
        return None
    known = await ctx.session.scalar(select(IrregularSeasonRow.id).where(IrregularSeasonRow.source_impact_id == impact_id).limit(1))
    if known is not None:
        return None
    return await single_winter(
        ctx,
        world,
        SeasonCause.IMPACT,
        length=epochs,
        severity=size * table.impact_severity_per_size_pct // PERCENT,
        reach=LongSeasonReach.WORLD,
        sources=SpellSources(impact_id=impact_id),
    )


async def eruption_spell(ctx: TickContext, world: WorldRow, region: EntityRow, strength: int) -> IrregularSeasonRow | None:
    table = ctx.rules.long_seasons
    if strength < table.eruption_strength_min:
        return None
    reach = LongSeasonReach.WORLD if strength >= table.eruption_world_strength else (LongSeasonReach.NORTH if northern(region.map_y) else LongSeasonReach.SOUTH)
    length = ctx.rng(f"eruption_spell.{region.id}.{ctx.epoch}").integer(table.eruption_length_min, table.eruption_length_max)
    return await single_winter(
        ctx,
        world,
        SeasonCause.ERUPTION,
        length=length,
        severity=strength * table.eruption_severity_pct // PERCENT,
        reach=reach,
        sources=SpellSources(region_id=region.id),
    )


async def current_spell(ctx: TickContext, world: WorldRow, region: EntityRow, warmer: bool) -> IrregularSeasonRow | None:
    table = ctx.rules.long_seasons
    if not ctx.rng(f"current_spell.{region.id}.{ctx.epoch}").chance(table.ocean_shift_pct):
        return None
    length = ctx.rng(f"current_spell_length.{region.id}.{ctx.epoch}").integer(table.shortest_spell, table.longest_spell)
    reach = LongSeasonReach.NORTH if northern(region.map_y) else LongSeasonReach.SOUTH
    return await begin_spell(
        ctx,
        world,
        SeasonCause.OCEAN_SHIFT,
        shape=SeasonSpellShape.SINGLE,
        spell=SeasonSpell.SUMMER if warmer else SeasonSpell.WINTER,
        length=length,
        severity=table.mildest,
        reach=reach,
        sources=SpellSources(region_id=region.id),
    )


async def made_spell(ctx: TickContext, world: WorldRow, *, winter: bool, severity: int, incident_id: int | None) -> IrregularSeasonRow | None:
    table = ctx.rules.long_seasons
    spell = SeasonSpell.WINTER if winter else SeasonSpell.SUMMER
    ongoing = await ctx.session.scalar(
        select(IrregularSeasonRow.id)
        .where(IrregularSeasonRow.world_id == world.id, IrregularSeasonRow.cause == SeasonCause.MADE, IrregularSeasonRow.spell == spell)
        .limit(1)
    )
    if ongoing is not None or held(world.id):
        return None
    length = ctx.rng(f"made_spell.{world.id}.{ctx.epoch}").integer(table.shortest_spell, table.longest_spell)
    return await begin_spell(
        ctx,
        world,
        SeasonCause.MADE,
        shape=SeasonSpellShape.SINGLE,
        spell=spell,
        length=length,
        severity=severity,
        sources=SpellSources(incident_id=incident_id),
    )
