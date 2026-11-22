from collections.abc import Mapping
from types import MappingProxyType

from aerona.core.total import partial
from aerona.domain.enums.demography import AgeBand, CohortCondition, InheritanceCustom, Job
from aerona.domain.enums.polity import SuccessionRule
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import ShortfallEffect

INHERITANCE_RULES: dict[InheritanceCustom, SuccessionRule] = {
    InheritanceCustom.PRIMOGENITURE: SuccessionRule.PRIMOGENITURE,
    InheritanceCustom.EQUAL_SHARES: SuccessionRule.SENIORITY,
    InheritanceCustom.ELECTIVE: SuccessionRule.ELECTIVE,
    InheritanceCustom.BY_MERIT: SuccessionRule.TANISTRY,
    InheritanceCustom.ULTIMOGENITURE: SuccessionRule.ULTIMOGENITURE,
    InheritanceCustom.THROUGH_SECOND_LINE: SuccessionRule.THROUGH_SECOND_LINE,
}


AGE_WORK: Mapping[AgeBand, float] = MappingProxyType({AgeBand.CHILD: 0.2, AgeBand.ADULT: 1.0, AgeBand.ELDER: 0.5})


CONDITION_WORK: Mapping[CohortCondition, float] = MappingProxyType(
    {CohortCondition.NONE: 1.0, CohortCondition.VETERAN: 0.9, CohortCondition.ENSLAVED: 1.0, CohortCondition.CAPTIVE: 0.8}
)


CLASS_JOBS = partial(
    SocialClass,
    {
        SocialClass.FARMER: {Job.FARMING: 1.0},
        SocialClass.SERF_OR_SLAVE: {Job.FARMING: 0.6, Job.MINING: 0.3, Job.BUILDING: 0.1},
        SocialClass.ARTISAN: {Job.CRAFTING: 0.7, Job.BUILDING: 0.2, Job.MINING: 0.1},
        SocialClass.MERCHANT: {Job.TRADE: 1.0},
        SocialClass.PRIEST: {Job.CLERGY: 1.0},
        SocialClass.MONASTIC: {Job.CLERGY: 0.5, Job.SCHOLARSHIP: 0.3, Job.FARMING: 0.2},
        SocialClass.SCRIBE: {Job.SCHOLARSHIP: 1.0},
        SocialClass.NOBLE: {Job.IDLE: 0.8, Job.SOLDIERING: 0.2},
        SocialClass.WORKER: {Job.CRAFTING: 0.6, Job.MINING: 0.2, Job.BUILDING: 0.2},
        SocialClass.PROFESSIONAL: {Job.SCHOLARSHIP: 0.4, Job.SERVICE: 0.4, Job.CRAFTING: 0.2},
        SocialClass.OFFICIAL: {Job.SERVICE: 1.0},
        SocialClass.CITIZEN: {Job.SERVICE: 0.3, Job.TRADE: 0.3, Job.CRAFTING: 0.2, Job.FARMING: 0.2},
        SocialClass.UNEMPLOYED: {Job.IDLE: 0.8, Job.BUILDING: 0.2},
    },
    without={SocialClass.OUTCAST, SocialClass.WARRIOR},
)


DEATH_RATES = (AgeBand.CHILD, AgeBand.ADULT, AgeBand.ELDER)

APPLY_SHORTFALLS_SHORTFALL_EFFECTS = (ShortfallEffect.HUNGER, ShortfallEffect.STATUS, ShortfallEffect.ARCANE)
MOVE_PEOPLE_COHORT_CONDITIONS = frozenset({CohortCondition.ENSLAVED, CohortCondition.CAPTIVE})
CORVEE_JOBS = (Job.FARMING, Job.HERDING)
ALLOCATE_COHORT_CONDITIONS = frozenset({CohortCondition.ENSLAVED, CohortCondition.CAPTIVE})
