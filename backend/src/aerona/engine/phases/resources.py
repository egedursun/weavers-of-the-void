from aerona.constants.units import PERCENT
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.economy import ExtractionKind
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import ExtractionTally, extract, extraction_kind, reconcile, regrow
from aerona.engine.economy.stocks import sync_aggregates
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

SEAM_KINDS = frozenset({ExtractionKind.MINING, ExtractionKind.QUARRYING})


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
    "resource.abundance",
    "resource.value",
    "settlement.population",
    "settlement.prosperity",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.forced_weather",
    "table.goods_flows",
    "table.holder_levels",
    "table.holder_techniques",
    "table.maimed_cohorts",
    "table.place_environment",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
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
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.entities",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.maimed_cohorts",
    "table.production_runs",
    "table.region_environment",
    "table.resource_profiles",
    "table.resource_workers",
)
async def resource_economy(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = ExtractionTally()
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


@reads(
    "resource.abundance",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.place_environment",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
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
        regrown += regrow(ctx.rules, resource, profile)
    ctx.count("regrown", regrown)


ECONOMY_PHASES = (Phase("resource_economy", resource_economy),)
REGENERATION_PHASES = (Phase("resource_regeneration", resource_regeneration),)
PHASES = ECONOMY_PHASES + REGENERATION_PHASES
