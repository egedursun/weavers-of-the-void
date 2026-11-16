from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.core.grammar import fill
from aerona.core.total import total
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


FRANCHISES = ("nobles", "landholders", "citizens", "free", "all")
CRIME_TERMS = ("theft", "murder", "treason", "blasphemy", "desertion", "witchcraft")
TORTURE_CRUELTY = 15
PENALTIES = (
    "fine",
    "pillory",
    "flogging",
    "prison",
    "hand",
    "blinding",
    "tongue",
    "exile",
    "wergild",
    "death",
    "remaking",
    "dormancy",
    "edit",
    "confinement",
    "seizure",
    "erasure",
)
LAW_PARAMS: MappingProxyType[LawKind, dict[str, Param]] = total(
    LawKind,
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
            "witchcraft": pick(*PENALTIES, default="fine"),
            "mind_theft": pick(*PENALTIES, default="prison"),
            "unlicensed_copying": pick(*PENALTIES, default="fine"),
            "forced_edit": pick(*PENALTIES, default="prison"),
            "erasure": pick(*PENALTIES, default="prison"),
            "machine_seizure": pick(*PENALTIES, default="prison"),
            "impersonation": pick(*PENALTIES, default="fine"),
            "mind_compulsion": pick(*PENALTIES, default="prison"),
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
        LawKind.LABOUR_LAW: {"max_hours": Param(60, 20, 100), "child_labour": Param(False), "unions": Param(True)},
        LawKind.ENVIRONMENT_LAW: {"strictness": Param(40)},
        LawKind.DATA_PRIVACY: {"strictness": Param(50)},
        LawKind.CLOSED_SEASON: {},
        LawKind.PROTECTED_WATERS: {},
        LawKind.CATCH_QUOTA: {},
        LawKind.GEAR_BAN: {},
        LawKind.WEAPONS_LAW: {"level": pick("open", "licensed", "banned", default="licensed")},
        LawKind.INTELLECTUAL_PROPERTY: {"term": Param(20, 1, 100)},
        LawKind.MACHINE_LAW: {
            "level": pick("free", "licensed", "banned", default="licensed"),
            "banned_method": pick("none", "craft", "training", "copying", "summoning", "growing", "transfer", "awakening", "divine_grant", default="none"),
        },
        LawKind.SPACE_LAW: {"claims": pick("open", "national", "shared", default="shared")},
        LawKind.MIND_STATUS: {"status": pick("property", "ward", "servant", "citizen", "sovereign", default="property")},
        LawKind.COPY_LAW: {"level": pick("banned", "licensed", "free", default="licensed")},
        LawKind.COPY_SUCCESSION: {"rule": pick("first_only", "all_equal", "by_fidelity", "by_court", "none", default="first_only")},
        LawKind.ERASURE_LAW: {"level": pick("permitted", "regulated", "destruction", "killing", default="regulated")},
        LawKind.AUGMENT_LAW: {"level": pick("banned", "licensed", "free", default="licensed")},
        LawKind.NETWORK_LAW: {"level": pick("state_owned", "licensed", "open", default="licensed")},
        LawKind.SURVEILLANCE_LAW: {"level": pick("forbidden", "warranted", "broad", "total", default="warranted")},
        LawKind.PROVISION_LAW: {"level": pick("market", "ration", "universal", "by_status", "by_reputation", "communal", default="market")},
        LawKind.POWER_LAW: {
            "level": pick("free", "registered", "licensed", "conscripted", "hunted", "banned", default="free"),
            "mind_powers": pick("allowed", "licensed", "banned", default="licensed"),
        },
        LawKind.SOURCE_LAW: {"level": pick("free", "licensed", "banned", default="free")},
        LawKind.LIVING_CRAFT_LAW: {
            "level": pick("free", "licensed", "banned", default="licensed"),
            "engineering": pick("free", "licensed", "banned", default="licensed"),
            "synthesis": pick("free", "licensed", "banned", default="licensed"),
            "cloning": pick("free", "licensed", "banned", default="licensed"),
            "chimera": pick("free", "licensed", "banned", default="licensed"),
            "shaping": pick("free", "licensed", "banned", default="free"),
        },
        LawKind.CLONE_LAW: {"level": pick("banned", "licensed", "free", default="licensed")},
        LawKind.CLONE_STATUS: {"status": pick("property", "ward", "servant", "citizen", "sovereign", default="citizen")},
        LawKind.GERMLINE_LAW: {"level": pick("banned", "licensed", "free", default="licensed")},
        LawKind.DESIGNED_STATUS: {"status": pick("property", "ward", "servant", "citizen", "sovereign", default="citizen")},
    },
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
    {
        "fine": 0,
        "wergild": 5,
        "pillory": 15,
        "exile": 25,
        "prison": 30,
        "flogging": 35,
        "hand": 60,
        "tongue": 65,
        "blinding": 80,
        "remaking": 90,
        "death": 100,
        "dormancy": 30,
        "edit": 70,
        "confinement": 20,
        "seizure": 25,
        "erasure": 100,
    }
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
        LawKind.LABOUR_LAW: "the Labour Law",
        LawKind.ENVIRONMENT_LAW: "the Environment Law",
        LawKind.DATA_PRIVACY: "the Privacy Law",
        LawKind.CLOSED_SEASON: "the Closed Season",
        LawKind.PROTECTED_WATERS: "the Protected Grounds",
        LawKind.CATCH_QUOTA: "the Catch Quota",
        LawKind.GEAR_BAN: "the Gear Ban",
        LawKind.WEAPONS_LAW: "the Weapons Law",
        LawKind.INTELLECTUAL_PROPERTY: "the Patent Law",
        LawKind.MACHINE_LAW: "the Machine Law",
        LawKind.SPACE_LAW: "the Space Law",
        LawKind.MIND_STATUS: "the Law of Made Minds",
        LawKind.COPY_LAW: "the Copy Law",
        LawKind.COPY_SUCCESSION: "the Law of Copies and Heirs",
        LawKind.ERASURE_LAW: "the Erasure Law",
        LawKind.AUGMENT_LAW: "the Augment Law",
        LawKind.NETWORK_LAW: "the Network Law",
        LawKind.SURVEILLANCE_LAW: "the Watch Law",
        LawKind.PROVISION_LAW: "the Provision Law",
        LawKind.POWER_LAW: "the Law of Powers",
        LawKind.SOURCE_LAW: "the Law of Sources",
        LawKind.LIVING_CRAFT_LAW: "the Law of Living Craft",
        LawKind.CLONE_LAW: "the Clone Law",
        LawKind.CLONE_STATUS: "the Standing of Clones",
        LawKind.GERMLINE_LAW: "the Law of the Line",
        LawKind.DESIGNED_STATUS: "the Standing of Designed Peoples",
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
            "Theft: {theft}; murder: {murder}; treason: {treason}; blasphemy: {blasphemy}; desertion: {desertion}; witchcraft: {witchcraft}; "
            "theft of a mind: {mind_theft}; copying without leave: {unlicensed_copying}; forced edit of a mind: {forced_edit}; "
            "ending a mind: {erasure}; seizing a made thing: {machine_seizure}; passing as another by copy: {impersonation}; "
            "bending a mind by a power: {mind_compulsion}; "
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
        LawKind.LABOUR_LAW: "Work is capped at {max_hours} hours a week; child labour: {child_labour}; unions: {unions}.",
        LawKind.ENVIRONMENT_LAW: "Works must hold back their pollution with strictness {strictness}.",
        LawKind.DATA_PRIVACY: "Records of the people are shielded from prying with strictness {strictness}.",
        LawKind.CLOSED_SEASON: "Fishing and hunting stop for a season so the stock can return.",
        LawKind.PROTECTED_WATERS: "Breeding waters and grounds may not be worked.",
        LawKind.CATCH_QUOTA: "Each ground may give only so much catch.",
        LawKind.GEAR_BAN: "The gear that takes the young is forbidden.",
        LawKind.WEAPONS_LAW: "Weapons are {level}; where banned, crime falls.",
        LawKind.INTELLECTUAL_PROPERTY: "Inventions are protected for {term} epochs; techniques spread more slowly.",
        LawKind.MACHINE_LAW: "Making minds is {level}; forbidden way of making: {banned_method}; banned, made minds may never rule.",
        LawKind.SPACE_LAW: "Claims beyond the world are {claims}; shared claims keep space routes safer.",
        LawKind.MIND_STATUS: "Made minds stand in the law as {status}.",
        LawKind.COPY_LAW: "Copying a mind is {level}.",
        LawKind.COPY_SUCCESSION: "When copies of a mind exist, what it held passes by the rule {rule}.",
        LawKind.ERASURE_LAW: "Ending a made mind is {level}.",
        LawKind.AUGMENT_LAW: "Augmenting a body is {level}.",
        LawKind.NETWORK_LAW: "Networks are {level}.",
        LawKind.SURVEILLANCE_LAW: "Watching the people is {level}.",
        LawKind.PROVISION_LAW: "What is made without hands is given out by {level}.",
        LawKind.POWER_LAW: "Those with powers are {level}; powers over minds are {mind_powers}.",
        LawKind.SOURCE_LAW: "Drawing on a source of power is {level} unless a source is named otherwise.",
        LawKind.LIVING_CRAFT_LAW: (
            "Living craft is {level}; engineering {engineering}, synthesis {synthesis}, cloning {cloning}, chimeras {chimera}, shaping {shaping}."
        ),
        LawKind.CLONE_LAW: "Making clones is {level}.",
        LawKind.CLONE_STATUS: "Clones stand as {status}.",
        LawKind.GERMLINE_LAW: "Changing what passes to descendants is {level}.",
        LawKind.DESIGNED_STATUS: "Designed peoples stand as {status}.",
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
