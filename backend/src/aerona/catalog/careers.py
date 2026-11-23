from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.mind import NeedKind, SkillKind, TraitKind, ValueAxis
from aerona.domain.enums.mortal import CareerPath
from aerona.rules.registry import Rules

P = CareerPath
T = TraitKind


@dataclass(frozen=True)
class CareerSpec:
    label: str
    role: MortalRole | None
    traits: frozenset[TraitKind]
    value: ValueAxis | None
    need: NeedKind | None
    skills: tuple[SkillKind, ...]
    weight: Callable[[Rules], int]
    opening: bool = False
    crews: bool = False
    household: bool = False
    venues: bool = False
    frontier: bool = False


CAREERS: Mapping[CareerPath, CareerSpec] = total(
    CareerPath,
    {
        P.STAY: CareerSpec("Staying home", None, frozenset(), None, None, (), lambda rules: rules.careers.stay_weight, opening=True),
        P.ARMY: CareerSpec(
            "Soldiering",
            MortalRole.WARRIOR,
            frozenset({T.BRAVE, T.WRATHFUL, T.RECKLESS, T.CUNNING_TACTICIAN}),
            ValueAxis.MARTIAL,
            NeedKind.STATUS,
            (SkillKind.SPEAR, SkillKind.SHIELD, SkillKind.TACTICS),
            lambda rules: rules.careers.army_weight,
        ),
        P.OFFICE: CareerSpec(
            "Office",
            MortalRole.SCRIBE,
            frozenset({T.AMBITIOUS, T.JUST, T.PROUD}),
            ValueAxis.HIERARCHY,
            NeedKind.STATUS,
            (SkillKind.WRITING, SkillKind.ADMINISTRATION),
            lambda rules: rules.careers.office_weight,
        ),
        P.APPRENTICE: CareerSpec(
            "Apprenticeship",
            MortalRole.APPRENTICE,
            frozenset({T.PATIENT, T.HUMBLE, T.CURIOUS}),
            ValueAxis.TRADITION,
            NeedKind.PURPOSE,
            (),
            lambda rules: rules.careers.apprentice_weight,
        ),
        P.VOWS: CareerSpec(
            "Vows",
            MortalRole.PRIEST,
            frozenset({T.ZEALOUS, T.ASCETIC, T.CHASTE}),
            ValueAxis.PIETY,
            NeedKind.FAITH,
            (SkillKind.RITUAL, SkillKind.THEOLOGY),
            lambda rules: rules.careers.vows_weight,
            opening=True,
        ),
        P.TRADE: CareerSpec(
            "Trade",
            MortalRole.MERCHANT,
            frozenset({T.GREEDY, T.GREGARIOUS, T.DECEITFUL}),
            ValueAxis.WEALTH,
            NeedKind.SUSTENANCE,
            (SkillKind.NEGOTIATION, SkillKind.ACCOUNTING),
            lambda rules: rules.careers.trade_weight,
            opening=True,
        ),
        P.WANDER: CareerSpec(
            "Wandering",
            MortalRole.EXPLORER,
            frozenset({T.CURIOUS, T.RECKLESS, T.FICKLE}),
            ValueAxis.XENOPHILIA,
            NeedKind.PURPOSE,
            (SkillKind.TRACKING, SkillKind.FORAGING),
            lambda rules: rules.careers.wander_weight,
            opening=True,
        ),
        P.BANDIT: CareerSpec(
            "Banditry",
            MortalRole.BANDIT,
            frozenset({T.CRUEL, T.GREEDY, T.DECEITFUL}),
            None,
            NeedKind.SUSTENANCE,
            (SkillKind.BLADE, SkillKind.INTIMIDATION),
            lambda rules: rules.careers.bandit_weight,
        ),
        P.STUDY: CareerSpec(
            "Study",
            MortalRole.SCIENTIST,
            frozenset({T.CURIOUS, T.SCHOLARLY, T.PATIENT}),
            ValueAxis.KNOWLEDGE,
            NeedKind.PURPOSE,
            (SkillKind.LORE, SkillKind.WRITING),
            lambda rules: rules.careers.study_weight,
        ),
        P.SEA: CareerSpec(
            "The sea",
            MortalRole.CAPTAIN,
            frozenset({T.ADVENTUROUS, T.HARDY, T.RECKLESS}),
            ValueAxis.XENOPHILIA,
            NeedKind.ADVENTURE,
            (SkillKind.SAILING, SkillKind.NAVIGATION, SkillKind.SWIMMING),
            lambda rules: rules.careers.sea_weight,
            crews=True,
        ),
        P.SERVICE: CareerSpec(
            "Service in a great house",
            MortalRole.COMMONER,
            frozenset({T.LOYAL, T.DISCREET, T.DUTIFUL, T.OBEDIENT}),
            ValueAxis.LOYALTY,
            NeedKind.BELONGING,
            (SkillKind.ETIQUETTE, SkillKind.INTRIGUE),
            lambda rules: rules.careers.service_weight,
            household=True,
        ),
        P.ARTS: CareerSpec(
            "The arts",
            MortalRole.ARTISAN,
            frozenset({T.IMAGINATIVE, T.MUSICAL, T.PASSIONATE}),
            ValueAxis.ARTWORK,
            NeedKind.CREATING,
            (SkillKind.WRITING, SkillKind.ORATORY),
            lambda rules: rules.careers.arts_weight,
            opening=True,
            venues=True,
        ),
        P.SETTLE: CareerSpec(
            "Settling a frontier",
            MortalRole.FARMER,
            frozenset({T.ADVENTUROUS, T.HARDY, T.DILIGENT}),
            ValueAxis.PERSEVERANCE,
            NeedKind.AUTONOMY,
            (SkillKind.FORAGING, SkillKind.CARPENTRY),
            lambda rules: rules.careers.settle_weight,
            opening=True,
            frontier=True,
        ),
    },
)
OPEN_PATHS = frozenset(path for path, spec in CAREERS.items() if spec.opening)
