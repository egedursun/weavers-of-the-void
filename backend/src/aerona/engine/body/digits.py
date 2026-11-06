from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import anatomy_of
from aerona.catalog.tissues import DIGIT_LIMBS, FULL_COUNTS, SIDES, digit_keys, digit_part, intact_share
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.body import BodyRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.domain.enums.body import BodyFunction, Handedness
from aerona.rules.registry import Rules

FUNCTIONS = frozenset(item.value for item in BodyFunction)


def sync(body: BodyRow) -> None:
    for part in DIGIT_LIMBS:
        setattr(body, part, FULL_COUNTS[part] - sum(1 for key in body.lost_digits if digit_part(key) == part))


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
    counts = {part: round(FULL_COUNTS[part] * intact_share(part, body.lost_digits)) for part in DIGIT_LIMBS}
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
        anatomy = anatomy_of(body.plan, frozenset(BodyFunction(trait) for trait in body.traits if trait in FUNCTIONS))
        owed = {
            part: FULL_COUNTS[part] - int(getattr(body, part) or 0) - sum(1 for key in body.lost_digits if digit_part(key) == part)
            for part in DIGIT_LIMBS
            if anatomy.part(part) is not None
        }
        for part, missing in owed.items():
            if missing > 0:
                lose(body, part, missing, SeededRandom(RandomKey(body.node_id, 0, f"digits.{part}")))
    session.add(AppliedFixupRow(key=DIGITS_FIXUP, result={"bodies": len(bodies)}))
    await session.flush()
    return len(bodies)
