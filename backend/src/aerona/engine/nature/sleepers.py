from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.nature import Dormancy
from aerona.engine.context import TickContext
from aerona.engine.nature.seasons import activity, asleep, band_at, season_bands
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules


@dataclass
class SleeperTally:
    sleeping: int = 0
    woken: int = 0


def awake_now(profile: SpeciesProfileRow, epoch: int) -> bool:
    return profile.woken_epoch is not None and profile.woken_epoch >= epoch - 1


async def raid_factor(session: AsyncSession, rules: Rules, epoch: int, monster: EntityRow) -> float:
    profile = await session.get(SpeciesProfileRow, monster.id)
    if profile is None:
        return 1.0
    band = await band_at(session, rules, epoch, monster.id)
    if awake_now(profile, epoch):
        return rules.dormancy.woken_raid_pct / PERCENT * activity(rules, profile.thermoregulation, band)
    if asleep(profile.dormancy, band):
        return 0.0
    return activity(rules, profile.thermoregulation, band)


async def lair_factor(session: AsyncSession, rules: Rules, epoch: int, monster: EntityRow) -> float:
    profile = await session.get(SpeciesProfileRow, monster.id)
    if profile is None:
        return 1.0
    band = await band_at(session, rules, epoch, monster.id)
    sleeping = asleep(profile.dormancy, band) and not awake_now(profile, epoch)
    return activity(rules, profile.thermoregulation, band) / (1 + rules.dormancy.lair_hunt_pct / PERCENT if sleeping else 1)


async def keep_sleepers(ctx: TickContext, tally: SleeperTally) -> None:
    table = ctx.rules.dormancy
    atlas = await RegionAtlas.load(ctx.session)
    bands = await season_bands(ctx.session, ctx.rules, ctx.epoch)
    crowd: dict[int, int] = {}
    for profile in list(
        await ctx.session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.dormancy != Dormancy.NONE).order_by(SpeciesProfileRow.species_entity_id))
    ):
        if held(profile.species_entity_id):
            continue
        lands = await ctx.session.scalars(
            select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == profile.species_entity_id, SpeciesRangeRow.abundance > 0)
        )
        for region in sorted(lands):
            if not asleep(profile.dormancy, bands.get(region)):
                continue
            tally.sleeping += 1
            if region not in crowd:
                crowd[region] = sum(
                    stat(town, "population") or 0
                    for town in [await ctx.session.get(EntityRow, item) for item in atlas.communities_in(region)]
                    if town is not None
                )
            if profile.aggression < table.disturb_aggression or crowd[region] < table.disturb_population or "woken_epoch" in profile.locked:
                continue
            if ctx.rng(seed_of("dormancy.disturb", profile.species_entity_id, region, ctx.epoch)).chance(table.disturb_chance):
                profile.woken_epoch = ctx.epoch
                tally.woken += 1
                break
    await ctx.session.flush()
