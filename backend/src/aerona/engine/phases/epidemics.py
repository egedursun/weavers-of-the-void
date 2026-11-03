from sqlalchemy import select

from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.course import camp_disease, carry_by_armies, carry_by_journeys, fade_immunity, mutate, run_course, settle_endemic
from aerona.engine.disease.emergence import ensure_profile
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
    "people.population",
    "settlement.population",
    "table.armies",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.immunities",
    "table.journeys",
    "table.outbreaks",
    "table.quarantines",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sieges",
)
@writes(
    "army.size",
    "disease.dead",
    "disease.infected",
    "people.population",
    "settlement.population",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.entities",
    "table.immunities",
    "table.outbreaks",
)
async def epidemics(ctx: TickContext) -> None:
    await ensure_profiles(ctx)
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    await run_course(ctx, book)
    fade_immunity(ctx, book)
    await settle_endemic(ctx, book)
    ctx.count("strains", await mutate(ctx, book))
    ctx.count("army_carried", await carry_by_armies(ctx, book))
    ctx.count("journey_carried", await carry_by_journeys(ctx, book))
    ctx.count("camp_dead", await camp_disease(ctx, book))
    ctx.count("expelled", await expel_sick(ctx, book))
    ctx.count("hospitals", await build_hospitals(ctx, book))
    await ctx.session.flush()


PHASES = (Phase("epidemics", epidemics),)
