from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.transmission import ROUTES
from aerona.core.total import total
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent
from aerona.rules.registry import Rules

A = DiseaseAgent
K = CureClass


@dataclass(frozen=True)
class AgentSpec:
    label: str
    cures: frozenset[CureClass]
    water: int
    soil: int
    objects: int
    cold: int
    spreads: bool = True


AGENTS: MappingProxyType[DiseaseAgent, AgentSpec] = total(
    A,
    {
        A.VIRUS: AgentSpec("Virus", frozenset({K.ANTIVIRAL, K.REST_AND_CARE, K.DESIGNED, K.POWER}), 20, 5, 30, 60),
        A.BACTERIUM: AgentSpec("Bacterium", frozenset({K.ANTIMICROBIAL, K.SURGERY, K.HERBAL, K.REST_AND_CARE, K.POWER}), 60, 40, 40, 50),
        A.FUNGUS: AgentSpec("Fungus", frozenset({K.ANTIMICROBIAL, K.SURGERY, K.HERBAL, K.POWER}), 40, 70, 50, 30),
        A.PARASITE: AgentSpec("Parasite", frozenset({K.ANTIPARASITIC, K.SURGERY, K.HERBAL, K.POWER}), 70, 50, 10, 20),
        A.PRION: AgentSpec("Prion", frozenset({K.DESIGNED, K.POWER}), 30, 80, 80, 90),
        A.TOXIN: AgentSpec("Toxin", frozenset({K.ANTITOXIN, K.HERBAL, K.REST_AND_CARE}), 50, 30, 40, 70),
        A.DEFICIENCY: AgentSpec("Deficiency", frozenset({K.NUTRITIONAL, K.DIET}), 0, 0, 0, 0, spreads=False),
        A.SPIRIT: AgentSpec("Spirit", frozenset({K.EXORCISM, K.RITE, K.POWER}), 0, 0, 20, 100),
        A.CURSE: AgentSpec("Curse", frozenset({K.RITE, K.EXORCISM, K.POWER}), 0, 0, 60, 100),
        A.MADE: AgentSpec("Made agent", frozenset({K.DESIGNED, K.POWER}), 40, 30, 40, 50),
        A.UNKNOWN: AgentSpec("Unknown", frozenset({K.REST_AND_CARE}), 30, 30, 30, 50),
        A.HEREDITARY: AgentSpec("Hereditary", frozenset({K.DESIGNED, K.REST_AND_CARE}), 0, 0, 0, 0, spreads=False),
        A.AUTOIMMUNE: AgentSpec("Body against itself", frozenset({K.REST_AND_CARE, K.DIET, K.DESIGNED}), 0, 0, 0, 0, spreads=False),
    },
)

AGENT_OF_VECTOR: MappingProxyType[Transmission, DiseaseAgent] = MappingProxyType({route: spec.agent for route, spec in ROUTES.items()})


@dataclass(frozen=True)
class CureSpec:
    label: str
    level: Callable[[Rules], int] | None
    overused: bool
    resistance: Callable[[Rules], int]
    worked: str = "disease.right_cure"


def by_medicine(rules: Rules) -> int:
    return rules.disease.identify_level


def advanced(rules: Rules) -> int:
    return rules.cures.antiviral_level


def ordinary_resistance(rules: Rules) -> int:
    return rules.disease.resistance_per_overuse


CURES: Mapping[CureClass, CureSpec] = total(
    CureClass,
    {
        K.ANTIVIRAL: CureSpec("Antiviral", advanced, overused=True, resistance=lambda rules: rules.cures.antiviral_resistance, worked="disease.cure_worked"),
        K.ANTIMICROBIAL: CureSpec("Antimicrobial", by_medicine, overused=True, resistance=ordinary_resistance),
        K.ANTIPARASITIC: CureSpec("Antiparasitic", by_medicine, overused=True, resistance=ordinary_resistance),
        K.ANTITOXIN: CureSpec("Antitoxin", by_medicine, overused=True, resistance=ordinary_resistance),
        K.SURGERY: CureSpec("Surgery", lambda rules: rules.cures.surgery_level, overused=False, resistance=ordinary_resistance, worked="disease.cure_worked"),
        K.NUTRITIONAL: CureSpec("Nutritional", by_medicine, overused=False, resistance=ordinary_resistance),
        K.HERBAL: CureSpec("Herbal", lambda rules: rules.cures.herb_level, overused=False, resistance=ordinary_resistance),
        K.REST_AND_CARE: CureSpec("Rest and care", lambda rules: 0, overused=False, resistance=ordinary_resistance),
        K.RITE: CureSpec("Rite", None, overused=False, resistance=ordinary_resistance),
        K.EXORCISM: CureSpec("Exorcism", None, overused=False, resistance=ordinary_resistance),
        K.POWER: CureSpec("Power", None, overused=False, resistance=ordinary_resistance),
        K.DESIGNED: CureSpec("Designed", None, overused=False, resistance=ordinary_resistance),
        K.IMMUNISATION: CureSpec(
            "Immunisation", lambda rules: rules.cures.immunisation_level, overused=False, resistance=ordinary_resistance, worked="disease.cure_worked"
        ),
        K.DIET: CureSpec("Diet", lambda rules: 0, overused=False, resistance=ordinary_resistance),
    },
)
CURE_LABELS = MappingProxyType({cure: spec.label for cure, spec in CURES.items()})
MEDICINE_ORDER = tuple(cure for cure, spec in CURES.items() if spec.level is not None)
OVERUSED = frozenset(cure for cure, spec in CURES.items() if spec.overused)
