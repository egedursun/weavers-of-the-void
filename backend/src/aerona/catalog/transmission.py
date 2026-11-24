from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import DiseaseTarget
from aerona.domain.enums.disease_agents import DiseaseAgent
from aerona.domain.enums.evolution import PlagueResponse
from aerona.rules.registry import Rules

T = Transmission


@dataclass(frozen=True)
class RouteSpec:
    label: str
    functions: tuple[DiseaseTarget, ...]
    stigma: int
    agent: DiseaseAgent
    disease: bool
    rate: Callable[[Rules], int]
    block: Callable[[Rules], int]
    blocked_by: frozenset[PlagueResponse]


ROUTES: Mapping[Transmission, RouteSpec] = total(
    Transmission,
    {
        T.INHALATION: RouteSpec(
            "airborne",
            (
                DiseaseTarget.BREATH,
                DiseaseTarget.VITAL,
            ),
            20,
            DiseaseAgent.VIRUS,
            disease=True,
            blocked_by=frozenset({PlagueResponse.QUARANTINE, PlagueResponse.CLOSE_GATHERINGS, PlagueResponse.INOCULATE}),
            rate=lambda rules: rules.transmission.inhalation_rate,
            block=lambda rules: rules.transmission.inhalation_block_pct,
        ),
        T.WATER: RouteSpec(
            "waterborne",
            (DiseaseTarget.VITAL,),
            15,
            DiseaseAgent.BACTERIUM,
            disease=True,
            blocked_by=frozenset({PlagueResponse.SANITATION}),
            rate=lambda rules: rules.transmission.water_rate,
            block=lambda rules: rules.transmission.water_block_pct,
        ),
        T.CONTACT: RouteSpec(
            "contact",
            (
                DiseaseTarget.SKIN,
                DiseaseTarget.SIGHT,
            ),
            70,
            DiseaseAgent.BACTERIUM,
            disease=True,
            blocked_by=frozenset({PlagueResponse.QUARANTINE, PlagueResponse.BURN_DEAD, PlagueResponse.EXPEL_SICK}),
            rate=lambda rules: rules.transmission.contact_rate,
            block=lambda rules: rules.transmission.contact_block_pct,
        ),
        T.BITE: RouteSpec(
            "bite-borne",
            (
                DiseaseTarget.VITAL,
                DiseaseTarget.COGNITION,
            ),
            10,
            DiseaseAgent.PARASITE,
            disease=True,
            blocked_by=frozenset(),
            rate=lambda rules: rules.transmission.bite_rate,
            block=lambda rules: rules.transmission.bite_block_pct,
        ),
        T.SPIRIT: RouteSpec(
            "spirit-borne",
            (DiseaseTarget.COGNITION,),
            50,
            DiseaseAgent.SPIRIT,
            disease=True,
            blocked_by=frozenset({PlagueResponse.PRAYER}),
            rate=lambda rules: rules.transmission.spirit_rate,
            block=lambda rules: rules.transmission.spirit_block_pct,
        ),
        T.VOID: RouteSpec(
            "void-borne",
            (
                DiseaseTarget.COGNITION,
                DiseaseTarget.VITAL,
            ),
            80,
            DiseaseAgent.UNKNOWN,
            disease=True,
            blocked_by=frozenset(),
            rate=lambda rules: rules.transmission.void_rate,
            block=lambda rules: rules.transmission.void_block_pct,
        ),
        T.CURSE: RouteSpec(
            "cursed",
            (
                DiseaseTarget.VITAL,
                DiseaseTarget.SKIN,
            ),
            90,
            DiseaseAgent.CURSE,
            disease=True,
            blocked_by=frozenset({PlagueResponse.PRAYER}),
            rate=lambda rules: rules.transmission.curse_rate,
            block=lambda rules: rules.transmission.curse_block_pct,
        ),
        T.INGESTION: RouteSpec(
            "foodborne",
            (DiseaseTarget.VITAL,),
            20,
            DiseaseAgent.BACTERIUM,
            disease=True,
            blocked_by=frozenset({PlagueResponse.SANITATION}),
            rate=lambda rules: rules.transmission.ingestion_rate,
            block=lambda rules: rules.transmission.ingestion_block_pct,
        ),
        T.BLOOD: RouteSpec(
            "blood-borne",
            (DiseaseTarget.VITAL,),
            60,
            DiseaseAgent.VIRUS,
            disease=True,
            blocked_by=frozenset({PlagueResponse.EXPEL_SICK}),
            rate=lambda rules: rules.transmission.blood_rate,
            block=lambda rules: rules.transmission.blood_block_pct,
        ),
        T.BIRTH: RouteSpec(
            "inborn",
            (
                DiseaseTarget.VITAL,
                DiseaseTarget.COGNITION,
            ),
            40,
            DiseaseAgent.VIRUS,
            disease=True,
            blocked_by=frozenset(),
            rate=lambda rules: rules.transmission.birth_rate,
            block=lambda rules: rules.transmission.birth_block_pct,
        ),
        T.RITE: RouteSpec(
            "rite-borne",
            (DiseaseTarget.COGNITION,),
            50,
            DiseaseAgent.CURSE,
            disease=False,
            blocked_by=frozenset(),
            rate=lambda rules: rules.transmission.rite_rate,
            block=lambda rules: rules.transmission.rite_block_pct,
        ),
        T.GAZE: RouteSpec(
            "passed by a gaze",
            (
                DiseaseTarget.COGNITION,
                DiseaseTarget.SIGHT,
            ),
            70,
            DiseaseAgent.CURSE,
            disease=False,
            blocked_by=frozenset(),
            rate=lambda rules: rules.transmission.gaze_rate,
            block=lambda rules: rules.transmission.gaze_block_pct,
        ),
        T.EXPERIENCE: RouteSpec(
            "borne of what was lived through",
            (DiseaseTarget.COGNITION,),
            30,
            DiseaseAgent.UNKNOWN,
            disease=False,
            blocked_by=frozenset(),
            rate=lambda rules: rules.transmission.experience_rate,
            block=lambda rules: rules.transmission.experience_block_pct,
        ),
        T.INTIMATE: RouteSpec(
            "passed by intimacy",
            (
                DiseaseTarget.SKIN,
                DiseaseTarget.VITAL,
            ),
            80,
            DiseaseAgent.BACTERIUM,
            disease=True,
            blocked_by=frozenset({PlagueResponse.QUARANTINE, PlagueResponse.EXPEL_SICK}),
            rate=lambda rules: rules.transmission.intimate_rate,
            block=lambda rules: rules.transmission.intimate_block_pct,
        ),
        T.OBJECTS: RouteSpec(
            "carried on goods",
            (
                DiseaseTarget.SKIN,
                DiseaseTarget.BREATH,
            ),
            30,
            DiseaseAgent.BACTERIUM,
            disease=True,
            blocked_by=frozenset({PlagueResponse.BURN_DEAD, PlagueResponse.QUARANTINE, PlagueResponse.SANITATION}),
            rate=lambda rules: rules.transmission.objects_rate,
            block=lambda rules: rules.transmission.objects_block_pct,
        ),
        T.SOIL: RouteSpec(
            "lying in the ground",
            (DiseaseTarget.SKIN, DiseaseTarget.VITAL),
            20,
            DiseaseAgent.FUNGUS,
            disease=True,
            blocked_by=frozenset({PlagueResponse.SANITATION}),
            rate=lambda rules: rules.transmission.soil_rate,
            block=lambda rules: rules.transmission.soil_block_pct,
        ),
        T.SOUND: RouteSpec(
            "carried by a sound",
            (DiseaseTarget.COGNITION,),
            40,
            DiseaseAgent.CURSE,
            disease=False,
            blocked_by=frozenset({PlagueResponse.QUARANTINE, PlagueResponse.PRAYER}),
            rate=lambda rules: rules.transmission.sound_rate,
            block=lambda rules: rules.transmission.sound_block_pct,
        ),
    },
)
DISEASE_ROUTES = tuple(route for route, spec in ROUTES.items() if spec.disease)


def main_share(further: Iterable[int]) -> int:
    return max(0, PERCENT - sum(further))
