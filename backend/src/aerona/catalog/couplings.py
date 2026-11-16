from types import MappingProxyType

from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.couplings import CarrionRest, RestraintKind, RiteComponent
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.world import WorldType

C = RiteComponent
F = BodyFunction
S = MagicSchool
V = BiologyVariant

COMPONENT_FUNCTIONS = MappingProxyType(
    {
        C.SPOKEN: (F.SPEECH,),
        C.GESTURED: (F.GRASP, F.FINE_MANIPULATION),
        C.INSCRIBED: (F.SIGHT, F.FINE_MANIPULATION),
        C.SUNG: (F.BREATH, F.SPEECH),
        C.DANCED: (F.LOCOMOTION,),
        C.MATERIAL: (),
        C.MENTAL: (F.COGNITION,),
    }
)

RESTRAINT_BLOCKS = MappingProxyType(
    {
        RestraintKind.GAG: frozenset({C.SPOKEN, C.SUNG}),
        RestraintKind.BOUND_HANDS: frozenset({C.GESTURED, C.INSCRIBED}),
        RestraintKind.BLINDFOLD: frozenset({C.INSCRIBED}),
    }
)

SCHOOL_COMPONENTS = MappingProxyType(
    {
        S.ELEMENTAL_FIRE: (C.SPOKEN, C.GESTURED, C.MATERIAL),
        S.ELEMENTAL_WATER: (C.SUNG, C.GESTURED),
        S.EARTH: (C.DANCED, C.MATERIAL),
        S.STORM: (C.SPOKEN, C.GESTURED),
        S.LIFE: (C.SUNG, C.MATERIAL),
        S.DEATH: (C.SPOKEN, C.MATERIAL),
        S.MIND: (C.MENTAL,),
        S.ILLUSION: (C.GESTURED, C.MENTAL),
        S.DIVINATION: (C.INSCRIBED, C.MENTAL),
        S.WARDING: (C.INSCRIBED, C.SPOKEN),
        S.BINDING: (C.SPOKEN, C.INSCRIBED),
        S.SUMMONING: (C.SPOKEN, C.DANCED, C.MATERIAL),
        S.BLOOD: (C.MATERIAL, C.GESTURED),
        S.VOID: (C.MENTAL, C.SPOKEN),
    }
)

BIOLOGY_COMPONENTS = MappingProxyType(
    {
        V.INCORPOREAL: frozenset({C.MENTAL, C.SPOKEN}),
        V.CONSTRUCT: frozenset({C.INSCRIBED, C.MATERIAL}),
        V.AQUATIC: frozenset(set(RiteComponent) - {C.INSCRIBED}),
        V.PLANT_LIKE: frozenset({C.MATERIAL}),
    }
)
ENSOULED_COMPONENTS = frozenset({C.MENTAL})
BODILESS_VARIANTS = frozenset({V.INCORPOREAL, V.GASEOUS})
VOICE_REPLACED = MappingProxyType({V.GASEOUS: frozenset({C.SPOKEN, C.SUNG})})
COLLECTIVE_COMPONENTS = MappingProxyType({V.HIVE: frozenset({C.MENTAL})})
SLOW_VARIANTS = frozenset({V.PLANT_LIKE})

W = WorldType
WORLD_RESTS = MappingProxyType(
    {
        W.GAS: CarrionRest.DRIFTING,
        W.HOT_GIANT: CarrionRest.DRIFTING,
        W.ICE_GIANT: CarrionRest.DRIFTING,
        W.ASTEROID_BELT: CarrionRest.FLOATING,
        W.VOID_POCKET: CarrionRest.FLOATING,
        W.SHATTERED: CarrionRest.FLOATING,
        W.GENERATION_SHIP: CarrionRest.FLOATING,
        W.ICE: CarrionRest.FROZEN,
        W.ICE_SHELL: CarrionRest.FROZEN,
        W.METHANE: CarrionRest.FROZEN,
        W.DWARF_PLANET: CarrionRest.FROZEN,
        W.SAND: CarrionRest.MUMMIFIED,
        W.DEAD: CarrionRest.MUMMIFIED,
    }
)
KEEPING_RESTS = frozenset({CarrionRest.MUMMIFIED, CarrionRest.FROZEN, CarrionRest.FLOATING})
