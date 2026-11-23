from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.genetics import DwellingKind, GiftStance, HouseholdDecision, HouseholdRole, Locus, LocusGroup
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.urban import HousingLevel
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class Allele:
    key: str
    label: str
    dominance: int
    weight: int
    score: int = 0


@dataclass(frozen=True)
class LocusSpec:
    locus: Locus
    label: str
    group: LocusGroup
    alleles: tuple[Allele, ...]
    graded: bool = False
    visible: bool = False
    noun: str = ""

    def allele(self, key: str) -> Allele:
        return next((allele for allele in self.alleles if allele.key == key), self.common)

    @property
    def common(self) -> Allele:
        return max(self.alleles, key=lambda allele: (allele.weight, -self.alleles.index(allele)))

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(allele.key for allele in self.alleles)


def looks(locus: Locus, label: str, noun: str, alleles: tuple[Allele, ...], *, graded: bool = False) -> LocusSpec:
    return LocusSpec(locus, label, LocusGroup.LOOKS, alleles, graded=graded, visible=True, noun=noun)


def leaning(locus: Locus, label: str, alleles: tuple[Allele, ...], *, visible: bool = False) -> LocusSpec:
    return LocusSpec(locus, label, LocusGroup.PREDISPOSITION, alleles, visible=visible)


def graded(locus: Locus, label: str, group: LocusGroup, words: tuple[str, str, str], *, rare: int = 15) -> LocusSpec:
    low, common, high = words
    return LocusSpec(
        locus,
        label,
        group,
        (Allele("low", low, 1, rare, -1), Allele("common", common, 1, PERCENT - 2 * rare, 0), Allele("high", high, 1, rare, 1)),
        graded=True,
    )


GIFT_LOCI: Mapping[MagicSchool, Locus] = total(
    MagicSchool,
    {
        MagicSchool.ELEMENTAL_FIRE: Locus.GIFT_ELEMENTAL_FIRE,
        MagicSchool.ELEMENTAL_WATER: Locus.GIFT_ELEMENTAL_WATER,
        MagicSchool.EARTH: Locus.GIFT_EARTH,
        MagicSchool.STORM: Locus.GIFT_STORM,
        MagicSchool.LIFE: Locus.GIFT_LIFE,
        MagicSchool.DEATH: Locus.GIFT_DEATH,
        MagicSchool.MIND: Locus.GIFT_MIND,
        MagicSchool.ILLUSION: Locus.GIFT_ILLUSION,
        MagicSchool.DIVINATION: Locus.GIFT_DIVINATION,
        MagicSchool.WARDING: Locus.GIFT_WARDING,
        MagicSchool.BINDING: Locus.GIFT_BINDING,
        MagicSchool.SUMMONING: Locus.GIFT_SUMMONING,
        MagicSchool.BLOOD: Locus.GIFT_BLOOD,
        MagicSchool.VOID: Locus.GIFT_VOID,
    },
)
SCHOOL_OF_LOCUS: Mapping[Locus, MagicSchool] = {locus: school for school, locus in GIFT_LOCI.items()}


def gift(school: MagicSchool) -> LocusSpec:
    label = spoken(school).removeprefix("elemental ")
    return LocusSpec(
        GIFT_LOCI[school],
        f"Gift of {label}",
        LocusGroup.GIFT,
        (Allele("dormant", "dormant", 2, 88, 0), Allele("gifted", "gifted", 1, 11, 1), Allele("wild", "wild", 3, 1, 2)),
    )


LOCI: dict[Locus, LocusSpec] = {
    spec.locus: spec
    for spec in (
        looks(
            Locus.HEIGHT,
            "Height",
            "stature",
            (Allele("short", "short", 1, 25, -1), Allele("middling", "of middling height", 1, 50, 0), Allele("tall", "tall", 1, 25, 1)),
            graded=True,
        ),
        looks(
            Locus.BUILD,
            "Build",
            "build",
            (Allele("slender", "slender", 1, 30, -1), Allele("sturdy", "sturdy", 1, 45, 0), Allele("broad", "broad", 1, 25, 1)),
            graded=True,
        ),
        looks(
            Locus.SKIN,
            "Skin",
            "skin",
            (
                Allele("pale", "pale-skinned", 1, 15, 0),
                Allele("fair", "fair-skinned", 1, 20, 1),
                Allele("olive", "olive-skinned", 1, 20, 2),
                Allele("tawny", "tawny-skinned", 1, 15, 3),
                Allele("brown", "brown-skinned", 1, 15, 4),
                Allele("dark", "dark-skinned", 1, 15, 5),
            ),
            graded=True,
        ),
        looks(
            Locus.HAIR_COLOUR,
            "Hair colour",
            "hair",
            (
                Allele("black", "black-haired", 5, 30),
                Allele("brown", "brown-haired", 4, 30),
                Allele("copper", "copper-haired", 2, 12),
                Allele("golden", "golden-haired", 1, 14),
                Allele("ash", "ash-haired", 3, 14),
            ),
        ),
        looks(
            Locus.HAIR_TEXTURE,
            "Hair texture",
            "hair",
            (Allele("curly", "curly hair", 3, 30), Allele("wavy", "wavy hair", 2, 35), Allele("straight", "straight hair", 1, 35)),
        ),
        looks(
            Locus.EYE_COLOUR,
            "Eye colour",
            "eyes",
            (
                Allele("brown", "brown eyes", 5, 35),
                Allele("amber", "amber eyes", 4, 10),
                Allele("hazel", "hazel eyes", 3, 15),
                Allele("green", "green eyes", 2, 12),
                Allele("grey", "grey eyes", 1, 14),
                Allele("blue", "blue eyes", 1, 14),
            ),
        ),
        looks(
            Locus.FACE,
            "Features",
            "features",
            (
                Allele("broad", "broad features", 3, 30),
                Allele("round", "round features", 2, 25),
                Allele("fine", "fine features", 1, 25),
                Allele("sharp", "sharp features", 1, 20),
            ),
        ),
        looks(
            Locus.VOICE,
            "Voice",
            "voice",
            (
                Allele("low", "a low voice", 2, 30),
                Allele("warm", "a warm voice", 2, 30),
                Allele("clear", "a clear voice", 1, 25),
                Allele("high", "a high voice", 1, 15),
            ),
        ),
        looks(
            Locus.PROPORTIONS,
            "Proportions",
            "proportions",
            (Allele("compact", "compact", 1, 25, -1), Allele("even", "evenly proportioned", 1, 50, 0), Allele("long", "long-limbed", 1, 25, 1)),
            graded=True,
        ),
        looks(
            Locus.MARKINGS,
            "Markings",
            "markings",
            (
                Allele("plain", "unmarked", 1, 55),
                Allele("flecked", "flecked", 2, 20),
                Allele("patterned", "patterned", 3, 15),
                Allele("banded", "banded", 3, 10),
            ),
        ),
        graded(Locus.MUSCLE, "Muscle", LocusGroup.BODY, ("light of muscle", "of common muscle", "heavily muscled")),
        graded(Locus.STAMINA, "Stamina", LocusGroup.BODY, ("quick to tire", "of common stamina", "tireless")),
        graded(Locus.AGILITY, "Agility", LocusGroup.BODY, ("slow of reflex", "of common reflexes", "quick of reflex")),
        graded(Locus.METABOLISM, "Metabolism", LocusGroup.BODY, ("slow-burning", "of common metabolism", "fast-burning")),
        graded(Locus.COLD_TOLERANCE, "Cold tolerance", LocusGroup.BODY, ("suffers in the cold", "of common cold tolerance", "at ease in the cold")),
        graded(Locus.HEAT_TOLERANCE, "Heat tolerance", LocusGroup.BODY, ("suffers in the heat", "of common heat tolerance", "at ease in the heat")),
        graded(Locus.LUNG_CAPACITY, "Breath", LocusGroup.BODY, ("short of breath", "of common breath", "deep of breath")),
        graded(Locus.BONE_DENSITY, "Bone", LocusGroup.BODY, ("light of bone", "of common bone", "heavy of bone")),
        graded(Locus.WOUND_HEALING, "Wound healing", LocusGroup.BODY, ("slow to heal", "heals at a common pace", "quick to heal")),
        graded(Locus.AGEING_PACE, "Ageing pace", LocusGroup.BODY, ("slow to age", "ages at a common pace", "quick to age")),
        graded(Locus.PAIN_SENSE, "Pain sense", LocusGroup.BODY, ("dull to pain", "of common pain sense", "keen to pain")),
        graded(Locus.SIGHT, "Sight", LocusGroup.SENSE, ("dim-sighted", "of common sight", "sharp-sighted")),
        graded(Locus.HEARING, "Hearing", LocusGroup.SENSE, ("hard of hearing", "of common hearing", "sharp of hearing")),
        graded(Locus.SMELL, "Smell", LocusGroup.SENSE, ("dull of smell", "of common smell", "keen of smell")),
        graded(Locus.TASTE, "Taste", LocusGroup.SENSE, ("dull of taste", "of common taste", "fine of taste")),
        graded(Locus.NIGHT_VISION, "Night vision", LocusGroup.SENSE, ("blind in the dark", "of common night vision", "sees well in the dark")),
        graded(Locus.EXCITABILITY, "Excitability", LocusGroup.TEMPERAMENT, ("hard to stir", "of common excitability", "easily stirred")),
        graded(Locus.SOCIABILITY, "Sociability", LocusGroup.TEMPERAMENT, ("drawn to solitude", "of common sociability", "drawn to company")),
        graded(Locus.RISK_APPETITE, "Risk appetite", LocusGroup.TEMPERAMENT, ("shy of risk", "of common daring", "drawn to risk")),
        graded(Locus.ATTENTION, "Attention", LocusGroup.TEMPERAMENT, ("easily distracted", "of common attention", "steady of attention")),
        graded(Locus.STRESS_RESPONSE, "Stress response", LocusGroup.TEMPERAMENT, ("calm under strain", "of common steadiness", "shaken by strain")),
        graded(Locus.MEMORY, "Memory", LocusGroup.APTITUDE, ("forgetful", "of common memory", "of long memory")),
        graded(Locus.SPATIAL_SENSE, "Spatial sense", LocusGroup.APTITUDE, ("easily lost", "of common sense of place", "sure of place and shape")),
        graded(Locus.LANGUAGE_EASE, "Language ease", LocusGroup.APTITUDE, ("slow with tongues", "of common ease with tongues", "quick with tongues")),
        graded(Locus.NUMBER_SENSE, "Number sense", LocusGroup.APTITUDE, ("slow with numbers", "of common number sense", "quick with numbers")),
        graded(Locus.MUSICAL_EAR, "Musical ear", LocusGroup.APTITUDE, ("deaf to tune", "of common ear", "fine of ear")),
        graded(Locus.COORDINATION, "Coordination", LocusGroup.APTITUDE, ("clumsy of hand", "of common coordination", "deft of hand")),
        leaning(
            Locus.LONGEVITY,
            "Longevity",
            (Allele("common", "common span", 2, 80, 0), Allele("brief", "brief-lived", 1, 10, -1), Allele("enduring", "long-lived", 1, 10, 1)),
        ),
        leaning(
            Locus.TWINNING,
            "Twinning",
            (Allele("common", "single births", 2, 90, 0), Allele("twinning", "given to twins", 1, 10, 1)),
        ),
        leaning(
            Locus.FERTILITY,
            "Fertility",
            (Allele("common", "common fertility", 2, 80, 0), Allele("barren", "low fertility", 1, 10, -1), Allele("fruitful", "high fertility", 1, 10, 1)),
        ),
        leaning(
            Locus.DISEASE_RESISTANCE,
            "Disease resistance",
            (
                Allele("common", "common resistance", 2, 75, 0),
                Allele("frail", "frail against sickness", 1, 12, -1),
                Allele("hardy", "hardy against sickness", 1, 13, 1),
            ),
        ),
        leaning(Locus.MADNESS, "Madness", (Allele("sound", "sound of mind", 2, 92, 0), Allele("touched", "prone to madness", 1, 8, 1))),
        leaning(
            Locus.COLOUR_BLINDNESS,
            "Colour sight",
            (Allele("seeing", "full colour sight", 2, 91, 0), Allele("blind", "colour-blind", 1, 6, 1), Allele("keen", "keen colour sight", 1, 3, -1)),
            visible=True,
        ),
        leaning(Locus.GIANT_BLOOD, "Giant blood", (Allele("none", "no giant blood", 1, 97, 0), Allele("giant", "giant blood", 2, 3, 1)), visible=True),
        leaning(Locus.DIVINE_BLOOD, "Divine blood", (Allele("none", "mortal blood", 1, 100, 0), Allele("divine", "divine blood", 2, 0, 1)), visible=True),
        leaning(Locus.CURSE_MARKER, "Curse marker", (Allele("clean", "clean blood", 1, 99, 0), Allele("marked", "cursed blood", 2, 1, 1))),
        *(gift(school) for school in MagicSchool),
    )
}

LOOKS_LOCI = tuple(locus for locus, spec in LOCI.items() if spec.group is LocusGroup.LOOKS)
GIFT_LOCI_ORDER = tuple(locus for locus, spec in LOCI.items() if spec.group is LocusGroup.GIFT)
VISIBLE_LOCI = tuple(locus for locus, spec in LOCI.items() if spec.visible)
HARMFUL: dict[Locus, str] = {Locus.MADNESS: "touched", Locus.COLOUR_BLINDNESS: "blind", Locus.DISEASE_RESISTANCE: "frail", Locus.LONGEVITY: "brief"}

LOCUS_GROUP_LABELS: Mapping[LocusGroup, str] = total(
    LocusGroup,
    {
        LocusGroup.LOOKS: "Looks",
        LocusGroup.BODY: "Body and constitution",
        LocusGroup.SENSE: "Senses",
        LocusGroup.TEMPERAMENT: "Temperament",
        LocusGroup.APTITUDE: "Aptitudes",
        LocusGroup.PREDISPOSITION: "Predispositions",
        LocusGroup.GIFT: "Magical gift",
    },
)

GIFT_STANCE_LABELS: dict[GiftStance, str] = {
    GiftStance.HONOURED: "Honoured",
    GiftStance.FEARED: "Feared",
    GiftStance.PERSECUTED: "Persecuted",
    GiftStance.TAXED: "Taxed",
}

HOUSEHOLD_ROLE_LABELS: dict[HouseholdRole, str] = {
    HouseholdRole.HEAD: "Head",
    HouseholdRole.SPOUSE: "Spouse",
    HouseholdRole.HEIR: "Heir",
    HouseholdRole.DEPENDENT: "Dependent",
    HouseholdRole.CARER: "Carer",
    HouseholdRole.SERVANT: "Servant",
    HouseholdRole.WARD: "Ward",
    HouseholdRole.LODGER: "Lodger",
}

HOUSEHOLD_DECISION_LABELS: dict[HouseholdDecision, str] = {
    HouseholdDecision.MARRY: "Arranged a marriage",
    HouseholdDecision.APPRENTICE: "Apprenticed a child",
    HouseholdDecision.MIGRATE: "Moved away",
    HouseholdDecision.RENOVATE: "Improved the home",
    HouseholdDecision.TAKE_LODGER: "Took in a lodger",
    HouseholdDecision.HIRE_SERVANT: "Hired a servant",
    HouseholdDecision.DISMISS_SERVANT: "Let a servant go",
    HouseholdDecision.SELL_FURNISHING: "Sold a furnishing",
    HouseholdDecision.LEND: "Lent at interest",
}


CLASS_INCOME_PCT: dict[SocialClass, int] = {
    SocialClass.NOBLE: 400,
    SocialClass.MERCHANT: 250,
    SocialClass.PRIEST: 150,
    SocialClass.SCRIBE: 150,
    SocialClass.ARTISAN: 130,
    SocialClass.WARRIOR: 110,
    SocialClass.FARMER: 100,
    SocialClass.MONASTIC: 50,
    SocialClass.WORKER: 90,
    SocialClass.PROFESSIONAL: 220,
    SocialClass.OFFICIAL: 180,
    SocialClass.CITIZEN: 110,
    SocialClass.UNEMPLOYED: 25,
    SocialClass.SERF_OR_SLAVE: 40,
    SocialClass.OUTCAST: 20,
}


@dataclass(frozen=True)
class DwellingSpec:
    key: DwellingKind
    label: str
    level: HousingLevel
    rooms: int
    quality: int
    upkeep: int
    mobile: bool = False
    floods: Callable[[Rules], int] | None = None
    cold: Callable[[Rules], int] | None = None
    stores: bool = False
    since_w52: bool = False
    bodily: bool = False


D = DwellingKind
DWELLINGS: Mapping[DwellingKind, DwellingSpec] = total(
    DwellingKind,
    {
        D.HUT: DwellingSpec(D.HUT, "Hut", HousingLevel.HUT, 1, 25, 1),
        D.LONGHOUSE: DwellingSpec(D.LONGHOUSE, "Longhouse", HousingLevel.HOUSE, 3, 40, 2),
        D.TOWNHOUSE: DwellingSpec(D.TOWNHOUSE, "Townhouse", HousingLevel.TOWNHOUSE, 4, 55, 4),
        D.MANOR: DwellingSpec(D.MANOR, "Manor", HousingLevel.MANOR, 10, 72, 8, stores=True),
        D.PALACE: DwellingSpec(D.PALACE, "Palace", HousingLevel.MANOR, 30, 90, 18, stores=True),
        D.TENT: DwellingSpec(D.TENT, "Tent", HousingLevel.HUT, 1, 20, 1, mobile=True),
        D.CAVE: DwellingSpec(D.CAVE, "Cave", HousingLevel.HUT, 2, 15, 0, cold=lambda rules: rules.dwellings.burrow_cold_cut_pct // 2),
        D.SHIP: DwellingSpec(D.SHIP, "Ship", HousingLevel.SHIP_BERTH, 2, 35, 3, mobile=True),
        D.TOWER: DwellingSpec(D.TOWER, "Tower", HousingLevel.TOWNHOUSE, 6, 60, 6),
        D.APARTMENT: DwellingSpec(D.APARTMENT, "Apartment", HousingLevel.APARTMENT, 2, 50, 3),
        D.FARMSTEAD: DwellingSpec(D.FARMSTEAD, "Farmstead", HousingLevel.HOUSE, 4, 45, 2, stores=True, since_w52=True),
        D.STILT_HOUSE: DwellingSpec(
            D.STILT_HOUSE, "House on stilts", HousingLevel.HOUSE, 2, 40, 2, floods=lambda rules: rules.dwellings.stilt_flood_cut_pct, since_w52=True
        ),
        D.BURROW: DwellingSpec(
            D.BURROW, "Burrow", HousingLevel.HUT, 3, 35, 1, cold=lambda rules: rules.dwellings.burrow_cold_cut_pct, since_w52=True, bodily=True
        ),
        D.NEST: DwellingSpec(D.NEST, "Nest", HousingLevel.HUT, 1, 30, 1, since_w52=True, bodily=True),
        D.SUBMERGED: DwellingSpec(
            D.SUBMERGED,
            "Dwelling under water",
            HousingLevel.HOUSE,
            2,
            40,
            2,
            floods=lambda rules: rules.dwellings.stilt_flood_cut_pct,
            since_w52=True,
            bodily=True,
        ),
    },
)
BODILY_DWELLING_KEYS = frozenset(kind.value for kind, spec in DWELLINGS.items() if spec.bodily)
APTITUDE_LOCI = tuple(locus for locus, spec in LOCI.items() if spec.group is LocusGroup.APTITUDE)
TEMPERAMENT_LOCI = tuple(locus for locus, spec in LOCI.items() if spec.group is LocusGroup.TEMPERAMENT)


def dwelling_spec(key: str | None) -> DwellingSpec | None:
    known = {kind.value for kind in DwellingKind}
    return DWELLINGS[DwellingKind(key)] if key is not None and key in known else None
