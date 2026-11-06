from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache

from aerona.domain.enums.body import BodyFunction, BodyPlan, BodyRegion

F = BodyFunction
R = BodyRegion

FINGER_COUNT = 10
FINGERS = "fingers"
TOE_COUNT = 10
TOES = "toes"
TOOTH_COUNT = 32
TEETH = "teeth"


@dataclass(frozen=True)
class Part:
    key: str
    label: str
    region: BodyRegion
    functions: tuple[BodyFunction, ...]
    severable: bool = False
    internal: bool = False
    vital: bool = False
    counted: int = 0

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

    def part(self, key: str) -> Part | None:
        return next((part for part in self.parts if part.key == key), None)

    def with_function(self, function: BodyFunction) -> tuple[Part, ...]:
        return tuple(part for part in self.parts if function in part.functions)

    def in_region(self, region: BodyRegion) -> tuple[Part, ...]:
        return tuple(part for part in self.parts if part.region is region)

    @property
    def functions(self) -> frozenset[BodyFunction]:
        return frozenset(function for part in self.parts for function in part.functions)


def _pair(key: str, label: str, region: BodyRegion, functions: tuple[BodyFunction, ...], *, severable: bool = True) -> tuple[Part, Part]:
    return (
        Part(f"left_{key}", f"Left {label}", region, functions, severable=severable),
        Part(f"right_{key}", f"Right {label}", region, functions, severable=severable),
    )


def _organs(*, breath: bool = True) -> tuple[Part, ...]:
    lungs = (Part("lungs", "Lungs", R.TORSO, (F.BREATH,), internal=True, vital=True),) if breath else ()
    return (
        Part("heart", "Heart", R.TORSO, (F.VITAL,), internal=True, vital=True),
        *lungs,
        Part("gut", "Gut", R.TORSO, (F.VITAL,), internal=True),
        Part("groin", "Groin", R.TORSO, (F.REPRODUCTION,), internal=True),
    )


HUMANOID_PARTS: tuple[Part, ...] = (
    Part("head", "Head", R.HEAD, (F.COGNITION,), vital=True),
    Part("face", "Face", R.HEAD, (F.PRESENCE,)),
    *_pair("eye", "eye", R.HEAD, (F.SIGHT,)),
    *_pair("ear", "ear", R.HEAD, (F.HEARING,)),
    Part("nose", "Nose", R.HEAD, (F.PRESENCE,), severable=True),
    Part("jaw", "Jaw", R.HEAD, (F.SPEECH,)),
    Part(TEETH, "Teeth", R.HEAD, (F.SPEECH, F.PRESENCE), severable=True, counted=TOOTH_COUNT),
    Part("tongue", "Tongue", R.HEAD, (F.SPEECH,), severable=True, internal=True),
    Part("neck", "Neck", R.TORSO, (F.BREATH,), vital=True),
    Part("torso", "Torso", R.TORSO, (F.VITAL,)),
    *_organs(),
    *_pair("arm", "arm", R.ARMS, (F.GRASP,)),
    *_pair("hand", "hand", R.ARMS, (F.GRASP,)),
    Part(FINGERS, "Fingers", R.ARMS, (F.FINE_MANIPULATION,), severable=True, counted=FINGER_COUNT),
    *_pair("leg", "leg", R.LEGS, (F.LOCOMOTION,)),
    *_pair("foot", "foot", R.LEGS, (F.LOCOMOTION,)),
    Part(TOES, "Toes", R.LEGS, (F.LOCOMOTION,), severable=True, counted=TOE_COUNT),
)

QUADRUPED_PARTS: tuple[Part, ...] = (
    Part("head", "Head", R.HEAD, (F.COGNITION,), vital=True),
    Part("face", "Muzzle", R.HEAD, (F.PRESENCE,)),
    *_pair("eye", "eye", R.HEAD, (F.SIGHT,)),
    *_pair("ear", "ear", R.HEAD, (F.HEARING,)),
    Part("jaw", "Jaws", R.HEAD, (F.SPEECH, F.GRASP)),
    Part("neck", "Neck", R.TORSO, (F.BREATH,), vital=True),
    Part("torso", "Flank", R.TORSO, (F.VITAL,)),
    *_organs(),
    *_pair("foreleg", "foreleg", R.LEGS, (F.LOCOMOTION,)),
    *_pair("hindleg", "hind leg", R.LEGS, (F.LOCOMOTION,)),
    Part("tail", "Tail", R.TAIL, (F.TAIL,), severable=True),
)

AVIAN_PARTS: tuple[Part, ...] = (
    Part("head", "Head", R.HEAD, (F.COGNITION,), vital=True),
    *_pair("eye", "eye", R.HEAD, (F.SIGHT,)),
    Part("jaw", "Beak", R.HEAD, (F.SPEECH, F.GRASP, F.PRESENCE)),
    Part("neck", "Neck", R.TORSO, (F.BREATH,), vital=True),
    Part("torso", "Breast", R.TORSO, (F.VITAL,)),
    *_organs(),
    *_pair("wing", "wing", R.WINGS, (F.FLIGHT,)),
    *_pair("leg", "talon", R.LEGS, (F.LOCOMOTION, F.FINE_MANIPULATION)),
    Part("tail", "Tail feathers", R.TAIL, (F.TAIL,), severable=True),
)

SERPENTINE_PARTS: tuple[Part, ...] = (
    Part("head", "Head", R.HEAD, (F.COGNITION, F.PRESENCE), vital=True),
    *_pair("eye", "eye", R.HEAD, (F.SIGHT,)),
    Part("jaw", "Jaws", R.HEAD, (F.SPEECH, F.GRASP)),
    Part("tongue", "Forked tongue", R.HEAD, (F.HEARING,), severable=True, internal=True),
    Part("torso", "Coils", R.TORSO, (F.LOCOMOTION, F.VITAL)),
    *_organs(),
    Part("tail", "Tail", R.TAIL, (F.LOCOMOTION, F.TAIL), severable=True),
)

INSECTOID_PARTS: tuple[Part, ...] = (
    Part("head", "Head", R.HEAD, (F.COGNITION,), vital=True),
    *_pair("eye", "compound eye", R.HEAD, (F.SIGHT,)),
    *_pair("antenna", "antenna", R.HEAD, (F.HEARING,)),
    Part("jaw", "Mandibles", R.HEAD, (F.SPEECH, F.GRASP)),
    Part("torso", "Thorax", R.TORSO, (F.VITAL, F.PRESENCE)),
    *_organs(breath=False),
    *_pair("foreleg", "foreleg", R.ARMS, (F.GRASP, F.FINE_MANIPULATION)),
    *_pair("midleg", "middle leg", R.LEGS, (F.LOCOMOTION,)),
    *_pair("hindleg", "hind leg", R.LEGS, (F.LOCOMOTION,)),
)

AQUATIC_PARTS: tuple[Part, ...] = (
    Part("head", "Head", R.HEAD, (F.COGNITION, F.PRESENCE), vital=True),
    *_pair("eye", "eye", R.HEAD, (F.SIGHT,)),
    Part("jaw", "Jaws", R.HEAD, (F.SPEECH, F.GRASP)),
    Part("gills", "Gills", R.TORSO, (F.BREATH,), vital=True),
    Part("torso", "Body", R.TORSO, (F.VITAL,)),
    *_organs(breath=False),
    *_pair("fin", "fin", R.ARMS, (F.LOCOMOTION, F.FINE_MANIPULATION)),
    Part("tail", "Tail fin", R.TAIL, (F.LOCOMOTION, F.TAIL), severable=True),
)

AMORPHOUS_PARTS: tuple[Part, ...] = (
    Part("core", "Core", R.TORSO, (F.VITAL, F.COGNITION), internal=True, vital=True),
    Part("torso", "Mass", R.TORSO, (F.LOCOMOTION, F.BREATH, F.REPRODUCTION, F.PRESENCE)),
    Part("pseudopods", "Pseudopods", R.ARMS, (F.GRASP, F.FINE_MANIPULATION), severable=True),
    Part("eye", "Sensing skin", R.HEAD, (F.SIGHT, F.HEARING, F.SPEECH)),
)

ARBOREAL_PARTS: tuple[Part, ...] = (
    Part("head", "Crown", R.HEAD, (F.SIGHT, F.PRESENCE)),
    Part("face", "Bark face", R.HEAD, (F.SPEECH, F.HEARING)),
    Part("torso", "Trunk", R.TORSO, (F.VITAL, F.BREATH)),
    Part("core", "Heartwood", R.TORSO, (F.VITAL, F.COGNITION), internal=True, vital=True),
    Part("groin", "Seed pods", R.TORSO, (F.REPRODUCTION,), severable=True),
    *_pair("branch", "branch", R.ARMS, (F.GRASP, F.FINE_MANIPULATION)),
    Part("roots", "Roots", R.LEGS, (F.LOCOMOTION,)),
)

INCORPOREAL_PARTS: tuple[Part, ...] = (
    Part("core", "Essence", R.TORSO, (F.VITAL, F.COGNITION, F.REPRODUCTION), vital=True),
    Part("face", "Visage", R.HEAD, (F.PRESENCE, F.SPEECH, F.SIGHT, F.HEARING)),
    Part("torso", "Shroud", R.TORSO, (F.LOCOMOTION, F.GRASP, F.FINE_MANIPULATION, F.BREATH)),
)

CONSTRUCT_PARTS: tuple[Part, ...] = (
    Part("head", "Rune head", R.HEAD, (F.COGNITION,), vital=True),
    *_pair("eye", "lens", R.HEAD, (F.SIGHT,)),
    Part("jaw", "Voice grille", R.HEAD, (F.SPEECH, F.HEARING, F.PRESENCE)),
    Part("torso", "Frame", R.TORSO, (F.BREATH,)),
    Part("core", "Animating core", R.TORSO, (F.VITAL,), internal=True, vital=True),
    *_pair("arm", "arm", R.ARMS, (F.GRASP,)),
    *_pair("hand", "hand", R.ARMS, (F.GRASP,)),
    Part(FINGERS, "Fingers", R.ARMS, (F.FINE_MANIPULATION,), severable=True, counted=FINGER_COUNT),
    *_pair("leg", "leg", R.LEGS, (F.LOCOMOTION,)),
)

DIVINE_PARTS: tuple[Part, ...] = (*HUMANOID_PARTS, Part("aura", "Aura", R.HEAD, (F.PRESENCE,)))

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
}

SIGHT_PARTS = frozenset(part.key for anatomy in ANATOMIES.values() for part in anatomy.parts if F.SIGHT in part.functions)

TRAIT_PARTS: dict[BodyFunction, Part] = {
    F.FLIGHT: Part("wings", "Wings", R.WINGS, (F.FLIGHT,), severable=True),
    F.VENOM: Part("venom_gland", "Venom gland", R.HEAD, (F.VENOM,), internal=True),
    F.HORN: Part("horn", "Horn", R.HEAD, (F.HORN, F.PRESENCE), severable=True),
    F.TAIL: Part("tail", "Tail", R.TAIL, (F.TAIL,), severable=True),
}


@cache
def anatomy_of(plan: BodyPlan, traits: frozenset[BodyFunction] = frozenset()) -> Anatomy:
    base = ANATOMIES[plan]
    extra = tuple(TRAIT_PARTS[trait] for trait in sorted(traits) if trait in TRAIT_PARTS and trait not in base.functions)
    if not extra:
        return base
    return Anatomy(base.plan, base.label, (*base.parts, *extra), base.breathes, base.bleeds, base.heals, base.infects, base.material)


def part_label(plan: BodyPlan, key: str, traits: Iterable[BodyFunction] = ()) -> str:
    part = anatomy_of(plan, frozenset(traits)).part(key)
    return part.label if part is not None else key.replace("_", " ").capitalize()
