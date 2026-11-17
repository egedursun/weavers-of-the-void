from aerona.engine.context import TickContext
from aerona.engine.fortune.backfill import keep_judgements, legacy_backfill
from aerona.engine.fortune.cohorts import keep_cohort_mishaps
from aerona.engine.fortune.profiles import keep_fortune
from aerona.engine.interconnect.annotations import reads, writes


@reads("settlement.population", "table.bonds", "table.cohort_mishap_rates", "table.fortune_laws", "table.fortune_profiles", "table.fortune_sources")
@writes("settlement.population", "table.applied_fixups", "table.cohort_mishap_rates", "table.entities", "table.fortune_profiles")
async def fortune(ctx: TickContext) -> None:
    ctx.count("fortune_backfilled", await legacy_backfill(ctx))
    ctx.count("divine_judgements_kept", await keep_judgements(ctx))
    ctx.count("fortunes_kept", await keep_fortune(ctx))
    ctx.count("cohort_mishaps_counted", await keep_cohort_mishaps(ctx))
    await ctx.session.flush()
