from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.materials import MATERIALS
from aerona.catalog.production import EXTRACTION, EXTRACTION_OF
from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.db.tables.economy import ProductionRunRow, ResourceProfileRow, ResourceWorkerRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import HarmCause, InjuryKind, MaimedKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.economy import CommodityKind, ExtractionKind, GoodsFlow, HazardKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.body.cohorts import cohort, labour_factor
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import cosmography_of
from aerona.engine.crafts.catch import catch_factor
from aerona.engine.crafts.linking import affinity_value
from aerona.engine.crafts.timekeeping import clock_output
from aerona.engine.crafts.works import blasted, fertilised
from aerona.engine.customs.relief import commute_share
from aerona.engine.dominion.effects import step_here
from aerona.engine.ecology.domestication import draught
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.environment.years import world_years
from aerona.engine.eras.effects import channel_value
from aerona.engine.industry.energy import scale_by_energy
from aerona.engine.industry.methods import feed, method_for, outdated, process_of_kind
from aerona.engine.industry.pollution import fish_factor
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount, set_stats, stat
from aerona.engine.structures.readers import workshop_output
from aerona.rules.registry import Rules

THOUSAND = 1000
WORKING_ROLES = frozenset({MortalRole.FARMER, MortalRole.ARTISAN, MortalRole.COMMONER, MortalRole.APPRENTICE, MortalRole.HUNTER, MortalRole.ENGINEER})
ARTISAN_KINDS = frozenset({ExtractionKind.MINING, ExtractionKind.QUARRYING})
BRANCH_OF: dict[ExtractionKind, KnowledgeBranch] = {
    ExtractionKind.MINING: KnowledgeBranch.METALLURGY,
    ExtractionKind.QUARRYING: KnowledgeBranch.ARCHITECTURE,
    ExtractionKind.FISHING: KnowledgeBranch.SEAFARING,
    ExtractionKind.FARMING: KnowledgeBranch.AGRICULTURE,
    ExtractionKind.HERDING: KnowledgeBranch.AGRICULTURE,
}
HAZARD_HARM: dict[HazardKind, tuple[InjuryKind, str, int]] = {
    HazardKind.CAVE_IN: (InjuryKind.CRUSH, "crushed in a cave-in", 40),
    HazardKind.FLOODED_SHAFT: (InjuryKind.BRUISE, "drowned in a flooded shaft", 30),
    HazardKind.FELLING_ACCIDENT: (InjuryKind.FRACTURE, "struck by a falling tree", 30),
    HazardKind.DROWNING: (InjuryKind.BRUISE, "dragged under by rough water", 35),
    HazardKind.GORING: (InjuryKind.PUNCTURE, "gored by the herd", 25),
}
WORKS_HAZARDS = frozenset({HazardKind.CAVE_IN, HazardKind.FLOODED_SHAFT})
HAZARD_MAIMS: dict[HazardKind, MaimedKind] = {
    HazardKind.CAVE_IN: MaimedKind.ONE_LEGGED,
    HazardKind.FLOODED_SHAFT: MaimedKind.BROKEN_MINDED,
    HazardKind.FELLING_ACCIDENT: MaimedKind.ONE_ARMED,
    HazardKind.DROWNING: MaimedKind.SCARRED,
    HazardKind.GORING: MaimedKind.LAME,
}


@dataclass
class ExtractionTally:
    worked: int = 0
    output: int = 0
    hazards: int = 0
    sealed: int = 0
    gated: int = 0


def extraction_kind(profile: ResourceProfileRow) -> ExtractionKind:
    return EXTRACTION_OF.get(profile.commodity, ExtractionKind.GATHERING)


def abundance_of(profile: ResourceProfileRow) -> int:
    return clamp_int(round_half_up(profile.reserve * PERCENT / max(1, profile.initial_reserve)), 0, PERCENT)


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


KIND_JOBS = MappingProxyType(
    {
        ExtractionKind.MINING: Job.MINING,
        ExtractionKind.QUARRYING: Job.MINING,
        ExtractionKind.FISHING: Job.FISHING,
        ExtractionKind.HERDING: Job.HERDING,
        ExtractionKind.FARMING: Job.FARMING,
        ExtractionKind.GATHERING: Job.FARMING,
        ExtractionKind.LOGGING: Job.BUILDING,
    }
)


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
    held = sum(row.quantity for row in lots)
    if held <= 0 or workers <= 0:
        return 1.0
    quality = sum(row.quality * row.quantity for row in lots) / held
    ratio = min(1.0, held / max(1, workers * table.tools_per_1000_workers / THOUSAND))
    return 1 + table.tools_pct / PERCENT * ratio * (0.5 + quality / (2 * PERCENT))


def material_value(profile: ResourceProfileRow) -> int:
    if profile.material is not None:
        return MATERIALS[profile.material].base_value
    return COMMODITIES[profile.commodity].base_price


HILLY = frozenset({TerrainKind.HILLS, TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS, TerrainKind.CANYON})


def craft_factor(ctx: TickContext, book: EconomyBook, community_id: int, resource_id: int, kind: ExtractionKind) -> float:
    table = ctx.rules.technique_effects
    held = book.techniques.get(community_id, set())
    lift = 0.0
    if kind in (ExtractionKind.FARMING, ExtractionKind.HERDING) and Technique.SELECTIVE_BREEDING in held:
        lift += table.breeding_pct / PERCENT
    if kind is ExtractionKind.FARMING:
        land = book.ground.region_of(resource_id)
        lift += (table.plough_pct / PERCENT) * (Technique.PLOUGH in held) + (table.crop_rotation_pct / PERCENT) * (Technique.CROP_ROTATION in held)
        if land is not None and Technique.IRRIGATION in held:
            lift += table.irrigation_pct / PERCENT * max(0, PERCENT - land.moisture) / PERCENT
        if land is not None and Technique.TERRACING in held and land.dominant_terrain in HILLY:
            lift += table.terracing_pct / PERCENT
        lift += channel_value(ctx.rules, held, EraChannel.FARMING) / PERCENT
    if kind in ARTISAN_KINDS:
        lift += channel_value(ctx.rules, held, EraChannel.MINING) / PERCENT
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
    return spec.output_pct / PERCENT * powered * await feed(ctx, community_id, spec, crews) * outdated(book, ctx.rules, community_id, process)


def knowledge_gate(rules: Rules, book: EconomyBook, profile: ResourceProfileRow, community_id: int) -> float:
    if profile.required_branch is None or profile.required_level <= 0:
        return 1.0
    short = profile.required_level - book.level(community_id, profile.required_branch)
    if short <= 0:
        return 1.0
    return (rules.extraction.knowledge_short_pct / PERCENT) ** short


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
    raw *= await clock_output(ctx.session, ctx.rules, community.id)
    raw *= craft_factor(ctx, book, community.id, resource.id, kind) * gate * await method_factor(ctx, book, community.id, kind, workers)
    if kind is ExtractionKind.FISHING:
        raw *= fish_factor(ctx.rules, book.pollution.get(region_key(book, resource.id))) * await catch_factor(ctx.session, ctx.rules, resource.id)
    if kind is ExtractionKind.FARMING:
        raw *= await draught(ctx, community.id) * await fertilised(ctx.session, ctx.rules, community.id)
    else:
        raw *= await step_here(ctx, community.id, DivineScale.PRODUCTIVITY, ctx.rules.dominion.output_per_step_pct)
    if kind is ExtractionKind.MINING:
        raw *= await blasted(ctx.session, ctx.rules, community.id)
        ladder = await cosmography_of(ctx.session)
        raw *= ladder.pull(ctx.rules, ladder.place_world_id(resource.world_id)).ore
    return max(0, min(profile.reserve, round_half_up(raw)))


def hazard_chance(rules: Rules, kind: HazardKind, difficulty: int, engineering: int) -> int:
    table = rules.mining_hazards
    base = {
        HazardKind.CAVE_IN: table.cave_in_pct,
        HazardKind.FLOODED_SHAFT: table.cave_in_pct,
        HazardKind.FELLING_ACCIDENT: table.felling_pct,
        HazardKind.DROWNING: table.drowning_pct,
        HazardKind.GORING: table.goring_pct,
    }[kind]
    averted = max(0.0, 1 - engineering * table.engineering_pct_per_level / PERCENT)
    return round_half_up(base * max(difficulty, 1) / PERCENT * averted)


async def _hurt_named(ctx: TickContext, book: EconomyBook, community: EntityRow, hazard: HazardKind, resource: EntityRow) -> list[int]:
    kind, words, damage = HAZARD_HARM[hazard]
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
        await apply_hits(ctx, mortal, Harm(damage, cause, words, kind=kind, severity=3, event_entity_id=resource.id))
        hurt.append(mortal.id)
    return hurt


async def _open_cavern(ctx: TickContext, resource: EntityRow) -> EntityRow:
    rng = ctx.rng(f"cavern.{resource.id}")
    return await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.SPECIES,
            name=f"Deep Thing of {resource.name}",
            body=f"Something woke when the galleries of {resource.name} broke into a cavern below.",
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
        if ctx.rng(f"cavern.roll.{resource.id}").chance(table.cavern_chance):
            cavern = await _open_cavern(ctx, resource)
    woodcutters_counted = several(killed, "woodcutter", "woodcutters")
    words = {
        HazardKind.CAVE_IN: f"The galleries of {resource.name} caved in on the miners of {community.name}: {killed} died and {maimed} were maimed",
        HazardKind.FLOODED_SHAFT: f"Water broke into the shafts of {resource.name}: {killed} of {community.name} drowned",
        HazardKind.FELLING_ACCIDENT: f"Falling trees at {resource.name} killed {woodcutters_counted} of {community.name} and crippled {maimed}",
        HazardKind.DROWNING: f"Rough water at {resource.name} took {several(killed, 'fisher', 'fishers')} of {community.name}",
        HazardKind.GORING: f"The herds of {resource.name} gored {several(killed, 'herder', 'herders')} of {community.name}",
    }[hazard]
    tail = f"; the collapse broke into a cavern and {cavern.name} came out of the dark" if cavern is not None else ""
    sealed = "; the mine is sealed" if hazard is HazardKind.CAVE_IN else ""
    ids = [resource.id, community.id, *hurt, *([cavern.id] if cavern is not None else [])]
    await ctx.chronicle(
        ChronicleKind.DISASTER, f"{words}{sealed}{tail}.", template_key=f"mining.{hazard.value}", entity_ids=ids, place_entity_id=resource.location_id
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
    if spec.hazard is None or workers <= 0:
        return None
    hazard = spec.hazard
    region = book.ground.region_of(resource.id)
    if hazard is HazardKind.CAVE_IN and region is not None and region.rainfall >= ctx.rules.mining_hazards.flood_rainfall:
        hazard = HazardKind.FLOODED_SHAFT
    chance = hazard_chance(ctx.rules, hazard, profile.extraction_difficulty, book.skill(community.id, SkillKind.ENGINEERING))
    if hazard in (HazardKind.CAVE_IN, HazardKind.FLOODED_SHAFT):
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


async def extract(ctx: TickContext, book: EconomyBook, resource: EntityRow, profile: ResourceProfileRow, tally: ExtractionTally) -> int:
    reconcile(resource, profile)
    if not profile.revealed or (profile.sealed_until_epoch is not None and profile.sealed_until_epoch >= ctx.epoch):
        return 0
    kind = extraction_kind(profile)
    produced = 0
    for owner_id in book.owners.get(resource.id, []):
        owner = book.entities.get(owner_id)
        community = book.community_of(owner_id)
        if owner is None or community is None or profile.reserve <= 0:
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
        if output <= 0:
            if knowledge_gate(ctx.rules, book, profile, community.id) <= 0:
                tally.gated += 1
            continue
        write_reserve(resource, profile, profile.reserve - output)
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
