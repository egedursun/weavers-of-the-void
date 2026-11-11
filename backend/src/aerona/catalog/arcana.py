from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.arcana import SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.cosmography import PhenomenonKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.society import CreatureTrait

T = SpellTechnique
F = SpellForm
S = MagicSchool

SCHOOL_GRAMMAR = total(
    MagicSchool,
    {
        S.ELEMENTAL_FIRE: (T.DESTROY, F.FIRE),
        S.ELEMENTAL_WATER: (T.CREATE, F.WATER),
        S.EARTH: (T.TRANSFORM, F.EARTH),
        S.STORM: (T.CONTROL, F.AIR),
        S.LIFE: (T.CREATE, F.BODY),
        S.DEATH: (T.DESTROY, F.DEATH),
        S.MIND: (T.CONTROL, F.MIND),
        S.ILLUSION: (T.CREATE, F.IMAGE),
        S.DIVINATION: (T.PERCEIVE, F.TIME),
        S.WARDING: (T.WARD, F.SPIRIT),
        S.BINDING: (T.BIND, F.SPIRIT),
        S.SUMMONING: (T.SUMMON, F.SPIRIT),
        S.BLOOD: (T.CONTROL, F.BODY),
        S.VOID: (T.DESTROY, F.VOID),
    },
)

TECHNIQUE_COST = total(SpellTechnique, {T.CREATE: 3, T.PERCEIVE: 1, T.TRANSFORM: 3, T.DESTROY: 2, T.CONTROL: 3, T.BIND: 4, T.SUMMON: 4, T.WARD: 2})

FORM_COST = total(
    SpellForm,
    {
        F.FIRE: 2,
        F.WATER: 2,
        F.AIR: 2,
        F.EARTH: 2,
        F.PLANT: 1,
        F.ANIMAL: 2,
        F.BODY: 3,
        F.MIND: 4,
        F.IMAGE: 1,
        F.SPIRIT: 4,
        F.TIME: 5,
        F.VOID: 5,
        F.DEATH: 4,
        F.LIGHT: 2,
    },
)

RANGE_STEP = total(SpellRange, {SpellRange.TOUCH: 0, SpellRange.SIGHT: 1, SpellRange.REGION: 2, SpellRange.WORLD: 4})
DURATION_STEP = total(SpellDuration, {SpellDuration.INSTANT: 0, SpellDuration.SEASON: 1, SpellDuration.EPOCH: 2, SpellDuration.PERMANENT: 4})
TARGET_STEP = total(SpellTarget, {SpellTarget.ONE: 0, SpellTarget.GROUP: 1, SpellTarget.STRUCTURE: 1, SpellTarget.REGION: 3})
DURATION_EPOCHS = total(SpellDuration, {SpellDuration.INSTANT: 0, SpellDuration.SEASON: 1, SpellDuration.EPOCH: 1, SpellDuration.PERMANENT: 1000})

RAIN_HELPED = frozenset({F.WATER, F.PLANT})
RAIN_HINDERED = frozenset({F.FIRE, F.LIGHT})
WET_CONDUCTED = frozenset({F.AIR})
DRY_SPREAD = frozenset({F.FIRE})
IRON_DISRUPTED = frozenset({F.SPIRIT})
LEAK_EMPOWERED = frozenset({F.VOID})


K = PhenomenonKind

PHENOMENON_FORMS = total(
    PhenomenonKind,
    {
        K.ETERNAL_STORM: F.AIR,
        K.TIME_SLIP: F.TIME,
        K.LEAK_WOUND: F.VOID,
        K.LEY_NEXUS_FLARE: F.SPIRIT,
        K.GOD_CORPSE_AURA: F.DEATH,
        K.LIVING_FOG: F.WATER,
        K.CRYSTAL_BLOOM: F.EARTH,
        K.DEAD_ZONE: F.DEATH,
        K.MIRROR_LAKE: F.IMAGE,
        K.GRAVITY_WELL: F.VOID,
        K.SINGING_STONES: F.EARTH,
        K.AURORA_PERMANENT: F.LIGHT,
        K.GHOST_ROAD: F.SPIRIT,
        K.BLIGHT: F.PLANT,
    },
)

TRAIT_FORMS = MappingProxyType(
    {
        CreatureTrait.FLYING: F.AIR,
        CreatureTrait.VENOMOUS: F.DEATH,
        CreatureTrait.SOUL_EATER: F.SPIRIT,
        CreatureTrait.RADIANT: F.LIGHT,
        CreatureTrait.STONESKIN: F.EARTH,
        CreatureTrait.TIME_REWINDER: F.TIME,
        CreatureTrait.SHAPESHIFTER: F.BODY,
        CreatureTrait.MIND_READER: F.MIND,
        CreatureTrait.HIVE_MIND: F.MIND,
        CreatureTrait.FIRE_BREATHING: F.FIRE,
        CreatureTrait.COLD_BREATHING: F.WATER,
        CreatureTrait.AQUATIC: F.WATER,
        CreatureTrait.REGENERATING: F.BODY,
        CreatureTrait.CAMOUFLAGE: F.IMAGE,
        CreatureTrait.MIMIC: F.IMAGE,
        CreatureTrait.SPIRIT_SIGHT: F.SPIRIT,
        CreatureTrait.PLAGUE_BEARER: F.DEATH,
        CreatureTrait.LONG_LIVED: F.TIME,
        CreatureTrait.BURROWING: F.EARTH,
        CreatureTrait.CROP_PEST: F.PLANT,
        CreatureTrait.SWARM_BREEDER: F.ANIMAL,
        CreatureTrait.PACK_HUNTER: F.ANIMAL,
    }
)
