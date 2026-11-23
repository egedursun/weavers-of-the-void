from aerona.engine.context import TickContext
from aerona.engine.death_work.handling import DeathTally, keep_death_work
from aerona.engine.death_work.seed import seed_death_work
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mortal.readings import backfill_drownings, keep_readings
from aerona.engine.phase import Phase


@reads(
    "people.population",
    "table.bonds",
    "table.creator",
    "table.culture_values",
    "table.death_readings",
    "table.death_work",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.injuries",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.people_cultures",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.death_readings",
    "table.death_work",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.outbreaks",
    "table.people_culture",
    "table.people_cultures",
    "table.settlement_profiles",
)
async def death_work(ctx: TickContext) -> None:
    ctx.count("death_readings_seeded", await keep_readings(ctx))
    ctx.count("drownings_named", await backfill_drownings(ctx.session))
    tally = DeathTally(seeded=await seed_death_work(ctx))
    await keep_death_work(ctx, tally)
    ctx.count("death_work_seeded", tally.seeded)
    ctx.count("death_work_treated", tally.treated)
    ctx.count("death_work_exceptions", tally.exceptions)
    ctx.count("death_work_untended", tally.untended)
    ctx.count("death_work_shunned", tally.shunned)
    ctx.count("death_work_called", tally.called)
    ctx.count("death_work_left", tally.left)


PHASES = (Phase("death_work", death_work),)
