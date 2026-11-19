from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.body import BodyPlan, BodyRegion, TissueKind

T = TissueKind


@dataclass(frozen=True)
class TissueSpec:
    kind: TissueKind
    label: str
    shear_yield: int
    impact_yield: int


TISSUES: MappingProxyType[TissueKind, TissueSpec] = MappingProxyType(
    {
        T.SKIN: TissueSpec(T.SKIN, "Skin", 4, 10),
        T.SCALE: TissueSpec(T.SCALE, "Scales", 22, 28),
        T.CHITIN: TissueSpec(T.CHITIN, "Chitin", 40, 45),
        T.BARK: TissueSpec(T.BARK, "Bark", 15, 35),
        T.FAT: TissueSpec(T.FAT, "Fat", 2, 15),
        T.MUSCLE: TissueSpec(T.MUSCLE, "Muscle", 8, 25),
        T.TENDON: TissueSpec(T.TENDON, "Tendons and ligaments", 14, 20),
        T.BONE: TissueSpec(T.BONE, "Bone", 25, 30),
        T.ARTERY: TissueSpec(T.ARTERY, "Artery", 2, 6),
        T.MOTOR_NERVE: TissueSpec(T.MOTOR_NERVE, "Motor nerve", 1, 4),
        T.SENSORY_NERVE: TissueSpec(T.SENSORY_NERVE, "Sensory nerve", 1, 4),
        T.ORGAN: TissueSpec(T.ORGAN, "Organ", 1, 5),
    }
)

COVERINGS: MappingProxyType[BodyPlan, TissueKind] = MappingProxyType(
    {
        BodyPlan.SERPENTINE: T.SCALE,
        BodyPlan.AQUATIC: T.SCALE,
        BodyPlan.COLOSSAL: T.SCALE,
        BodyPlan.INSECTOID: T.CHITIN,
        BodyPlan.ARBOREAL: T.BARK,
    }
)

LIMB_STACK = (T.FAT, T.MUSCLE, T.MOTOR_NERVE, T.ARTERY, T.TENDON, T.BONE)
DIGIT_STACK = (T.SENSORY_NERVE, T.TENDON, T.BONE)
HEAD_STACK = (T.MUSCLE, T.BONE, T.ORGAN)
FACE_STACK = (T.SENSORY_NERVE, T.MUSCLE, T.BONE)
SOFT_STACK = (T.SENSORY_NERVE, T.ORGAN)
NECK_STACK = (T.MUSCLE, T.ARTERY, T.MOTOR_NERVE, T.BONE)
TORSO_STACK = (T.FAT, T.MUSCLE, T.BONE, T.ARTERY, T.ORGAN)
ORGAN_STACK = (T.ORGAN, T.ARTERY)
REGION_STACKS: MappingProxyType[BodyRegion, tuple[TissueKind, ...]] = MappingProxyType(
    {
        BodyRegion.HEAD: HEAD_STACK,
        BodyRegion.TORSO: TORSO_STACK,
        BodyRegion.ARMS: LIMB_STACK,
        BodyRegion.LEGS: LIMB_STACK,
        BodyRegion.WINGS: LIMB_STACK,
        BodyRegion.TAIL: LIMB_STACK,
    }
)
PART_STACKS: MappingProxyType[str, tuple[TissueKind, ...]] = MappingProxyType(
    {
        "fingers": DIGIT_STACK,
        "toes": DIGIT_STACK,
        "teeth": (T.SENSORY_NERVE, T.BONE),
        "face": FACE_STACK,
        "nose": FACE_STACK,
        "jaw": FACE_STACK,
        "left_eye": SOFT_STACK,
        "right_eye": SOFT_STACK,
        "left_ear": SOFT_STACK,
        "right_ear": SOFT_STACK,
        "tongue": SOFT_STACK,
        "neck": NECK_STACK,
        "heart": ORGAN_STACK,
        "lungs": ORGAN_STACK,
        "gut": ORGAN_STACK,
        "groin": (T.ARTERY, T.ORGAN),
    }
)
MAJOR_VESSELS = frozenset({"neck", "torso", "heart", "lungs", "groin", "left_leg", "right_leg", "left_arm", "right_arm", "left_hindleg", "right_hindleg"})
COUNTED_PARTS: MappingProxyType[str, str] = MappingProxyType({"fingers": "fingers", "toes": "toes", "teeth": "teeth"})


def covering_of(plan: BodyPlan) -> TissueKind:
    return COVERINGS.get(plan, T.SKIN)


def stack_of(plan: BodyPlan, part_key: str, region: BodyRegion) -> tuple[TissueKind, ...]:
    return (covering_of(plan), *PART_STACKS.get(part_key, REGION_STACKS.get(region, LIMB_STACK)))


SIDES = ("left", "right")
HAND_DIGITS: MappingProxyType[str, int] = MappingProxyType({"thumb": 35, "index": 25, "middle": 18, "ring": 12, "little": 10})
FOOT_DIGITS: MappingProxyType[str, int] = MappingProxyType({"big": 40, "second": 15, "third": 15, "fourth": 15, "little": 15})
DIGIT_LIMBS: MappingProxyType[str, tuple[str, MappingProxyType[str, int]]] = MappingProxyType({"fingers": ("hand", HAND_DIGITS), "toes": ("foot", FOOT_DIGITS)})
DIGIT_NOUNS = MappingProxyType({"hand": ("finger", "fingers", "thumb"), "foot": ("toe", "toes", "big")})


def digit_keys(part: str, side: str | None = None) -> tuple[str, ...]:
    limb, names = DIGIT_LIMBS[part]
    return tuple(f"{each}_{limb}.{name}" for each in SIDES if side in (None, each) for name in names)


def digit_part(key: str) -> str | None:
    limb = key.split(".", 1)[0].split("_", 1)[-1]
    return next((part for part, (found, _) in DIGIT_LIMBS.items() if found == limb), None)


def digit_weight(key: str) -> int:
    part = digit_part(key)
    if part is None:
        return 0
    return DIGIT_LIMBS[part][1].get(key.split(".", 1)[-1], 0)


def intact_share(part: str, lost: list[str] | tuple[str, ...], side: str | None = None) -> float:
    keys = digit_keys(part, side)
    total = sum(digit_weight(key) for key in keys)
    missing = sum(digit_weight(key) for key in keys if key in lost)
    return (total - missing) / total if total else 1.0


def digit_label(key: str) -> str:
    place, name = key.split(".", 1)
    side, limb = place.split("_", 1)
    single, _, whole = DIGIT_NOUNS[limb]
    noun = name if name == whole and limb == "hand" else f"{name} {single}" if name != whole else f"big {single}"
    return f"{noun} of the {side} {limb}"


def digits_phrase(keys: list[str] | tuple[str, ...]) -> str:
    groups: dict[str, list[str]] = {}
    for key in keys:
        place, name = key.split(".", 1)
        groups.setdefault(place, []).append(name)
    phrases: list[str] = []
    for place, names in groups.items():
        side, limb = place.split("_", 1)
        single, plural, special = DIGIT_NOUNS[limb]
        lead = [special if limb == "hand" else f"big {single}"] if special in names else []
        rest = [name for name in names if name != special]
        tail = f"{_joined(rest)} {plural if len(rest) > 1 else single}" if rest else ""
        phrases.append(f"{_joined([*lead, tail] if tail else lead)} of the {side} {limb}")
    return _joined(phrases)


def _joined(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" and {items[-1]}"
