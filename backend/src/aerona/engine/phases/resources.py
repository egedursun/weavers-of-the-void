from aerona.catalog.life_traits import EXTRACTION_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.life_traits import ExtractionKindTrait
from aerona.domain.enums.region import DangerHarm
from aerona.engine.context import TickContext
from aerona.engine.crafts.catch import regrowth_scale
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import ExtractionTally, extract, extraction_kind, keep_methods, reconcile, regrow
from aerona.engine.economy.stocks import sync_aggregates
from aerona.engine.environment.cells import keep_the_deep
from aerona.engine.environment.columns import columns_by_region
from aerona.engine.environment.dangers import weighted_dangers
from aerona.engine.environment.deep import deepen
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

SEAM_KINDS = having(EXTRACTION_KIND_TRAITS, ExtractionKindTrait.ARTISAN_KINDS)


def deepest_layer(ground: RegionEnvironmentRow | None) -> str | None:
    if ground is None or not ground.mineral_layers:
        return None
    return max(sorted(ground.mineral_layers), key=lambda material: ground.mineral_layers[material])


def work_seam(rules: Rules, ground: RegionEnvironmentRow | None, owners: int, material: str | None = None) -> None:
    seam = material if ground is not None and material in ground.mineral_layers else deepest_layer(ground)
    if ground is None or seam is None:
        return
    settings = rules.land_use
    if "mined" not in ground.locked:
        ground.mined = clamp_int(ground.mined + settings.mining_per_owner * owners, 0, PERCENT)
    layers = dict(ground.mineral_layers)
    if f"seam.{seam}" not in ground.locked:
        layers[seam] = max(0, layers[seam] - settings.seam_depletion * owners)
    ground.mineral_layers = {key: value for key, value in layers.items() if value > 0}


@reads(
    "faction.wealth",
    "people.craft",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "region.danger",
    "region.fertility",
    "region.magic",
    "resource.abundance",
    "resource.value",
    "settlement.population",
    "settlement.prosperity",
    "table.army_profiles",
    "table.biology_variants",
    "table.bodies",
    "table.bonds",
    "table.calendars",
    "table.chemical_works",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.commutes",
    "table.cosmos",
    "table.creator",
    "table.cult_doctrines",
    "table.culture_values",
    "table.deep_passages",
    "table.deep_seals",
    "table.dimensional_events",
    "table.dimensions",
    "table.endemic_diseases",
    "table.entities",
    "table.entity_traits",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.goods_flows",
    "table.herds",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.irregular_seasons",
    "table.kinship_systems",
    "table.language_profiles",
    "table.language_standing",
    "table.lexemes",
    "table.maimed_cohorts",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.place_environment",
    "table.place_profiles",
    "table.plague_responses",
    "table.plant_profiles",
    "table.polity_deep_knowledge",
    "table.polity_members",
    "table.polity_profiles",
    "table.public_clocks",
    "table.region_crops",
    "table.region_dangers",
    "table.region_environment",
    "table.region_geology",
    "table.region_pollution",
    "table.region_underground",
    "table.resource_profiles",
    "table.resource_workers",
    "table.salvage_sites",
    "table.skills",
    "table.sky_events",
    "table.sons",
    "table.species_products",
    "table.species_profiles",
    "table.stars",
    "table.treaty_parties",
    "table.water_lifts",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "faction.wealth",
    "people.craft",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "resource.abundance",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_industry",
    "table.community_societies",
    "table.community_stocks",
    "table.deep_passages",
    "table.entities",
    "table.entity_flags",
    "table.goods_flows",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.maimed_cohorts",
    "table.name_registry",
    "table.node_births",
    "table.people_biology",
    "table.people_culture",
    "table.place_environment",
    "table.place_profiles",
    "table.polity_deep_knowledge",
    "table.production_runs",
    "table.region_environment",
    "table.region_geology",
    "table.region_underground",
    "table.resource_profiles",
    "table.resource_workers",
    "table.tradition_profiles",
    "table.union_customs",
)
async def resource_economy(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    book.worker_danger = await weighted_dangers(ctx.session, ctx.rules, DangerHarm.WORKERS)
    book.rock_columns = await columns_by_region(ctx.session)
    tally = ExtractionTally()
    pairs = [(resource, book.profiles[resource.id]) for resource in book.resources() if resource.id in book.profiles]
    ctx.count("extraction_methods_moved", await keep_methods(ctx, pairs))
    for resource in book.resources():
        profile = book.profiles.get(resource.id)
        if profile is None:
            continue
        if await extract(ctx, book, resource, profile, tally) > 0 and extraction_kind(profile) in SEAM_KINDS:
            material = profile.material.value if profile.material is not None else None
            work_seam(ctx.rules, book.ground.region_of(resource.id), len(book.owners.get(resource.id, [])), material)
    for community in book.communities:
        await sync_aggregates(ctx.session, ctx.rules, community)
    ctx.count("resources_worked", tally.worked)
    ctx.count("output", tally.output)
    ctx.count("hazards", tally.hazards)
    ctx.count("knowledge_gated", tally.gated)
    deep = await deepen(ctx)
    ctx.count("layers_reached", deep.layers)
    ctx.count("veins_found", deep.veins)
    ctx.count("strata_reached", deep.strata)
    ctx.count("gas_fires", deep.fires)
    ctx.count("reservoirs_tapped", deep.tapped)
    ctx.count("faults_stressed", deep.stressed)
    below = await keep_the_deep(ctx)
    ctx.count("cells_shaped", below.shaped)
    ctx.count("cells_named", below.named)
    ctx.count("passages_formed", below.passages)
    ctx.count("passages_dug", below.dug)
    ctx.count("passages_collapsed", below.collapsed)
    ctx.count("passages_flooded", below.flooded)
    ctx.count("passages_drained", below.drained)
    ctx.count("passages_cleared", below.cleared)
    ctx.count("passages_sealed", below.sealed)
    ctx.count("cells_known", below.known)
    ctx.count("contacts_below", below.contacts)
    ctx.count("unadapted_below", below.strained)
    ctx.count("peoples_below", below.peoples)
    ctx.count("armies_strung_out_below", below.narrowed)


@reads(
    "resource.abundance",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.catch_grounds",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.entities",
    "table.forced_weather",
    "table.herds",
    "table.holder_levels",
    "table.holder_techniques",
    "table.irregular_seasons",
    "table.nodes",
    "table.place_environment",
    "table.plague_responses",
    "table.plant_profiles",
    "table.polity_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_products",
    "table.species_profiles",
    "table.stars",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
    "table.worlds",
)
@writes("resource.abundance", "table.entities", "table.resource_profiles")
async def resource_regeneration(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    regrown = 0
    for resource in book.resources():
        profile = book.profiles.get(resource.id)
        if profile is None:
            continue
        reconcile(resource, profile)
        regrown += regrow(ctx.rules, resource, profile, scale=await regrowth_scale(ctx.session, ctx.rules, resource.id))
    ctx.count("regrown", regrown)


ECONOMY_PHASES = (Phase("resource_economy", resource_economy),)
REGENERATION_PHASES = (Phase("resource_regeneration", resource_regeneration),)
PHASES = ECONOMY_PHASES + REGENERATION_PHASES
