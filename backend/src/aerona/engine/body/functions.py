from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from aerona.catalog.anatomy import FINGERS, Anatomy
from aerona.catalog.harm_kinds import injuries_where
from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.domain.enums.body import BodyFunction, Handedness, InjuryKind, NerveDamage
from aerona.rules.registry.body import CapacityRules

LEFT = "left_"
RIGHT = "right_"


@dataclass(frozen=True)
class Wound:
    part: str
    kind: InjuryKind
    severity: int
    loss: int
    nerve: NerveDamage = NerveDamage.NONE

    @classmethod
    def of(cls, row: InjuryRow, restored: int = 0) -> "Wound":
        return cls(row.part, row.kind, row.severity, round(row.function_loss * (PERCENT - restored) / PERCENT), row.nerve)


def redundancy(rules: CapacityRules, function: BodyFunction) -> int:
    table = {
        BodyFunction.SIGHT: rules.sight_redundancy_pct,
        BodyFunction.HEARING: rules.hearing_redundancy_pct,
        BodyFunction.GRASP: rules.grasp_redundancy_pct,
        BodyFunction.LOCOMOTION: rules.locomotion_redundancy_pct,
        BodyFunction.FLIGHT: rules.flight_redundancy_pct,
    }
    return table.get(function, rules.default_redundancy_pct)


MIND_WOUNDS = injuries_where(lambda spec: spec.of_the_mind)


def part_losses(anatomy: Anatomy, wounds: Iterable[Wound], venom_paralysis_at: int) -> tuple[dict[str, float], dict[BodyFunction, float]]:
    losses: dict[str, float] = defaultdict(float)
    direct: dict[BodyFunction, float] = defaultdict(float)
    for wound in wounds:
        share = wound.loss / PERCENT
        if wound.kind is InjuryKind.VENOM:
            direct[BodyFunction.VITAL] = max(direct[BodyFunction.VITAL], share)
            if wound.severity >= venom_paralysis_at:
                direct[BodyFunction.LOCOMOTION] = max(direct[BodyFunction.LOCOMOTION], share)
            continue
        if wound.kind in MIND_WOUNDS:
            direct[BodyFunction.COGNITION] = max(direct[BodyFunction.COGNITION], share)
            continue
        if wound.kind is InjuryKind.RADIATION_SICKNESS:
            direct[BodyFunction.VITAL] = max(direct[BodyFunction.VITAL], share)
            continue
        if anatomy.part(wound.part) is not None:
            losses[wound.part] = min(1.0, max(losses[wound.part], share))
    return losses, direct


def function_levels(
    rules: CapacityRules,
    anatomy: Anatomy,
    wounds: Iterable[Wound],
    counts: Mapping[str, int],
    venom_paralysis_at: int,
    *,
    afflicted: Iterable[tuple[str, int]] = (),
) -> dict[BodyFunction, float]:
    losses, direct = part_losses(anatomy, wounds, venom_paralysis_at)
    for key, loss in afflicted:
        if anatomy.part(key) is not None:
            losses[key] = min(1.0, max(losses.get(key, 0.0), loss / PERCENT))
    levels: dict[BodyFunction, float] = {}
    for function in BodyFunction:
        parts = anatomy.with_function(function)
        if not parts:
            levels[function] = 0.0
            continue
        values = []
        for part in parts:
            value = 1 - losses.get(part.key, 0.0)
            if part.counted:
                value *= max(0, min(part.counted, counts.get(part.key, part.counted))) / part.counted
            values.append(value)
        weight = redundancy(rules, function) / PERCENT
        level = max(values) * (1 - weight) + sum(values) / len(values) * weight
        levels[function] = max(0.0, level * (1 - direct.get(function, 0.0)))
    return levels


def weapon_grasp(
    rules: CapacityRules,
    anatomy: Anatomy,
    wounds: Iterable[Wound],
    counts: Mapping[str, int],
    *,
    hands: Mapping[str, float] | None = None,
    handedness: Handedness = Handedness.RIGHT,
) -> float:
    losses, _ = part_losses(anatomy, wounds, venom_paralysis_at=PERCENT)
    grasping = anatomy.with_function(BodyFunction.GRASP)
    sides: dict[str, float] = {}
    for prefix in (RIGHT, LEFT):
        parts = [part for part in grasping if part.key.startswith(prefix)]
        if parts:
            value = 1.0
            for part in parts:
                value *= 1 - losses.get(part.key, 0.0)
            share = (hands or {}).get(prefix.removesuffix("_"), 1.0)
            sides[prefix] = value * (rules.fingerless_grip_pct / PERCENT + (1 - rules.fingerless_grip_pct / PERCENT) * share)
    if not sides:
        return max((1 - losses.get(part.key, 0.0) for part in grasping), default=0.0)
    main, off = (LEFT, RIGHT) if handedness is Handedness.LEFT else (RIGHT, LEFT)
    off_pct = PERCENT if handedness is Handedness.BOTH else rules.off_hand_pct
    best = max(sides.get(main, 0.0), sides.get(off, 0.0) * off_pct / PERCENT)
    has_fingers = anatomy.part(FINGERS) is not None
    return best * (rules.fingerless_grip_pct / PERCENT if has_fingers and counts.get(FINGERS, 1) <= 0 else 1.0)
