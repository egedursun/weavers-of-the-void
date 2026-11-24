from aerona.catalog.kinds.labels import plain
from aerona.core.grammar import spoken
from aerona.domain.enums.kind_crafts import (
    ColourFocus,
    ColourMeaning,
    EmblemSystem,
    EnsembleRole,
    FurnishingCategory,
    GameCategory,
    GarmentCategory,
    InstrumentCategory,
    MusicForm,
    ScentUse,
    SubstanceCategory,
    ToolCategory,
    WearingRule,
)
from aerona.domain.enums.mind import SkillKind

GARMENT_LABELS = plain(
    GarmentCategory,
    {
        GarmentCategory.BODY_WRAP: "Body wrap",
        GarmentCategory.UPPER: "Upper garment",
        GarmentCategory.LOWER: "Lower garment",
        GarmentCategory.FULL_BODY: "Full-body garment",
        GarmentCategory.OUTER_LAYER: "Outer layer",
        GarmentCategory.HEAD: "Headwear",
        GarmentCategory.FACE_COVERING: "Face covering",
        GarmentCategory.FEET: "Footwear",
        GarmentCategory.HANDS: "Handwear",
        GarmentCategory.UNDERGARMENT: "Undergarment",
        GarmentCategory.FASTENING: "Fastening",
        GarmentCategory.ORNAMENT: "Ornament",
        GarmentCategory.UNIFORM: "Uniform",
        GarmentCategory.RITUAL_DRESS: "Ritual dress",
        GarmentCategory.WORK_PROTECTION: "Work protection",
        GarmentCategory.ENVIRONMENT_SUIT: "Environment suit",
        GarmentCategory.BODY_MARKING: "Body marking",
        GarmentCategory.SLEEPWEAR: "Sleepwear",
        GarmentCategory.WATER_WEAR: "Wear for water",
        GarmentCategory.CARRIER: "Sling or pack for carrying",
    },
)
WEARING_LABELS = plain(
    WearingRule,
    {
        WearingRule.ANYONE: "Anyone may wear it",
        WearingRule.BY_ROLE: "Worn by those of a role",
        WearingRule.BY_CLASS: "Worn by a social class",
        WearingRule.BY_AGE: "Worn at an age",
        WearingRule.BY_FAITH: "Worn by those of a faith",
        WearingRule.BY_RANK: "Worn by a rank",
        WearingRule.BY_GENDER_AS_THE_CULTURE_HOLDS: "Worn by a gender, as the culture holds it",
    },
)
COLOUR_LABELS = plain(
    ColourFocus,
    {
        ColourFocus.DARK: "Dark",
        ColourFocus.LIGHT: "Light",
        ColourFocus.RED: "Red",
        ColourFocus.YELLOW: "Yellow",
        ColourFocus.GREEN: "Green",
        ColourFocus.BLUE: "Blue",
        ColourFocus.BROWN: "Brown",
        ColourFocus.PURPLE: "Purple",
        ColourFocus.PINK: "Pink",
        ColourFocus.ORANGE: "Orange",
        ColourFocus.GREY: "Grey",
    },
)
MEANING_LABELS = plain(
    ColourMeaning,
    {
        ColourMeaning.MOURNING: "Mourning",
        ColourMeaning.RANK: "Rank",
        ColourMeaning.SACRED: "Sacred",
        ColourMeaning.DANGER: "Danger",
        ColourMeaning.JOY: "Joy",
        ColourMeaning.FACTION: "Faction",
        ColourMeaning.NONE: "No meaning",
        ColourMeaning.HEALTH: "Health",
        ColourMeaning.PURITY: "Purity",
        ColourMeaning.LIFE_STAGE: "A stage of life",
    },
)
SCENT_LABELS = plain(
    ScentUse,
    {
        ScentUse.BURNED: "Burned",
        ScentUse.WORN: "Worn",
        ScentUse.ANOINTED: "Anointed",
        ScentUse.HOUSEHOLD: "Household",
        ScentUse.RITUAL: "Ritual",
        ScentUse.MEDICINAL: "Medicinal",
        ScentUse.SIGNAL: "Signal",
    },
)
EMBLEM_LABELS = plain(
    EmblemSystem,
    {
        EmblemSystem.HERALDRY: "Heraldry",
        EmblemSystem.SEAL: "Seal",
        EmblemSystem.BANNER: "Banner",
        EmblemSystem.TOTEM: "Totem",
        EmblemSystem.BADGE: "Badge",
        EmblemSystem.MONOGRAM: "Monogram",
        EmblemSystem.MARK: "Mark",
        EmblemSystem.GLYPH: "Glyph",
    },
)
FURNISHING_LABELS = plain(
    FurnishingCategory,
    {
        FurnishingCategory.SLEEPING: "Sleeping",
        FurnishingCategory.SEATING: "Seating",
        FurnishingCategory.STORAGE: "Storage",
        FurnishingCategory.TABLE: "Table",
        FurnishingCategory.LIGHTING: "Lighting",
        FurnishingCategory.HEATING: "Heating",
        FurnishingCategory.COOKING_VESSEL: "Cooking vessel",
        FurnishingCategory.TABLEWARE: "Tableware",
        FurnishingCategory.HOUSEHOLD_TEXTILE: "Household textile",
        FurnishingCategory.DECORATION: "Decoration",
        FurnishingCategory.SANITATION: "Sanitation",
        FurnishingCategory.SHRINE: "Household shrine",
        FurnishingCategory.BATHING: "Bathing furnishing",
        FurnishingCategory.PLAY: "Toys and play things",
    },
)
TOOL_LABELS = plain(
    ToolCategory,
    {
        ToolCategory.CUTTING: "Cutting",
        ToolCategory.DIGGING: "Digging",
        ToolCategory.LIFTING: "Lifting",
        ToolCategory.MEASURING: "Measuring",
        ToolCategory.WRITING: "Writing",
        ToolCategory.FIRE_MAKING: "Fire making",
        ToolCategory.CRAFTING: "Crafting",
        ToolCategory.MEDICAL: "Medical",
        ToolCategory.NAVIGATION: "Navigation",
        ToolCategory.COMPUTING: "Computing",
        ToolCategory.FARMING: "Farming",
        ToolCategory.FISHING: "Fishing",
        ToolCategory.HUNTING: "Hunting",
    },
)
INSTRUMENT_LABELS = plain(
    InstrumentCategory,
    {
        InstrumentCategory.STRING: "String",
        InstrumentCategory.WIND: "Wind",
        InstrumentCategory.PERCUSSION: "Percussion",
        InstrumentCategory.VOICE: "Voice",
        InstrumentCategory.KEYBOARD: "Keyboard",
        InstrumentCategory.ELECTRONIC: "Electronic",
        InstrumentCategory.MADE: "Made instrument",
        InstrumentCategory.LIVING: "Living instrument",
        InstrumentCategory.WATER: "Water instrument",
    },
)
ENSEMBLE_LABELS = plain(
    EnsembleRole,
    {
        EnsembleRole.LEAD: "Leads",
        EnsembleRole.ACCOMPANIMENT: "Accompanies",
        EnsembleRole.RHYTHM: "Keeps the rhythm",
        EnsembleRole.DRONE: "Holds a sustained tone",
        EnsembleRole.SOLO: "Plays alone",
    },
)
MUSIC_LABELS = plain(
    MusicForm,
    {
        MusicForm.SOLO: "Solo",
        MusicForm.CHORUS: "Chorus",
        MusicForm.ENSEMBLE: "Ensemble",
        MusicForm.CALL_AND_RESPONSE: "Call and response",
        MusicForm.LAYERED: "Layered parts",
        MusicForm.IMPROVISED: "Improvised",
        MusicForm.NOTATED: "Written down",
    },
)
GAME_LABELS = plain(
    GameCategory,
    {
        GameCategory.BOARD: "Board game",
        GameCategory.CHANCE: "Game of chance",
        GameCategory.CARD: "Card game",
        GameCategory.BALL: "Ball game",
        GameCategory.RACING: "Racing",
        GameCategory.COMBAT_SPORT: "Combat sport",
        GameCategory.ATHLETIC: "Athletics",
        GameCategory.HUNTING_SPORT: "Hunting sport",
        GameCategory.WIT: "Game of wit",
        GameCategory.TEAM: "Team game",
        GameCategory.SPECTACLE: "Spectacle",
        GameCategory.GAMBLING: "Gambling",
        GameCategory.NETWORK: "Networked game",
        GameCategory.PUZZLE: "Puzzle",
        GameCategory.ANIMAL_CONTEST: "Animal contest",
    },
)
SUBSTANCE_LABELS = plain(
    SubstanceCategory,
    {
        SubstanceCategory.STIMULANT: "Stimulant",
        SubstanceCategory.DEPRESSANT: "Depressant",
        SubstanceCategory.HALLUCINOGEN: "Hallucinogen",
        SubstanceCategory.ANALGESIC: "Analgesic",
        SubstanceCategory.EUPHORIANT: "Euphoriant",
        SubstanceCategory.POWER_SUBSTANCE: "Power substance",
        SubstanceCategory.MEDICINAL: "Medicinal",
    },
)
SKILL_LABELS = {skill.value: spoken(skill).capitalize() for skill in SkillKind}

CLEANSING_FURNISHINGS = frozenset({FurnishingCategory.SANITATION, FurnishingCategory.BATHING})
WORKING_WEAR = frozenset({GarmentCategory.CARRIER, GarmentCategory.WATER_WEAR})
