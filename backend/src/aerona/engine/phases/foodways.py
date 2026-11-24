from aerona.engine.context import TickContext
from aerona.engine.cuisine.cuisines import keep_cuisines
from aerona.engine.cuisine.drinks import keep_drinks
from aerona.engine.cuisine.legacy import foodways_backfill
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "settlement.prosperity",
    "table.applied_fixups",
    "table.bonds",
    "table.community_stocks",
    "table.creator",
    "table.cuisines",
    "table.deep_passages",
    "table.designs",
    "table.dimensions",
    "table.dish_ingredients",
    "table.dish_steps",
    "table.dishes",
    "table.drink_kinds",
    "table.entities",
    "table.equipment_models",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.good_kinds",
    "table.incident_participants",
    "table.incidents",
    "table.kind_holdings",
    "table.lexemes",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.plant_parts",
    "table.settlement_profiles",
    "table.sons",
    "table.species_ranges",
    "table.stars",
    "table.structure_designs",
    "table.unit_designs",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.cuisines",
    "table.dish_ingredients",
    "table.dish_steps",
    "table.dishes",
    "table.drink_kinds",
    "table.entities",
    "table.good_kinds",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.kind_holdings",
    "table.memories",
    "table.settlement_profiles",
)
async def foodways(ctx: TickContext) -> None:
    ctx.count("foodways_backfilled", await foodways_backfill(ctx))
    drinks = await keep_drinks(ctx)
    ctx.count("drinks_founded", drinks.founded)
    ctx.count("drinks_derived", drinks.derived)
    ctx.count("drinks_shared", drinks.shared)
    ctx.count("drink_towns", drinks.drunk)
    cuisines = await keep_cuisines(ctx)
    ctx.count("cuisines_founded", cuisines.founded)
    ctx.count("cuisines_fused", cuisines.fused)
    ctx.count("towns_feasted", cuisines.feasted)


PHASES = (Phase("foodways", foodways),)
