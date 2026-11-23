from dataclasses import dataclass
from functools import cache

from aerona.domain.enums.body import BodyFunction, BodyPart, BodyPlan, BodyRegion
from aerona.domain.enums.mortal import PunishmentKind

F = BodyFunction
P = BodyPart
R = BodyRegion

FINGER_COUNT = 10
FINGERS = BodyPart.FINGERS
TOE_COUNT = 10
TOES = BodyPart.TOES
TOOTH_COUNT = 32
MAMMAL_TOOTH_COUNT = 42
SERPENT_TOOTH_COUNT = 100
FISH_TOOTH_COUNT = 60
TEETH = BodyPart.TEETH
COUNTED_KEYS = (FINGERS, TOES, TEETH)


@dataclass(frozen=True)
class Part:
    key: BodyPart
    label: str
    region: BodyRegion
    functions: tuple[BodyFunction, ...]
    severable: bool = False
    internal: bool = False
    vital: bool = False
    counted: int = 0
    guards: bool = False
    shared: bool = False
    paralyses: bool = False

    @property
    def visible(self) -> bool:
        return not self.internal


@dataclass(frozen=True)
class Anatomy:
    plan: BodyPlan
    label: str
    parts: tuple[Part, ...]
    breathes: bool = True
    bleeds: bool = True
    heals: bool = True
    infects: bool = True
    material: bool = True
    colonial: bool = False

    def part(self, key: str) -> Part | None:
        return next((part for part in self.parts if part.key == key), None)

    def with_function(self, function: BodyFunction) -> tuple[Part, ...]:
        return tuple(part for part in self.parts if function in part.functions)

    def in_region(self, region: BodyRegion) -> tuple[Part, ...]:
        return tuple(part for part in self.parts if part.region is region)

    @property
    def functions(self) -> frozenset[BodyFunction]:
        return frozenset(function for part in self.parts for function in part.functions)

    def full_count(self, key: str) -> int:
        part = self.part(key)
        return part.counted if part is not None else 0

    @property
    def full_counts(self) -> dict[str, int]:
        return {key.value: self.full_count(key) for key in COUNTED_KEYS}


def _pair(left: BodyPart, right: BodyPart, label: str, region: BodyRegion, functions: tuple[BodyFunction, ...], *, severable: bool = True) -> tuple[Part, Part]:
    return (
        Part(left, f"Left {label}", region, functions, severable=severable),
        Part(right, f"Right {label}", region, functions, severable=severable),
    )


SPINE_PART = Part(P.SPINE, "Spine", R.TORSO, (F.LOCOMOTION,), internal=True, paralyses=True)
CARAPACE_PART = Part(P.CARAPACE, "Carapace", R.TORSO, (F.VITAL,), guards=True)


def _organs(*, breath: bool = True) -> tuple[Part, ...]:
    lungs = (Part(P.LUNGS, "Lungs", R.TORSO, (F.BREATH,), internal=True, vital=True),) if breath else ()
    return (
        Part(P.HEART, "Heart", R.TORSO, (F.VITAL,), internal=True, vital=True),
        *lungs,
        Part(P.GUT, "Gut", R.TORSO, (F.VITAL,), internal=True),
        Part(P.GROIN, "Groin", R.TORSO, (F.REPRODUCTION,), internal=True),
    )


HUMANOID_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION,), vital=True),
    Part(P.FACE, "Face", R.HEAD, (F.PRESENCE,)),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "eye", R.HEAD, (F.SIGHT,)),
    *_pair(P.LEFT_EAR, P.RIGHT_EAR, "ear", R.HEAD, (F.HEARING,)),
    Part(P.NOSE, "Nose", R.HEAD, (F.PRESENCE,), severable=True),
    Part(P.JAW, "Jaw", R.HEAD, (F.SPEECH,)),
    Part(TEETH, "Teeth", R.HEAD, (F.SPEECH, F.PRESENCE), severable=True, counted=TOOTH_COUNT),
    Part(P.TONGUE, "Tongue", R.HEAD, (F.SPEECH,), severable=True, internal=True),
    Part(P.NECK, "Neck", R.TORSO, (F.BREATH,), vital=True),
    Part(P.TORSO, "Torso", R.TORSO, (F.VITAL,)),
    *_organs(),
    *_pair(P.LEFT_ARM, P.RIGHT_ARM, "arm", R.ARMS, (F.GRASP,)),
    *_pair(P.LEFT_HAND, P.RIGHT_HAND, "hand", R.ARMS, (F.GRASP,)),
    Part(FINGERS, "Fingers", R.ARMS, (F.FINE_MANIPULATION,), severable=True, counted=FINGER_COUNT),
    *_pair(P.LEFT_LEG, P.RIGHT_LEG, "leg", R.LEGS, (F.LOCOMOTION,)),
    *_pair(P.LEFT_FOOT, P.RIGHT_FOOT, "foot", R.LEGS, (F.LOCOMOTION,)),
    Part(TOES, "Toes", R.LEGS, (F.LOCOMOTION,), severable=True, counted=TOE_COUNT),
    SPINE_PART,
)

QUADRUPED_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION,), vital=True),
    Part(P.FACE, "Muzzle", R.HEAD, (F.PRESENCE,)),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "eye", R.HEAD, (F.SIGHT,)),
    *_pair(P.LEFT_EAR, P.RIGHT_EAR, "ear", R.HEAD, (F.HEARING,)),
    Part(P.JAW, "Jaws", R.HEAD, (F.SPEECH, F.GRASP)),
    Part(TEETH, "Teeth", R.HEAD, (F.GRASP, F.PRESENCE), severable=True, counted=MAMMAL_TOOTH_COUNT),
    Part(P.NECK, "Neck", R.TORSO, (F.BREATH,), vital=True),
    Part(P.TORSO, "Flank", R.TORSO, (F.VITAL,)),
    *_organs(),
    *_pair(P.LEFT_FORELEG, P.RIGHT_FORELEG, "foreleg", R.LEGS, (F.LOCOMOTION,)),
    *_pair(P.LEFT_HINDLEG, P.RIGHT_HINDLEG, "hind leg", R.LEGS, (F.LOCOMOTION,)),
    Part(P.TAIL, "Tail", R.TAIL, (F.TAIL,), severable=True),
    SPINE_PART,
)

AVIAN_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION,), vital=True),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "eye", R.HEAD, (F.SIGHT,)),
    Part(P.JAW, "Beak", R.HEAD, (F.SPEECH, F.GRASP, F.PRESENCE)),
    Part(P.NECK, "Neck", R.TORSO, (F.BREATH,), vital=True),
    Part(P.TORSO, "Breast", R.TORSO, (F.VITAL,)),
    *_organs(),
    *_pair(P.LEFT_WING, P.RIGHT_WING, "wing", R.WINGS, (F.FLIGHT,)),
    *_pair(P.LEFT_LEG, P.RIGHT_LEG, "talon", R.LEGS, (F.LOCOMOTION, F.FINE_MANIPULATION)),
    Part(P.TAIL, "Tail feathers", R.TAIL, (F.TAIL,), severable=True),
    SPINE_PART,
)

SERPENTINE_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION, F.PRESENCE), vital=True),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "eye", R.HEAD, (F.SIGHT,)),
    Part(P.JAW, "Jaws", R.HEAD, (F.SPEECH, F.GRASP)),
    Part(TEETH, "Teeth", R.HEAD, (F.GRASP, F.PRESENCE), severable=True, counted=SERPENT_TOOTH_COUNT),
    Part(P.TONGUE, "Forked tongue", R.HEAD, (F.HEARING,), severable=True, internal=True),
    Part(P.TORSO, "Coils", R.TORSO, (F.LOCOMOTION, F.VITAL)),
    *_organs(),
    Part(P.TAIL, "Tail", R.TAIL, (F.LOCOMOTION, F.TAIL), severable=True),
    SPINE_PART,
)

INSECTOID_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION,), vital=True),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "compound eye", R.HEAD, (F.SIGHT,)),
    *_pair(P.LEFT_ANTENNA, P.RIGHT_ANTENNA, "antenna", R.HEAD, (F.HEARING,)),
    Part(P.JAW, "Mandibles", R.HEAD, (F.SPEECH, F.GRASP)),
    Part(P.TORSO, "Thorax", R.TORSO, (F.VITAL, F.PRESENCE)),
    *_organs(breath=False),
    *_pair(P.LEFT_FORELEG, P.RIGHT_FORELEG, "foreleg", R.ARMS, (F.GRASP, F.FINE_MANIPULATION)),
    *_pair(P.LEFT_MIDLEG, P.RIGHT_MIDLEG, "middle leg", R.LEGS, (F.LOCOMOTION,)),
    *_pair(P.LEFT_HINDLEG, P.RIGHT_HINDLEG, "hind leg", R.LEGS, (F.LOCOMOTION,)),
    CARAPACE_PART,
)

AQUATIC_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION, F.PRESENCE), vital=True),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "eye", R.HEAD, (F.SIGHT,)),
    Part(P.JAW, "Jaws", R.HEAD, (F.SPEECH, F.GRASP)),
    Part(TEETH, "Teeth", R.HEAD, (F.GRASP, F.PRESENCE), severable=True, counted=FISH_TOOTH_COUNT),
    Part(P.GILLS, "Gills", R.TORSO, (F.BREATH,), vital=True),
    Part(P.TORSO, "Body", R.TORSO, (F.VITAL,)),
    *_organs(breath=False),
    *_pair(P.LEFT_FIN, P.RIGHT_FIN, "fin", R.ARMS, (F.LOCOMOTION, F.FINE_MANIPULATION)),
    Part(P.TAIL, "Tail fin", R.TAIL, (F.LOCOMOTION, F.TAIL), severable=True),
    SPINE_PART,
)

AMORPHOUS_PARTS: tuple[Part, ...] = (
    Part(P.CORE, "Core", R.TORSO, (F.VITAL, F.COGNITION), internal=True, vital=True),
    Part(P.TORSO, "Mass", R.TORSO, (F.LOCOMOTION, F.BREATH, F.REPRODUCTION, F.PRESENCE)),
    Part(P.PSEUDOPODS, "Pseudopods", R.ARMS, (F.GRASP, F.FINE_MANIPULATION), severable=True),
    Part(P.EYE, "Sensing skin", R.HEAD, (F.SIGHT, F.HEARING, F.SPEECH)),
)

ARBOREAL_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Crown", R.HEAD, (F.SIGHT, F.PRESENCE)),
    Part(P.FACE, "Bark face", R.HEAD, (F.SPEECH, F.HEARING)),
    Part(P.TORSO, "Trunk", R.TORSO, (F.VITAL, F.BREATH)),
    Part(P.CORE, "Heartwood", R.TORSO, (F.VITAL, F.COGNITION), internal=True, vital=True),
    Part(P.GROIN, "Seed pods", R.TORSO, (F.REPRODUCTION,), severable=True),
    *_pair(P.LEFT_BRANCH, P.RIGHT_BRANCH, "branch", R.ARMS, (F.GRASP, F.FINE_MANIPULATION)),
    Part(P.ROOTS, "Roots", R.LEGS, (F.LOCOMOTION,)),
)

INCORPOREAL_PARTS: tuple[Part, ...] = (
    Part(P.CORE, "Essence", R.TORSO, (F.VITAL, F.COGNITION, F.REPRODUCTION), vital=True),
    Part(P.FACE, "Visage", R.HEAD, (F.PRESENCE, F.SPEECH, F.SIGHT, F.HEARING)),
    Part(P.TORSO, "Shroud", R.TORSO, (F.LOCOMOTION, F.GRASP, F.FINE_MANIPULATION, F.BREATH)),
)

CONSTRUCT_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION,), vital=True),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "lens", R.HEAD, (F.SIGHT,)),
    Part(P.JAW, "Voice", R.HEAD, (F.SPEECH, F.HEARING, F.PRESENCE)),
    Part(P.TORSO, "Frame", R.TORSO, (F.BREATH,)),
    Part(P.CORE, "Animating core", R.TORSO, (F.VITAL,), internal=True, vital=True),
    *_pair(P.LEFT_ARM, P.RIGHT_ARM, "arm", R.ARMS, (F.GRASP,)),
    *_pair(P.LEFT_HAND, P.RIGHT_HAND, "hand", R.ARMS, (F.GRASP,)),
    Part(FINGERS, "Fingers", R.ARMS, (F.FINE_MANIPULATION,), severable=True, counted=FINGER_COUNT),
    *_pair(P.LEFT_LEG, P.RIGHT_LEG, "leg", R.LEGS, (F.LOCOMOTION,)),
)

DIVINE_PARTS: tuple[Part, ...] = (*HUMANOID_PARTS, Part(P.AURA, "Aura", R.HEAD, (F.PRESENCE,)))

TENTACLED_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION,), vital=True),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "eye", R.HEAD, (F.SIGHT,)),
    Part(P.BEAK, "Beak", R.HEAD, (F.SPEECH, F.GRASP, F.PRESENCE)),
    Part(P.CORE, "Mantle", R.TORSO, (F.VITAL, F.PRESENCE)),
    Part(P.GILLS, "Gills", R.TORSO, (F.BREATH,), internal=True, vital=True),
    *_organs(breath=False),
    Part(P.TENTACLES, "Tentacles", R.ARMS, (F.GRASP, F.FINE_MANIPULATION, F.LOCOMOTION), severable=True, shared=True),
)

CENTAUROID_PARTS: tuple[Part, ...] = (
    Part(P.HEAD, "Head", R.HEAD, (F.COGNITION,), vital=True),
    Part(P.FACE, "Face", R.HEAD, (F.PRESENCE,)),
    *_pair(P.LEFT_EYE, P.RIGHT_EYE, "eye", R.HEAD, (F.SIGHT,)),
    *_pair(P.LEFT_EAR, P.RIGHT_EAR, "ear", R.HEAD, (F.HEARING,)),
    Part(P.JAW, "Jaw", R.HEAD, (F.SPEECH,)),
    Part(TEETH, "Teeth", R.HEAD, (F.SPEECH, F.PRESENCE), severable=True, counted=TOOTH_COUNT),
    Part(P.TONGUE, "Tongue", R.HEAD, (F.SPEECH,), severable=True, internal=True),
    Part(P.NECK, "Neck", R.TORSO, (F.BREATH,), vital=True),
    Part(P.TORSO, "Upper body and flank", R.TORSO, (F.VITAL,)),
    *_organs(),
    SPINE_PART,
    *_pair(P.LEFT_ARM, P.RIGHT_ARM, "arm", R.ARMS, (F.GRASP,)),
    *_pair(P.LEFT_HAND, P.RIGHT_HAND, "hand", R.ARMS, (F.GRASP,)),
    Part(FINGERS, "Fingers", R.ARMS, (F.FINE_MANIPULATION,), severable=True, counted=FINGER_COUNT),
    *_pair(P.LEFT_FORELEG, P.RIGHT_FORELEG, "foreleg", R.LEGS, (F.LOCOMOTION,)),
    *_pair(P.LEFT_HINDLEG, P.RIGHT_HINDLEG, "hind leg", R.LEGS, (F.LOCOMOTION,)),
    Part(P.TAIL, "Tail", R.TAIL, (F.TAIL,), severable=True),
)

RADIAL_PARTS: tuple[Part, ...] = (
    Part(P.CORE, "Core", R.TORSO, (F.VITAL, F.COGNITION), vital=True),
    Part(P.EYE, "Sensing spots", R.TORSO, (F.SIGHT, F.HEARING)),
    *_organs(breath=False),
    Part(P.TENTACLES, "Arms around the core", R.ARMS, (F.GRASP, F.FINE_MANIPULATION, F.LOCOMOTION), severable=True, shared=True),
)

COLONIAL_PARTS: tuple[Part, ...] = (
    Part(P.TORSO, "Members", R.TORSO, (F.VITAL, F.LOCOMOTION, F.BREATH, F.REPRODUCTION, F.PRESENCE), shared=True),
    Part(P.CORE, "Joined centre", R.TORSO, (F.COGNITION,), internal=True),
    Part(P.EYE, "Sensing members", R.HEAD, (F.SIGHT, F.HEARING)),
    Part(P.PSEUDOPODS, "Reaching members", R.ARMS, (F.GRASP, F.FINE_MANIPULATION), severable=True, shared=True),
)

ANATOMIES: dict[BodyPlan, Anatomy] = {
    BodyPlan.HUMANOID: Anatomy(BodyPlan.HUMANOID, "Humanoid", HUMANOID_PARTS),
    BodyPlan.QUADRUPED: Anatomy(BodyPlan.QUADRUPED, "Four-legged", QUADRUPED_PARTS),
    BodyPlan.AVIAN: Anatomy(BodyPlan.AVIAN, "Winged", AVIAN_PARTS),
    BodyPlan.SERPENTINE: Anatomy(BodyPlan.SERPENTINE, "Serpentine", SERPENTINE_PARTS),
    BodyPlan.INSECTOID: Anatomy(BodyPlan.INSECTOID, "Insectoid", INSECTOID_PARTS),
    BodyPlan.AQUATIC: Anatomy(BodyPlan.AQUATIC, "Aquatic", AQUATIC_PARTS),
    BodyPlan.AMORPHOUS: Anatomy(BodyPlan.AMORPHOUS, "Amorphous", AMORPHOUS_PARTS, bleeds=False),
    BodyPlan.ARBOREAL: Anatomy(BodyPlan.ARBOREAL, "Tree-bodied", ARBOREAL_PARTS, bleeds=False),
    BodyPlan.INCORPOREAL: Anatomy(BodyPlan.INCORPOREAL, "Incorporeal", INCORPOREAL_PARTS, breathes=False, bleeds=False, infects=False, material=False),
    BodyPlan.COLOSSAL: Anatomy(BodyPlan.COLOSSAL, "Colossal", HUMANOID_PARTS),
    BodyPlan.CONSTRUCT: Anatomy(BodyPlan.CONSTRUCT, "Construct", CONSTRUCT_PARTS, breathes=False, bleeds=False, heals=False, infects=False),
    BodyPlan.DIVINE_MANIFEST: Anatomy(BodyPlan.DIVINE_MANIFEST, "Divine manifestation", DIVINE_PARTS, infects=False),
    BodyPlan.TENTACLED: Anatomy(BodyPlan.TENTACLED, "Many-armed", TENTACLED_PARTS),
    BodyPlan.CENTAUROID: Anatomy(BodyPlan.CENTAUROID, "Upright on four legs", CENTAUROID_PARTS),
    BodyPlan.RADIAL: Anatomy(BodyPlan.RADIAL, "Built round a centre", RADIAL_PARTS),
    BodyPlan.COLONIAL: Anatomy(BodyPlan.COLONIAL, "Many living members", COLONIAL_PARTS, colonial=True),
}

SIGHT_PARTS = frozenset(part.key for anatomy in ANATOMIES.values() for part in anatomy.parts if F.SIGHT in part.functions)

TRAIT_PARTS: dict[BodyFunction, Part] = {
    F.FLIGHT: Part(P.WINGS, "Wings", R.WINGS, (F.FLIGHT,), severable=True),
    F.VENOM: Part(P.VENOM_GLAND, "Venom gland", R.HEAD, (F.VENOM,), internal=True),
    F.HORN: Part(P.HORN, "Horn", R.HEAD, (F.HORN, F.PRESENCE), severable=True),
    F.TAIL: Part(P.TAIL, "Tail", R.TAIL, (F.TAIL,), severable=True),
}


@cache
def anatomy_of(plan: BodyPlan, traits: frozenset[BodyFunction] = frozenset()) -> Anatomy:
    base = ANATOMIES[plan]
    extra = tuple(TRAIT_PARTS[trait] for trait in sorted(traits) if trait in TRAIT_PARTS and trait not in base.functions)
    if not extra:
        return base
    return Anatomy(base.plan, base.label, (*base.parts, *extra), base.breathes, base.bleeds, base.heals, base.infects, base.material)


HEAD_PARTS = frozenset({BodyPart.HEAD, BodyPart.FACE})
MUTILATIONS: dict[PunishmentKind, tuple[BodyPart, ...]] = {
    PunishmentKind.HAND: (BodyPart.RIGHT_HAND,),
    PunishmentKind.TONGUE: (BodyPart.TONGUE,),
    PunishmentKind.EYES: (BodyPart.LEFT_EYE, BodyPart.RIGHT_EYE),
}
