from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import rebalance_classes, reconcile, seed
from aerona.engine.demography.labour import allocate
from aerona.engine.demography.mobility import class_mobility, desertion, ennoble_heroes, ruin_merchants
from aerona.engine.demography.peoples import culture_for, ensure_profiles, refresh_culture
from aerona.engine.demography.promotion import doze, promote, sync_veterans
from aerona.engine.disease.emergence import WET
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat

COLD = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})


async def region_of(ctx: TickContext, atlas: RegionAtlas, community: EntityRow) -> RegionEnvironmentRow | None:
    region = atlas.top_region(community.id)
    return await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None


@reads(
    "people.population",
    "settlement.population",
    "table.community_cohorts",
    "table.community_societies",
    "table.culture_values",
    "table.entity_flags",
    "table.incident_participants",
    "table.incidents",
    "table.maimed_cohorts",
    "table.outbreaks",
    "table.people_biology",
    "table.people_culture",
    "table.region_environment",
    "table.world_maps",
)
@writes("table.community_cohorts", "table.entities", "table.entity_flags", "table.people_biology", "table.people_culture")
async def cohort_upkeep(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    seeded = 0
    for community in await canon(ctx.session, LAND_COMMUNITY_TYPES):
        if (stat(community, "population") or 0) <= 0:
            continue
        if community.entity_type is EntityType.PEOPLE:
            await ensure_profiles(ctx.session, ctx.rules, community, await region_of(ctx, atlas, community))
        rows = await seed(ctx.session, ctx.rules, community, ctx.epoch)
        seeded += 1
        await rebalance_classes(ctx.session, ctx.rules, community, rows, ctx.epoch)
        await sync_veterans(ctx, community)
        await reconcile(ctx.session, ctx.rules, community, rows, ctx.epoch)
    ctx.count("cohorts_kept", seeded)
    ctx.count("promoted", await promote(ctx))
    slept, woke = await doze(ctx)
    ctx.count("dormant", slept)
    ctx.count("woken", woke)
    await ctx.session.flush()


@reads(
    "people.population",
    "settlement.population",
    "table.community_cohorts",
    "table.community_labour",
    "table.community_societies",
    "table.region_environment",
    "table.world_maps",
)
@writes("table.community_cohorts", "table.community_labour")
async def labour_allocation(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    kept = 0
    for community in await canon(ctx.session, LAND_COMMUNITY_TYPES):
        if (stat(community, "population") or 0) <= 0:
            continue
        ground = await region_of(ctx, atlas, community)
        wet_cold = ground is not None and (ground.temperature_band in COLD or ground.wetland >= WET)
        await allocate(ctx, community, ground, wet_cold=wet_cold)
        kept += 1
    ctx.count("labour_kept", kept)
    await ctx.session.flush()


@reads(
    "army.size",
    "people.population",
    "settlement.population",
    "table.armies",
    "table.battles",
    "table.bonds",
    "table.community_cohorts",
    "table.community_societies",
    "table.cult_tenets",
    "table.loans",
    "table.people_culture",
)
@writes(
    "army.size", "people.population", "settlement.population", "table.community_cohorts", "table.community_societies", "table.entities", "table.people_culture"
)
async def society_mobility(ctx: TickContext) -> None:
    ctx.count("deserted", await desertion(ctx))
    ctx.count("ennobled", await ennoble_heroes(ctx))
    ctx.count("ruined", await ruin_merchants(ctx))
    for community in await canon(ctx.session, LAND_COMMUNITY_TYPES):
        for key, value in (await class_mobility(ctx, community)).items():
            ctx.count(key, value)
    await ctx.session.flush()


@reads(
    "people.population",
    "table.bonds",
    "table.culture_values",
    "table.holder_levels",
    "table.holder_techniques",
    "table.language_profiles",
    "table.people_biology",
    "table.people_culture",
    "table.region_environment",
    "table.world_maps",
)
@writes("people.population", "table.entities", "table.people_biology", "table.people_culture")
async def people_cycles(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        ground = await region_of(ctx, atlas, people)
        _, culture = await ensure_profiles(ctx.session, ctx.rules, people, ground)
        refresh_culture(culture, await culture_for(ctx.session, ctx.rules, people, ground))
    await ctx.session.flush()


PHASES = (
    Phase("cohort_upkeep", cohort_upkeep),
    Phase("labour_allocation", labour_allocation),
    Phase("society_mobility", society_mobility),
    Phase("people_cycles", people_cycles),
)
