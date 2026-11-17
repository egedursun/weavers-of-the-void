from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.kinds.society import keep_society_kinds
from aerona.engine.phase import Phase


@reads(
    "table.community_societies",
    "table.entities",
    "table.faction_profiles",
    "table.kind_holdings",
    "table.mortal_profiles",
    "table.organisation_kinds",
    "table.profession_kinds",
    "table.rank_kinds",
)
@writes("table.community_societies", "table.entities", "table.faction_profiles", "table.organisation_kinds", "table.profession_kinds", "table.rank_kinds")
async def society_kinds(ctx: TickContext) -> None:
    tally = await keep_society_kinds(ctx)
    ctx.count("built_in_kinds", tally.built_in)
    ctx.count("rank_effects", tally.ranks)
    ctx.count("profession_earnings", tally.earnings)
    ctx.count("work_mishaps", tally.mishaps)
    ctx.count("organisations_shaped", tally.organisations)


PHASES = (Phase("society_kinds", society_kinds),)
