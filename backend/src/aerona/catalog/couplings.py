from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.couplings import CarrionRest, RestraintKind, RiteComponent
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.world import WorldType
from aerona.rules.registry import Rules

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
        C.OFFERED: (),
        C.COMMUNAL: (F.SPEECH,),
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
        W.ROGUE: CarrionRest.FROZEN,
        W.DWARF_PLANET: CarrionRest.FROZEN,
        W.SAND: CarrionRest.MUMMIFIED,
        W.DEAD: CarrionRest.MUMMIFIED,
    }
)


@dataclass(frozen=True)
class RestSpec:
    keeps: bool
    soil: int
    disease: Callable[[Rules], int]
    scavenger: Callable[[Rules], int]
    restless: Callable[[Rules], int]
    fossil: Callable[[Rules], int]
    gone: bool = False


CARRION_RESTS: Mapping[CarrionRest, RestSpec] = total(
    CarrionRest,
    {
        CarrionRest.ROTTING: RestSpec(
            keeps=False,
            soil=1,
            disease=lambda rules: rules.carrion.rotting_disease,
            scavenger=lambda rules: rules.carrion.rotting_scavenger,
            restless=lambda rules: rules.carrion.rotting_restless,
            fossil=lambda rules: rules.carrion.rotting_fossil,
        ),
        CarrionRest.MUMMIFIED: RestSpec(
            keeps=True,
            soil=0,
            disease=lambda rules: rules.carrion.mummified_disease,
            scavenger=lambda rules: rules.carrion.mummified_scavenger,
            restless=lambda rules: rules.carrion.mummified_restless,
            fossil=lambda rules: rules.carrion.mummified_fossil,
        ),
        CarrionRest.FROZEN: RestSpec(
            keeps=True,
            soil=0,
            disease=lambda rules: rules.carrion.frozen_disease,
            scavenger=lambda rules: rules.carrion.frozen_scavenger,
            restless=lambda rules: rules.carrion.frozen_restless,
            fossil=lambda rules: rules.carrion.frozen_fossil,
        ),
        CarrionRest.DRIFTING: RestSpec(
            gone=True,
            keeps=False,
            soil=0,
            disease=lambda rules: rules.carrion.drifting_disease,
            scavenger=lambda rules: rules.carrion.drifting_scavenger,
            restless=lambda rules: rules.carrion.drifting_restless,
            fossil=lambda rules: rules.carrion.drifting_fossil,
        ),
        CarrionRest.FLOATING: RestSpec(
            keeps=True,
            soil=0,
            disease=lambda rules: rules.carrion.floating_disease,
            scavenger=lambda rules: rules.carrion.floating_scavenger,
            restless=lambda rules: rules.carrion.floating_restless,
            fossil=lambda rules: rules.carrion.floating_fossil,
        ),
        CarrionRest.BURIED: RestSpec(
            keeps=True,
            soil=2,
            disease=lambda rules: rules.carrion.buried_disease,
            scavenger=lambda rules: rules.carrion.buried_scavenger,
            restless=lambda rules: rules.carrion.buried_restless,
            fossil=lambda rules: rules.carrion.buried_fossil,
        ),
        CarrionRest.BURNED: RestSpec(
            gone=True,
            keeps=False,
            soil=1,
            disease=lambda rules: rules.carrion.burned_disease,
            scavenger=lambda rules: rules.carrion.burned_scavenger,
            restless=lambda rules: rules.carrion.burned_restless,
            fossil=lambda rules: rules.carrion.burned_fossil,
        ),
        CarrionRest.SCAVENGED: RestSpec(
            gone=True,
            keeps=False,
            soil=0,
            disease=lambda rules: rules.carrion.scavenged_disease,
            scavenger=lambda rules: rules.carrion.scavenged_scavenger,
            restless=lambda rules: rules.carrion.scavenged_restless,
            fossil=lambda rules: rules.carrion.scavenged_fossil,
        ),
        CarrionRest.SUNK: RestSpec(
            keeps=False,
            soil=0,
            disease=lambda rules: rules.carrion.sunk_disease,
            scavenger=lambda rules: rules.carrion.sunk_scavenger,
            restless=lambda rules: rules.carrion.sunk_restless,
            fossil=lambda rules: rules.carrion.sunk_fossil,
        ),
    },
)
KEEPING_RESTS = frozenset(rest for rest, spec in CARRION_RESTS.items() if spec.keeps)
