from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.disease import DiseaseVector
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent

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


AGENTS: MappingProxyType[DiseaseAgent, AgentSpec] = total(
    A,
    {
        A.VIRUS: AgentSpec("Virus", frozenset({K.REST_AND_CARE, K.DESIGNED, K.POWER}), 20, 5, 30, 60),
        A.BACTERIUM: AgentSpec("Bacterium", frozenset({K.ANTIMICROBIAL, K.HERBAL, K.REST_AND_CARE, K.POWER}), 60, 40, 40, 50),
        A.FUNGUS: AgentSpec("Fungus", frozenset({K.ANTIMICROBIAL, K.HERBAL, K.POWER}), 40, 70, 50, 30),
        A.PARASITE: AgentSpec("Parasite", frozenset({K.ANTIPARASITIC, K.HERBAL, K.POWER}), 70, 50, 10, 20),
        A.PRION: AgentSpec("Prion", frozenset({K.DESIGNED, K.POWER}), 30, 80, 80, 90),
        A.TOXIN: AgentSpec("Toxin", frozenset({K.ANTITOXIN, K.HERBAL, K.REST_AND_CARE}), 50, 30, 40, 70),
        A.DEFICIENCY: AgentSpec("Deficiency", frozenset({K.NUTRITIONAL}), 0, 0, 0, 0),
        A.SPIRIT: AgentSpec("Spirit", frozenset({K.EXORCISM, K.RITE, K.POWER}), 0, 0, 20, 100),
        A.CURSE: AgentSpec("Curse", frozenset({K.RITE, K.EXORCISM, K.POWER}), 0, 0, 60, 100),
        A.MADE: AgentSpec("Made agent", frozenset({K.DESIGNED, K.POWER}), 40, 30, 40, 50),
        A.UNKNOWN: AgentSpec("Unknown", frozenset({K.REST_AND_CARE}), 30, 30, 30, 50),
    },
)

AGENT_OF_VECTOR: MappingProxyType[DiseaseVector, DiseaseAgent] = total(
    DiseaseVector,
    {
        DiseaseVector.AIR: A.VIRUS,
        DiseaseVector.WATER: A.BACTERIUM,
        DiseaseVector.TOUCH: A.BACTERIUM,
        DiseaseVector.BITE: A.PARASITE,
        DiseaseVector.SPIRIT: A.SPIRIT,
        DiseaseVector.VOID: A.UNKNOWN,
        DiseaseVector.CURSE: A.CURSE,
    },
)

CURE_LABELS: MappingProxyType[CureClass, str] = total(
    K,
    {
        K.REST_AND_CARE: "Rest and care",
        K.HERBAL: "Herbal",
        K.ANTIMICROBIAL: "Antimicrobial",
        K.ANTIPARASITIC: "Antiparasitic",
        K.ANTITOXIN: "Antitoxin",
        K.NUTRITIONAL: "Nutritional",
        K.RITE: "Rite",
        K.EXORCISM: "Exorcism",
        K.POWER: "Power",
        K.DESIGNED: "Designed",
    },
)
