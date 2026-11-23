from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import AttackDelivery, AttackEffect, AttackRange, Biochemistry, SizeClass, TissueMaterial
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import CreatureTrait

P = BodyPlan
T = TissueMaterial


@dataclass(frozen=True)
class TissueSpec:
    material: TissueMaterial
    label: str
    armour_pct: int
    harm_pct: int
    shear_yield: int
    impact_yield: int
    hardness: int
    flexibility: int
    heat_resistance: int
    conductivity: int


@dataclass(frozen=True)
class AttackSpec:
    delivery: AttackDelivery
    effect: AttackEffect
    range: AttackRange
    permanent: bool = False


PLAN_LIMBS: MappingProxyType[BodyPlan, int] = total(
    BodyPlan,
    {
        P.HUMANOID: 4,
        P.QUADRUPED: 4,
        P.AVIAN: 2,
        P.SERPENTINE: 0,
        P.INSECTOID: 6,
        P.AQUATIC: 0,
        P.AMORPHOUS: 0,
        P.ARBOREAL: 0,
        P.INCORPOREAL: 0,
        P.COLOSSAL: 4,
        P.CONSTRUCT: 4,
        P.DIVINE_MANIFEST: 4,
        P.TENTACLED: 8,
        P.CENTAUROID: 6,
        P.RADIAL: 5,
        P.COLONIAL: 0,
    },
)
PLAN_SKIN: MappingProxyType[BodyPlan, TissueMaterial] = total(
    BodyPlan,
    {
        P.HUMANOID: T.SOFT_TISSUE,
        P.QUADRUPED: T.HIDE,
        P.AVIAN: T.PLUMAGE,
        P.SERPENTINE: T.PLATES,
        P.INSECTOID: T.SHELL,
        P.AQUATIC: T.PLATES,
        P.AMORPHOUS: T.SOFT_TISSUE,
        P.ARBOREAL: T.FIBROUS,
        P.INCORPOREAL: T.INSUBSTANTIAL,
        P.COLOSSAL: T.HIDE,
        P.CONSTRUCT: T.MINERAL,
        P.DIVINE_MANIFEST: T.SOFT_TISSUE,
        P.TENTACLED: T.SOFT_TISSUE,
        P.CENTAUROID: T.HIDE,
        P.RADIAL: T.RIGID,
        P.COLONIAL: T.SOFT_TISSUE,
    },
)
LIFE_SKIN: MappingProxyType[Biochemistry, TissueMaterial] = MappingProxyType(
    {Biochemistry.SILICON: T.MINERAL, Biochemistry.CRYSTAL: T.CRYSTALLINE, Biochemistry.VOID: T.INSUBSTANTIAL, Biochemistry.CARBON_AMMONIA: T.FROZEN}
)
TRAIT_SKIN: MappingProxyType[CreatureTrait, TissueMaterial] = MappingProxyType({CreatureTrait.STONESKIN: T.MINERAL, CreatureTrait.ARMOURED: T.PLATES})
TRAIT_ATTACKS: MappingProxyType[CreatureTrait, AttackSpec] = MappingProxyType(
    {
        CreatureTrait.FIRE_BREATHING: AttackSpec(AttackDelivery.BREATH, AttackEffect.HEAT, AttackRange.NEAR),
        CreatureTrait.COLD_BREATHING: AttackSpec(AttackDelivery.BREATH, AttackEffect.COLD, AttackRange.NEAR),
    }
)
MONSTER_PLANS: tuple[BodyPlan, ...] = (
    P.QUADRUPED,
    P.SERPENTINE,
    P.AVIAN,
    P.INSECTOID,
    P.AQUATIC,
    P.AMORPHOUS,
    P.ARBOREAL,
    P.HUMANOID,
    P.COLOSSAL,
    P.CONSTRUCT,
)
MONSTER_SIZES: tuple[SizeClass, ...] = (SizeClass.LARGE, SizeClass.HUGE, SizeClass.COLOSSAL)
EXOTIC_TISSUES: tuple[TissueMaterial, ...] = (T.CRYSTALLINE, T.ENERGY, T.VAPOUR, T.METALLIC, T.GEL)
HOARDED: tuple[MaterialKind, ...] = (MaterialKind.GOLD, MaterialKind.SILVER, MaterialKind.GEMS, MaterialKind.AMBER, MaterialKind.IVORY, MaterialKind.CRYSTAL)
TISSUES: MappingProxyType[TissueMaterial, TissueSpec] = MappingProxyType(
    {
        spec.material: spec
        for spec in (
            TissueSpec(T.SOFT_TISSUE, "Soft tissue", 0, 0, 4, 10, 5, 80, 10, 40),
            TissueSpec(T.HIDE, "Hide", 10, 0, 10, 16, 20, 70, 20, 30),
            TissueSpec(T.PLATES, "Plates", 20, 0, 22, 28, 45, 40, 35, 20),
            TissueSpec(T.SHELL, "Shell", 25, 0, 40, 45, 60, 15, 30, 10),
            TissueSpec(T.PLUMAGE, "Plumage", 5, 0, 3, 8, 5, 90, 40, 5),
            TissueSpec(T.FIBROUS, "Fibrous", 20, 0, 15, 35, 35, 50, 5, 15),
            TissueSpec(T.FROZEN, "Frozen", 25, 5, 20, 25, 50, 5, 0, 30),
            TissueSpec(T.VAPOUR, "Vapour", 30, 15, 3, 3, 0, 100, 60, 50),
            TissueSpec(T.RIGID, "Rigid frame", 15, 0, 25, 30, 50, 20, 30, 20),
            TissueSpec(T.MINERAL, "Mineral", 40, 5, 45, 60, 75, 5, 70, 15),
            TissueSpec(T.METALLIC, "Metallic", 50, 10, 60, 55, 85, 20, 60, 95),
            TissueSpec(T.CRYSTALLINE, "Crystalline", 35, 10, 50, 35, 80, 5, 55, 5),
            TissueSpec(T.GEL, "Gel", 15, 5, 8, 30, 5, 100, 25, 60),
            TissueSpec(T.ENERGY, "Energy", 15, 25, 5, 5, 0, 100, 95, 90),
            TissueSpec(T.INSUBSTANTIAL, "Insubstantial", 45, 15, 55, 55, 0, 100, 80, 0),
        )
    }
)
