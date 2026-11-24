from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import partial, total
from aerona.domain.enums.demography import AgeBand, CohortCondition, InheritanceCustom, Job
from aerona.domain.enums.polity import SuccessionRule
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import ShortfallEffect
from aerona.rules.registry import Rules

INHERITANCE_RULES: dict[InheritanceCustom, SuccessionRule] = {
    InheritanceCustom.PRIMOGENITURE: SuccessionRule.PRIMOGENITURE,
    InheritanceCustom.EQUAL_SHARES: SuccessionRule.SENIORITY,
    InheritanceCustom.ELECTIVE: SuccessionRule.ELECTIVE,
    InheritanceCustom.BY_MERIT: SuccessionRule.TANISTRY,
    InheritanceCustom.ULTIMOGENITURE: SuccessionRule.ULTIMOGENITURE,
    InheritanceCustom.THROUGH_SECOND_LINE: SuccessionRule.THROUGH_SECOND_LINE,
    InheritanceCustom.SENIORITY: SuccessionRule.SENIORITY,
    InheritanceCustom.DESIGNATED: SuccessionRule.TANISTRY,
    InheritanceCustom.COMMUNAL: SuccessionRule.ELECTIVE,
}


@dataclass(frozen=True)
class BandSpec:
    label: str
    work: float
    youth_share: float | None
    minor: bool = False
    fights: bool = False
    bears: bool = False


AGE_BANDS: Mapping[AgeBand, BandSpec] = total(
    AgeBand,
    {
        AgeBand.INFANT: BandSpec("Infants", 0.0, 1 / 6, minor=True),
        AgeBand.CHILD: BandSpec("Children", 0.2, 1 / 2, minor=True),
        AgeBand.YOUTH: BandSpec("Youths", 0.8, 1 / 3, fights=True, bears=True),
        AgeBand.ADULT: BandSpec("Adults", 1.0, None, fights=True, bears=True),
        AgeBand.ELDER: BandSpec("Elders", 0.5, None),
        AgeBand.ANCIENT: BandSpec("The very old", 0.2, None),
    },
)
AGE_ORDER = tuple(AgeBand)
AGE_WORK: Mapping[AgeBand, float] = MappingProxyType({band: spec.work for band, spec in AGE_BANDS.items()})
MINOR_BANDS = frozenset(band for band, spec in AGE_BANDS.items() if spec.minor)
FIGHTING_BANDS = frozenset(band for band, spec in AGE_BANDS.items() if spec.fights)
BEARING_BANDS = frozenset(band for band, spec in AGE_BANDS.items() if spec.bears)
CONDITION_EMERGES: Mapping[CohortCondition, bool] = total(
    CohortCondition,
    {
        CohortCondition.NONE: False,
        CohortCondition.VETERAN: False,
        CohortCondition.SICK: False,
        CohortCondition.ENSLAVED: False,
        CohortCondition.CAPTIVE: False,
        CohortCondition.MAIMED: False,
        CohortCondition.ORPHANED: True,
        CohortCondition.DISPLACED: True,
        CohortCondition.INDEBTED: True,
        CohortCondition.GIFTED: False,
    },
)
EMERGING_CONDITIONS = frozenset(condition for condition, emerges in CONDITION_EMERGES.items() if emerges)
GROWN_BANDS = frozenset(band for band, spec in AGE_BANDS.items() if spec.work >= 1 or spec.bears)


CONDITION_WORK: Mapping[CohortCondition, float] = partial(
    CohortCondition,
    {
        CohortCondition.NONE: 1.0,
        CohortCondition.VETERAN: 0.9,
        CohortCondition.ENSLAVED: 1.0,
        CohortCondition.CAPTIVE: 0.8,
        CohortCondition.ORPHANED: 0.6,
        CohortCondition.DISPLACED: 0.7,
        CohortCondition.INDEBTED: 1.1,
        CohortCondition.GIFTED: 1.2,
    },
    without=(CohortCondition.SICK, CohortCondition.MAIMED),
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


DEATH_RATES = AGE_ORDER

APPLY_SHORTFALLS_SHORTFALL_EFFECTS = (ShortfallEffect.HUNGER, ShortfallEffect.STATUS, ShortfallEffect.ARCANE, ShortfallEffect.JUSTICE)
MOVE_PEOPLE_COHORT_CONDITIONS = frozenset({CohortCondition.ENSLAVED, CohortCondition.CAPTIVE})
CORVEE_JOBS = (Job.FARMING, Job.HERDING)
ALLOCATE_COHORT_CONDITIONS = frozenset({CohortCondition.ENSLAVED, CohortCondition.CAPTIVE})


@dataclass(frozen=True)
class NewTrade:
    source: Job
    classes: frozenset[SocialClass]
    share: Callable[[Rules], int]


NEW_TRADES: Mapping[Job, NewTrade] = MappingProxyType(
    {
        Job.TRANSPORT: NewTrade(Job.TRADE, frozenset({SocialClass.MERCHANT, SocialClass.CITIZEN}), lambda rules: rules.labour.transport_base_share),
        Job.ADMINISTRATION: NewTrade(
            Job.SERVICE, frozenset({SocialClass.OFFICIAL, SocialClass.PROFESSIONAL}), lambda rules: rules.labour.administration_base_share
        ),
        Job.GATHERING: NewTrade(Job.FARMING, frozenset({SocialClass.FARMER, SocialClass.SERF_OR_SLAVE}), lambda rules: rules.labour.gathering_base_share),
        Job.INDUSTRY: NewTrade(Job.CRAFTING, frozenset({SocialClass.WORKER, SocialClass.PROFESSIONAL}), lambda rules: rules.labour.industry_base_share),
        Job.ARTS: NewTrade(Job.CRAFTING, frozenset({SocialClass.ARTISAN, SocialClass.CITIZEN}), lambda rules: rules.labour.arts_base_share),
    }
)
