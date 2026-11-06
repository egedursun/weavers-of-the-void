from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.chronicle import write_line
from aerona.agents.context.briefs import son_brief
from aerona.agents.context.scope import load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.stats import stats_from
from aerona.agents.summoner import NO_PARENT, insert_son
from aerona.agents.text import sanitize
from aerona.cartography.terrain import default_terrain
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import DEFAULT_FIRST_SONS, RARITY_LABELS
from aerona.core.errors import ConflictError
from aerona.core.random import SeededRandom
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import LoreLanguage, WorldType
from aerona.domain.models.genesis import GenesisSettings
from aerona.domain.models.profiles import TravelResource
from aerona.engine.cosmos.birth import phonology_from
from aerona.engine.cosmos.resources import DepositSpec, create_cosmic_deposit
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.genesis import CreatorPortraitContext, GenesisContext, GenesisWizardContext
from aerona.prompts.schemas.genesis import GenesisOutput
from aerona.prompts.schemas.shared import CreatorGodOutput
from aerona.rules.registry import Rules

PERCENT = 100
GENESIS_STREAM = "agents.genesis"
GENESIS_COSMIC_STREAM = "agents.genesis.cosmic"
FIRST_EPOCH = 1
FIRST_ORBIT = 1.0


@dataclass(frozen=True)
class GenesisRequest:
    god_name: str
    seed_idea: str
    lore_language: LoreLanguage
    rng_seed: int
    tone: str | None = None
    settings: GenesisSettings | None = None
    first_sons: tuple[Rarity, ...] = DEFAULT_FIRST_SONS


def wizard_text(rules: Rules, settings: GenesisSettings | None) -> str | None:
    if settings is None:
        return None
    context = GenesisWizardContext(
        rules=rules,
        template_name=settings.template.value if settings.template else None,
        magic=settings.magic,
        darkness=settings.darkness,
        technology=settings.technology,
        language=settings.language_texture,
        cosmos=settings.cosmos_size,
    )
    return render(PromptId.GENESIS_WIZARD_SETTINGS, context)


def biased(value: int, settings: GenesisSettings | None, key: str) -> int:
    if settings is None:
        return value
    shift = {"magic": settings.magic, "danger": settings.darkness}.get(key)
    return max(0, min(PERCENT, (value + shift) // 2 if shift is not None else value))


async def genesis(runtime: AgentRuntime, request: GenesisRequest, rules: Rules) -> int:
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
        wizard_text=wizard_text(rules, settings),
        first_son_rarities=[RARITY_LABELS[rarity] for rarity in request.first_sons],
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
        world_id = await write_genesis(session, rules, request, output)
    runtime.publish(EventKind.GENESIS_FINISHED, {"world_id": world_id})
    return world_id


async def write_genesis(session: AsyncSession, rules: Rules, request: GenesisRequest, output: GenesisOutput) -> int:
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
    terrain = default_terrain(WorldType.ORDINARY, rules)
    world = await WorldRepository(session).create_world(
        WorldDraft(
            name=await NameRepository(session).unique_name(output.world_name),
            world_type=WorldType.ORDINARY,
            orbit=FIRST_ORBIT,
            terrain_seed=f"{output.world_name}:{request.rng_seed}",
            terrain_sea=(terrain.sea_pct or 0) / PERCENT,
            terrain_mountains=(terrain.mountains_pct or 0) / PERCENT,
            terrain_humidity=(terrain.moisture_pct or 0) / PERCENT,
            danger=biased(rules.world_birth.danger_base, settings, "danger"),
            created_epoch=FIRST_EPOCH,
            phonology=phonology_from(output.naming, rules),
            cosmology=sanitize(output.cosmology),
        )
    )
    cosmos.primary_world_id = world.id
    entities = EntityRepository(session)
    genesis_rules = rules.genesis
    regions = []
    for region in output.regions[: max(genesis_rules.regions_min, genesis_rules.regions_max)]:
        stats = {
            "breadth": genesis_rules.region_breadth,
            "danger": biased(region.danger, settings, "danger"),
            "fertility": region.fertility,
            "magic": biased(region.magic, settings, "magic"),
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
    text = f"{creator.name}{title}, named the void {world.name}, separated by their own hand the lands and waters of {names} and hung {star.name} in the sky."
    await write_line(
        session, rules, FIRST_EPOCH, ChronicleKind.CREATOR_HAND, text, key="genesis.world", entity_ids=[*(region.id for region in regions), star.id]
    )
    for son in sons:
        domains = f"{DOMAIN_LABELS[son.domain_primary]} and {DOMAIN_LABELS[son.domain_secondary]}"
        line = f"{creator.name}'s son {son.name}, {son.title}, awoke with the domains {domains}."
        await write_line(session, rules, FIRST_EPOCH, ChronicleKind.BIRTH, line, key="genesis.son", son_id=son.id)
    await session.flush()
    return world.id


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
