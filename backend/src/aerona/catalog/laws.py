from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.core.grammar import fill
from aerona.domain.enums.demography import MarriageCustom
from aerona.domain.enums.polity import DebtRemedy, DecisionRule, GenderRule, GovernmentKind, LawKind, SuccessionRule


@dataclass(frozen=True)
class Param:
    default: int | str | bool
    low: int = 0
    high: int = 100
    choices: tuple[str, ...] = field(default_factory=tuple)

    def valid(self, value: int | str | bool) -> bool:
        if isinstance(self.default, bool):
            return isinstance(value, bool)
        if self.choices:
            return isinstance(value, str) and value in self.choices
        return isinstance(value, int) and not isinstance(value, bool) and self.low <= value <= self.high


def pick(*values: str, default: str | None = None) -> Param:
    return Param(default if default is not None else values[0], choices=values)


FRANCHISES = ("nobles", "landholders", "free", "all")
CRIME_TERMS = ("theft", "murder", "treason", "blasphemy", "desertion")
TORTURE_CRUELTY = 15
PENALTIES = ("fine", "pillory", "flogging", "hand", "blinding", "tongue", "exile", "wergild", "death")
LAW_PARAMS: MappingProxyType[LawKind, dict[str, Param]] = MappingProxyType(
    {
        LawKind.SUCCESSION_RULE: {
            "rule": pick(*(item.value for item in SuccessionRule)),
            "gender": pick(*(item.value for item in GenderRule), default=GenderRule.ANY.value),
            "wholeness_required": Param(False),
            "min_age": Param(16, 0, 200),
        },
        LawKind.INHERITANCE_SPLIT: {"split": pick("eldest", "equal", "youngest")},
        LawKind.LAND_TENURE: {"tenure": pick("feudal", "communal", "freehold", default="communal")},
        LawKind.SLAVERY: {"status": pick("allowed", "banned", "debt_only", default="banned")},
        LawKind.SERFDOM: {"allowed": Param(False), "labour_days": Param(30, 0, 200)},
        LawKind.TAX_RATE: {"rate": Param(10)},
        LawKind.TITHE: {"rate": Param(5, 0, 50), "enforced": Param(False)},
        LawKind.TOLLS: {"rate": Param(5)},
        LawKind.DEBT_LAW: {"remedy": pick(*(item.value for item in DebtRemedy), default=DebtRemedy.PRISON.value), "jubilee_epochs": Param(2, 1, 20)},
        LawKind.PENAL_CODE: {
            "theft": pick(*PENALTIES, default="fine"),
            "murder": pick(*PENALTIES, default="wergild"),
            "treason": pick(*PENALTIES, default="death"),
            "blasphemy": pick(*PENALTIES, default="fine"),
            "desertion": pick(*PENALTIES, default="flogging"),
            "trial": pick("judge", "jury", "combat", "ordeal"),
            "torture": pick("allowed", "forbidden", default="forbidden"),
        },
        LawKind.LEVY_LAW: {"share": Param(10, 0, 50), "duration": Param(1, 1, 10)},
        LawKind.CONSCRIPTION: {"min_age": Param(16, 10, 60), "share": Param(20, 0, 60)},
        LawKind.STANDING_ARMY: {"share": Param(3, 0, 20)},
        LawKind.VETERAN_PENSION: {"amount": Param(20)},
        LawKind.RANSOM_CUSTOM: {"allowed": Param(True), "price": Param(30)},
        LawKind.MARRIAGE_LAW: {
            "custom": pick(*(item.value for item in MarriageCustom)),
            "endogamy": Param(False),
            "divorce": pick("for_cause", "forbidden", "free"),
        },
        LawKind.SUMPTUARY: {"noble_luxury": Param(60), "merchant_luxury": Param(20)},
        LawKind.GUILD_CHARTER: {"guild_id": Param(0, 0, 10**9), "monopoly": Param(False)},
        LawKind.FOREIGNER_RIGHTS: {"level": pick("none", "residence", "citizenship", default="residence")},
        LawKind.RELIGIOUS_TOLERANCE: {"level": pick("persecution", "tolerated", "free", default="tolerated")},
        LawKind.WORSHIP_BAN: {"son_id": Param(0, 0, 10**9)},
        LawKind.CENSORSHIP: {"strictness": Param(50)},
        LawKind.BLOOD_FEUD: {"wergild_allowed": Param(True)},
        LawKind.QUARANTINE: {"automatic": Param(True), "epochs": Param(2, 1, 20)},
        LawKind.BURIAL_LAW: {"rite": pick("burial", "burning", "exposure")},
        LawKind.SANITATION: {"works": Param(10)},
        LawKind.FAIR_MARKET: {"strength": Param(60, 0, 100)},
        LawKind.MAGIC_BAN: {"severity": Param(50)},
        LawKind.LICENSED_MAGIC: {"fee": Param(20)},
        LawKind.RITE_RESTRICTIONS: {"level": Param(30)},
        LawKind.FRANCHISE: {"voters": pick(*FRANCHISES)},
        LawKind.CONSTITUTION: {
            "government": pick(*(item.value for item in GovernmentKind), default=GovernmentKind.MONARCHY.value),
            "decision_rule": pick(*(item.value for item in DecisionRule), default=DecisionRule.COUNCIL.value),
            "voters": pick(*FRANCHISES),
            "estates_rights": Param(True),
        },
        LawKind.CUSTOM: {},
    }
)


def term_text(name: str, param: Param) -> str:
    if isinstance(param.default, bool):
        return f"{name} true/false"
    if param.choices:
        return f"{name} {'/'.join(param.choices)}"
    return f"{name} {param.low}-{param.high}"


def law_terms(kind: LawKind) -> str:
    terms = LAW_PARAMS[kind]
    return ", ".join(term_text(name, param) for name, param in terms.items()) if terms else "no terms"


def law_terms_guide() -> str:
    return "; ".join(f"{kind.value}: {law_terms(kind)}" for kind in LAW_PARAMS)


PENALTY_CRUELTY = MappingProxyType(
    {"fine": 0, "wergild": 5, "pillory": 15, "exile": 25, "flogging": 35, "hand": 60, "tongue": 65, "blinding": 80, "death": 100}
)
LAW_TITLES = MappingProxyType(
    {
        LawKind.SUCCESSION_RULE: "the Law of the Throne",
        LawKind.SLAVERY: "the Law of the Bound",
        LawKind.TAX_RATE: "the Tax Law",
        LawKind.PENAL_CODE: "the Code of Punishments",
        LawKind.LEVY_LAW: "the Levy",
        LawKind.CONSCRIPTION: "the Conscription",
        LawKind.CENSORSHIP: "the Law of Censorship",
        LawKind.FRANCHISE: "the Law of the Franchise",
        LawKind.CONSTITUTION: "the Fundamental Law",
        LawKind.QUARANTINE: "the Quarantine Law",
        LawKind.VETERAN_PENSION: "the Veterans' Due",
        LawKind.SUMPTUARY: "the Sumptuary Law",
        LawKind.RELIGIOUS_TOLERANCE: "the Law of the Temples",
        LawKind.FOREIGNER_RIGHTS: "the Law of Strangers",
        LawKind.MAGIC_BAN: "the Ban on Sorcery",
    }
)


def defaults_for(kind: LawKind) -> dict[str, int | str | bool]:
    return {key: param.default for key, param in LAW_PARAMS[kind].items()}


def penal_cruelty(params: dict[str, int | str | bool]) -> int:
    values = [PENALTY_CRUELTY.get(str(params[key]), 0) for key in CRIME_TERMS if key in params]
    torture = TORTURE_CRUELTY if params.get("torture") == "allowed" else 0
    return min(100, round(sum(values) / len(values)) + torture if values else torture)


LAW_EFFECTS = MappingProxyType(
    {
        LawKind.SUCCESSION_RULE: "Decides who inherits the throne: {rule}, {gender}{wholeness}.",
        LawKind.INHERITANCE_SPLIT: "Property passes {split}.",
        LawKind.LAND_TENURE: "Land is held {tenure}.",
        LawKind.SLAVERY: "Slavery is {status}; captives may be bound where it is allowed.",
        LawKind.SERFDOM: "Serfs {allowed} be held; they owe {labour_days} days of labour.",
        LawKind.TAX_RATE: "Cities pay {rate}% of their output; high taxes stir unrest.",
        LawKind.TITHE: "{rate}% goes to the state temples.",
        LawKind.TOLLS: "Roads through the realm charge {rate}%.",
        LawKind.DEBT_LAW: "Defaulters face {remedy}.",
        LawKind.PENAL_CODE: (
            "Theft: {theft}; murder: {murder}; treason: {treason}; blasphemy: {blasphemy}; desertion: {desertion}; "
            "trial by {trial}; questioning under torture {torture}."
        ),
        LawKind.LEVY_LAW: "{share}% of the able are levied for {duration} seasons; armies grow.",
        LawKind.CONSCRIPTION: "Everyone from age {min_age} may be drafted; {share}% more soldiers.",
        LawKind.STANDING_ARMY: "{share}% of the people serve in a standing army.",
        LawKind.VETERAN_PENSION: "The maimed are kept from begging; warriors are content.",
        LawKind.RANSOM_CUSTOM: "Captives {allowed} be ransomed.",
        LawKind.MARRIAGE_LAW: "Marriage is {custom}; divorce is {divorce}.",
        LawKind.SUMPTUARY: "Nobles may show {noble_luxury} luxury, merchants {merchant_luxury}.",
        LawKind.GUILD_CHARTER: "A guild holds a charter; monopoly: {monopoly}.",
        LawKind.FOREIGNER_RIGHTS: "Foreigners have {level}; citizenship pulls migrants.",
        LawKind.RELIGIOUS_TOLERANCE: "Foreign faiths are under {level}; conversions follow.",
        LawKind.WORSHIP_BAN: "The worship of a god is banned.",
        LawKind.BLOOD_FEUD: "Blood feuds may end in wergild: {wergild_allowed}.",
        LawKind.CENSORSHIP: "Contrary rumours, broadsheets and satire are suppressed with strictness {strictness}.",
        LawKind.QUARANTINE: "Sick lands are sealed for {epochs} epochs.",
        LawKind.BURIAL_LAW: "The dead are given to {rite}; burning slows plague.",
        LawKind.SANITATION: "The realm pays for sanitation works.",
        LawKind.FAIR_MARKET: "Buying up a market to raise its prices, or flooding a rival's, is forbidden ({strength}).",
        LawKind.MAGIC_BAN: "Sorcery is banned; {severity}% of would-be wizards are stopped.",
        LawKind.LICENSED_MAGIC: "Mages pay a licence of {fee}.",
        LawKind.RITE_RESTRICTIONS: "Rites are restricted ({level}).",
        LawKind.FRANCHISE: "The vote belongs to the {voters}.",
        LawKind.CONSTITUTION: "The realm is {government:an} that decides by {decision_rule}; the vote belongs to the {voters}, and {estates}.",
        LawKind.CUSTOM: "An old custom without a written rule.",
    }
)


def law_effect(kind: LawKind, params: dict[str, int | str | bool]) -> str:
    merged = {**defaults_for(kind), **params}
    words = {key: str(value).replace("_", " ") for key, value in merged.items()}
    words["wholeness"] = ", the maimed may not rule" if merged.get("wholeness_required") else ""
    words["allowed"] = "may" if merged.get("allowed") else "may not"
    words["estates"] = "the estates keep their rights" if merged.get("estates_rights") else "the estates hold no rights of their own"
    template = LAW_EFFECTS[kind]
    try:
        return fill(template, **words)
    except KeyError:
        return template
