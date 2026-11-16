from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.living.backfill import legacy_backfill
from aerona.engine.living.disease import loose_designed
from aerona.engine.living.kin import keep_banks, keep_symbionts
from aerona.engine.living.lines import keep_lines
from aerona.engine.living.production import blight_monocultures, keep_living_works
from aerona.engine.living.profiles import keep_profiles
from aerona.engine.living.society import keep_standing
from aerona.engine.living.world import clone_peoples, designed_sapience, shape_lands


@reads(
    "table.bonds",
    "table.breeding_plans",
    "table.community_methods",
    "table.cult_doctrines",
    "table.disease_profiles",
    "table.dishes",
    "table.entity_flags",
    "table.gene_banks",
    "table.living_lines",
    "table.living_profiles",
    "table.perennials",
    "table.species_profiles",
    "table.structure_profiles",
    "table.symbionts",
    "table.vessel_profiles",
)
@writes("table.applied_fixups", "table.cult_doctrines", "table.living_profiles")
async def keep_living(ctx: TickContext) -> None:
    ctx.count("living_backfilled", await legacy_backfill(ctx))
    ctx.count("living_things_kept", await keep_profiles(ctx))
    ctx.count("living_lines_kept", await keep_lines(ctx))
    ctx.count("bank_samples_lost", await keep_banks(ctx))
    ctx.count("symbionts_spread", await keep_symbionts(ctx))
    ctx.count("living_works_lapsed", await keep_living_works(ctx))
    ctx.count("monocultures_blighted", await blight_monocultures(ctx))
    ctx.count("designed_diseases_loosed", await loose_designed(ctx))
    ctx.count("species_risen", await designed_sapience(ctx))
    ctx.count("clone_peoples", await clone_peoples(ctx))
    ctx.count("living_risings", await keep_standing(ctx))
    ctx.count("lands_shaped_by_life", await shape_lands(ctx))
    await ctx.session.flush()
