from aerona.core.total import partial, total
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.faith import AfterlifeState, StratumKind
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.sacred import AfterlifeModel, BureauRank, DivinationKind, GeniusLocusKind, SacramentKind, SacramentProtection
from aerona.domain.enums.society import NaturalLaw

G = GeniusLocusKind
P = PlaceKind
E = Emotion
M = AfterlifeModel

PLACE_SPIRITS = partial(
    PlaceKind,
    {
        P.MOUNTAIN: G.MOUNTAIN,
        P.PEAK: G.MOUNTAIN,
        P.PASS: G.CROSSROADS,
        P.FOREST: G.FOREST,
        P.GROVE: G.GROVE,
        P.RIVER: G.RIVER,
        P.FORD: G.RIVER,
        P.LAKE: G.LAKE,
        P.SPRING: G.SPRING,
        P.CAVE: G.CAVE,
        P.CAVERN_SYSTEM: G.CAVE,
        P.ISLAND: G.SHORE,
        P.SWAMP: G.WILDS,
        P.WELL: G.WELL,
        P.VALLEY: G.FIELD,
        P.CLIFF: G.SHORE,
        P.VOLCANO: G.MOUNTAIN,
        P.CROSSROADS: G.CROSSROADS,
        P.REEF: G.SHORE,
        P.GLACIER: G.MOUNTAIN,
        P.DUNES: G.WILDS,
        P.CANYON: G.WILDS,
        P.OASIS: G.SPRING,
        P.GEYSER: G.SPRING,
        P.HARBOUR_SITE: G.SHORE,
    },
    without=(
        P.RUIN,
        P.CRATER,
        P.BATTLEFIELD,
        P.BURIAL_GROUND,
        P.LAIR,
        P.NEXUS,
        P.SHRINE_SITE,
        P.GOD_CORPSE,
        P.MINE_SITE,
        P.WRECK_SITE,
        P.MEGASTRUCTURE_RUIN,
        P.ANOMALY,
        P.DEBRIS_FIELD,
    ),
)

SPIRIT_RANKS = total(
    GeniusLocusKind,
    {
        G.RIVER: BureauRank.PROVINCE,
        G.SPRING: BureauRank.LOCAL,
        G.LAKE: BureauRank.PROVINCE,
        G.WELL: BureauRank.LOCAL,
        G.SHORE: BureauRank.LOCAL,
        G.GROVE: BureauRank.LOCAL,
        G.FOREST: BureauRank.PROVINCE,
        G.MOUNTAIN: BureauRank.PROVINCE,
        G.CAVE: BureauRank.LOCAL,
        G.CROSSROADS: BureauRank.LOCAL,
        G.WILDS: BureauRank.LOCAL,
        G.FIELD: BureauRank.LOCAL,
        G.CITY: BureauRank.CITY,
        G.HEARTH: BureauRank.HEARTH,
    },
)

WOODLAND_SPIRITS = frozenset({G.GROVE, G.FOREST})

DOMAIN_FEEDINGS = total(
    Domain,
    {
        Domain.SEA: (E.AWE, E.FEAR),
        Domain.FIRE: (E.RAGE, E.AWE),
        Domain.EARTH: (E.CONTENTMENT, E.GRATITUDE),
        Domain.SKY: (E.AWE, E.HOPE),
        Domain.STORM: (E.FEAR, E.AWE),
        Domain.DEATH: (E.GRIEF, E.FEAR),
        Domain.LIFE: (E.JOY, E.LOVE),
        Domain.DREAM: (E.LONGING, E.AWE),
        Domain.TIME: (E.ANXIETY, E.LONGING),
        Domain.LIGHT: (E.HOPE, E.JOY),
        Domain.SHADOW: (E.FEAR, E.ANXIETY),
        Domain.WAR: (E.RAGE, E.PRIDE),
        Domain.CRAFT: (E.PRIDE, E.CONTENTMENT),
        Domain.KNOWLEDGE: (E.AWE, E.PRIDE),
        Domain.LOVE: (E.LOVE, E.LONGING),
        Domain.TRICKERY: (E.AMUSEMENT, E.ENVY),
        Domain.HUNT: (E.FEAR, E.PRIDE),
        Domain.PLANTS: (E.CONTENTMENT, E.HOPE),
        Domain.BONE: (E.GRIEF, E.FEAR),
        Domain.BLOOD: (E.RAGE, E.FEAR),
        Domain.SOUND: (E.JOY, E.AWE),
        Domain.STONE: (E.CONTENTMENT, E.PRIDE),
        Domain.ICE: (E.FEAR, E.LONELINESS),
        Domain.MADNESS: (E.DESPAIR, E.FEAR),
        Domain.TRADE: (E.ENVY, E.CONTENTMENT),
        Domain.ROAD: (E.LONGING, E.HOPE),
        Domain.PLAGUE: (E.FEAR, E.DESPAIR),
        Domain.HARVEST: (E.GRATITUDE, E.RELIEF),
        Domain.MOON: (E.LONGING, E.LONELINESS),
        Domain.SUN: (E.JOY, E.HOPE),
        Domain.STAR: (E.AWE, E.LONGING),
        Domain.LIES: (E.SHAME, E.ENVY),
        Domain.OATH: (E.GUILT, E.PRIDE),
        Domain.MEMORY: (E.GRIEF, E.LONGING),
        Domain.HUNGER: (E.DESPAIR, E.ENVY),
        Domain.GLASS: (E.AWE, E.ANXIETY),
        Domain.SALT: (E.GRIEF, E.SADNESS),
        Domain.ASH: (E.GRIEF, E.DESPAIR),
        Domain.BORDER: (E.FEAR, E.PRIDE),
        Domain.SLEEP: (E.RELIEF, E.CONTENTMENT),
        Domain.TECHNOLOGY: (E.PRIDE, E.AWE),
        Domain.MACHINES: (E.AWE, E.ANXIETY),
        Domain.CITIES: (E.PRIDE, E.LONELINESS),
        Domain.INDUSTRY: (E.PRIDE, E.BOREDOM),
        Domain.INFORMATION: (E.ANXIETY, E.AMUSEMENT),
        Domain.SPACE: (E.AWE, E.LONELINESS),
        Domain.SCIENCE: (E.AWE, E.PRIDE),
    },
)

SACRAMENT_GUARDS = total(
    SacramentKind,
    {
        SacramentKind.BIRTH_BLESSING: SacramentProtection.POSSESSION,
        SacramentKind.INITIATION: SacramentProtection.ROUTING,
        SacramentKind.MARRIAGE: SacramentProtection.UNREST,
        SacramentKind.LAST_RITES: SacramentProtection.ROUTING,
    },
)

STRATUM_MODELS = total(
    StratumKind,
    {
        StratumKind.PARADISE: M.JUDGED_REALMS,
        StratumKind.TORMENT: M.JUDGED_REALMS,
        StratumKind.PLAIN: M.COMMON_REALM,
        StratumKind.OBLIVION: M.OBLIVION,
        StratumKind.WARRIOR_HALL: M.WARRIOR_HALL,
        StratumKind.ANCESTOR_HALL: M.ANCESTOR_HALL,
    },
)

STATE_MODELS = partial(
    AfterlifeState,
    {
        AfterlifeState.WANDERING: M.WANDERING,
        AfterlifeState.REBORN: M.REBIRTH,
        AfterlifeState.CONSUMED: M.OBLIVION,
        AfterlifeState.RELEASED: M.UNION,
    },
    without=(AfterlifeState.JUDGED, AfterlifeState.IN_REALM),
)

MODEL_STRATA = partial(
    AfterlifeModel,
    {
        M.JUDGED_REALMS: StratumKind.PARADISE,
        M.COMMON_REALM: StratumKind.PLAIN,
        M.WARRIOR_HALL: StratumKind.WARRIOR_HALL,
        M.ANCESTOR_HALL: StratumKind.ANCESTOR_HALL,
        M.OBLIVION: StratumKind.OBLIVION,
    },
    without=(M.REBIRTH, M.WANDERING, M.UNION),
)

DIVINATION_LAWS = partial(
    DivinationKind,
    {
        DivinationKind.DREAM_READING: NaturalLaw.DREAMS_ARE_REAL,
        DivinationKind.ORACLE: NaturalLaw.THE_DEAD_SPEAK,
        DivinationKind.HARUSPICY: NaturalLaw.THE_DEAD_SPEAK,
    },
    without=(DivinationKind.AUGURY, DivinationKind.ASTROLOGY, DivinationKind.LOTS),
)
