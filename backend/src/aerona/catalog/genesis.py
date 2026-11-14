from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.cosmography import DimensionKind, WorldAge
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.domain.enums.world import ClimateEra, CosmosShape, CosmosSize, GenesisTemplate, LanguageTexture, LoreLanguage, TechnologyEra, WorldType

T = GenesisTemplate

TECHNOLOGY_LABELS: MappingProxyType[TechnologyEra, str] = MappingProxyType(
    {
        TechnologyEra.STONE: "Stone age",
        TechnologyEra.BRONZE: "Bronze age",
        TechnologyEra.IRON: "Iron age",
        TechnologyEra.MEDIEVAL: "Medieval",
        TechnologyEra.RENAISSANCE: "Renaissance",
        TechnologyEra.STEAM: "Steam and gunpowder",
    }
)
TEXTURE_LABELS: MappingProxyType[LanguageTexture, str] = MappingProxyType(
    {
        LanguageTexture.FLOWING: "Flowing, vowel-rich, soft (l, m, n, y)",
        LanguageTexture.HARD: "Hard consonants, short syllables (k, t, g, r)",
        LanguageTexture.GUTTURAL: "Guttural, deep (h, gh, q, kh)",
        LanguageTexture.SIBILANT: "Sibilant, fricative (s, sh, z, ch)",
        LanguageTexture.LONG: "Long, agglutinative, polysyllabic",
        LanguageTexture.FREE: "Free",
    }
)
COSMOS_LABELS: MappingProxyType[CosmosSize, str] = MappingProxyType(
    {CosmosSize.SINGLE: "Single world", CosmosSize.SMALL: "Small cosmos", CosmosSize.LARGE: "Large cosmos"}
)
SHAPE_LABELS: MappingProxyType[CosmosShape, str] = MappingProxyType(
    {CosmosShape.ONE_SUN: "One sun", CosmosShape.MANY_SUNS: "Many suns", CosmosShape.LAYERED: "Layered"}
)
SHAPE_HINTS: MappingProxyType[CosmosShape, str] = MappingProxyType(
    {
        CosmosShape.ONE_SUN: "Every further world circles the first sun",
        CosmosShape.MANY_SUNS: "Each further world has a sun of its own",
        CosmosShape.LAYERED: "In a second layer, reached through a rift",
    }
)
SHAPE_LINES: MappingProxyType[CosmosShape, str] = MappingProxyType(
    {
        CosmosShape.ONE_SUN: "every further world circles the sun of the first world",
        CosmosShape.MANY_SUNS: "each further world circles a sun of its own",
        CosmosShape.LAYERED: "the further worlds lie in a second layer of the cosmos, reached from the first world through a rift",
    }
)
STORYTELLER_LABELS: MappingProxyType[StorytellerProfile, str] = MappingProxyType(
    {
        StorytellerProfile.STEADY: "Steady",
        StorytellerProfile.RISING: "Rising",
        StorytellerProfile.CYCLIC: "Cyclic",
        StorytellerProfile.CHAOTIC: "Chaotic",
    }
)
AGE_CYCLE_LABELS: MappingProxyType[AgeCycle, str] = MappingProxyType(
    {AgeCycle.LINEAR: "Linear: the cosmos runs on to its end", AgeCycle.CYCLIC: "Cyclic: each end turns a new age"}
)
LORE_LANGUAGE_LABELS: MappingProxyType[LoreLanguage, str] = MappingProxyType({LoreLanguage.ENGLISH: "English", LoreLanguage.TURKISH: "Turkish"})
LAYER_KINDS: tuple[DimensionKind, ...] = tuple(kind for kind in DimensionKind if kind is not DimensionKind.PRIME)


@dataclass(frozen=True)
class WizardTemplate:
    key: GenesisTemplate
    name: str
    tone: str
    magic: int
    danger: int
    technology: TechnologyEra
    language: LanguageTexture
    peoples: int
    cosmos: CosmosSize
    seed: str
    storyteller: StorytellerProfile = StorytellerProfile.CYCLIC
    shape: CosmosShape = CosmosShape.ONE_SUN
    world_type: WorldType | None = None
    climate_era: ClimateEra | None = None
    world_age: WorldAge | None = None


TEMPLATES: MappingProxyType[GenesisTemplate, WizardTemplate] = MappingProxyType(
    {
        template.key: template
        for template in (
            WizardTemplate(
                T.DARK_FANTASY,
                "Dark fantasy",
                "gloomy, merciless, hope is hard to find",
                60,
                80,
                TechnologyEra.IRON,
                LanguageTexture.GUTTURAL,
                3,
                CosmosSize.SINGLE,
                "A world raised on the bodies of gods who died before time began.",
                storyteller=StorytellerProfile.RISING,
                world_type=WorldType.CORPSE_WORLD,
            ),
            WizardTemplate(
                T.MYTHIC_AGE,
                "Mythic age",
                "epic, solemn, full of prophecies",
                70,
                40,
                TechnologyEra.BRONZE,
                LanguageTexture.FLOWING,
                3,
                CosmosSize.SINGLE,
                "An age of myth, when the land is young and the gods still walk among the first peoples.",
                world_age=WorldAge.YOUNG,
            ),
            WizardTemplate(
                T.COSMIC_HORROR,
                "Cosmic horror",
                "uneasy, silent, in the shadow of incomprehensible things",
                50,
                90,
                TechnologyEra.STEAM,
                LanguageTexture.SIBILANT,
                2,
                CosmosSize.SMALL,
                "A cosmos where something vast and beyond understanding is stirring beyond the sky.",
                storyteller=StorytellerProfile.RISING,
            ),
            WizardTemplate(
                T.FAIRY_TALE,
                "Fairy tale",
                "warm, whimsical, wise and a little sad",
                85,
                25,
                TechnologyEra.MEDIEVAL,
                LanguageTexture.LONG,
                4,
                CosmosSize.SINGLE,
                "A world that runs on the logic of fairy tales.",
                storyteller=StorytellerProfile.STEADY,
            ),
            WizardTemplate(
                T.STAR_MYTH,
                "Star myth",
                "vast, full of wonder, cosmic in scale",
                55,
                45,
                TechnologyEra.RENAISSANCE,
                LanguageTexture.FLOWING,
                3,
                CosmosSize.LARGE,
                "A cosmos whose peoples look up at the stars and set out to reach them.",
            ),
            WizardTemplate(
                T.SAND_AND_ASH,
                "Sand and ash",
                "harsh, arid, proud",
                35,
                60,
                TechnologyEra.BRONZE,
                LanguageTexture.HARD,
                3,
                CosmosSize.SINGLE,
                "A desert world where water is the rarest thing of all.",
                world_type=WorldType.SAND,
                climate_era=ClimateEra.DROUGHT,
            ),
            WizardTemplate(
                T.PRIMORDIAL_DAWN,
                "Primordial dawn",
                "raw, wondrous, everything happens for the first time",
                75,
                35,
                TechnologyEra.STONE,
                LanguageTexture.FREE,
                5,
                CosmosSize.SINGLE,
                "A world just made, where everything happens for the first time.",
                world_age=WorldAge.YOUNG,
            ),
            WizardTemplate(
                T.CROWNS_AND_KNIVES,
                "Crowns and knives",
                "cunning, political, full of intrigue",
                12,
                55,
                TechnologyEra.MEDIEVAL,
                LanguageTexture.HARD,
                4,
                CosmosSize.SINGLE,
                "A world where magic has all but faded and power lies in bloodlines, marriages and debts.",
                storyteller=StorytellerProfile.CHAOTIC,
            ),
            WizardTemplate(
                T.DROWNED_WORLD,
                "Drowned world",
                "restless, wide, ruled by the tides",
                55,
                50,
                TechnologyEra.IRON,
                LanguageTexture.SIBILANT,
                3,
                CosmosSize.SINGLE,
                "A world where the sea covers almost everything and the peoples live on what little rises above it.",
                world_type=WorldType.OCEAN,
            ),
            WizardTemplate(
                T.LONG_WINTER,
                "Long winter",
                "stern, enduring, warmth must be earned",
                40,
                65,
                TechnologyEra.IRON,
                LanguageTexture.GUTTURAL,
                3,
                CosmosSize.SINGLE,
                "A world held in a winter that has lasted longer than anyone remembers.",
                climate_era=ClimateEra.ICE_AGE,
            ),
            WizardTemplate(
                T.AFTER_THE_FALL,
                "After the fall",
                "elegiac, scavenging, haunted by a greater past",
                45,
                70,
                TechnologyEra.MEDIEVAL,
                LanguageTexture.LONG,
                3,
                CosmosSize.SINGLE,
                "A world living among the remains of a civilization greater than any alive today.",
                world_age=WorldAge.OLD,
            ),
            WizardTemplate(
                T.SKY_ISLANDS,
                "Sky islands",
                "airy, adventurous, hopeful",
                70,
                30,
                TechnologyEra.RENAISSANCE,
                LanguageTexture.FLOWING,
                3,
                CosmosSize.SMALL,
                "A broken world whose pieces float in an open sky, and peoples who travel between them.",
                world_type=WorldType.SHATTERED,
            ),
            WizardTemplate(
                T.AGE_OF_ENGINES,
                "Age of engines",
                "curious, inventive, bright with possibility",
                30,
                30,
                TechnologyEra.STEAM,
                LanguageTexture.FREE,
                4,
                CosmosSize.SINGLE,
                "A world where the first engines have just been built and invention is changing everything.",
                storyteller=StorytellerProfile.RISING,
            ),
            WizardTemplate(
                T.MANY_SUNS,
                "Many suns",
                "vast, adventurous, many worlds to meet",
                50,
                45,
                TechnologyEra.RENAISSANCE,
                LanguageTexture.FREE,
                4,
                CosmosSize.LARGE,
                "A cosmos of many suns, each with worlds and peoples of its own.",
                shape=CosmosShape.MANY_SUNS,
            ),
            WizardTemplate(
                T.LAYERED_REALMS,
                "Layered realms",
                "layered, full of thresholds between its realms",
                65,
                50,
                TechnologyEra.MEDIEVAL,
                LanguageTexture.FLOWING,
                3,
                CosmosSize.SMALL,
                "A cosmos of more than one layer of reality, where another realm lies beside the first and the way between them is open.",
                shape=CosmosShape.LAYERED,
            ),
            WizardTemplate(
                T.LIVING_WORLD,
                "Living world",
                "intimate, organic, watchful",
                70,
                45,
                TechnologyEra.BRONZE,
                LanguageTexture.FLOWING,
                3,
                CosmosSize.SINGLE,
                "A world that is itself alive and feels what is done upon it.",
                world_type=WorldType.LIVING,
            ),
            WizardTemplate(
                T.DREAMING_WORLD,
                "Dreaming world",
                "drifting, shifting, half-remembered",
                80,
                40,
                TechnologyEra.MEDIEVAL,
                LanguageTexture.LONG,
                3,
                CosmosSize.SINGLE,
                "A world made of dream, where what is believed takes shape.",
                world_type=WorldType.DREAM,
            ),
            WizardTemplate(
                T.GENERATION_SHIP,
                "Generation ship",
                "close, enduring, far from home",
                15,
                45,
                TechnologyEra.MEDIEVAL,
                LanguageTexture.HARD,
                3,
                CosmosSize.SINGLE,
                "A vessel the size of a world travelling between the stars, whose peoples have lived aboard so long that they no longer know it is a ship.",
                world_type=WorldType.GENERATION_SHIP,
                world_age=WorldAge.MATURE,
            ),
            WizardTemplate(
                T.WITHOUT_MAGIC,
                "Without magic",
                "grounded, earthly, plain",
                0,
                40,
                TechnologyEra.IRON,
                LanguageTexture.FREE,
                4,
                CosmosSize.SINGLE,
                "A world without magic, where the peoples have only their own skill, their wits and one another.",
                storyteller=StorytellerProfile.STEADY,
            ),
        )
    }
)
