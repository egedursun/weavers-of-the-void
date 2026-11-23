from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.arcana import RechargeRule, RiteCondition, SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.cosmography import PhenomenonKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.enums.world import SkyEventKind
from aerona.rules.registry import Rules

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

COMMANDING_TECHNIQUES = frozenset({T.CONTROL, T.BIND})

TECHNIQUE_COST = total(
    SpellTechnique, {T.CREATE: 3, T.PERCEIVE: 1, T.TRANSFORM: 3, T.DESTROY: 2, T.CONTROL: 3, T.BIND: 4, T.SUMMON: 4, T.WARD: 2, T.DRAIN: 3, T.MIMIC: 4}
)

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
        F.SPACE: 4,
        F.FORCE: 2,
        F.SOUND: 1,
        F.EMOTION: 3,
        F.FATE: 5,
        F.MACHINE: 3,
        F.INFORMATION: 3,
    },
)


@dataclass(frozen=True)
class RangeSpec:
    label: str
    step: int
    through_link: bool = False
    beyond_world: bool = False


RANGES = total(
    SpellRange,
    {
        SpellRange.TOUCH: RangeSpec("Touch", 0),
        SpellRange.SIGHT: RangeSpec("Sight", 1),
        SpellRange.REGION: RangeSpec("Region", 2),
        SpellRange.WORLD: RangeSpec("World", 4),
        SpellRange.LINKED: RangeSpec("Through a link", 2, through_link=True),
        SpellRange.COSMOS: RangeSpec("Beyond the world", 6, beyond_world=True),
    },
)
RANGE_STEP = MappingProxyType({kind: spec.step for kind, spec in RANGES.items()})


@dataclass(frozen=True)
class DurationSpec:
    label: str
    step: int
    epochs: int
    sustained: bool = False
    conditional: bool = False


DURATIONS = total(
    SpellDuration,
    {
        SpellDuration.INSTANT: DurationSpec("Instant", 0, 0),
        SpellDuration.SEASON: DurationSpec("A season", 1, 1),
        SpellDuration.EPOCH: DurationSpec("An epoch", 2, 1),
        SpellDuration.PERMANENT: DurationSpec("Permanent", 4, 1000),
        SpellDuration.SUSTAINED: DurationSpec("While sustained", 2, 1000, sustained=True),
        SpellDuration.UNTIL_CONDITION: DurationSpec("Until a condition is met", 3, 1000, conditional=True),
    },
)
DURATION_STEP = MappingProxyType({kind: spec.step for kind, spec in DURATIONS.items()})
DURATION_EPOCHS = MappingProxyType({kind: spec.epochs for kind, spec in DURATIONS.items()})
SUSTAINED_DURATIONS = frozenset(kind for kind, spec in DURATIONS.items() if spec.sustained)
CONDITIONAL_DURATIONS = frozenset(kind for kind, spec in DURATIONS.items() if spec.conditional)


@dataclass(frozen=True)
class ConditionSpec:
    label: str
    needs_act: bool = False
    needs_epoch: bool = False
    by_anyone: bool = False


RITE_CONDITIONS = total(
    RiteCondition,
    {
        RiteCondition.ACT: ConditionSpec("Until its bearer does an act", needs_act=True),
        RiteCondition.TIME: ConditionSpec("Until a set time", needs_epoch=True),
        RiteCondition.WORD: ConditionSpec("Until its caster lifts it by word"),
        RiteCondition.DEED: ConditionSpec("Until someone does a deed for its bearer", needs_act=True, by_anyone=True),
    },
)


@dataclass(frozen=True)
class TargetSpec:
    label: str
    step: int
    item: bool = False
    line: bool = False
    world: bool = False


TARGETS = total(
    SpellTarget,
    {
        SpellTarget.ONE: TargetSpec("One", 0),
        SpellTarget.GROUP: TargetSpec("A group", 1),
        SpellTarget.STRUCTURE: TargetSpec("A structure", 1),
        SpellTarget.REGION: TargetSpec("A region", 3),
        SpellTarget.ITEM: TargetSpec("An item", 1, item=True),
        SpellTarget.LINE: TargetSpec("A line of descent", 3, line=True),
        SpellTarget.WORLD: TargetSpec("A whole world", 6, world=True),
    },
)
TARGET_STEP = MappingProxyType({kind: spec.step for kind, spec in TARGETS.items()})

SKY_SIGNS = frozenset({SkyEventKind.ECLIPSE, SkyEventKind.ALIGNMENT, SkyEventKind.COMET})


@dataclass(frozen=True)
class RechargeSpec:
    label: str
    fill: Callable[[Rules], int]


RECHARGES = total(
    RechargeRule,
    {
        RechargeRule.SITE: RechargeSpec("At a magic site", lambda rules: rules.arcana.site_fill),
        RechargeRule.VIS: RechargeSpec("By vis", lambda rules: rules.arcana.vis_fill),
        RechargeRule.MOON: RechargeSpec("At the full moon", lambda rules: rules.arcana.moon_fill),
        RechargeRule.NONE: RechargeSpec("Never", lambda rules: rules.arcana.none_fill),
        RechargeRule.SKY_EVENT: RechargeSpec("At a sign in the sky", lambda rules: rules.arcana.sky_event_fill),
        RechargeRule.BODILY_OFFERING: RechargeSpec("By an offering of the body", lambda rules: rules.arcana.bodily_offering_fill),
    },
)

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
        K.LASTING_STORM: F.AIR,
        K.TIME_DISTORTION: F.TIME,
        K.OUTSIDE_OPENING: F.VOID,
        K.POWER_SURGE: F.SPIRIT,
        K.DIVINE_RESIDUE: F.DEATH,
        K.MOVING_FOG: F.WATER,
        K.MINERAL_GROWTH: F.EARTH,
        K.BARREN_GROUND: F.DEATH,
        K.DISTANT_VIEW: F.IMAGE,
        K.GRAVITY_ANOMALY: F.VOID,
        K.SOUNDING_GROUND: F.EARTH,
        K.LASTING_LIGHTS: F.LIGHT,
        K.PATH_OF_THE_DEAD: F.SPIRIT,
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
