from aerona.engine.context import TickContext
from aerona.engine.primitives.naming import seed_of

SEVERITY_LOW = 1
SEVERITY_HIGH = 5


def banded(ctx: TickContext, centre: int, *key: object) -> int:
    drawn = centre + ctx.rng(seed_of("band", *key, ctx.epoch)).integer(-1, 1)
    return max(SEVERITY_LOW, min(SEVERITY_HIGH, drawn))
