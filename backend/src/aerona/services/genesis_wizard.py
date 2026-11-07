import secrets
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.achievements import ordinal_word
from aerona.catalog.image_styles import CUSTOM_STYLE_MAX_LENGTH
from aerona.catalog.rarities import DEFAULT_FIRST_SONS
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.rarity import RARITY_ORDER, Rarity
from aerona.domain.enums.world import CosmosSize, GenesisTemplate, ImageStyle, LanguageTexture, LoreLanguage, TechnologyEra
from aerona.domain.models.genesis import GenesisSettings
from aerona.engine.primitives.stats import set_stats, stat
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.prompts.catalog import render
from aerona.prompts.contexts.genesis import GenesisWizardContext
from aerona.prompts.ids import PromptId
from aerona.rules.registry import Rules
from aerona.services.lore_ports import GenesisRequest, LorePorts
from aerona.services.player.ports import WorldCreationRequest

PERCENT = 100
DEFAULT_REGION_VALUE = 50
TONE_MAX_LENGTH = 300
SEED_MAX_LENGTH = 2000
SEED_BITS = 62
EXTRA_WORLD_INSPIRATION = "The {ordinal} world of creation; sister of the first world but entirely different."
PEOPLES_WAKING = "The first mortal peoples are waking."
STAGE_GENESIS = "genesis"
STAGE_PEOPLES = "peoples"
STAGE_WORLDS = "worlds"
STAGE_DONE = "done"
FIRST_EXTRA_WORLD = 2

TECHNOLOGY_LABELS: dict[TechnologyEra, str] = {
    TechnologyEra.STONE: "Stone age",
    TechnologyEra.BRONZE: "Bronze age",
    TechnologyEra.IRON: "Iron age",
    TechnologyEra.MEDIEVAL: "Medieval",
    TechnologyEra.RENAISSANCE: "Renaissance",
    TechnologyEra.STEAM: "Steam and gunpowder",
}
TEXTURE_LABELS: dict[LanguageTexture, str] = {
    LanguageTexture.FLOWING: "Flowing, vowel-rich, soft (l, m, n, y)",
    LanguageTexture.HARD: "Hard consonants, short syllables (k, t, g, r)",
    LanguageTexture.GUTTURAL: "Guttural, deep (h, gh, q, kh)",
    LanguageTexture.SIBILANT: "Sibilant, fricative (s, sh, z, ch)",
    LanguageTexture.LONG: "Long, agglutinative, polysyllabic",
    LanguageTexture.FREE: "Free",
}
COSMOS_LABELS: dict[CosmosSize, str] = {CosmosSize.SINGLE: "Single world", CosmosSize.SMALL: "Small cosmos", CosmosSize.LARGE: "Large cosmos"}
LORE_LANGUAGE_LABELS: dict[LoreLanguage, str] = {LoreLanguage.ENGLISH: "English", LoreLanguage.TURKISH: "Turkish"}


@dataclass(frozen=True)
class WizardTemplate:
    key: GenesisTemplate
    name: str
    tone: str
    magic: int
    darkness: int
    technology: TechnologyEra
    language: LanguageTexture
    peoples: int
    cosmos: CosmosSize
    seed: str


TEMPLATES: dict[GenesisTemplate, WizardTemplate] = {
    template.key: template
    for template in (
        WizardTemplate(
            GenesisTemplate.DARK_FANTASY,
            "Dark fantasy",
            "gloomy, merciless, hope comes at a high price",
            60,
            80,
            TechnologyEra.IRON,
            LanguageTexture.GUTTURAL,
            3,
            CosmosSize.SINGLE,
            "A world built on the corpses of gods who once died; every bounty comes from a rot.",
        ),
        WizardTemplate(
            GenesisTemplate.MYTHIC_AGE,
            "Mythic age",
            "epic, solemn, full of prophecies",
            70,
            40,
            TechnologyEra.BRONZE,
            LanguageTexture.FLOWING,
            3,
            CosmosSize.SINGLE,
            "Continents born from the sea and mountains carrying the sky; every river has a name, every name a price.",
        ),
        WizardTemplate(
            GenesisTemplate.COSMIC_HORROR,
            "Cosmic horror",
            "uneasy, silent, in the shadow of incomprehensible things",
            50,
            90,
            TechnologyEra.STEAM,
            LanguageTexture.SIBILANT,
            2,
            CosmosSize.SMALL,
            "A cosmos where something behind the sky is awakening and the stars go out one by one.",
        ),
        WizardTemplate(
            GenesisTemplate.FAIRY_TALE,
            "Fairy tale",
            "warm, strange, wise and a little sad",
            85,
            25,
            TechnologyEra.MEDIEVAL,
            LanguageTexture.LONG,
            4,
            CosmosSize.SINGLE,
            "A world where animals talk, forests change places, and dreams are taxed.",
        ),
        WizardTemplate(
            GenesisTemplate.STAR_MYTH,
            "Star myth",
            "vast, full of wonder, cosmic in scale",
            55,
            45,
            TechnologyEra.RENAISSANCE,
            LanguageTexture.FLOWING,
            3,
            CosmosSize.LARGE,
            "A cosmos where star-wind fills the ships' sails and every world circles a sun of its own.",
        ),
        WizardTemplate(
            GenesisTemplate.SAND_AND_ASH,
            "Sand and ash",
            "harsh, arid, proud",
            35,
            60,
            TechnologyEra.BRONZE,
            LanguageTexture.HARD,
            3,
            CosmosSize.SINGLE,
            "A world where the sun once fell and left a desert; where water is worth more than money and ashes speak prophecies.",
        ),
        WizardTemplate(
            GenesisTemplate.PRIMORDIAL_DAWN,
            "Primordial dawn",
            "raw, wondrous, everything happens for the first time",
            75,
            35,
            TechnologyEra.STONE,
            LanguageTexture.FREE,
            5,
            CosmosSize.SINGLE,
            "A young world still warm from its making; the first fires are being lit, the first words spoken, and every hill waits for a name.",
        ),
        WizardTemplate(
            GenesisTemplate.CROWNS_AND_KNIVES,
            "Crowns and knives",
            "cunning, political, every oath hides a blade",
            12,
            55,
            TechnologyEra.MEDIEVAL,
            LanguageTexture.HARD,
            4,
            CosmosSize.SINGLE,
            "A world where magic has all but faded and power lives in bloodlines, marriages and whispered debts; every throne is one betrayal from falling.",
        ),
        WizardTemplate(
            GenesisTemplate.DROWNED_WORLD,
            "Drowned world",
            "salt-worn, restless, ruled by the tides",
            55,
            50,
            TechnologyEra.IRON,
            LanguageTexture.SIBILANT,
            3,
            CosmosSize.SINGLE,
            "A world where the sea swallowed the continents long ago; "
            "peoples live on scattered islands, reefs and floating towns, and every map is wrong by the next tide.",
        ),
        WizardTemplate(
            GenesisTemplate.LONG_WINTER,
            "Long winter",
            "stern, enduring, warmth must be earned",
            40,
            65,
            TechnologyEra.IRON,
            LanguageTexture.GUTTURAL,
            3,
            CosmosSize.SINGLE,
            "A world whose sun has dimmed for a thousand years; the ice creeps further south each winter and the peoples burn their histories to stay warm.",
        ),
        WizardTemplate(
            GenesisTemplate.AFTER_THE_FALL,
            "After the fall",
            "elegiac, scavenging, haunted by a greater past",
            45,
            70,
            TechnologyEra.MEDIEVAL,
            LanguageTexture.LONG,
            3,
            CosmosSize.SINGLE,
            "A world built on the ruins of a civilization far greater than any living one; "
            "its towers still hum, its roads lead nowhere, and no one remembers how its wonders were made.",
        ),
        WizardTemplate(
            GenesisTemplate.SKY_ISLANDS,
            "Sky islands",
            "airy, adventurous, hopeful",
            70,
            30,
            TechnologyEra.RENAISSANCE,
            LanguageTexture.FLOWING,
            3,
            CosmosSize.SMALL,
            "A cosmos of shattered worlds whose fragments drift on rivers of wind; "
            "peoples sail between the islands on kite-ships, and falling past the edge is the oldest fear.",
        ),
        WizardTemplate(
            GenesisTemplate.AGE_OF_ENGINES,
            "Age of engines",
            "curious, inventive, bright with possibility",
            30,
            30,
            TechnologyEra.STEAM,
            LanguageTexture.FREE,
            4,
            CosmosSize.SINGLE,
            "A world where the first engines have just learned to breathe; "
            "tinkers rival priests, railways cut through sacred forests, and every invention wakes an old spirit.",
        ),
    )
}


class WizardInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    template: str | None = None
    magic: Any = None
    darkness: Any = None
    technology: str | None = None
    language: str | None = None
    peoples: Any = None
    cosmos: str | None = None
    tone: str | None = None
    seed: str | None = None


@dataclass(frozen=True)
class CosmosOption:
    size: CosmosSize
    label: str
    worlds: int


@dataclass(frozen=True)
class FirstSonsOptions:
    minimum: int
    maximum: int
    rarities: list[Rarity]
    default: list[Rarity]


@dataclass(frozen=True)
class WizardOptions:
    technology: dict[TechnologyEra, str]
    language: dict[LanguageTexture, str]
    cosmos: list[CosmosOption]
    lore_languages: dict[LoreLanguage, str]
    templates: list[WizardTemplate]
    first_sons: FirstSonsOptions


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
        language=dict(TEXTURE_LABELS),
        cosmos=[CosmosOption(size, COSMOS_LABELS[size], 1 + extra_worlds(rules, size)) for size in CosmosSize],
        lore_languages=dict(LORE_LANGUAGE_LABELS),
        templates=list(TEMPLATES.values()),
        first_sons=FirstSonsOptions(
            minimum=rules.setup_wizard.first_sons_min,
            maximum=rules.setup_wizard.first_sons_max,
            rarities=allowed_first_son_rarities(rules),
            default=list(DEFAULT_FIRST_SONS),
        ),
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
            raise ValidationFailedError(f"A first son cannot be of {rarity.value} rarity.")
    return tuple(sorted(requested, key=lambda item: item.rank))


def _percent(value: Any, fallback: int) -> int:
    if value is None or value == "":
        return fallback
    try:
        return max(0, min(PERCENT, round(float(value))))
    except (TypeError, ValueError):
        return fallback


def _choice[E: (TechnologyEra, LanguageTexture, CosmosSize)](kind: type[E], value: str | None, fallback: E) -> E:
    try:
        return kind(value) if value is not None else fallback
    except ValueError:
        return fallback


def sanitize(rules: Rules, raw: WizardInput) -> GenesisSettings:
    wizard = rules.setup_wizard
    key = raw.template if raw.template in {item.value for item in GenesisTemplate} else None
    template = TEMPLATES[GenesisTemplate(key)] if key is not None else None
    magic = raw.magic if raw.magic not in (None, "") else (template.magic if template else None)
    darkness = raw.darkness if raw.darkness not in (None, "") else (template.darkness if template else None)
    peoples_raw = raw.peoples if raw.peoples not in (None, "") else (template.peoples if template else wizard.peoples)
    try:
        peoples = max(1, min(wizard.peoples_max, round(float(peoples_raw))))
    except (TypeError, ValueError):
        peoples = wizard.peoples
    tone = (raw.tone or (template.tone if template else "") or "").strip()[:TONE_MAX_LENGTH] or None
    seed = (raw.seed or (template.seed if template else "") or "").strip()[:SEED_MAX_LENGTH] or None
    return GenesisSettings(
        template=template.key if template else None,
        magic=_percent(magic, wizard.magic),
        darkness=_percent(darkness, wizard.darkness),
        technology=_choice(TechnologyEra, raw.technology or (template.technology.value if template else None), TechnologyEra.IRON),
        language_texture=_choice(LanguageTexture, raw.language or (template.language.value if template else None), LanguageTexture.FREE),
        peoples=peoples,
        cosmos_size=_choice(CosmosSize, raw.cosmos or (template.cosmos.value if template else None), CosmosSize.SINGLE),
        tone=tone,
        seed_idea=seed,
    )


def wizard_text(rules: Rules, settings: GenesisSettings) -> str:
    context = GenesisWizardContext(
        rules=rules,
        template_name=TEMPLATES[settings.template].name if settings.template else None,
        magic=settings.magic,
        darkness=settings.darkness,
        technology=settings.technology,
        language=settings.language_texture,
        cosmos=settings.cosmos_size,
    )
    return render(PromptId.GENESIS_WIZARD_SETTINGS, context)


def pulled(value: int | None, target: int, pull_pct: int) -> int:
    current = DEFAULT_REGION_VALUE if value is None else value
    return round(current * (PERCENT - pull_pct) / PERCENT + target * pull_pct / PERCENT)


async def pull_regions(session: AsyncSession, rules: Rules, settings: GenesisSettings) -> int:
    pull = rules.setup_wizard.setting_pull_pct
    regions = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)))
    for region in regions:
        set_stats(region, magic=pulled(stat(region, "magic"), settings.magic, pull), danger=pulled(stat(region, "danger"), settings.darkness, pull))
    await session.flush()
    return len(regions)


async def save_settings(session: AsyncSession, settings: GenesisSettings) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.genesis_settings = settings
    await session.flush()


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
            raise ValidationFailedError(f"The custom image style is limited to {CUSTOM_STYLE_MAX_LENGTH} characters.")
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
            wizard_text=wizard_text(self._rules, settings) if settings else None,
            first_sons=resolve_first_sons(self._rules, command.first_sons),
        )
        self._report(context, 0.05, STAGE_GENESIS)
        await author.create(request)
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
        self._publish(EventKind.GENESIS_FINISHED, {})
        peoples = settings.peoples if settings else self._rules.setup_wizard.peoples
        awakened: list[int] = []
        if self._ports.awakener is not None:
            self._report(context, 0.5, STAGE_PEOPLES)
            self._publish(EventKind.SYSTEM_NOTE, {"text": PEOPLES_WAKING})
            awakened = await self._ports.awakener.awaken(peoples, first_world)
        worlds: list[int] = []
        extra = extra_worlds(self._rules, settings.cosmos_size) if settings else 0
        if extra and self._ports.worlds is not None:
            self._report(context, 0.75, STAGE_WORLDS)
            for number in range(FIRST_EXTRA_WORLD, FIRST_EXTRA_WORLD + extra):
                inspiration = EXTRA_WORLD_INSPIRATION.format(ordinal=ordinal_word(number).lower())
                worlds.append(await self._ports.worlds.create(WorldCreationRequest(None, inspiration, None, None, False, None)))
        self._report(context, 1.0, STAGE_DONE)
        return {"peoples": awakened, "worlds": worlds}

    @staticmethod
    def _report(context: JobContext | None, progress: float, stage: str) -> None:
        if context is not None:
            context.report(progress, stage)
