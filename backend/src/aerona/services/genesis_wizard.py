import secrets
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.climate import CLIMATES
from aerona.catalog.cosmography import DIMENSION_KINDS, WORLD_AGE_LABELS
from aerona.catalog.genesis import (
    AGE_CYCLE_LABELS,
    COSMOS_LABELS,
    LAYER_KINDS,
    LORE_LANGUAGE_LABELS,
    SHAPE_HINTS,
    SHAPE_LABELS,
    STORYTELLER_LABELS,
    TECHNOLOGY_LABELS,
    TEMPLATES,
    TEXTURE_LABELS,
    WizardTemplate,
)
from aerona.catalog.image_styles import CUSTOM_STYLE_MAX_LENGTH
from aerona.catalog.rarities import DEFAULT_FIRST_SONS
from aerona.catalog.technology import ERA_LEVEL
from aerona.catalog.worlds import WORLD_TYPES
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.core.grammar import ordinal_word, several, spoken
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import DimensionRow, GalaxyRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.cosmography import DimensionKind, RiftCause, WorldAge
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.rarity import RARITY_ORDER, Rarity
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.domain.enums.world import (
    ClimateEra,
    CosmosShape,
    CosmosSize,
    GenesisTemplate,
    ImageStyle,
    LanguageTexture,
    LoreLanguage,
    TechnologyEra,
    WorldType,
)
from aerona.domain.models.genesis import MOISTURE_FLOOR, PREHISTORY_CEILING, TECH_LEVEL_CEILING, GenesisOutcome, GenesisSettings
from aerona.engine.cosmos.control import tear_rift
from aerona.engine.made.genesis import seed_made_world
from aerona.engine.prehistory.control import configure
from aerona.engine.prehistory.run import run_prehistory
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.lore_ports import GenesisRequest, LorePorts
from aerona.services.player.ports import WorldCreationRequest

PERCENT = 100
DEFAULT_REGION_VALUE = 50
TONE_MAX_LENGTH = 300
SEED_MAX_LENGTH = 2000
SEED_BITS = 62
EXTRA_WORLD_INSPIRATION = "The {ordinal} world of this creation, grown from the same seed as the first world: {seed}"
LAYER_INSPIRATION = " It lies in {layer}, the second layer of the cosmos."
PEOPLES_WAKING = "The first mortal peoples are waking."
STAGE_GENESIS = "genesis"
STAGE_PEOPLES = "peoples"
STAGE_WORLDS = "worlds"
STAGE_PREHISTORY = "prehistory"
STAGE_DONE = "done"
FIRST_EXTRA_WORLD = 2


class WizardInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    template: str | None = None
    magic: Any = None
    danger: Any = None
    technology: str | None = None
    technology_levels: Any = None
    language: str | None = None
    peoples: Any = None
    cosmos: str | None = None
    shape: str | None = None
    layer_kind: str | None = None
    storyteller: str | None = None
    age_cycle: str | None = None
    world_type: str | None = None
    sea_pct: Any = None
    mountains_pct: Any = None
    moisture_pct: Any = None
    climate_era: str | None = None
    world_age: str | None = None
    prehistory_epochs: Any = None
    made_minds: Any = None
    information_reach: Any = None
    tone: str | None = None
    seed: str | None = None


@dataclass(frozen=True)
class PrehistoryOptions:
    default: int
    maximum: int


@dataclass(frozen=True)
class CosmosOption:
    size: CosmosSize
    label: str
    worlds: int


@dataclass(frozen=True)
class ShapeOption:
    shape: CosmosShape
    label: str
    hint: str


@dataclass(frozen=True)
class WorldTypeOption:
    world_type: WorldType
    label: str
    description: str


@dataclass(frozen=True)
class ClimateOption:
    era: ClimateEra
    label: str
    description: str


@dataclass(frozen=True)
class LayerOption:
    kind: DimensionKind
    label: str
    description: str


@dataclass(frozen=True)
class FirstSonsOptions:
    minimum: int
    maximum: int
    rarities: list[Rarity]
    default: list[Rarity]


@dataclass(frozen=True)
class WizardOptions:
    technology: dict[TechnologyEra, str]
    technology_levels: dict[TechnologyEra, int]
    technology_level_max: int
    language: dict[LanguageTexture, str]
    cosmos: list[CosmosOption]
    shapes: list[ShapeOption]
    layer_kinds: list[LayerOption]
    world_types: list[WorldTypeOption]
    climate_eras: list[ClimateOption]
    world_ages: dict[WorldAge, str]
    storyteller: dict[StorytellerProfile, str]
    age_cycles: dict[AgeCycle, str]
    lore_languages: dict[LoreLanguage, str]
    templates: list[WizardTemplate]
    first_sons: FirstSonsOptions
    prehistory: PrehistoryOptions


@dataclass(frozen=True)
class GenesisCommand:
    creator_name: str
    seed: str
    tone: str | None = None
    lore_language: LoreLanguage = LoreLanguage.ENGLISH
    wizard: WizardInput | None = None
    first_sons: tuple[Rarity, ...] | None = None
    image_style: ImageStyle = ImageStyle.PHOTOREAL
    image_style_custom: str = ""


def extra_worlds(rules: Rules, size: CosmosSize) -> int:
    return {CosmosSize.SINGLE: 0, CosmosSize.SMALL: rules.setup_wizard.small_cosmos_worlds, CosmosSize.LARGE: rules.setup_wizard.large_cosmos_worlds}[size]


def options(rules: Rules) -> WizardOptions:
    return WizardOptions(
        technology=dict(TECHNOLOGY_LABELS),
        technology_levels=dict(ERA_LEVEL),
        technology_level_max=TECH_LEVEL_CEILING,
        language=dict(TEXTURE_LABELS),
        cosmos=[CosmosOption(size, COSMOS_LABELS[size], 1 + extra_worlds(rules, size)) for size in CosmosSize],
        shapes=[ShapeOption(shape, SHAPE_LABELS[shape], SHAPE_HINTS[shape]) for shape in CosmosShape],
        layer_kinds=[LayerOption(kind, DIMENSION_KINDS[kind].label, DIMENSION_KINDS[kind].description) for kind in LAYER_KINDS],
        world_types=[WorldTypeOption(kind, spec.label, spec.description) for kind, spec in WORLD_TYPES.items()],
        climate_eras=[ClimateOption(era, spec.label, spec.description) for era, spec in CLIMATES.items()],
        world_ages=dict(WORLD_AGE_LABELS),
        storyteller=dict(STORYTELLER_LABELS),
        age_cycles=dict(AGE_CYCLE_LABELS),
        lore_languages=dict(LORE_LANGUAGE_LABELS),
        templates=list(TEMPLATES.values()),
        first_sons=FirstSonsOptions(
            minimum=rules.setup_wizard.first_sons_min,
            maximum=rules.setup_wizard.first_sons_max,
            rarities=allowed_first_son_rarities(rules),
            default=list(DEFAULT_FIRST_SONS),
        ),
        prehistory=PrehistoryOptions(default=rules.prehistory.epochs, maximum=PREHISTORY_CEILING),
    )


def allowed_first_son_rarities(rules: Rules) -> list[Rarity]:
    return [rarity for rarity in RARITY_ORDER if rarity.rank <= rules.setup_wizard.first_sons_top_rarity_rank]


def resolve_first_sons(rules: Rules, requested: tuple[Rarity, ...] | None) -> tuple[Rarity, ...]:
    if requested is None:
        return DEFAULT_FIRST_SONS
    wizard = rules.setup_wizard
    if not wizard.first_sons_min <= len(requested) <= wizard.first_sons_max:
        raise ValidationFailedError(f"Choose between {wizard.first_sons_min} and {wizard.first_sons_max} first sons.")
    allowed = allowed_first_son_rarities(rules)
    for rarity in requested:
        if rarity not in allowed:
            raise ValidationFailedError(f"A first son cannot be of {spoken(rarity)} rarity.")
    return tuple(sorted(requested, key=lambda item: item.rank))


def _bounded(value: Any, fallback: int | None, low: int, high: int) -> int | None:
    if value is None or value == "":
        return fallback
    try:
        return max(low, min(high, round(float(value))))
    except (TypeError, ValueError):
        return fallback


def _levels(value: Any) -> dict[TechFamily, int]:
    if not isinstance(value, dict):
        return {}
    known = {family.value: family for family in TechFamily}
    levels = {known[key]: _bounded(level, None, 0, TECH_LEVEL_CEILING) for key, level in value.items() if key in known}
    return {family: level for family, level in levels.items() if level is not None}


def _percent(value: Any, fallback: int) -> int:
    bounded = _bounded(value, fallback, 0, PERCENT)
    return fallback if bounded is None else bounded


def _choice[E: (TechnologyEra, LanguageTexture, CosmosSize, CosmosShape, StorytellerProfile, AgeCycle)](kind: type[E], value: str | None, fallback: E) -> E:
    try:
        return kind(value) if value is not None else fallback
    except ValueError:
        return fallback


def _optional[E: (WorldType, ClimateEra, WorldAge, DimensionKind)](kind: type[E], value: str | None, fallback: E | None) -> E | None:
    if value is None or value == "":
        return fallback
    try:
        return kind(value)
    except ValueError:
        return fallback


def _layer_kind(value: str | None) -> DimensionKind | None:
    kind = _optional(DimensionKind, value, None)
    return kind if kind in LAYER_KINDS else None


def sanitize(rules: Rules, raw: WizardInput) -> GenesisSettings:
    wizard = rules.setup_wizard
    key = raw.template if raw.template in {item.value for item in GenesisTemplate} else None
    template = TEMPLATES[GenesisTemplate(key)] if key is not None else None
    magic = raw.magic if raw.magic not in (None, "") else (template.magic if template else None)
    danger = raw.danger if raw.danger not in (None, "") else (template.danger if template else None)
    peoples = _bounded(raw.peoples, template.peoples if template else wizard.peoples, 1, wizard.peoples_max) or wizard.peoples
    tone = (raw.tone or (template.tone if template else "") or "").strip()[:TONE_MAX_LENGTH] or None
    seed = (raw.seed or (template.seed if template else "") or "").strip()[:SEED_MAX_LENGTH] or None
    size = _choice(CosmosSize, raw.cosmos or (template.cosmos.value if template else None), CosmosSize.SINGLE)
    chosen_shape = _choice(CosmosShape, raw.shape or (template.shape.value if template else None), CosmosShape.ONE_SUN)
    shape = chosen_shape if size is not CosmosSize.SINGLE else CosmosShape.ONE_SUN
    return GenesisSettings(
        template=template.key if template else None,
        magic=_percent(magic, wizard.magic),
        danger=_percent(danger, wizard.danger),
        technology=_choice(TechnologyEra, raw.technology or (template.technology.value if template else None), TechnologyEra.IRON),
        technology_levels=_levels(raw.technology_levels),
        language_texture=_choice(LanguageTexture, raw.language or (template.language.value if template else None), LanguageTexture.FREE),
        peoples=peoples,
        cosmos_size=size,
        cosmos_shape=shape,
        layer_kind=_layer_kind(raw.layer_kind) if shape is CosmosShape.LAYERED else None,
        storyteller=_choice(StorytellerProfile, raw.storyteller or (template.storyteller.value if template else None), StorytellerProfile.CYCLIC),
        age_cycle=_choice(AgeCycle, raw.age_cycle, AgeCycle.LINEAR),
        world_type=_optional(WorldType, raw.world_type, template.world_type if template else None),
        sea_pct=_bounded(raw.sea_pct, None, 0, PERCENT),
        mountains_pct=_bounded(raw.mountains_pct, None, 0, PERCENT),
        moisture_pct=_bounded(raw.moisture_pct, None, MOISTURE_FLOOR, PERCENT),
        climate_era=_optional(ClimateEra, raw.climate_era, template.climate_era if template else None),
        world_age=_optional(WorldAge, raw.world_age, template.world_age if template else None),
        prehistory_epochs=_bounded(raw.prehistory_epochs, rules.prehistory.epochs, 0, PREHISTORY_CEILING) or 0,
        made_minds=_bounded(raw.made_minds, template.made_minds if template else None, 0, PERCENT),
        information_reach=_bounded(raw.information_reach, template.information_reach if template else None, 0, PERCENT),
        tone=tone,
        seed_idea=seed,
    )


def pulled(value: int | None, target: int, pull_pct: int) -> int:
    current = DEFAULT_REGION_VALUE if value is None else value
    return round(current * (PERCENT - pull_pct) / PERCENT + target * pull_pct / PERCENT)


async def pull_regions(session: AsyncSession, rules: Rules, settings: GenesisSettings) -> int:
    pull = rules.setup_wizard.setting_pull_pct
    cosmos = await CosmosRepository(session).require_cosmos()
    world_id = cosmos.primary_world_id
    regions = list(
        await session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world_id)
        )
    )
    for region in regions:
        set_stats(region, magic=pulled(stat(region, "magic"), settings.magic, pull), danger=pulled(stat(region, "danger"), settings.danger, pull))
    world = await session.get(WorldRow, world_id) if world_id is not None else None
    if world is not None and regions:
        world.danger = round(sum(stat(region, "danger") or 0 for region in regions) / len(regions))
    await session.flush()
    return len(regions)


async def save_settings(session: AsyncSession, settings: GenesisSettings) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.genesis_settings = settings
    await session.flush()


def extra_world_order(settings: GenesisSettings, seed: str, number: int, *, sun: int | None, layer: tuple[int, str] | None) -> WorldCreationRequest:
    inspiration = EXTRA_WORLD_INSPIRATION.format(ordinal=ordinal_word(number).lower(), seed=seed)
    if layer is not None:
        inspiration += LAYER_INSPIRATION.format(layer=layer[1])
    shared = settings.cosmos_shape is CosmosShape.ONE_SUN and sun is not None
    return WorldCreationRequest(
        world_type=None,
        inspiration=inspiration,
        star_id=sun if shared else None,
        parent_world_id=None,
        new_star=not shared,
        new_star_type=None,
        galaxy_id=layer[0] if layer is not None else None,
    )


class GenesisWizard:
    def __init__(self, database: Database, rules: Rules, ports: LorePorts, bus: EventBus | None = None) -> None:
        self._database = database
        self._rules = rules
        self._ports = ports
        self._bus = bus

    def _publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        if self._bus is not None:
            self._bus.publish(kind, payload)

    async def validate(self, command: GenesisCommand) -> GenesisSettings | None:
        if not command.creator_name.strip() or not command.seed.strip():
            raise ValidationFailedError("Creator name and world seed are required.")
        resolve_first_sons(self._rules, command.first_sons)
        if len(command.image_style_custom.strip()) > CUSTOM_STYLE_MAX_LENGTH:
            raise ValidationFailedError(f"The custom image style is limited to {several(CUSTOM_STYLE_MAX_LENGTH, 'character', 'characters')}.")
        if command.image_style is ImageStyle.CUSTOM and not command.image_style_custom.strip():
            raise ValidationFailedError("Describe the custom image style.")
        if self._ports.genesis is None:
            raise ConflictError("Genesis needs the language model, which is turned off.")
        async with self._database.read() as session:
            if await CosmosRepository(session).get() is not None:
                raise ConflictError("World already exists.")
        return sanitize(self._rules, command.wizard) if command.wizard is not None else None

    async def run(self, command: GenesisCommand, context: JobContext | None = None) -> dict[str, Any]:
        settings = await self.validate(command)
        author = self._ports.genesis
        if author is None:
            raise ConflictError("Genesis needs the language model, which is turned off.")
        seed = (settings.seed_idea if settings and settings.seed_idea else None) or command.seed.strip()
        tone = (settings.tone if settings and settings.tone else None) or command.tone
        request = GenesisRequest(
            creator_name=command.creator_name.strip(),
            seed=seed,
            tone=tone,
            lore_language=command.lore_language,
            rng_seed=secrets.randbits(SEED_BITS),
            settings=settings,
            first_sons=resolve_first_sons(self._rules, command.first_sons),
        )
        self._report(context, 0.05, STAGE_GENESIS)
        outcome = await author.create(request)
        async with self._database.write() as session:
            repository = CosmosRepository(session)
            cosmos = await repository.require_cosmos()
            if not cosmos.rules_snapshot:
                await repository.store_rules(self._rules)
            cosmos.image_style = command.image_style
            cosmos.image_style_custom = command.image_style_custom.strip() if command.image_style is ImageStyle.CUSTOM else ""
            if settings is not None:
                await save_settings(session, settings)
                await pull_regions(session, self._rules, settings)
            first_world = cosmos.primary_world_id
            home = await session.get(WorldRow, first_world) if first_world is not None else None
            sun = home.star_id if home is not None else None
            layer = await self._layer(session, outcome)
        self._publish(EventKind.GENESIS_FINISHED, {})
        peoples = settings.peoples if settings else self._rules.setup_wizard.peoples
        awakened: list[int] = []
        if self._ports.awakener is not None:
            self._report(context, 0.5, STAGE_PEOPLES)
            self._publish(EventKind.SYSTEM_NOTE, {"text": PEOPLES_WAKING})
            awakened = await self._ports.awakener.awaken(peoples, first_world)
        worlds: list[int] = []
        extra = extra_worlds(self._rules, settings.cosmos_size) if settings else 0
        if settings is not None and extra and self._ports.worlds is not None:
            self._report(context, 0.75, STAGE_WORLDS)
            for number in range(FIRST_EXTRA_WORLD, FIRST_EXTRA_WORLD + extra):
                worlds.append(await self._ports.worlds.create(extra_world_order(settings, seed, number, sun=sun, layer=layer)))
        if layer is not None and first_world is not None:
            await self._join_layer(first_world, layer[0], worlds[0] if worlds else None)
        if settings is not None and first_world is not None and (settings.made_minds is not None or settings.information_reach):
            await self._made_world([first_world, *worlds], settings)
        if settings is not None and settings.prehistory_epochs and first_world is not None:
            self._report(context, 0.9, STAGE_PREHISTORY)
            await self._prehistory(first_world, settings.prehistory_epochs)
        self._report(context, 1.0, STAGE_DONE)
        return {"peoples": awakened, "worlds": worlds}

    @staticmethod
    async def _layer(session: AsyncSession, outcome: GenesisOutcome) -> tuple[int, str] | None:
        galaxy = await session.get(GalaxyRow, outcome.layer_galaxy_id) if outcome.layer_galaxy_id is not None else None
        dimension = await session.get(DimensionRow, galaxy.dimension_id) if galaxy is not None and galaxy.dimension_id is not None else None
        return (galaxy.id, dimension.name) if galaxy is not None and dimension is not None else None

    async def _join_layer(self, first_world: int, galaxy_id: int, target_world: int | None) -> None:
        async with self._database.write() as session:
            galaxy = await session.get(GalaxyRow, galaxy_id)
            creator = await CosmosRepository(session).creator()
            if galaxy is None or galaxy.dimension_id is None:
                return
            ctx = await manual_context(session, "genesis_layer", self._rules)
            await tear_rift(
                ctx,
                first_world,
                None,
                dimension_id=galaxy.dimension_id,
                target_world_id=target_world,
                by_node_id=creator.id if creator is not None else None,
                cause=RiftCause.CREATOR,
            )

    async def _made_world(self, world_ids: list[int], settings: GenesisSettings) -> None:
        async with self._database.write() as session:
            ctx = await manual_context(session, "genesis_made_world", self._rules)
            await seed_made_world(ctx, world_ids, prevalence=settings.made_minds, reach=settings.information_reach, technology=settings.technology)

    async def _prehistory(self, world_id: int, epochs: int) -> None:
        async with self._database.write() as session:
            ctx = await manual_context(session, "genesis_prehistory", self._rules)
            await configure(ctx, world_id, epochs, self._rules.prehistory.resolution)
        await run_prehistory(self._database, world_id, rules=self._rules, publish=self._publish)

    @staticmethod
    def _report(context: JobContext | None, progress: float, stage: str) -> None:
        if context is not None:
            context.report(progress, stage)
