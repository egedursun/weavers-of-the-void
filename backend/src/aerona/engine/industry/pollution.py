from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.methods import METHODS, POLLUTANTS
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.economy import ProductionRunRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.industry import EnergyKind, Pollutant
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.engine.body.conditions import gain_condition
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.environment.book import add_scar
from aerona.engine.eras.effects import tech_factor
from aerona.engine.industry.energy import draw
from aerona.engine.industry.methods import reveres_nature
from aerona.engine.lore.research import has_technique
from aerona.engine.mortal.standing import add_stress
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation
from aerona.rules.registry import Rules

TENTH = 10
EVERY_KIND = "every_kind"
TEN_THOUSAND = 10000
RITE_DIVINE = 2


@dataclass
class PollutionTally:
    fouled: int = 0
    cleared: int = 0
    rites: int = 0
    blighted: int = 0
    turned: int = 0


def pollution_row(ctx: TickContext, book: EconomyBook, region_id: int) -> RegionPollutionRow:
    row = book.pollution.get(region_id)
    if row is None:
        row = RegionPollutionRow(region_node_id=region_id, air=0, water=0, soil=0, polluters={}, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        book.pollution[region_id] = row
    return row


def shift(row: RegionPollutionRow, pollutant: Pollutant, amount: float) -> int:
    if pollutant.value in row.locked or held(row.region_node_id):
        return 0
    before = int(getattr(row, pollutant.value))
    after = clamp_int(before + amount, 0, PERCENT)
    setattr(row, pollutant.value, after)
    return after - before


def worst(row: RegionPollutionRow | None) -> int:
    return max(int(getattr(row, pollutant.value)) for pollutant in Pollutant) if row is not None else 0


def level(row: RegionPollutionRow | None, pollutant: Pollutant) -> int:
    return int(getattr(row, pollutant.value)) if row is not None else 0


def sky_factor(rules: Rules, row: RegionPollutionRow | None) -> float:
    return 1 - level(row, Pollutant.LIGHT) * rules.pollution.light_harm / PERCENT / PERCENT


def fertility_factor(rules: Rules, row: RegionPollutionRow | None) -> float:
    return 1 - (row.soil if row is not None else 0) * rules.pollution.fertility_soil_pct / PERCENT / PERCENT


def fish_factor(rules: Rules, row: RegionPollutionRow | None) -> float:
    water = (row.water if row is not None else 0) * rules.pollution.fish_water_pct / PERCENT / PERCENT
    heat = (row.heat if row is not None else 0) * rules.pollution.heat_harm / PERCENT / PERCENT
    return max(0.0, 1 - water - heat)


def disease_extra(rules: Rules, row: RegionPollutionRow | None) -> int:
    if row is None:
        return 0
    table = rules.pollution
    return round_half_up(row.air * table.disease_air_pct / PERCENT + row.water * table.disease_water_pct / PERCENT)


def region_id_of(book: EconomyBook, community_id: int) -> int | None:
    region = book.ground.region_of(community_id)
    return region.entity_id if region is not None else None


async def foul_from_runs(ctx: TickContext, book: EconomyBook, tally: PollutionTally) -> dict[int, dict[int, int]]:
    rate = ctx.rules.pollution.per_batch_pct
    sources: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    runs = await ctx.session.scalars(select(ProductionRunRow).where(ProductionRunRow.epoch == ctx.epoch, ProductionRunRow.method.is_not(None)))
    for run in runs:
        region_id = region_id_of(book, run.community_entity_id)
        if region_id is None or run.method is None or run.quantity <= 0 or held(region_id):
            continue
        spec = METHODS[run.method]
        row = pollution_row(ctx, book, region_id)
        strict = await law_param(ctx.session, run.community_entity_id, LawKind.ENVIRONMENT_LAW, "strictness")
        aimed = await law_param(ctx.session, run.community_entity_id, LawKind.ENVIRONMENT_LAW, "pollutant")
        held_back = (int(strict) if isinstance(strict, int) else 0) * ctx.rules.pollution.law_cut_pct / PERCENT / PERCENT
        lowered = await tech_factor(ctx.session, ctx.rules, run.community_entity_id, EraChannel.POLLUTION)
        for pollutant in Pollutant:
            kept = (1 - held_back if aimed in (None, EVERY_KIND, pollutant.value) else 1) * lowered
            amount = spec.pollution(pollutant) * run.quantity * rate / PERCENT / TENTH * kept
            if amount:
                tally.fouled += max(0, shift(row, pollutant, amount))
        if spec.fouls:
            sources[region_id][run.community_entity_id] += round_half_up(spec.fouls * run.quantity / TENTH)
    return sources


async def foul_from_crowds(ctx: TickContext, book: EconomyBook, tally: PollutionTally) -> None:
    table = ctx.rules.pollution
    for community in book.communities:
        region_id = region_id_of(book, community.id)
        people = headcount(community)
        if region_id is None or people <= 0 or held(region_id):
            continue
        settlement = await ctx.session.get(SettlementProfileRow, community.id)
        clean = (settlement.sanitation if settlement is not None else 0) * table.sanitation_pct / PERCENT / PERCENT
        row = pollution_row(ctx, book, region_id)
        tally.fouled += max(0, shift(row, Pollutant.AIR, people * table.crowd_air_per_10000 / TEN_THOUSAND))
        tally.fouled += max(0, shift(row, Pollutant.WATER, people * table.crowd_water_per_10000 / TEN_THOUSAND * (1 - clean)))
        tally.fouled += max(0, shift(row, Pollutant.NOISE, people * table.crowd_noise_per_10000 / TEN_THOUSAND))
        if await has_technique(ctx.session, community.id, Technique.ELECTRIC_LIGHT):
            tally.fouled += max(0, shift(row, Pollutant.LIGHT, people * table.crowd_light_per_10000 / TEN_THOUSAND))


def recover(ctx: TickContext, book: EconomyBook, tally: PollutionTally) -> None:
    table = ctx.rules.pollution
    for region_id, row in book.pollution.items():
        land = book.ground.regions.get(region_id)
        boost = 1 + (land.forest_cover if land is not None else 0) * table.forest_recover_pct / PERCENT / PERCENT
        for pollutant, spec in POLLUTANTS.items():
            tally.cleared -= min(0, shift(row, pollutant, -int(getattr(table, spec.recover_rule)) * boost))
        row.epoch = ctx.epoch


async def rites(ctx: TickContext, book: EconomyBook, tally: PollutionTally) -> None:
    table = ctx.rules.pollution
    for community in book.communities:
        region_id = region_id_of(book, community.id)
        row = book.pollution.get(region_id) if region_id is not None else None
        if row is None or worst(row) < table.opinion_at or held(community.id) or not await reveres_nature(ctx, community.id):
            continue
        if draw(book, community.id, EnergyKind.DIVINE, RITE_DIVINE) < RITE_DIVINE:
            continue
        for pollutant in Pollutant:
            tally.cleared -= min(0, shift(row, pollutant, -table.rite_clean))
        tally.rites += 1


async def turn_against(ctx: TickContext, book: EconomyBook, sources: dict[int, dict[int, int]], tally: PollutionTally) -> None:
    table = ctx.rules.pollution
    for region_id, polluters in sorted(sources.items()):
        row = book.pollution.get(region_id)
        if row is None:
            continue
        row.polluters = {str(key): value for key, value in sorted(polluters.items())}
        if worst(row) < table.opinion_at:
            continue
        for community in book.communities:
            if region_id_of(book, community.id) != region_id or held(community.id) or not await reveres_nature(ctx, community.id):
                continue
            for polluter in sorted(polluters):
                if polluter == community.id:
                    continue
                await change_relation(ctx, community.id, polluter, table.opinion_shift, MemoryKind.ILL_WILL, note="fouled the land")
                tally.turned += 1


async def blight(ctx: TickContext, book: EconomyBook, tally: PollutionTally) -> None:
    table = ctx.rules.pollution
    for region_id, row in sorted(book.pollution.items()):
        land = book.ground.regions.get(region_id)
        if land is None or row.soil < table.blight_at or held(region_id):
            continue
        before = land.scars.get(ScarKind.BLIGHTED.value, 0)
        after = add_scar(land, ScarKind.BLIGHTED, table.blight_depth)
        if after > before:
            tally.blighted += 1
            if before == 0:
                await record(ctx, "industry.blight", roles={IncidentRole.SUBJECT: region_id}, facts={"soil": row.soil, "depth": after}, place=region_id)


async def tell_rises(ctx: TickContext, book: EconomyBook, before: dict[int, dict[Pollutant, int]]) -> None:
    mark = ctx.rules.pollution.rose_at
    for region_id, row in sorted(book.pollution.items()):
        for pollutant in Pollutant:
            now = level(row, pollutant)
            if before.get(region_id, {}).get(pollutant, 0) < mark <= now:
                await record(ctx, "pollution.rose", roles={IncidentRole.PLACE: region_id}, facts={"pollutant": pollutant, "level": now}, place=region_id)


async def harm_the_living(ctx: TickContext, book: EconomyBook, tally: PollutionTally) -> None:
    table = ctx.rules.pollution
    atlas = await RegionAtlas.load(ctx.session)
    for region_id, row in sorted(book.pollution.items()):
        if held(region_id):
            continue
        rays, din, glare = level(row, Pollutant.RADIATION), level(row, Pollutant.NOISE), level(row, Pollutant.LIGHT)
        if rays >= table.blight_at:
            land = book.ground.regions.get(region_id)
            if land is not None:
                add_scar(land, ScarKind.POISONED, table.radiation_scar)
        if rays or din:
            for mortal in await ctx.session.scalars(
                select(EntityRow)
                .where(
                    EntityRow.entity_type == EntityType.MORTAL,
                    EntityRow.status == EntityStatus.CANON,
                    EntityRow.location_id.in_(atlas.communities_in(region_id)),
                )
                .order_by(EntityRow.id)
            ):
                if held(mortal.id):
                    continue
                if din:
                    await add_stress(ctx.session, mortal.id, din * table.noise_harm / PERCENT, ctx.epoch)
                if rays:
                    await gain_condition(ctx, mortal, ConditionKind.CHRONIC_ILLNESS, HarmCause.RADIATION, chance=rays * table.radiation_harm / PERCENT)
        if glare:
            night = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.nocturnal.is_(True))
            for found in await ctx.session.scalars(
                select(SpeciesRangeRow)
                .where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.species_entity_id.in_(night))
                .order_by(SpeciesRangeRow.species_entity_id)
            ):
                if "abundance" not in found.locked and not held(found.species_entity_id):
                    found.abundance = clamp_int(found.abundance - round_half_up(found.abundance * glare * table.light_harm / PERCENT / PERCENT), 0, PERCENT)
                    tally.blighted += 1


async def tend_pollution(ctx: TickContext, book: EconomyBook, tally: PollutionTally) -> None:
    before = {region_id: {pollutant: level(row, pollutant) for pollutant in Pollutant} for region_id, row in book.pollution.items()}
    sources = await foul_from_runs(ctx, book, tally)
    await foul_from_crowds(ctx, book, tally)
    recover(ctx, book, tally)
    await rites(ctx, book, tally)
    await turn_against(ctx, book, sources, tally)
    await blight(ctx, book, tally)
    await harm_the_living(ctx, book, tally)
    await tell_rises(ctx, book, before)


async def void_scar(ctx: TickContext, entity_id: int) -> int:
    region_id = (await RegionAtlas.load(ctx.session)).top_region(entity_id)
    if region_id is None:
        return 0
    row = await ctx.session.get(RegionPollutionRow, region_id)
    if row is None:
        row = RegionPollutionRow(region_node_id=region_id, air=0, water=0, soil=0, polluters={}, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    amount = ctx.rules.pollution.void_rite
    return shift(row, Pollutant.AIR, amount) + shift(row, Pollutant.SOIL, amount)
