import math
from collections.abc import Callable, Sequence

from aerona.cartography.model import Coordinates
from aerona.rules.registry import Rules

UnitRandom = Callable[[], float]


def frontier_position(source: Coordinates, occupied: Sequence[Coordinates], random: UnitRandom, rules: Rules) -> tuple[int, int]:
    settings = rules.exploration
    attempts = max(1, settings.map_attempts)
    start = random() * math.tau
    best: tuple[float, float] | None = None
    best_room = -math.inf
    for attempt in range(attempts):
        angle = start + math.tau * attempt / attempts
        candidate = (source[0] + math.cos(angle) * settings.map_distance, source[1] + math.sin(angle) * settings.map_distance)
        room = min((math.hypot(candidate[0] - x, candidate[1] - y) for x, y in occupied), default=math.inf)
        if room > best_room:
            best = candidate
            best_room = room
    chosen = best if best is not None else source
    return (round(chosen[0]), round(chosen[1]))
