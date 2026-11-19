from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.kinds.crafts_life import keep_crafts_of_life
from aerona.engine.kinds.derive import derive_kinds
from aerona.engine.kinds.legacy import legacy_holdings
from aerona.engine.kinds.life import keep_kinds
from aerona.engine.kinds.nature import ensure_built_ins, keep_traits, legacy_traits
from aerona.engine.phase import Phase


@reads(
    "table.aim_kinds",
    "table.applied_fixups",
    "table.bonds",
    "table.colour_terms",
    "table.community_dishes",
    "table.creator",
    "table.cuisines",
    "table.dimensions",
    "table.dish_ingredients",
    "table.dishes",
    "table.divine_office_kinds",
    "table.drink_kinds",
    "table.dwelling_kinds",
    "table.emblem_systems",
    "table.entities",
    "table.faction_profiles",
    "table.fear_kinds",
    "table.foreign_gods",
    "table.furnishing_kinds",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.games",
    "table.garment_kinds",
    "table.good_kinds",
    "table.incident_participants",
    "table.incidents",
    "table.instrument_kinds",
    "table.item_profiles",
    "table.kind_holdings",
    "table.language_profiles",
    "table.lexemes",
    "table.loop_signals",
    "table.market_prices",
    "table.music_traditions",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.organisation_kinds",
    "table.polity_members",
    "table.production_method_kinds",
    "table.profession_kinds",
    "table.rank_kinds",
    "table.reading_kinds",
    "table.realm_kinds",
    "table.scent_kinds",
    "table.sons",
    "table.stars",
    "table.substance_kinds",
    "table.tenet_kinds",
    "table.tool_kinds",
    "table.trait_kinds",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.dish_ingredients",
    "table.dishes",
    "table.emblem_systems",
    "table.good_kinds",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_terms",
    "table.incidents",
    "table.kind_holdings",
    "table.language_profiles",
    "table.loop_signals",
    "table.organisation_kinds",
)
async def ways_of_life(ctx: TickContext) -> None:
    for name, count in (await legacy_holdings(ctx)).items():
        ctx.count(f"kinds_legacy_{name}", count)
    tally = await keep_kinds(ctx)
    ctx.count("kinds_spread", tally.spread)
    ctx.count("kinds_faded", tally.faded)
    ctx.count("kinds_retired", tally.retired)
    derived = await derive_kinds(ctx)
    ctx.count("kinds_substituted", derived.substituted)
    ctx.count("kinds_fused", derived.fused)
    ctx.count("kinds_prestige_moved", derived.prestige_moved)


@reads(
    "table.applied_fixups",
    "table.arms",
    "table.colour_meanings",
    "table.colour_terms",
    "table.emblem_systems",
    "table.entities",
    "table.furnishing_kinds",
    "table.games",
    "table.garment_kinds",
    "table.instrument_kinds",
    "table.kind_holdings",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.music_traditions",
    "table.nodes",
    "table.polity_members",
    "table.scent_kinds",
    "table.settlement_profiles",
    "table.substance_kinds",
    "table.tool_kinds",
)
@writes(
    "settlement.prosperity",
    "table.applied_fixups",
    "table.arms",
    "table.colour_meanings",
    "table.colour_terms",
    "table.emblem_systems",
    "table.garment_kinds",
    "table.kind_holdings",
    "table.settlement_profiles",
)
async def crafts_of_life(ctx: TickContext) -> None:
    tally = await keep_crafts_of_life(ctx)
    ctx.count("craft_towns", tally.towns)
    ctx.count("colours_restricted", tally.restricted)
    ctx.count("colours_smuggled", tally.smuggled)
    ctx.count("colours_repealed", tally.repealed)
    ctx.count("forbidden_substances_used", tally.forbidden_use)
    ctx.count("fine_dress_worn", tally.fine_dress)
    ctx.count("dress_revivals", tally.revived)
    ctx.count("arms_linked_to_heraldry", tally.arms_linked)
    ctx.count("dress_worn_by_fashion", tally.worn)


@reads(
    "table.applied_fixups",
    "table.divine_office_kinds",
    "table.entity_traits",
    "table.house_profiles",
    "table.kind_holdings",
    "table.people_biology",
    "table.production_method_kinds",
    "table.realm_kinds",
    "table.trait_kinds",
)
@writes(
    "species.strength",
    "table.applied_fixups",
    "table.divine_office_kinds",
    "table.kind_holdings",
    "table.production_method_kinds",
    "table.realm_kinds",
    "table.trait_kinds",
)
async def traits_and_works(ctx: TickContext) -> None:
    ctx.count("nature_built_ins", await ensure_built_ins(ctx.session))
    ctx.count("traits_legacy", await legacy_traits(ctx))
    ctx.count("traits_shifted", (await keep_traits(ctx)).shifted)


PHASES = (Phase("ways_of_life", ways_of_life), Phase("crafts_of_life", crafts_of_life), Phase("traits_and_works", traits_and_works))
