from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.goods_traits import commodities_with
from aerona.catalog.life.economy import BRANCH_OF, CRAFT_FACTOR_EXTRACTION_KINDS, HAZARD_HARM, HAZARD_MAIMS, HAZARD_RULES, KIND_JOBS, ROLL_HAZARDS_HAZARD_KINDS
from aerona.catalog.life_traits import EXTRACTION_KIND_TRAITS, HAZARD_KIND_TRAITS, WORLD_TYPE_TRAITS, having
from aerona.catalog.materials import MATERIALS
from aerona.catalog.methods import method_output
from aerona.catalog.production import EXTRACTION, EXTRACTION_OF
from aerona.catalog.terrain import terrains
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import ProductionRunRow, ResourceProfileRow, ResourceWorkerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.made import SalvageSiteRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.economy import CommodityKind, ExtractionKind, GoodsFlow, HazardKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.environment import ScarKind, TerrainTrait
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.life_traits import ExtractionKindTrait, HazardKindTrait, WorldTypeTrait
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.body.book import capacity_lean
from aerona.engine.body.cohorts import cohort, labour_factor
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import cosmography_of
from aerona.engine.cosmos.world_views import WorldView, light_pct, view_of
from aerona.engine.couplings.deep import active_seal, seal_after_breach
from aerona.engine.crafts.catch import catch_factor
from aerona.engine.crafts.linking import affinity_value
from aerona.engine.crafts.timekeeping import clock_output
from aerona.engine.crafts.works import blasted, fertilised
from aerona.engine.customs.relief import commute_share
from aerona.engine.dominion.effects import step_here
from aerona.engine.ecology.domestication import draught
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.cells import breach_opening
from aerona.engine.environment.columns import rock_cut
from aerona.engine.environment.years import world_years
from aerona.engine.eras.effects import channel_value
from aerona.engine.industry.energy import scale_by_energy
from aerona.engine.industry.methods import feed, method_for, outdated, process_of_kind
from aerona.engine.industry.pollution import fish_factor
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.means.water import flooded_yield
from aerona.engine.nature.effects import cold_work
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount, set_stats, stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import term
from aerona.engine.structures.readers import workshop_output
from aerona.rules.registry import Rules

THOUSAND = 1000
WORKING_ROLES = frozenset({MortalRole.FARMER, MortalRole.ARTISAN, MortalRole.COMMONER, MortalRole.APPRENTICE, MortalRole.HUNTER, MortalRole.ENGINEER})
ARTISAN_KINDS = having(EXTRACTION_KIND_TRAITS, ExtractionKindTrait.ARTISAN_KINDS)
WORKS_HAZARDS = having(HAZARD_KIND_TRAITS, HazardKindTrait.WORKS_HAZARDS)


@dataclass
class ExtractionTally:
    worked: int = 0
    output: int = 0
    hazards: int = 0
    sealed: int = 0
    gated: int = 0


def extraction_kind(profile: ResourceProfileRow) -> ExtractionKind:
    return profile.extraction or EXTRACTION_OF.get(profile.commodity, ExtractionKind.GATHERING)


ORE_LIKE = frozenset(commodities_with(CommodityTrait.DUG))
BELTS = having(WORLD_TYPE_TRAITS, WorldTypeTrait.BELTS)
GIANTS = having(WORLD_TYPE_TRAITS, WorldTypeTrait.GIANTS)
SEAS = terrains(TerrainTrait.COASTAL)
WETLANDS = terrains(TerrainTrait.WET)
DRYLANDS = terrains(TerrainTrait.ARID)


async def extraction_method(ctx: TickContext, resource: EntityRow, profile: ResourceProfileRow) -> ExtractionKind | None:
    world = await ctx.session.get(WorldRow, resource.world_id) if resource.world_id is not None else None
    land = await ctx.session.get(RegionEnvironmentRow, resource.location_id) if resource.location_id is not None else None
    terrain = land.dominant_terrain if land is not None else None
    kind = world.world_type if world is not None else None
    salvage = resource.location_id is not None and await ctx.session.get(SalvageSiteRow, resource.location_id) is not None
    collectors = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.kind == StructureKind.STAR_COLLECTOR)
    starlit = (
        resource.world_id is not None
        and await ctx.session.scalar(select(EntityRow.id).where(EntityRow.id.in_(collectors), EntityRow.world_id == resource.world_id).limit(1)) is not None
    )
    fuel = profile.commodity is CommodityKind.FUEL
    choices = (
        (salvage, ExtractionKind.SALVAGE),
        (kind in BELTS and profile.commodity in ORE_LIKE, ExtractionKind.ASTEROID),
        (kind in GIANTS and fuel, ExtractionKind.ATMOSPHERIC),
        (fuel and starlit, ExtractionKind.STELLAR),
        ((kind is WorldType.OCEAN or terrain in SEAS) and (fuel or profile.commodity is CommodityKind.ORE), ExtractionKind.DEEP_SEA),
        (terrain in WETLANDS and profile.commodity is CommodityKind.STONE, ExtractionKind.DREDGING),
        (terrain in DRYLANDS and fuel, ExtractionKind.PUMPING),
    )
    return next((method for fits, method in choices if fits), None)


async def keep_methods(ctx: TickContext, rows: list[tuple[EntityRow, ResourceProfileRow]]) -> int:
    moved = 0
    for resource, profile in rows:
        if profile.held or held(resource.id):
            continue
        method = await extraction_method(ctx, resource, profile)
        if method != profile.extraction:
            profile.extraction = method
            moved += 1
    return moved


def abundance_of(profile: ResourceProfileRow) -> int:
    return clamp_int(round_half_up(profile.reserve * PERCENT / max(1, profile.initial_reserve)), 0, PERCENT)


async def mine_out(ctx: TickContext, resource: EntityRow) -> None:
    region_id = (await RegionAtlas.load(ctx.session)).top_region(resource.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if ground is None or held(ground.entity_id) or "scar.mined_out" in ground.locked:
        return
    add_scar(ground, ScarKind.MINED_OUT, PERCENT // 2)
    await record(
        ctx, "scar.made", roles={IncidentRole.PLACE: ground.entity_id}, facts={"scar": ScarKind.MINED_OUT, "depth": PERCENT // 2}, place=ground.entity_id
    )


def write_reserve(resource: EntityRow, profile: ResourceProfileRow, reserve: int, *, force: bool = False) -> None:
    if profile.held and not force:
        set_stats(resource, abundance=abundance_of(profile))
        return
    profile.reserve = clamp_int(reserve, 0, profile.initial_reserve * 4)
    set_stats(resource, abundance=abundance_of(profile))


def reconcile(resource: EntityRow, profile: ResourceProfileRow) -> None:
    if profile.held:
        return
    current = stat(resource, "abundance")
    if current is not None and current != abundance_of(profile):
        profile.reserve = clamp_int(round_half_up(current * profile.initial_reserve / PERCENT), 0, profile.initial_reserve * 4)


def season_fit(book: EconomyBook, world_id: int | None, kind: ExtractionKind) -> float:
    spec = EXTRACTION[kind]
    seasons = book.ground.seasons_of(world_id) if world_id is not None else []
    if spec.season_key is None or not seasons:
        return 0.0
    if spec.season_key == "winter":
        coldest = min(seasons, key=lambda season: (season.temperature_shift, season.position))
        return (PERCENT - coldest.growth) / PERCENT
    warmest = max(seasons, key=lambda season: (season.temperature_shift, -season.position))
    return warmest.travel / PERCENT


def labour_pool(rules: Rules, book: EconomyBook, community: EntityRow, kind: ExtractionKind) -> int:
    hands = book.hands(community.id, KIND_JOBS[kind])
    if hands is not None:
        labour = rules.extraction.artisan_labour_pct if kind in ARTISAN_KINDS else rules.extraction.farmer_labour_pct
        return round_half_up(hands * (1 if kind in ARTISAN_KINDS else labour / PERCENT))
    row = book.societies.get(community.id)
    social_class = SocialClass.ARTISAN if kind in ARTISAN_KINDS else SocialClass.FARMER
    share = row.share(social_class) if row is not None else PERCENT / len(SocialClass)
    labour = rules.extraction.artisan_labour_pct if kind in ARTISAN_KINDS else rules.extraction.farmer_labour_pct
    return round_half_up(headcount(community) * share / PERCENT * labour / PERCENT)


def worked_by(book: EconomyBook, community_id: int, kind: ExtractionKind) -> int:
    same = ARTISAN_KINDS if kind in ARTISAN_KINDS else frozenset(ExtractionKind) - ARTISAN_KINDS
    count = 0
    for resource_id, owners in book.owners.items():
        profile = book.profiles.get(resource_id)
        if profile is None or not profile.revealed or extraction_kind(profile) not in same:
            continue
        if any(book.affiliated.get(owner) == community_id for owner in owners):
            count += 1
    return max(1, count)


async def tools_factor(ctx: TickContext, community_id: int, workers: int) -> float:
    table = ctx.rules.extraction
    lots = [row for row in await lots_of(ctx.session, community_id, CommodityKind.TOOLS) if row.quantity > 0]
    owned = sum(row.quantity for row in lots)
    if owned <= 0 or workers <= 0:
        return 1.0
    quality = sum(row.quality * row.quantity for row in lots) / owned
    ratio = min(1.0, owned / max(1, workers * table.tools_per_1000_workers / THOUSAND))
    return 1 + table.tools_pct / PERCENT * ratio * (0.5 + quality / (2 * PERCENT))


def material_value(profile: ResourceProfileRow) -> int:
    if profile.material is not None:
        return MATERIALS[profile.material].base_value
    return COMMODITIES[profile.commodity].base_price


HILLY = terrains(TerrainTrait.ROUGH)
RUINS = terrains(TerrainTrait.RUINED)
FROM_RUINS = having(EXTRACTION_KIND_TRAITS, ExtractionKindTrait.TAKES_FROM_RUINS)


def craft_factor(ctx: TickContext, book: EconomyBook, community_id: int, resource_id: int, kind: ExtractionKind) -> float:
    table = ctx.rules.technique_effects
    known = book.techniques.get(community_id, set())
    lift = 0.0
    if kind in CRAFT_FACTOR_EXTRACTION_KINDS and Technique.SELECTIVE_BREEDING in known:
        lift += table.breeding_pct / PERCENT
    if kind is ExtractionKind.FARMING:
        land = book.ground.region_of(resource_id)
        lift += (table.plough_pct / PERCENT) * (Technique.PLOUGH in known) + (table.crop_rotation_pct / PERCENT) * (Technique.CROP_ROTATION in known)
        if land is not None and Technique.IRRIGATION in known:
            lift += table.irrigation_pct / PERCENT * max(0, PERCENT - land.moisture) / PERCENT
        if land is not None and Technique.TERRACING in known and land.dominant_terrain in HILLY:
            lift += table.terracing_pct / PERCENT
        lift += channel_value(ctx.rules, known, EraChannel.FARMING) / PERCENT
    if kind in ARTISAN_KINDS:
        lift += channel_value(ctx.rules, known, EraChannel.MINING) / PERCENT
    if kind in FROM_RUINS and (ground := book.ground.region_of(resource_id)) is not None and ground.dominant_terrain in RUINS:
        lift += ctx.rules.ruined_ground.stone_pct / PERCENT
    return 1 + lift


def region_key(book: EconomyBook, entity_id: int) -> int:
    region = book.ground.region_of(entity_id)
    return region.entity_id if region is not None else -1


async def method_factor(ctx: TickContext, book: EconomyBook, community_id: int, kind: ExtractionKind, workers: int) -> float:
    process = process_of_kind(kind)
    if process is None:
        return 1.0
    spec = method_for(book, community_id, process)
    crews = round_half_up(workers * ctx.rules.energy.extraction_per_100_workers / PERCENT)
    powered = scale_by_energy(book, community_id, spec.energy, spec.energy_need * crews)
    return method_output(ctx.rules, spec) / PERCENT * powered * await feed(ctx, community_id, spec, crews) * outdated(book, ctx.rules, community_id, process)


def knowledge_gate(rules: Rules, book: EconomyBook, profile: ResourceProfileRow, community_id: int) -> float:
    if profile.required_branch is None or profile.required_level <= 0:
        return 1.0
    short = profile.required_level - book.level(community_id, profile.required_branch)
    if short <= 0:
        return 1.0
    return (rules.extraction.knowledge_short_pct / PERCENT) ** short


def world_share(rules: Rules, view: WorldView, kind: ExtractionKind) -> float:
    if kind is ExtractionKind.MINING:
        return view.ore_yield_pct / PERCENT
    if kind is ExtractionKind.LOGGING:
        return view.timber_pct / PERCENT
    if kind is ExtractionKind.FARMING:
        soil = PERCENT if view.soil else rules.world_views.soilless_harvest_pct
        return light_pct(rules, view.light) / PERCENT * soil / PERCENT
    return 1.0


async def named_labour(ctx: TickContext, book: EconomyBook, community_id: int) -> float:
    workers = [
        entity.id
        for entity in book.entities.values()
        if entity.entity_type is EntityType.MORTAL and entity.mortal_role in WORKING_ROLES and book.affiliated.get(entity.id) == community_id
    ]
    lean = await capacity_lean(ctx.session, workers, "labour", ctx.rules.capacities.labour_work_pct)
    term("capacities.labour_work", max(0.0, 1 + lean), ModifierOp.MULTIPLY, source_node_id=community_id)
    return max(0.0, 1 + lean)


async def output_of(ctx: TickContext, book: EconomyBook, resource: EntityRow, profile: ResourceProfileRow, community: EntityRow, *, workers: int) -> int:
    table = ctx.rules.extraction
    gate = knowledge_gate(ctx.rules, book, profile, community.id)
    if gate <= 0:
        return 0
    kind = extraction_kind(profile)
    spec = EXTRACTION[kind]
    base = workers * table.output_per_1000_workers / THOUSAND * profile.richness / PERCENT
    skill = 1 + book.skill(community.id, spec.skill) * table.skill_pct_per_level / PERCENT
    branch = profile.required_branch or BRANCH_OF.get(kind)
    knowledge = 1 + (book.level(community.id, branch) if branch is not None else 0) * table.knowledge_pct_per_level / PERCENT
    season = 1 + table.season_pct / PERCENT * season_fit(book, resource.world_id, kind)
    difficulty = 1 - profile.extraction_difficulty * table.difficulty_pct / PERCENT / PERCENT
    site = book.workshop(community.id, spec.workshop) if spec.workshop is not None else None
    works = (1 + (site.level if site is not None else 0) * table.workshop_pct_per_level / PERCENT) * await workshop_output(ctx.session, ctx.rules, site)
    raw = base * skill * knowledge * season * difficulty * works * await tools_factor(ctx, community.id, workers) * await labour_factor(ctx, community)
    raw *= await named_labour(ctx, book, community.id)
    raw *= await clock_output(ctx.session, ctx.rules, community.id) * await cold_work(ctx, community)
    raw *= craft_factor(ctx, book, community.id, resource.id, kind) * gate * await method_factor(ctx, book, community.id, kind, workers)
    if kind is ExtractionKind.FISHING:
        raw *= fish_factor(ctx.rules, book.pollution.get(region_key(book, resource.id))) * await catch_factor(ctx.session, ctx.rules, resource.id)
    if kind is ExtractionKind.FARMING:
        raw *= await draught(ctx, community.id) * await fertilised(ctx.session, ctx.rules, community.id)
    else:
        raw *= await step_here(ctx, community.id, DivineScale.PRODUCTIVITY, ctx.rules.dominion.output_per_step_pct)
    raw *= world_share(ctx.rules, await view_of(ctx.session, ctx.rules, resource.world_id), kind)
    if kind is ExtractionKind.MINING:
        raw *= await blasted(ctx.session, ctx.rules, community.id)
        ladder = await cosmography_of(ctx.session)
        raw *= ladder.pull(ctx.rules, ladder.place_world_id(resource.world_id)).ore
    return max(0, min(profile.reserve, round_half_up(raw)))


def hazard_chance(rules: Rules, kind: HazardKind, difficulty: int, engineering: int) -> int:
    table = rules.mining_hazards
    base: int = getattr(table, HAZARD_RULES[kind])
    averted = max(0.0, 1 - engineering * table.engineering_pct_per_level / PERCENT)
    return round_half_up(base * max(difficulty, 1) / PERCENT * averted)


async def _hurt_named(ctx: TickContext, book: EconomyBook, community: EntityRow, hazard: HazardKind, resource: EntityRow) -> list[int]:
    damage_type, words, damage = HAZARD_HARM[hazard]
    workers = sorted(
        (
            entity
            for entity in book.entities.values()
            if entity.entity_type is EntityType.MORTAL and entity.mortal_role in WORKING_ROLES and book.affiliated.get(entity.id) == community.id
        ),
        key=lambda entity: entity.id,
    )
    rng = ctx.rng(f"hazard.named.{resource.id}.{hazard.value}")
    hurt: list[int] = []
    for mortal in rng.sample(workers, min(len(workers), ctx.rules.mining_hazards.named_hurt)):
        cause = HarmCause.INDUSTRIAL if hazard in WORKS_HAZARDS else HarmCause.ACCIDENT
        await apply_hits(ctx, mortal, Harm(damage, cause, words, damage_type=damage_type, event_entity_id=resource.id))
        hurt.append(mortal.id)
    return hurt


async def _open_cavern(ctx: TickContext, resource: EntityRow) -> EntityRow:
    rng = ctx.rng(f"cavern.{resource.id}")
    return await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.SPECIES,
            name=f"Dweller of the cavern under {resource.name}",
            body=f"It came out when the galleries of {resource.name} broke into a cavern below.",
            stats=SpeciesStats(
                hp=60 + rng.die(60), strength=55 + rng.die(30), agility=30 + rng.die(30), intelligence=10 + rng.die(30), danger=65 + rng.die(30), abundance=5
            ),
            power=6,
            location_id=resource.location_id,
            world_id=resource.world_id,
            subtype="cavern beast",
            is_underworld=True,
        ),
    )


async def strike_hazard(
    ctx: TickContext, book: EconomyBook, resource: EntityRow, profile: ResourceProfileRow, community: EntityRow, *, workers: int, hazard: HazardKind
) -> None:
    table = ctx.rules.mining_hazards
    killed = round_half_up(workers * table.workers_lost_pct / PERCENT)
    population = stat(community, "population")
    if population is not None and killed > 0:
        with flowing(FlowCategory.DISASTER):
            set_stats(community, population=max(0, population - killed))
    maimed = round_half_up(killed * table.maimed_pct / PERCENT)
    if maimed > 0:
        row = await cohort(ctx, community.id, HAZARD_MAIMS[hazard])
        row.count += maimed
        row.updated_epoch = ctx.epoch
    hurt = await _hurt_named(ctx, book, community, hazard, resource)
    cavern: EntityRow | None = None
    if hazard is HazardKind.CAVE_IN and not profile.held:
        profile.sealed_until_epoch = ctx.epoch + table.seal_epochs
        if await active_seal(ctx.session, resource.id) is None and ctx.rng(f"cavern.roll.{resource.id}").chance(table.cavern_chance):
            cavern = await _open_cavern(ctx, resource)
            await breach_opening(ctx, resource, cavern)
            await seal_after_breach(ctx, resource, community)
    await record(
        ctx,
        f"mining.{hazard.value}",
        roles={
            IncidentRole.SUBJECT: resource.id,
            IncidentRole.OWNER: community.id,
            IncidentRole.VICTIM: hurt,
            IncidentRole.PRODUCT: cavern.id if cavern is not None else None,
        },
        facts={
            "hazard": hazard,
            "workers": workers,
            "killed": killed,
            "maimed": maimed,
            "sealed_epochs": table.seal_epochs if hazard is HazardKind.CAVE_IN and not profile.held else 0,
        },
        place=resource.location_id,
    )


def shaft_factor(ctx: TickContext, book: EconomyBook, resource: EntityRow, profile: ResourceProfileRow, *, community: EntityRow, hazard: HazardKind) -> float:
    table = ctx.rules.mines
    depth = (profile.initial_reserve - profile.reserve) / max(1, profile.initial_reserve)
    props = book.materials.props(resource.world_id, profile.material, profile.world_material_id)
    hardness = props.hardness if props is not None else PERCENT // 2
    factor = (1 + depth * table.depth_pct / PERCENT) * max(0.0, 1 - hardness * table.support_pct / PERCENT / PERCENT)
    process = process_of_kind(extraction_kind(profile))
    method = method_for(book, community.id, process).kind if process is not None else None
    if hazard is HazardKind.FLOODED_SHAFT and method is MethodKind.PUMPED_SHAFTS:
        factor *= 1 - table.pumped_flood_pct / PERCENT
    if hazard is HazardKind.CAVE_IN and method is MethodKind.FIRE_SETTING:
        factor *= 1 + table.fire_cave_pct / PERCENT
    return factor


async def roll_hazards(
    ctx: TickContext, book: EconomyBook, resource: EntityRow, profile: ResourceProfileRow, community: EntityRow, *, workers: int
) -> HazardKind | None:
    spec = EXTRACTION[extraction_kind(profile)]
    if spec.hazard is None or workers <= 0 or held(resource.id, community.id):
        return None
    hazard = spec.hazard
    region = book.ground.region_of(resource.id)
    if hazard is HazardKind.CAVE_IN and region is not None and region.rainfall >= ctx.rules.mining_hazards.flood_rainfall:
        hazard = HazardKind.FLOODED_SHAFT
    chance = hazard_chance(ctx.rules, hazard, profile.extraction_difficulty, book.skill(community.id, SkillKind.ENGINEERING))
    if hazard in ROLL_HAZARDS_HAZARD_KINDS:
        chance = round_half_up(chance * shaft_factor(ctx, book, resource, profile, community=community, hazard=hazard))
    for year in world_years(ctx.environment, resource.world_id or 0, "mining"):
        if ctx.rng(f"hazard.{resource.id}.{community.id}.{year.year}").chance(chance):
            await strike_hazard(ctx, book, resource, profile, community, workers=workers, hazard=hazard)
            return hazard
    return None


async def _pay_owner(ctx: TickContext, owner: EntityRow, value: int) -> None:
    gain = round_half_up(value * ctx.rules.extraction.owner_wealth_per_value / PERCENT)
    if gain <= 0:
        return
    add_prosperity(ctx.rules, owner, gain)
    for key in ("wealth", "craft"):
        current = stat(owner, key)
        if current is not None:
            set_stats(owner, **{key: clamp_int(current + gain, 0, PERCENT)})


async def byproduct(ctx: TickContext, book: EconomyBook, resource: EntityRow, profile: ResourceProfileRow, *, community: EntityRow, output: int) -> None:
    if profile.byproduct_material is None or profile.byproduct_pct <= 0:
        return
    extra = round_half_up(output * profile.byproduct_pct / PERCENT)
    await goods_of(ctx.session, ctx.epoch).add(
        community.id,
        CommodityKind.ORE,
        extra,
        GoodsFlow.EXTRACTION,
        material=profile.byproduct_material,
        quality=profile.quality,
    )
    region = book.ground.region_of(resource.id)
    if region is None:
        return
    if "mined" not in region.locked:
        region.mined = clamp_int(region.mined + ctx.rules.extraction.byproduct_scar, 0, PERCENT)
    if "erosion" not in region.locked:
        region.erosion = clamp_int(region.erosion + ctx.rules.extraction.byproduct_scar, 0, PERCENT)


def perilous_work(rules: Rules, book: EconomyBook, resource: EntityRow, community_id: int, output: int) -> int:
    region = book.ground.region_of(resource.id)
    if region is None:
        return output
    lost = book.worker_danger.get(region.entity_id, 0) * rules.regional_danger.workers_harm_pct / PERCENT / PERCENT
    stone = rock_cut(rules, book.rock_columns.get(region.entity_id, []), book.techniques.get(community_id, set()))
    return round_half_up(output * (1 - lost) * (1 - stone))


async def extract(ctx: TickContext, book: EconomyBook, resource: EntityRow, profile: ResourceProfileRow, tally: ExtractionTally) -> int:
    reconcile(resource, profile)
    if not profile.revealed or (profile.sealed_until_epoch is not None and profile.sealed_until_epoch >= ctx.epoch):
        return 0
    kind = extraction_kind(profile)
    produced = 0
    for owner_id in book.owners.get(resource.id, []):
        owner = book.entities.get(owner_id)
        community = book.community_of(owner_id)
        if owner is None or community is None or profile.reserve <= 0 or held(community.id):
            continue
        workers = round_half_up(labour_pool(ctx.rules, book, community, kind) / worked_by(book, community.id, kind))
        row = book.workers.get(resource.id, {}).get(community.id)
        if row is None:
            row = ResourceWorkerRow(resource_entity_id=resource.id, community_entity_id=community.id, workers=0)
            ctx.session.add(row)
            book.workers.setdefault(resource.id, {})[community.id] = row
        workers = round_half_up(workers * await commute_share(ctx.session, community.id))
        if row.held:
            workers = row.workers
        else:
            row.workers = workers
        output = await output_of(ctx, book, resource, profile, community, workers=workers)
        output = perilous_work(ctx.rules, book, resource, community.id, output)
        if kind is ExtractionKind.MINING:
            output = await flooded_yield(ctx, community.id, profile.extraction_difficulty, output)
        if output <= 0:
            if knowledge_gate(ctx.rules, book, profile, community.id) <= 0:
                tally.gated += 1
            continue
        write_reserve(resource, profile, profile.reserve - output)
        if profile.reserve <= 0 and profile.regeneration <= 0:
            await mine_out(ctx, resource)
        material = profile.material if profile.world_material_id is None else None
        await goods_of(ctx.session, ctx.epoch).add(
            community.id,
            profile.commodity,
            output,
            GoodsFlow.EXTRACTION,
            material=material,
            world_material_id=profile.world_material_id,
            quality=profile.quality,
        )
        await byproduct(ctx, book, resource, profile, community=community, output=output)
        await _pay_owner(
            ctx, owner, round_half_up(output * material_value(profile) / PERCENT * await affinity_value(ctx.session, ctx.rules, profile.world_material_id))
        )
        ctx.session.add(
            ProductionRunRow(
                epoch=ctx.epoch,
                community_entity_id=community.id,
                step=kind.value,
                workshop=EXTRACTION[kind].workshop,
                resource_entity_id=resource.id,
                output=profile.commodity,
                material=material,
                quantity=output,
                quality=profile.quality,
                inputs={},
                workers=workers,
                method=method_for(book, community.id, process).kind if (process := process_of_kind(kind)) is not None else None,
            )
        )
        produced += output
        if await roll_hazards(ctx, book, resource, profile, community, workers=workers) is not None:
            tally.hazards += 1
    profile.last_output = produced
    if produced:
        tally.worked += 1
        tally.output += produced
    return produced


def regrow(rules: Rules, resource: EntityRow, profile: ResourceProfileRow, *, scale: float = 1.0) -> int:
    if profile.held or profile.regeneration <= 0 or profile.reserve >= profile.initial_reserve:
        return 0
    gain = min(round_half_up(profile.regeneration * scale), profile.initial_reserve - profile.reserve)
    write_reserve(resource, profile, profile.reserve + gain)
    return gain
