from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.chronicle import write_line
from aerona.agents.context.briefs import son_brief
from aerona.agents.context.creation import creation_text
from aerona.agents.context.scope import load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.stats import stats_from
from aerona.agents.summoner import NO_PARENT, insert_son
from aerona.agents.text import sanitize
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import DEFAULT_FIRST_SONS, RARITY_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError
from aerona.core.random import SeededRandom
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository, normalize_name
from aerona.db.repositories.sons import SonRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import DimensionKind, GalaxyType, WorldAge
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.domain.enums.world import Atmosphere, ClimateEra, CosmosShape, CosmosSize, Gravity, LoreLanguage, WorldType
from aerona.domain.models.genesis import GenesisOutcome, GenesisSettings
from aerona.domain.models.profiles import TravelResource
from aerona.engine.cosmos.birth import phonology_from
from aerona.engine.cosmos.ladder import DimensionDraft, GalaxyDraft, create_dimension, create_galaxy, ensure_ladder
from aerona.engine.cosmos.resources import DepositSpec, create_cosmic_deposit
from aerona.engine.cosmos.stars import StarSpec, create_star
from aerona.engine.cosmos.world_types import mechanics_of
from aerona.engine.primitives.numbers import clamp_float, clamp_int
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId
from aerona.prompts.contexts.genesis import CreatorPortraitContext, GenesisContext
from aerona.prompts.schemas.genesis import GenesisLayerOutput, GenesisOutput, GenesisWorldOutput
from aerona.prompts.schemas.shared import CreatorGodOutput
from aerona.rules.registry import Rules

GENESIS_STREAM = "agents.genesis"
GENESIS_COSMIC_STREAM = "agents.genesis.cosmic"
GENESIS_CLIMATE_STREAM = "agents.genesis.climate"
GENESIS_STAR_STREAM = "agents.genesis.star"
SUN_SUFFIX = "Sun"
FIRST_EPOCH = 1
FIRST_ORBIT = 1.0
MOISTURE_FLOOR = -PERCENT
LAYER_FALLBACK_KIND = DimensionKind.PARALLEL
LAYER_GALAXY_TYPE = GalaxyType.SPIRAL


@dataclass(frozen=True)
class GenesisRequest:
    god_name: str
    seed_idea: str
    lore_language: LoreLanguage
    rng_seed: int
    tone: str | None = None
    settings: GenesisSettings | None = None
    first_sons: tuple[Rarity, ...] = DEFAULT_FIRST_SONS


@dataclass(frozen=True)
class FirstWorld:
    world_type: WorldType
    gravity: Gravity
    atmosphere: Atmosphere
    sea_pct: int
    mountains_pct: int
    moisture_pct: int
    climate_era: ClimateEra
    age: WorldAge


def layered(settings: GenesisSettings | None) -> bool:
    return settings is not None and settings.cosmos_size is not CosmosSize.SINGLE and settings.cosmos_shape is CosmosShape.LAYERED


def first_world(settings: GenesisSettings | None, chosen: GenesisWorldOutput) -> FirstWorld:
    world_type = settings.world_type if settings is not None and settings.world_type is not None else chosen.type
    mechanics = mechanics_of(world_type)
    sea = settings.sea_pct if settings is not None and settings.sea_pct is not None else chosen.sea_pct
    mountains = settings.mountains_pct if settings is not None and settings.mountains_pct is not None else chosen.mountains_pct
    moisture = settings.moisture_pct if settings is not None and settings.moisture_pct is not None else chosen.moisture_pct
    return FirstWorld(
        world_type=world_type,
        gravity=mechanics.forced_gravity or chosen.gravity,
        atmosphere=mechanics.forced_atmosphere or chosen.atmosphere,
        sea_pct=clamp_int(sea, 0, PERCENT),
        mountains_pct=clamp_int(mountains, 0, PERCENT),
        moisture_pct=clamp_int(moisture, MOISTURE_FLOOR, PERCENT),
        climate_era=settings.climate_era if settings is not None and settings.climate_era is not None else chosen.climate_era,
        age=settings.world_age if settings is not None and settings.world_age is not None else chosen.age,
    )


def first_climate_epochs(rules: Rules, rng_seed: int) -> int:
    table = rules.climate_effects
    return table.first_duration + SeededRandom.for_epoch(rng_seed, FIRST_EPOCH, GENESIS_CLIMATE_STREAM).die(table.first_die)


async def genesis(runtime: AgentRuntime, request: GenesisRequest, rules: Rules) -> GenesisOutcome:
    runtime.require_llm("genesis")
    async with runtime.database.read() as session:
        if await CosmosRepository(session).get() is not None:
            raise ConflictError("A world already exists.")
    settings = request.settings
    context = GenesisContext(
        lore_language=request.lore_language,
        rules=rules,
        god_name=request.god_name,
        seed=(settings.seed_idea if settings and settings.seed_idea else request.seed_idea),
        tone=(settings.tone if settings and settings.tone else request.tone),
        wizard_text=creation_text(rules, settings, for_genesis=True) if settings is not None else None,
        first_son_rarities=[RARITY_LABELS[rarity] for rarity in request.first_sons],
        layered=layered(settings),
    )
    runtime.step("Genesis is writing the world…")
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.GENESIS,
        system=(PromptId.GENESIS_SYSTEM, context),
        user=(PromptId.GENESIS_USER, context),
        output=GenesisOutput,
        time_limit=rules.genesis.timeout,
    )
    async with runtime.database.write() as session:
        outcome = await write_genesis(session, rules, request, output)
    runtime.publish(EventKind.GENESIS_FINISHED, {"world_id": outcome.world_id})
    return outcome


async def kindle_sun(session: AsyncSession, rules: Rules, request: GenesisRequest, output: GenesisOutput) -> StarRow:
    chosen = output.star
    name = chosen.name.strip() or f"{output.world_name.strip()} {SUN_SUFFIX}"
    if normalize_name(name) == normalize_name(output.world_name):
        name = f"{output.world_name.strip()} {SUN_SUFFIX}"
    birth = rules.world_birth
    rng = SeededRandom.for_epoch(request.rng_seed, FIRST_EPOCH, GENESIS_STAR_STREAM)
    spec = StarSpec(name, chosen.type, birth.star_brightness_base, birth.star_brightness_die, sanitize(chosen.description) or None)
    return await create_star(session, rules, rng, FIRST_EPOCH, spec)


async def open_layer(session: AsyncSession, rules: Rules, world: WorldRow, *, settings: GenesisSettings, layer: GenesisLayerOutput | None) -> int:
    cosmos = await CosmosRepository(session).require_cosmos()
    kind = settings.layer_kind or (layer.kind if layer is not None else LAYER_FALLBACK_KIND)
    if kind is DimensionKind.PRIME:
        kind = LAYER_FALLBACK_KIND
    name = layer.name.strip() if layer is not None and layer.name.strip() else f"{cosmos.name} Beyond"
    description = sanitize(layer.description) if layer is not None else None
    dimension = await create_dimension(session, rules, DimensionDraft(name, kind, FIRST_EPOCH, description=description or None))
    galaxy = await create_galaxy(session, rules, GalaxyDraft(f"{dimension.name} Galaxy", LAYER_GALAXY_TYPE, FIRST_EPOCH, dimension_id=dimension.id))
    text = f"Beside {world.name} lies {dimension.name}, a second layer of the cosmos."
    await write_line(session, rules, FIRST_EPOCH, ChronicleKind.CREATOR_HAND, text, key="genesis.layer")
    return galaxy.id


async def write_genesis(session: AsyncSession, rules: Rules, request: GenesisRequest, output: GenesisOutput) -> GenesisOutcome:
    settings = request.settings
    cosmos_repository = CosmosRepository(session)
    cosmos = await cosmos_repository.create(
        CosmosDraft(
            name=output.world_name.strip(),
            rng_seed=request.rng_seed,
            lore_language=request.lore_language,
            seed_idea=request.seed_idea,
            cosmology=sanitize(output.cosmology),
            tone=sanitize(output.tone),
            rules=rules,
            genesis_settings=settings,
        )
    )
    cosmos.age_cycle = settings.age_cycle if settings is not None else AgeCycle.LINEAR
    mood = rules.creator
    god = output.god
    creator = await cosmos_repository.create_creator(
        CreatorDraft(
            name=request.god_name,
            essence=rules.balance.creator_starting_essence,
            mood_contentment=mood.start_contentment,
            mood_anger=mood.start_wrath,
            mood_interest=mood.start_attention,
            mood_loneliness=mood.start_loneliness,
            title=god.title,
            appearance=god.appearance,
            temperament=god.temperament,
        )
    )
    creator.image_prompt = god.image_prompt.strip() or None
    shape = first_world(settings, output.world)
    sun = await kindle_sun(session, rules, request, output)
    world = await WorldRepository(session).create_world(
        WorldDraft(
            name=await NameRepository(session).unique_name(output.world_name),
            world_type=shape.world_type,
            orbit=FIRST_ORBIT,
            terrain_seed=f"{output.world_name}:{request.rng_seed}",
            terrain_sea=shape.sea_pct / PERCENT,
            terrain_mountains=shape.mountains_pct / PERCENT,
            terrain_humidity=clamp_float(shape.moisture_pct / PERCENT, -1.0, 1.0),
            danger=rules.world_birth.danger_base,
            created_epoch=FIRST_EPOCH,
            star_id=sun.id,
            gravity=shape.gravity,
            atmosphere=shape.atmosphere,
            phonology=phonology_from(output.naming, rules),
            cosmology=sanitize(output.cosmology),
        )
    )
    begin_world(world, shape, first_climate_epochs(rules, request.rng_seed))
    cosmos.primary_world_id = world.id
    await ensure_ladder(session, rules)
    session.add(
        StorytellerRow(world_id=world.id, profile=settings.storyteller if settings is not None else StorytellerProfile.CYCLIC, recent_kinds={}, locked=[])
    )
    entities = EntityRepository(session)
    genesis_rules = rules.genesis
    regions = []
    for region in output.regions[: max(genesis_rules.regions_min, genesis_rules.regions_max)]:
        stats = {
            "breadth": genesis_rules.region_breadth,
            "danger": region.danger,
            "fertility": region.fertility,
            "magic": region.magic,
        }
        regions.append(
            await entities.create(
                EntityDraft(
                    name=await NameRepository(session).unique_name(region.name),
                    entity_type=EntityType.REGION,
                    description=sanitize(region.description),
                    stats=stats_from(EntityType.REGION, stats, rules),
                    power_level=genesis_rules.region_power,
                    origin=EntityOrigin.CREATOR,
                    birth_epoch=FIRST_EPOCH,
                    world_id=world.id,
                    subtype=region.subtype,
                    is_water=region.water,
                    image_prompt=region.image_prompt or None,
                    split_title=False,
                )
            )
        )
    cosmic = output.cosmic_resource
    if cosmic.name.strip():
        travel = TravelResource(
            name=cosmic.name.strip(), description=cosmic.description.strip(), rule=cosmic.rule.strip(), side_effect=cosmic.side_effect.strip()
        )
        cosmos.travel_resource = travel
        cosmic_rng = SeededRandom.for_epoch(request.rng_seed, FIRST_EPOCH, GENESIS_COSMIC_STREAM)
        birth = rules.world_birth
        deposit = await create_cosmic_deposit(
            session,
            rules,
            FIRST_EPOCH,
            travel,
            DepositSpec(
                region=regions[max(0, min(cosmic.region_index, len(regions) - 1))],
                abundance=birth.cosmic_deposit_abundance_base + cosmic_rng.die(birth.cosmic_deposit_abundance_die),
                value=birth.cosmic_deposit_value,
                might=birth.cosmic_deposit_might_base + cosmic_rng.die(birth.cosmic_deposit_might_die),
                power_level=birth.cosmic_deposit_power,
                name=f"{travel.name} Deposit",
                origin=EntityOrigin.CREATOR,
            ),
        )
        await entities.add_flag(deposit.id, EntityFlag.FIXED_NAME)
        deposit.image_prompt = cosmic.image_prompt or None
    sky = output.first_celestial
    star = await entities.create(
        EntityDraft(
            name=await NameRepository(session).unique_name(sky.name),
            entity_type=EntityType.CELESTIAL,
            description=sanitize(sky.description),
            stats=stats_from(EntityType.CELESTIAL, {"brightness": genesis_rules.sky_brightness, "influence": genesis_rules.sky_influence}, rules),
            power_level=genesis_rules.sky_power,
            origin=EntityOrigin.CREATOR,
            birth_epoch=FIRST_EPOCH,
            world_id=world.id,
            subtype=sky.subtype,
            domain=sky.domain,
            image_prompt=sky.image_prompt or None,
            split_title=False,
        )
    )
    world.epoch_star_entity_id = star.id
    rng = SeededRandom.for_epoch(request.rng_seed, FIRST_EPOCH, GENESIS_STREAM)
    sons: list[SonRow] = []
    for profile, rarity in zip(output.sons, request.first_sons, strict=False):
        sons.append(await insert_son(session, rules, rng, profile, rarity=rarity, epoch=FIRST_EPOCH, parentage=NO_PARENT, world_id=world.id))
    repository = SonRepository(session)
    for relation in output.relations:
        if relation.i != relation.j and relation.i < len(sons) and relation.j < len(sons):
            await repository.change_relation(sons[relation.i].id, sons[relation.j].id, relation.value, relation.note)
    names = ", ".join(region.name for region in regions)
    title = f", {creator.title}" if creator.title else ""
    text = f"{creator.name}{title} made the world {world.name} around the star {sun.name}, its first regions {names}, and {star.name} in its sky."
    await write_line(
        session, rules, FIRST_EPOCH, ChronicleKind.CREATOR_HAND, text, key="genesis.world", entity_ids=[*(region.id for region in regions), star.id]
    )
    for son in sons:
        domains = f"{DOMAIN_LABELS[son.domain_primary]} and {DOMAIN_LABELS[son.domain_secondary]}"
        line = f"{creator.name}'s son {son.name}, {son.title}, awoke with the domains {domains}."
        await write_line(session, rules, FIRST_EPOCH, ChronicleKind.BIRTH, line, key="genesis.son", son_id=son.id)
    layer_galaxy_id = await open_layer(session, rules, world, settings=settings, layer=output.layer) if settings is not None and layered(settings) else None
    await session.flush()
    return GenesisOutcome(world_id=world.id, layer_galaxy_id=layer_galaxy_id)


def begin_world(world: WorldRow, shape: FirstWorld, climate_epochs: int) -> None:
    world.climate_era = shape.climate_era
    world.climate_epochs_left = climate_epochs
    world.climate_since_epoch = FIRST_EPOCH
    world.age_stage = shape.age


async def creator_portrait(runtime: AgentRuntime) -> CreatorGodOutput:
    runtime.require_llm("creator portrait")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        sons = list(await SonRepository(session).living())
        context = CreatorPortraitContext(
            lore_language=scope.cosmos.lore_language,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope),
            god_name=scope.creator.name,
            sons=[son_brief(son) for son in sons],
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.CREATOR_PORTRAIT,
        system=(PromptId.CREATOR_PORTRAIT_SYSTEM, context),
        user=(PromptId.CREATOR_PORTRAIT_USER, context),
        output=CreatorGodOutput,
    )
    async with runtime.database.write() as session:
        creator = await CosmosRepository(session).require_creator()
        creator.title = output.title.strip() or creator.title
        creator.appearance = sanitize(output.appearance) or creator.appearance
        creator.temperament = sanitize(output.temperament) or creator.temperament
        creator.image_prompt = output.image_prompt.strip() or creator.image_prompt
    runtime.note(f"{scope.creator.name}'s likeness was redrawn.")
    return output
