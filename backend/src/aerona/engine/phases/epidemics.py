from sqlalchemy import select

from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.course import camp_disease, carry_by_armies, carry_by_journeys, fade_immunity, mutate, run_course, settle_endemic
from aerona.engine.disease.emergence import ensure_profile
from aerona.engine.disease.history import backfill_plagues
from aerona.engine.disease.seasons import season_disease
from aerona.engine.disease.sickness import sicken_cohorts
from aerona.engine.disease.stigma import build_hospitals, expel_sick
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


async def ensure_profiles(ctx: TickContext) -> int:
    made = 0
    diseases = await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.DISEASE, EntityRow.status == EntityStatus.CANON))
    profiled = set(await ctx.session.scalars(select(DiseaseProfileRow.disease_entity_id)))
    for disease in diseases:
        if disease.id not in profiled:
            await ensure_profile(ctx.session, ctx, disease)
            made += 1
    return made


@reads(
    "army.size",
    "disease.dead",
    "disease.infected",
    "event.severity",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "table.applied_fixups",
    "table.armies",
    "table.bonds",
    "table.calendars",
    "table.community_cohorts",
    "table.disease_cures",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.entity_traits",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.immunities",
    "table.incident_participants",
    "table.incidents",
    "table.journeys",
    "table.ley_lines",
    "table.outbreaks",
    "table.place_environment",
    "table.quarantines",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sieges",
    "table.sky_events",
    "table.sons",
    "table.species_hosts",
    "table.species_ranges",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "army.size",
    "disease.dead",
    "disease.infected",
    "people.population",
    "settlement.population",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_cohorts",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.entities",
    "table.immunities",
    "table.incident_participants",
    "table.incidents",
    "table.outbreaks",
    "table.species_hosts",
)
async def epidemics(ctx: TickContext) -> None:
    await ensure_profiles(ctx)
    for key, value in (await backfill_plagues(ctx)).items():
        ctx.count(f"backfilled_{key}", value)
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    ctx.count("seasoned_regions", await season_disease(ctx, book))
    await run_course(ctx, book)
    fade_immunity(ctx, book)
    await settle_endemic(ctx, book)
    ctx.count("strains", await mutate(ctx, book))
    ctx.count("army_carried", await carry_by_armies(ctx, book))
    ctx.count("journey_carried", await carry_by_journeys(ctx, book))
    ctx.count("camp_dead", await camp_disease(ctx, book))
    ctx.count("expelled", await expel_sick(ctx, book))
    ctx.count("hospitals", await build_hospitals(ctx, book))
    fell, recovered = await sicken_cohorts(ctx, book)
    ctx.count("fell_sick", fell)
    ctx.count("recovered", recovered)
    await ctx.session.flush()


PHASES = (Phase("epidemics", epidemics),)
