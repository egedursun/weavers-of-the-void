from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import Biochemistry, BreathKind, TissueMaterial
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


PLAN_LIMBS: MappingProxyType[BodyPlan, int] = MappingProxyType(
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
    }
)
PLAN_SKIN: MappingProxyType[BodyPlan, TissueMaterial] = MappingProxyType(
    {
        P.HUMANOID: T.FLESH,
        P.QUADRUPED: T.HIDE,
        P.AVIAN: T.FEATHER,
        P.SERPENTINE: T.SCALE,
        P.INSECTOID: T.CHITIN,
        P.AQUATIC: T.SCALE,
        P.AMORPHOUS: T.FLESH,
        P.ARBOREAL: T.WOOD,
        P.INCORPOREAL: T.VOID_STUFF,
        P.COLOSSAL: T.HIDE,
        P.CONSTRUCT: T.STONE,
        P.DIVINE_MANIFEST: T.FLESH,
    }
)
LIFE_SKIN: MappingProxyType[Biochemistry, TissueMaterial] = MappingProxyType(
    {Biochemistry.SILICON: T.STONE, Biochemistry.CRYSTAL: T.CRYSTAL, Biochemistry.VOID: T.VOID_STUFF, Biochemistry.CARBON_AMMONIA: T.ICE}
)
TRAIT_SKIN: MappingProxyType[CreatureTrait, TissueMaterial] = MappingProxyType({CreatureTrait.STONESKIN: T.STONE, CreatureTrait.ARMOURED: T.SCALE})
TRAIT_BREATH: MappingProxyType[CreatureTrait, BreathKind] = MappingProxyType(
    {CreatureTrait.FIRE_BREATHING: BreathKind.FIRE, CreatureTrait.COLD_BREATHING: BreathKind.FROST}
)
EXOTIC_TISSUES: tuple[TissueMaterial, ...] = (T.CRYSTAL, T.FIRE, T.STEAM, T.METAL)
HOARDED: tuple[MaterialKind, ...] = (MaterialKind.GOLD, MaterialKind.SILVER, MaterialKind.GEMS, MaterialKind.AMBER, MaterialKind.IVORY, MaterialKind.CRYSTAL)
TISSUES: MappingProxyType[TissueMaterial, TissueSpec] = MappingProxyType(
    {
        spec.material: spec
        for spec in (
            TissueSpec(T.FLESH, "Flesh", 0, 0),
            TissueSpec(T.HIDE, "Hide", 10, 0),
            TissueSpec(T.SCALE, "Scale", 20, 0),
            TissueSpec(T.CHITIN, "Chitin", 25, 0),
            TissueSpec(T.FEATHER, "Feather", 5, 0),
            TissueSpec(T.BONE, "Bone", 15, 0),
            TissueSpec(T.WOOD, "Wood", 20, 0),
            TissueSpec(T.STONE, "Stone", 40, 5),
            TissueSpec(T.CRYSTAL, "Crystal", 35, 10),
            TissueSpec(T.METAL, "Metal", 50, 10),
            TissueSpec(T.ICE, "Ice", 25, 5),
            TissueSpec(T.FIRE, "Fire", 15, 25),
            TissueSpec(T.STEAM, "Steam", 30, 15),
            TissueSpec(T.VOID_STUFF, "Void", 45, 15),
        )
    }
)
