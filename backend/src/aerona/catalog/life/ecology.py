from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.constructs import ContractStatus
from aerona.domain.enums.ecology import AttackDelivery, AttackRange, Diet, SizeClass, SpeciesClass, TissueMaterial

TOWN_DELIVERIES = (AttackDelivery.BREATH, AttackDelivery.SPIT, AttackDelivery.SPRAY, AttackDelivery.EMANATION, AttackDelivery.VOICE, AttackDelivery.SPORES)


CLOSE_DELIVERIES = (AttackDelivery.TOUCH, AttackDelivery.BITE, AttackDelivery.STING)


BONE_OF = {material: material for material in (TissueMaterial.MINERAL, TissueMaterial.CRYSTALLINE, TissueMaterial.METALLIC)}


CARRIED_BY: Mapping[AttackDelivery, Transmission] = total(
    AttackDelivery,
    {
        AttackDelivery.BREATH: Transmission.INHALATION,
        AttackDelivery.SPIT: Transmission.CONTACT,
        AttackDelivery.SPRAY: Transmission.CONTACT,
        AttackDelivery.EMANATION: Transmission.INHALATION,
        AttackDelivery.GAZE: Transmission.GAZE,
        AttackDelivery.VOICE: Transmission.EXPERIENCE,
        AttackDelivery.TOUCH: Transmission.CONTACT,
        AttackDelivery.SPORES: Transmission.INHALATION,
        AttackDelivery.BITE: Transmission.BITE,
        AttackDelivery.STING: Transmission.BLOOD,
        AttackDelivery.PROJECTILE: Transmission.BLOOD,
        AttackDelivery.CONSTRICTION: Transmission.CONTACT,
    },
)


OPEN = (ContractStatus.POSTED, ContractStatus.TAKEN)


LIFESPAN = {
    SizeClass.MICROSCOPIC: 1,
    SizeClass.TINY: 2,
    SizeClass.SMALL: 6,
    SizeClass.MEDIUM: 15,
    SizeClass.LARGE: 25,
    SizeClass.HUGE: 60,
    SizeClass.COLOSSAL: 200,
}


LITTER = {SizeClass.MICROSCOPIC: 50, SizeClass.TINY: 8, SizeClass.SMALL: 5, SizeClass.MEDIUM: 3, SizeClass.LARGE: 1, SizeClass.HUGE: 1, SizeClass.COLOSSAL: 1}


METABOLISM = {
    SizeClass.MICROSCOPIC: 95,
    SizeClass.TINY: 80,
    SizeClass.SMALL: 65,
    SizeClass.MEDIUM: 50,
    SizeClass.LARGE: 40,
    SizeClass.HUGE: 30,
    SizeClass.COLOSSAL: 20,
}


PLANT_PLANS = {SpeciesClass.PLANT: BodyPlan.ARBOREAL, SpeciesClass.FUNGUS: BodyPlan.AMORPHOUS}


PLANT_DIETS = {SpeciesClass.PLANT: Diet.PHOTOSYNTHETIC, SpeciesClass.FUNGUS: Diet.SCAVENGER}

GENERATE_PACKAGE_KINDS = (PackageKind.SNAKE_VENOM, PackageKind.LYCANTHROPY, PackageKind.VAMPIRISM, PackageKind.VOID_TAINT)
ATTACK_SPECS_ATTACK_RANGES = (AttackRange.NEAR, AttackRange.FAR)
USES_OF_SIZE_CLASSS = frozenset({SizeClass.LARGE, SizeClass.HUGE, SizeClass.COLOSSAL})
