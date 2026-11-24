from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.ecology import Biochemistry, DomesticationStage, Sociality
from aerona.domain.enums.society import CreatureTrait

S = DomesticationStage


@dataclass(frozen=True)
class StageSpec:
    kept: bool
    housed: bool
    rule: str | None


@dataclass(frozen=True)
class SocialSpec:
    trait: CreatureTrait | None
    keeps_numbers: bool
    rule: str | None
    nests: bool = False


@dataclass(frozen=True)
class BiochemistrySpec:
    unbound: bool
    charged: bool
    athermic: bool = False


STAGES: Mapping[DomesticationStage, StageSpec] = total(
    DomesticationStage,
    {
        S.WILD: StageSpec(kept=False, housed=False, rule=None),
        S.COMMENSAL: StageSpec(kept=False, housed=False, rule="domestication_depth.commensal_chance_pct"),
        S.TAMED: StageSpec(kept=False, housed=False, rule="domestication.starting_head"),
        S.HERDED: StageSpec(kept=True, housed=False, rule="domestication.herd_years"),
        S.DOMESTICATED: StageSpec(kept=True, housed=True, rule="domestication.domesticate_chance"),
        S.BREED: StageSpec(kept=True, housed=True, rule="domestication.breed_chance"),
        S.FERAL: StageSpec(kept=False, housed=False, rule="domestication_depth.feral_chance_pct"),
        S.CAPTIVE: StageSpec(kept=True, housed=True, rule="domestication_depth.captive_escape_pct"),
    },
)

SOCIALITIES: Mapping[Sociality, SocialSpec] = total(
    Sociality,
    {
        Sociality.SOLITARY: SocialSpec(None, keeps_numbers=False, rule=None),
        Sociality.PACK: SocialSpec(CreatureTrait.PACK_HUNTER, keeps_numbers=False, rule="habitat.pack_pct"),
        Sociality.HERD: SocialSpec(None, keeps_numbers=True, rule="habitat.herd_pct"),
        Sociality.HIVE: SocialSpec(CreatureTrait.HIVE_MIND, keeps_numbers=True, rule="habitat.herd_pct", nests=True),
        Sociality.COLONY: SocialSpec(None, keeps_numbers=True, rule="species_forms.colony_harvest_pct", nests=True),
        Sociality.SWARM: SocialSpec(None, keeps_numbers=True, rule="species_forms.swarm_move"),
        Sociality.PAIR: SocialSpec(None, keeps_numbers=False, rule="species_forms.pair_widow_pct"),
        Sociality.FAMILY_GROUP: SocialSpec(None, keeps_numbers=True, rule="species_forms.family_teach_pct"),
    },
)

BIOCHEMISTRIES: Mapping[Biochemistry, BiochemistrySpec] = total(
    Biochemistry,
    {
        Biochemistry.CARBON_WATER: BiochemistrySpec(unbound=False, charged=False),
        Biochemistry.CARBON_AMMONIA: BiochemistrySpec(unbound=False, charged=False),
        Biochemistry.SILICON: BiochemistrySpec(unbound=False, charged=True),
        Biochemistry.CRYSTAL: BiochemistrySpec(unbound=False, charged=True, athermic=True),
        Biochemistry.VOID: BiochemistrySpec(unbound=True, charged=False, athermic=True),
        Biochemistry.SPIRIT: BiochemistrySpec(unbound=True, charged=False, athermic=True),
        Biochemistry.CARBON_METHANE: BiochemistrySpec(unbound=False, charged=False),
        Biochemistry.PLASMA: BiochemistrySpec(unbound=True, charged=True, athermic=True),
        Biochemistry.METAL: BiochemistrySpec(unbound=False, charged=True),
    },
)

KEPT_STAGES = frozenset(stage for stage, spec in STAGES.items() if spec.kept)
HOUSED_STAGES = frozenset(stage for stage, spec in STAGES.items() if spec.housed)
WILDISH_STAGES = frozenset(stage for stage, spec in STAGES.items() if not spec.housed)
UNBOUND_BIOCHEMISTRY = frozenset(kind for kind, spec in BIOCHEMISTRIES.items() if spec.unbound)
CHARGED_BIOCHEMISTRY = frozenset(kind for kind, spec in BIOCHEMISTRIES.items() if spec.charged)
ATHERMIC_BIOCHEMISTRY = frozenset(kind for kind, spec in BIOCHEMISTRIES.items() if spec.athermic)
SOLVENT_BIOCHEMISTRY = frozenset(kind for kind, spec in BIOCHEMISTRIES.items() if not spec.unbound and not spec.charged)
