from aerona.catalog.kinds.crafts_labels import (
    COLOUR_LABELS,
    EMBLEM_LABELS,
    ENSEMBLE_LABELS,
    FURNISHING_LABELS,
    GAME_LABELS,
    GARMENT_LABELS,
    INSTRUMENT_LABELS,
    MUSIC_LABELS,
    SCENT_LABELS,
    SKILL_LABELS,
    SUBSTANCE_LABELS,
    TOOL_LABELS,
    WEARING_LABELS,
)
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.crafts import GameRow
from aerona.db.tables.kind_crafts import (
    ColourTermRow,
    EmblemSystemRow,
    FurnishingKindRow,
    GarmentKindRow,
    InstrumentKindRow,
    MusicTraditionRow,
    ScentKindRow,
    SubstanceKindRow,
    ToolKindRow,
)
from aerona.domain.enums.kind_crafts import (
    ColourFocus,
    EmblemSystem,
    FurnishingCategory,
    GameCategory,
    GarmentCategory,
    InstrumentCategory,
    MusicForm,
    ScentUse,
    SubstanceCategory,
    ToolCategory,
)
from aerona.domain.enums.kinds import KindConcept

PRESTIGE = KindProperty("prestige", "Prestige", "Standing it lends to those who hold it; raises how fast it spreads and the prestige of their towns")

GARMENT = ConceptSpec(
    concept=KindConcept.GARMENT,
    label="Garment",
    plural="Garments",
    hint="What a people wears, puts on or marks on the body",
    table=GarmentKindRow,
    category=GarmentCategory,
    category_labels=GARMENT_LABELS,
    properties=(
        KindProperty("wearing_rule", "Who wears it", "The rule of who may wear it; a sumptuary law reads it", options=WEARING_LABELS),
        KindProperty("layer", "Layer", "How close to the body it sits, from 0 the innermost to 5 the outermost", 0, 5),
        KindProperty("warmth", "Warmth", "How well it shields its wearers from the cold; read against the cold season"),
        KindProperty("protection", "Protection", "How well it guards against blows and hazards"),
        KindProperty("cost", "Cost", "Worth of one garment", 0, 1000),
        KindProperty("status_signal", "Status signal", "How strongly it marks class, rank, office or faith; fine dress under a sumptuary law"),
        KindProperty("modesty", "Coverage", "How much of the body it covers, read against the culture's norms"),
        PRESTIGE,
        KindProperty("fashion", "Fashion", "How much it rides on novelty; a fashionable garment rises and fades faster"),
        KindProperty("novelty", "Novelty", "How fresh it still feels; worn everywhere it wears thin, worn by few it regains its pull"),
    ),
    readers=("ways_of_life", "crafts_of_life", "mishaps", "norms"),
)
COLOUR = ConceptSpec(
    concept=KindConcept.COLOUR_TERM,
    label="Colour term",
    plural="Colour terms",
    hint="The colours a language names and what they mean to those who use them",
    table=ColourTermRow,
    category=ColourFocus,
    category_labels=COLOUR_LABELS,
    properties=(
        KindProperty("stage", "Stage", "The stage of the language's colour naming at which the term appears, from 1 to 11", 1, 11),
        KindProperty("rarity", "Rarity", "How scarce the dyes and pigments of this colour are; rarity becomes prestige"),
        KindProperty("prestige", "Prestige", "Standing the colour carries; a realm restricts a colour of high prestige to its highest rank"),
    ),
    readers=("ways_of_life", "crafts_of_life"),
)
SCENT = ConceptSpec(
    concept=KindConcept.SCENT,
    label="Scent",
    plural="Scents",
    hint="Scents a people burns, wears, anoints or uses in rites and trade",
    table=ScentKindRow,
    category=ScentUse,
    category_labels=SCENT_LABELS,
    properties=(
        PRESTIGE,
        KindProperty("rite_weight", "Weight in rites", "How much it is used in rites; eases the unrest of its users' towns"),
        KindProperty("trade_value", "Trade value", "What it earns its makers in trade", 0, 1000),
    ),
    readers=("ways_of_life", "crafts_of_life"),
)
EMBLEM = ConceptSpec(
    concept=KindConcept.EMBLEM_SYSTEM,
    label="Emblem system",
    plural="Emblem systems",
    hint="How a culture marks houses, realms, orders and faiths",
    table=EmblemSystemRow,
    category=EmblemSystem,
    category_labels=EMBLEM_LABELS,
    properties=(
        KindProperty("complexity", "Complexity", "How many rules and parts its emblems follow"),
        KindProperty("legibility", "Legibility", "How readily folk read its emblems; raises public order in its users' towns"),
        PRESTIGE,
    ),
    readers=("ways_of_life", "crafts_of_life"),
)
FURNISHING = ConceptSpec(
    concept=KindConcept.FURNISHING,
    label="Furnishing",
    plural="Furnishings",
    hint="What fills a people's dwellings",
    table=FurnishingKindRow,
    category=FurnishingCategory,
    category_labels=FURNISHING_LABELS,
    properties=(
        KindProperty("comfort", "Comfort", "How much it eases daily life; eases unrest, raises sanitation or fire risk by its category"),
        PRESTIGE,
        KindProperty("cost", "Cost", "Worth of one piece; what a household gets when it sells it", 0, 1000),
    ),
    readers=("ways_of_life", "crafts_of_life", "households"),
)
TOOL = ConceptSpec(
    concept=KindConcept.TOOL,
    label="Tool",
    plural="Tools",
    hint="The tools a people works with",
    table=ToolKindRow,
    category=ToolCategory,
    category_labels=TOOL_LABELS,
    properties=(
        KindProperty("skill", "Skill", "The skill it serves", options=SKILL_LABELS),
        KindProperty("craft_bonus", "Craft bonus", "How much it adds to the work done with it"),
        KindProperty("quality", "Quality", "How well it is made"),
        KindProperty("wear", "Wear", "How easily it slips, breaks or harms its user; raises everyday mishaps"),
    ),
    readers=("ways_of_life", "crafts_of_life", "mishaps"),
)
INSTRUMENT = ConceptSpec(
    concept=KindConcept.INSTRUMENT,
    label="Instrument",
    plural="Instruments",
    hint="The instruments a people plays",
    table=InstrumentKindRow,
    category=InstrumentCategory,
    category_labels=INSTRUMENT_LABELS,
    properties=(
        KindProperty("ensemble_role", "Part it plays", "Its part in an ensemble", options=ENSEMBLE_LABELS),
        KindProperty("range_span", "Range", "How wide a span of pitch it reaches"),
        KindProperty("loudness", "Loudness", "How far it carries; eases unrest at gatherings"),
        PRESTIGE,
    ),
    readers=("ways_of_life", "crafts_of_life"),
)
MUSIC = ConceptSpec(
    concept=KindConcept.MUSIC_TRADITION,
    label="Musical tradition",
    plural="Musical traditions",
    hint="How a people makes music: its scales, rhythms, ensembles and occasions",
    table=MusicTraditionRow,
    category=MusicForm,
    category_labels=MUSIC_LABELS,
    properties=(
        KindProperty("scale_steps", "Steps of the scale", "How many steps divide its scale", 2, 48),
        KindProperty("rhythm_complexity", "Rhythm", "How intricate its rhythms are"),
        KindProperty("ensemble_size", "Ensemble", "How many play together at most", 1, 500),
        KindProperty("rite_weight", "Weight in rites", "How much it is played in rites; eases the unrest of its holders' towns"),
        PRESTIGE,
    ),
    readers=("ways_of_life", "crafts_of_life"),
)
GAME = ConceptSpec(
    concept=KindConcept.GAME,
    label="Game",
    plural="Games and sports",
    hint="The games and sports a people plays and watches",
    table=GameRow,
    category=GameCategory,
    category_labels=GAME_LABELS,
    properties=(
        KindProperty("skill", "Skill", "The skill its players practise", options=SKILL_LABELS),
        KindProperty("chance_share", "Chance", "How much of the outcome is left to chance; chance games breed gambling"),
        KindProperty("violence", "Violence", "How rough it is; violent games injure their players"),
        KindProperty("team_size", "Team size", "Players on a side", 1, 500),
        KindProperty("betting", "Betting", "How much is wagered on it"),
        KindProperty("spectators", "Spectators", "How many come to watch; eases unrest and founds clubs and leagues"),
        PRESTIGE,
    ),
    readers=("ways_of_life", "learning_aids", "sport", "mishaps"),
)
SUBSTANCE = ConceptSpec(
    concept=KindConcept.SUBSTANCE,
    label="Substance",
    plural="Substances",
    hint="What a people takes to change body or mind",
    table=SubstanceKindRow,
    category=SubstanceCategory,
    category_labels=SUBSTANCE_LABELS,
    properties=(
        KindProperty("potency", "Potency", "How strongly it works"),
        KindProperty("dependence", "Dependence", "How readily its users come to need it; breeds crime"),
        KindProperty("harm", "Harm", "How much it harms its users; lowers sanitation"),
        KindProperty("rite_weight", "Weight in rites", "How much it is taken in rites; eases unrest"),
        KindProperty("trade_value", "Trade value", "What it earns its makers in trade", 0, 1000),
    ),
    readers=("ways_of_life", "crafts_of_life"),
)
SPECS = (GARMENT, COLOUR, SCENT, EMBLEM, FURNISHING, TOOL, INSTRUMENT, MUSIC, GAME, SUBSTANCE)
