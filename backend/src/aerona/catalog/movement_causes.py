from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.faction import FactionGoalKind, MovementCause
from aerona.domain.enums.polity import LawKind
from aerona.rules.registry import Rules

M = MovementCause
G = FactionGoalKind


@dataclass(frozen=True)
class CauseSpec:
    label: str
    goal: FactionGoalKind
    law: LawKind | None
    weight: Callable[[Rules], int]
    founds_union: bool = False
    reforms_faith: bool = False
    curbs_intoxicants: bool = False


MOVEMENT_CAUSES: Mapping[MovementCause, CauseSpec] = total(
    MovementCause,
    {
        M.ABOLITION: CauseSpec("Abolition of slavery", G.ABOLISH_LAW, LawKind.SLAVERY, lambda rules: rules.movements.abolition_weight),
        M.INDEPENDENCE: CauseSpec("Independence", G.INDEPENDENCE, None, lambda rules: rules.movements.independence_weight),
        M.REVIVAL: CauseSpec("A revival of faith", G.CONVERT_REALM, None, lambda rules: rules.movements.revival_weight),
        M.LAND_REFORM: CauseSpec("Land reform", G.ABOLISH_LAW, LawKind.SERFDOM, lambda rules: rules.movements.land_reform_weight),
        M.FRANCHISE: CauseSpec("A wider franchise", G.ENACT_LAW, LawKind.FRANCHISE, lambda rules: rules.movements.franchise_weight),
        M.PEACE: CauseSpec("Peace", G.PEACE_WITH, None, lambda rules: rules.movements.peace_weight),
        M.CONSERVATION: CauseSpec("Protection of the wild", G.ENACT_LAW, LawKind.ENVIRONMENT_LAW, lambda rules: rules.movements.conservation_weight),
        M.LABOUR: CauseSpec("The rights of labour", G.ENACT_LAW, LawKind.LABOUR_LAW, lambda rules: rules.movements.labour_weight, founds_union=True),
        M.FAITH_REFORM: CauseSpec("Reform of the faith", G.CONVERT_REALM, None, lambda rules: rules.movements.faith_reform_weight, reforms_faith=True),
        M.TEMPERANCE: CauseSpec("Temperance", G.ENACT_LAW, LawKind.SUMPTUARY, lambda rules: rules.movements.temperance_weight, curbs_intoxicants=True),
        M.MIND_RIGHTS: CauseSpec("Rights for made minds", G.ENACT_LAW, LawKind.MIND_STATUS, lambda rules: rules.movements.mind_rights_weight),
        M.EQUAL_STANDING: CauseSpec(
            "Equal standing of classes and kinds", G.ENACT_LAW, LawKind.FOREIGNER_RIGHTS, lambda rules: rules.movements.equal_standing_weight
        ),
        M.LEARNING: CauseSpec("Learning for all", G.ABOLISH_LAW, LawKind.CENSORSHIP, lambda rules: rules.movements.learning_weight),
        M.HEALTH: CauseSpec("Public health", G.ENACT_LAW, LawKind.SANITATION, lambda rules: rules.movements.health_weight),
    },
)
CAUSE_LABELS: Mapping[MovementCause, str] = MappingProxyType({cause: spec.label for cause, spec in MOVEMENT_CAUSES.items()})
GOALS: Mapping[MovementCause, FactionGoalKind] = MappingProxyType({cause: spec.goal for cause, spec in MOVEMENT_CAUSES.items()})
LAW_TARGETS: Mapping[MovementCause, LawKind] = MappingProxyType(
    {cause: spec.law for cause, spec in MOVEMENT_CAUSES.items() if spec.law is not None and spec.goal is G.ABOLISH_LAW}
)
ENACTED: Mapping[MovementCause, LawKind] = MappingProxyType(
    {cause: spec.law for cause, spec in MOVEMENT_CAUSES.items() if spec.law is not None and spec.goal is G.ENACT_LAW}
)
