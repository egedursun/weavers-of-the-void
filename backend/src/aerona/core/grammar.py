import re
from enum import Enum
from functools import cache
from string import Formatter
from typing import Any

VOWELS = "aeiou"
ARTICLE_SPECS = {"an": False, "An": True}
PERCENT_SPEC = "%"


VOWEL_NUMBER_PREFIXES = ("11", "18")
VOWEL_NUMBER_LENGTHS = frozenset({2, 5, 8})


CONSONANT_VOWELS = ("uni", "use", "usu", "uti", "ure", "uro", "eu", "ewe", "one", "once", "ubiq")
SILENT_H = ("hour", "honest", "honour", "heir")


def sounds_like_vowel(word: str) -> bool:
    digits = len(word) - len(word.lstrip("0123456789"))
    if digits:
        return word.startswith("8") or (word.startswith(VOWEL_NUMBER_PREFIXES) and digits in VOWEL_NUMBER_LENGTHS)
    lowered = word.lower()
    if lowered.startswith(CONSONANT_VOWELS):
        return False
    return lowered.startswith(SILENT_H) or lowered[:1] in VOWELS


def an(noun: object, *, capital: bool = False) -> str:
    word = str(noun)
    article = "an" if sounds_like_vowel(word) else "a"
    return f"{article.capitalize() if capital else article} {word}"


UNCHANGED_PLURALS = frozenset({"species", "series", "news", "means", "remains", "arms", "goods", "thanks", "data", "kin", "folk", "cosmos", "chaos"})
IRREGULAR_ENDINGS = (
    ("lives", "life"),
    ("wives", "wife"),
    ("knives", "knife"),
    ("wolves", "wolf"),
    ("halves", "half"),
    ("selves", "self"),
    ("crises", "crisis"),
    ("theses", "thesis"),
    ("oases", "oasis"),
    ("analyses", "analysis"),
    ("prostheses", "prosthesis"),
    ("biases", "bias"),
    ("statuses", "status"),
    ("viruses", "virus"),
    ("bonuses", "bonus"),
    ("censuses", "census"),
)
PLURAL_ENDINGS = (("ies", "y"), ("sses", "ss"), ("shes", "sh"), ("ches", "ch"), ("xes", "x"), ("zzes", "zz"), ("oes", "o"))


def singular(plural: str) -> str:
    head, _, last = plural.rpartition(" ")
    lead = f"{head} " if head else ""
    if last in UNCHANGED_PLURALS or last.endswith(("ss", "us", "is")):
        return plural
    for ending, replacement in (*IRREGULAR_ENDINGS, *PLURAL_ENDINGS):
        if last.endswith(ending):
            return lead + last.removesuffix(ending) + replacement
    return lead + last.removesuffix("s")


def plural(noun: str) -> str:
    if " of " in noun:
        head, rest = noun.split(" of ", 1)
        return f"{plural(head)} of {rest}"
    head, _, last = noun.rpartition(" ")
    lead = f"{head} " if head else ""
    for many, one in IRREGULAR_ENDINGS:
        if last.endswith(one):
            return lead + last.removesuffix(one) + many
    if last in UNCHANGED_PLURALS or (last.endswith("s") and not last.endswith(("ss", "us", "is"))):
        return noun
    if last.endswith("y") and last[-2:-1] not in VOWELS:
        return lead + last.removesuffix("y") + "ies"
    if last.endswith(("ss", "sh", "ch", "x", "z")):
        return lead + last + "es"
    return lead + last + "s"


def agree(count: int | None, one: str, many: str) -> str:
    return one if count == 1 else many


def several(count: int | None, one: str, many: str) -> str:
    if count is None:
        return f"an unknown number of {many}"
    return f"{count} {agree(count, one, many)}"


NUMBER_TEXT = re.compile(r"-?\d+(\.\d+)?")


COUNTED_FORMS = 3
SPANS = frozenset({"epoch", "age", "year", "season", "month", "round", "day", "hour", "generation"})
COUNT_MARK = "#"
OPTIONAL_MARK = "?"


class ArticleFormatter(Formatter):
    def format_field(self, value: Any, format_spec: str) -> str:
        if format_spec.startswith(OPTIONAL_MARK):
            text = format(value, "")
            return format_spec[len(OPTIONAL_MARK) :].replace(COUNT_MARK, text) if text.strip() else ""
        if format_spec in ARTICLE_SPECS or format_spec == PERCENT_SPEC:
            return f"{value}%" if format_spec == PERCENT_SPEC else an(str(value), capital=ARTICLE_SPECS[format_spec])
        if "|" in format_spec and isinstance(value, str) and NUMBER_TEXT.fullmatch(value.strip()):
            value = float(value)
        if "|" in format_spec and isinstance(value, (int, float)) and not isinstance(value, bool):
            return counted(int(value) if float(value).is_integer() else value, format_spec)
        formatted: str = super().format_field(value, format_spec)
        return formatted


def counted(count: float, format_spec: str) -> str:
    forms = format_spec.split("|")
    if len(forms) == COUNTED_FORMS:
        none, one, many = forms
        return (none if count == 0 else one if count == 1 else many).replace(COUNT_MARK, str(count))
    one, many = format_spec.split("|", 1)
    if count == 0:
        return f"less than one {one}" if one in SPANS else f"no {many}"
    return f"{count} {agree(1 if count == 1 else 0, one, many)}"


ARTICLES = ArticleFormatter()


def fill(template: str, **fields: object) -> str:
    return ARTICLES.format(template, **fields)


ORDINAL_WORDS = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth")
ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}
TEEN_LOW = 11
TEEN_HIGH = 13
HUNDRED = 100
TEN = 10


def ordinal_word(number: int) -> str:
    if 1 <= number <= len(ORDINAL_WORDS):
        return ORDINAL_WORDS[number - 1]
    if TEEN_LOW <= number % HUNDRED <= TEEN_HIGH:
        return f"{number}th"
    return f"{number}{ORDINAL_SUFFIXES.get(number % TEN, 'th')}"


AGE_NEUTRAL: dict[tuple[str, str], str] = {
    ("VeteranGrant", "none"): "no grant",
    ("MortalRole", "scribe"): "clerk",
    ("DangerSource", "volcanic"): "volcanic ground",
    ("MovementMode", "boat"): "by boat",
    ("MovementMode", "wheeled"): "on wheels",
    ("MovementMode", "flying"): "by flight",
    ("MovementMode", "burrowing"): "by burrowing",
    ("MovementMode", "swimming"): "by swimming",
    ("MovementMode", "climbing"): "by climbing",
    ("MovementMode", "incorporeal"): "without a body",
    ("DangerSource", "avalanche"): "avalanches",
    ("SocialClass", "scribe"): "clerk",
    ("SocialClass", "serf_or_slave"): "bonded",
    ("OrderLabour", "serf"): "tied to the land",
    ("ClergyFunction", "scribe"): "clerk",
    ("ServitorRole", "scribe"): "keeper of accounts",
    ("Profession", "smith"): "metalworker",
    ("SkillKind", "smithing"): "metalworking",
    ("ProcessKind", "smithing"): "metalworking",
    ("WorkshopKind", "scriptorium"): "copying house",
    ("MethodKind", "scriptorium"): "copying house",
    ("CourtLevel", "guild"): "trade court",
    ("FactionKind", "craft_guild"): "craft association",
    ("FactionKind", "merchant_guild"): "trade association",
    ("FactionKind", "thieves_guild"): "thieves' ring",
    ("FactionKind", "peasant_league"): "farmers' league",
    ("OwnerClass", "guild"): "craft association",
    ("HeraldryHolderKind", "guild"): "association",
    ("SociolectKind", "guild"): "trade",
    ("TitleTier", "guild"): "association",
    ("JurisdictionClaim", "guild"): "association",
    ("LawKind", "guild_charter"): "association charter",
    ("StructureKind", "guildhall"): "trade hall",
    ("StructureKind", "alchemist_lab"): "reagent laboratory",
    ("PeaceTermKind", "throne"): "rule",
    ("StepAction", "crown"): "raise to rule",
    ("WorkshopKind", "alchemist"): "chemical works",
    ("Technique", "guilds"): "craft associations",
    ("OathBreach", "the_throne_was_seized"): "rule was seized",
    ("CoupCause", "a_subject_turned_their_power_base_on_the_throne"): "a subject turned their power base on the ruler",
    ("CoupCause", "the_marshal_turned_the_army_on_the_throne"): "the marshal turned the army on the ruler",
    ("CoupCause", "the_regent_took_the_crown"): "the regent took power",
    ("GodGoalKind", "hold_thrones"): "hold thrones of power",
    ("GatheringKind", "coronation"): "accession",
    ("CollectionKind", "coronation"): "accession",
    ("DivinationQuestion", "coronation"): "accession",
    ("EngineKind", "coronation"): "accession",
    ("ItemDeed", "coronation"): "accession",
    ("GuestRole", "crowned"): "new ruler",
    ("EntryBarrier", "guild_right"): "chartered right",
    ("RuleMaker", "guild"): "trade association",
    ("HeadSelection", "appointed_by_owner"): "appointment by its owner",
    ("HeadSelection", "elected_by_body"): "election by its governing body",
    ("HeadSelection", "elected_by_members"): "election by its members",
    ("HeadSelection", "inherited"): "inheritance",
    ("DuelEnd", "yield"): "a yield",
    ("DuelEnd", "disarm"): "a disarming",
    ("DuelEnd", "crippled"): "a crippling",
    ("DuelEnd", "unconscious"): "unconsciousness",
    ("DuelEnd", "first_wound"): "the first wound",
    ("DuelEnd", "ring_out"): "a ring-out",
    ("DuelEnd", "stopped"): "a halt",
    ("SpreadPath", "loosed"): "deliberate release",
    ("LifecycleCause", "living"): "living use",
    ("LifecycleCause", "no_adherents"): "the loss of its adherents",
    ("LifecycleCause", "no_texts"): "the loss of its texts",
    ("LifecycleCause", "no_practitioners"): "the loss of its practitioners",
    ("LifecycleCause", "no_hosts"): "the loss of its hosts",
    ("LifecycleCause", "sealed"): "sealing",
    ("LifecycleCause", "revived"): "revival",
    ("LifecycleCause", "rediscovered"): "rediscovery",
    ("LifecycleCause", "reconstructed"): "reconstruction",
    ("LifecycleCause", "rereleased"): "a fresh release",
    ("LifecycleCause", "returned"): "return",
    ("LifecycleCause", "god_act"): "an act of a god",
    ("InheritanceCustom", "by_merit"): "merit",
    ("InheritanceCustom", "designated"): "designation",
    ("InheritanceCustom", "elective"): "election",
    ("InheritanceCustom", "through_second_line"): "the second line",
    ("RightAcquired", "created"): "creation",
    ("RightAcquired", "inherited"): "inheritance",
    ("RightAcquired", "bought"): "purchase",
    ("RightAcquired", "licensed"): "licence",
    ("RightAcquired", "stolen"): "theft",
    ("RightAcquired", "granted"): "grant",
    ("RightAcquired", "won"): "winning",
    ("RightAcquired", "wed"): "marriage",
    ("RightAcquired", "shared"): "sharing",
    ("ClaimBasis", "fabricated"): "fabrication",
    ("ClaimBasis", "divine"): "divine right",
    ("ClaimBasis", "de_jure"): "right in law",
    ("InfantFeeding", "by_birth_parent"): "its birth parent's milk",
    ("InfantFeeding", "by_other_nurse"): "a nurse's milk",
    ("InfantFeeding", "none_needed"): "a feeding it never needed",
    ("InterpretationFault", "none"): "no fault",
    ("InterpretationFault", "wrong_term"): "a wrong term",
    ("InterpretationFault", "softened"): "its meaning softened",
    ("InterpretationFault", "hardened"): "its meaning hardened",
    ("InterpretationFault", "slanted"): "a slant",
    ("InterpretationFault", "invented"): "invented words",
    ("TravelMethod", "carried_within"): "carriage within another",
    ("IndependenceAnswer", "released"): "release",
    ("NetworkCarrier", "wired"): "wire",
    ("TreatmentStep", "diagnose"): "diagnosis",
    ("TreatmentStep", "clean"): "cleaning",
    ("TreatmentStep", "suture"): "suturing",
    ("TreatmentStep", "set_bone"): "setting the bone",
    ("TreatmentStep", "splint"): "splinting",
    ("TreatmentStep", "dress"): "dressing",
    ("TreatmentStep", "amputate"): "amputation",
    ("TreatmentStep", "cauterise"): "cautery",
    ("TreatmentStep", "crutch"): "a crutch",
    ("TreatmentStep", "drain"): "draining",
    ("TreatmentStep", "bleed"): "bleeding",
    ("TreatmentStep", "medicate"): "medicine",
    ("TreatmentStep", "transfuse"): "transfusion",
    ("LawKind", "inheritance_split"): "inheritance law",
    ("LawKind", "land_tenure"): "land tenure law",
    ("LawKind", "slavery"): "slavery law",
    ("LawKind", "serfdom"): "serfdom law",
    ("LawKind", "tax_rate"): "tax law",
    ("LawKind", "tithe"): "tithe law",
    ("LawKind", "tolls"): "toll law",
    ("LawKind", "conscription"): "conscription law",
    ("LawKind", "standing_army"): "standing army law",
    ("LawKind", "veteran_pension"): "veteran pension law",
    ("LawKind", "sumptuary"): "sumptuary law",
    ("LawKind", "foreigner_rights"): "foreigner rights law",
    ("LawKind", "religious_tolerance"): "religious tolerance law",
    ("LawKind", "censorship"): "censorship law",
    ("LawKind", "blood_feud"): "blood feud law",
    ("LawKind", "quarantine"): "quarantine law",
    ("LawKind", "sanitation"): "sanitation law",
    ("LawKind", "fair_market"): "fair market law",
    ("LawKind", "licensed_magic"): "magic licence law",
    ("LawKind", "franchise"): "franchise law",
    ("LawKind", "custom"): "customary law",
    ("LawKind", "data_privacy"): "data privacy law",
    ("LawKind", "intellectual_property"): "intellectual property law",
    ("LawKind", "closed_season"): "closed season law",
    ("LawKind", "protected_waters"): "protected waters law",
    ("LawKind", "mind_status"): "mind status law",
    ("LawKind", "copy_succession"): "copy succession law",
    ("LawKind", "clone_status"): "clone status law",
    ("LawKind", "designed_status"): "designed status law",
    ("DistrictKind", "market"): "market quarter",
    ("DistrictKind", "slums"): "slum quarter",
    ("DistrictKind", "palace"): "palace quarter",
    ("DistrictKind", "residential"): "residential quarter",
    ("DistrictKind", "gardens"): "garden quarter",
    ("DistrictKind", "industrial"): "industrial quarter",
    ("DistrictKind", "business"): "business quarter",
    ("DistrictKind", "research"): "research quarter",
    ("DistrictKind", "university"): "university quarter",
    ("DistrictKind", "entertainment"): "entertainment quarter",
    ("DistrictKind", "floating"): "floating quarter",
    ("RightKind", "market_privilege"): "market",
    ("SanctuaryKind", "hospitality"): "guest right",
    ("SanctuaryKind", "wilds"): "wild country",
    ("HouseholdDecision", "marry"): "marry off one of its own",
    ("HouseholdDecision", "apprentice"): "apprentice one of its young",
    ("HouseholdDecision", "take_lodger"): "take in a lodger",
    ("HouseholdDecision", "hire_servant"): "hire a servant",
    ("HouseholdDecision", "dismiss_servant"): "dismiss a servant",
    ("HouseholdDecision", "sell_furnishing"): "sell its furnishings",
    ("HouseholdDecision", "lend"): "lend coin",
    ("FactionKind", "rebels"): "rebel band",
    ("FactionKind", "bandits"): "bandit band",
    ("FactionKind", "pirates"): "pirate crew",
    ("FactionKind", "assassins"): "assassins' order",
    ("FactionKind", "scholars_academy"): "scholars' academy",
    ("FactionKind", "route_raiders"): "band of route raiders",
    ("FactionKind", "financiers"): "financiers' house",
    ("FactionKind", "veterans"): "veterans' band",
    ("PreparednessKind", "shelters"): "shelter",
    ("PreparednessKind", "evacuation_routes"): "evacuation route",
    ("PreparednessKind", "reserves_of_energy"): "energy reserve",
    ("BindingNeed", "none"): "nothing",
    ("BindingNeed", "place"): "a place of its own",
    ("BindingNeed", "name"): "a name of its own",
    ("FactionActionKind", "fund_war"): "fund a war",
    ("FactionActionKind", "suppressed"): "suppress",
    ("FactionActionKind", "hired"): "hire",
    ("FactionActionKind", "defected"): "defect",
    ("FactionActionKind", "propaganda"): "spread its word",
    ("FactionActionKind", "schism"): "split away",
    ("KinGroupForm", "localized_group"): "local kin group",
    ("KinGroupForm", "age_linked_group"): "age-linked kin group",
    ("InteractionKind", "converse"): "talk",
    ("InteractionKind", "befriend"): "friendship",
    ("InteractionKind", "joke"): "jokes",
    ("InteractionKind", "comfort"): "comfort",
    ("InteractionKind", "flatter"): "flattery",
    ("InteractionKind", "boast"): "boasting",
    ("InteractionKind", "insult"): "insults",
    ("InteractionKind", "argue"): "an argument",
    ("InteractionKind", "flirt"): "flirting",
    ("InteractionKind", "court"): "courtship",
    ("InteractionKind", "propose"): "a proposal",
    ("InteractionKind", "seduce"): "seduction",
    ("InteractionKind", "quarrel"): "a quarrel",
    ("InteractionKind", "reconcile"): "reconciliation",
    ("InteractionKind", "teach"): "teaching",
    ("InteractionKind", "gift"): "a gift",
    ("InteractionKind", "ask_favour"): "a favour asked",
    ("InteractionKind", "confide_secret"): "a secret confided",
    ("InteractionKind", "threaten"): "threats",
    ("InteractionKind", "brawl"): "a brawl",
    ("InteractionKind", "apologise"): "an apology",
    ("InteractionKind", "share_meal"): "a shared meal",
    ("InteractionKind", "ask_counsel"): "counsel",
    ("InteractionKind", "warn"): "a warning",
    ("InteractionKind", "plead"): "pleading",
    ("InteractionKind", "share_news"): "news",
    ("ShortfallEffect", "herds"): "want of herds",
    ("ShortfallEffect", "status"): "lost standing",
    ("ShortfallEffect", "toil"): "heavier toil",
    ("ShortfallEffect", "arcane"): "want of arcane goods",
    ("ShortfallEffect", "shelter"): "want of shelter",
    ("ShortfallEffect", "learning"): "want of learning",
    ("ShortfallEffect", "justice"): "want of justice",
    ("RebuildPlan", "planned"): "to a new plan",
    ("RebuildPlan", "opportunistic"): "as chance allowed",
    ("RebuildPlan", "relocated"): "on a new site",
    ("RebuildPlan", "abandoned"): "not at all",
    ("RebuildPlan", "restored"): "as it stood before",
    ("SpiritOffence", "clearing"): "the clearing of its ground",
    ("SpiritOffence", "unpaid"): "unpaid offerings",
    ("SpiritOffence", "taboo"): "a broken taboo",
    ("SpiritOffence", "overharvest"): "overharvesting",
    ("FactionGoalKind", "monopoly_on"): "a monopoly",
    ("FactionGoalKind", "install_claimant"): "the rise of its claimant",
    ("FactionGoalKind", "abolish_law"): "the end of a law",
    ("FactionGoalKind", "enact_law"): "a new law",
    ("FactionGoalKind", "war_on"): "war",
    ("FactionGoalKind", "peace_with"): "peace",
    ("FactionGoalKind", "protect_craft"): "protection of its craft",
    ("FactionGoalKind", "convert_realm"): "the conversion of the realm",
    ("FactionGoalKind", "gain_privilege"): "privilege",
    ("FactionGoalKind", "win_office"): "office",
    ("FactionGoalKind", "ruin_rival"): "the ruin of a rival",
    ("FactionGoalKind", "protect_members"): "protection of its members",
    ("FactionGoalKind", "found_settlement"): "a settlement of its own",
}


def fact_word(enum_name: str | None, value: str) -> str:
    return AGE_NEUTRAL.get((enum_name or "", value), value.replace("_", " "))


def spoken(value: object) -> str:
    if isinstance(value, Enum):
        return spoken_member(type(value), str(value.value))
    raw = str(getattr(value, "value", value))
    return fact_word(type(value).__name__, raw) if hasattr(value, "value") else raw.replace("_", " ")


@cache
def spoken_member(kind: type[Enum], value: str) -> str:
    return fact_word(kind.__name__, value)
