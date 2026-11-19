from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import TEETH, TOOTH_COUNT, Anatomy, anatomy_of
from aerona.catalog.tissues import DIGIT_LIMBS, SIDES, digit_keys, digit_part, intact_share
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.body import BodyRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyFunction, BodyPlan, Handedness
from aerona.rules.registry import Rules

FUNCTIONS = frozenset(item.value for item in BodyFunction)


def plan_anatomy(body: BodyRow) -> Anatomy:
    return anatomy_of(body.plan, frozenset(BodyFunction(trait) for trait in body.traits if trait in FUNCTIONS))


def full_counts(body: BodyRow) -> dict[str, int]:
    return plan_anatomy(body).full_counts


def sync(body: BodyRow) -> None:
    full = full_counts(body)
    for part in DIGIT_LIMBS:
        setattr(body, part, max(0, full[part] - sum(1 for key in body.lost_digits if digit_part(key) == part)))


def fill_counts(body: BodyRow) -> BodyRow:
    sync(body)
    body.teeth = full_counts(body)[TEETH]
    return body


def replan(body: BodyRow, plan: BodyPlan, traits: list[str] | None = None) -> None:
    missing_teeth = max(0, full_counts(body)[TEETH] - body.teeth)
    body.plan = plan
    if traits is not None:
        body.traits = traits
    sync(body)
    body.teeth = max(0, full_counts(body)[TEETH] - missing_teeth)


def lose(body: BodyRow, part: str, count: int, rng: SeededRandom) -> list[str]:
    first = rng.pick(list(SIDES))
    order = [first, *(side for side in SIDES if side != first)]
    taken: list[str] = []
    for side in order:
        remaining = [key for key in digit_keys(part, side) if key not in body.lost_digits]
        for key in rng.shuffled(remaining)[: max(0, count - len(taken))]:
            taken.append(key)
    body.lost_digits = sorted({*body.lost_digits, *taken})
    sync(body)
    return taken


def lose_all(body: BodyRow, part: str) -> list[str]:
    taken = [key for key in digit_keys(part) if key not in body.lost_digits]
    body.lost_digits = sorted({*body.lost_digits, *taken})
    sync(body)
    return taken


def restore(body: BodyRow, part: str, keys: list[str] | None = None) -> list[str]:
    wanted = set(keys) if keys else set(digit_keys(part))
    given = [key for key in body.lost_digits if key in wanted]
    body.lost_digits = [key for key in body.lost_digits if key not in wanted]
    sync(body)
    return given


def effective_counts(body: BodyRow) -> dict[str, int]:
    full = full_counts(body)
    counts = {part: round(full[part] * intact_share(part, body.lost_digits)) for part in DIGIT_LIMBS}
    counts["teeth"] = body.teeth
    return counts


def hand_shares(lost: list[str] | tuple[str, ...]) -> dict[str, float]:
    return {side: intact_share("fingers", lost, side) for side in SIDES}


def handedness_for(rules: Rules, node_id: int) -> Handedness:
    roll = SeededRandom(RandomKey(node_id, 0, "handedness")).below(100)
    table = rules.anatomy
    if roll < table.two_handed_pct:
        return Handedness.BOTH
    return Handedness.LEFT if roll < table.two_handed_pct + table.left_handed_pct else Handedness.RIGHT


DIGITS_FIXUP = "body.named_digits"


async def backfill_digits(session: AsyncSession, rules: Rules) -> int:
    if await session.get(AppliedFixupRow, DIGITS_FIXUP) is not None:
        return 0
    bodies = list(await session.scalars(select(BodyRow)))
    for body in bodies:
        body.handedness = handedness_for(rules, body.node_id)
        anatomy = plan_anatomy(body)
        owed = {
            part: anatomy.full_count(part) - int(getattr(body, part) or 0) - sum(1 for key in body.lost_digits if digit_part(key) == part)
            for part in DIGIT_LIMBS
            if anatomy.part(part) is not None
        }
        for part, missing in owed.items():
            if missing > 0:
                lose(body, part, missing, SeededRandom(RandomKey(body.node_id, 0, f"digits.{part}")))
    session.add(AppliedFixupRow(key=DIGITS_FIXUP, result={"bodies": len(bodies)}))
    await session.flush()
    return len(bodies)


PLAN_COUNTS_FIXUP = "body.plan_counts"


async def backfill_plan_counts(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, PLAN_COUNTS_FIXUP) is not None:
        return 0
    refitted = 0
    for body in await session.scalars(select(BodyRow)):
        if held(body.node_id):
            continue
        before = (body.fingers, body.toes, body.teeth)
        sync(body)
        body.teeth = max(0, full_counts(body)[TEETH] - max(0, TOOTH_COUNT - body.teeth))
        refitted += before != (body.fingers, body.toes, body.teeth)
    session.add(AppliedFixupRow(key=PLAN_COUNTS_FIXUP, result={"bodies": refitted}))
    await session.flush()
    return refitted
