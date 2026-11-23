from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.physics import ImpactBody, ImpactOutcome


@dataclass(frozen=True)
class BodySpec:
    label: str
    called: bool = False
    from_ring: bool = False
    made: bool = False


@dataclass(frozen=True)
class OutcomeSpec:
    label: str
    landed: bool = False
    crater: bool = False
    settled: bool = True


IMPACT_BODIES: Mapping[ImpactBody, BodySpec] = total(
    ImpactBody,
    {
        ImpactBody.ASTEROID: BodySpec("Asteroid"),
        ImpactBody.COMET: BodySpec("Comet"),
        ImpactBody.ROGUE_WORLD: BodySpec("Rogue world"),
        ImpactBody.CALLED: BodySpec("Called down by a god", called=True),
        ImpactBody.MOON_FRAGMENT: BodySpec("Fragment of a broken moon", from_ring=True),
        ImpactBody.WRECK: BodySpec("Fallen made thing", made=True),
    },
)

IMPACT_OUTCOMES: Mapping[ImpactOutcome, OutcomeSpec] = total(
    ImpactOutcome,
    {
        ImpactOutcome.PENDING: OutcomeSpec("Coming", settled=False),
        ImpactOutcome.STRUCK: OutcomeSpec("Struck", landed=True, crater=True),
        ImpactOutcome.DEFLECTED: OutcomeSpec("Turned aside"),
        ImpactOutcome.MISSED: OutcomeSpec("Passed by"),
        ImpactOutcome.AIRBURST: OutcomeSpec("Burst in the air", landed=True),
    },
)
