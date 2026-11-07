from dataclasses import dataclass

from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.genetics import GIFT_LOCI, DwellingKind, GiftStance, HouseholdDecision, HouseholdRole, Locus, LocusGroup
from aerona.domain.enums.society import SocialClass


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
        return next((allele for allele in self.alleles if allele.key == key), self.alleles[0])

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(allele.key for allele in self.alleles)


def looks(locus: Locus, label: str, noun: str, alleles: tuple[Allele, ...], *, graded: bool = False) -> LocusSpec:
    return LocusSpec(locus, label, LocusGroup.LOOKS, alleles, graded=graded, visible=True, noun=noun)


def leaning(locus: Locus, label: str, alleles: tuple[Allele, ...], *, visible: bool = False) -> LocusSpec:
    return LocusSpec(locus, label, LocusGroup.PREDISPOSITION, alleles, visible=visible)


def gift(school: MagicSchool) -> LocusSpec:
    label = school.value.replace("elemental_", "").replace("_", " ")
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
        leaning(
            Locus.LONGEVITY,
            "Longevity",
            (Allele("common", "common span", 2, 80, 0), Allele("brief", "brief-lived", 1, 10, -1), Allele("enduring", "long-lived", 1, 10, 1)),
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
            Locus.COLOUR_BLINDNESS, "Colour sight", (Allele("seeing", "full colour sight", 2, 94, 0), Allele("blind", "colour-blind", 1, 6, 1)), visible=True
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

LOCUS_GROUP_LABELS: dict[LocusGroup, str] = {LocusGroup.LOOKS: "Looks", LocusGroup.PREDISPOSITION: "Predispositions", LocusGroup.GIFT: "Magical gift"}

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
    SocialClass.SERF_OR_SLAVE: 40,
    SocialClass.OUTCAST: 20,
}


@dataclass(frozen=True)
class DwellingSpec:
    kind: DwellingKind
    label: str
    rooms: int
    quality: int
    upkeep: int
    mobile: bool = False


DWELLINGS: dict[DwellingKind, DwellingSpec] = {
    spec.kind: spec
    for spec in (
        DwellingSpec(DwellingKind.HUT, "Hut", 1, 25, 1),
        DwellingSpec(DwellingKind.LONGHOUSE, "Longhouse", 3, 40, 2),
        DwellingSpec(DwellingKind.TOWNHOUSE, "Townhouse", 4, 55, 4),
        DwellingSpec(DwellingKind.MANOR, "Manor", 10, 72, 8),
        DwellingSpec(DwellingKind.PALACE, "Palace", 30, 90, 18),
        DwellingSpec(DwellingKind.TENT, "Tent", 1, 20, 1, mobile=True),
        DwellingSpec(DwellingKind.CAVE, "Cave", 2, 15, 0),
        DwellingSpec(DwellingKind.SHIP, "Ship", 2, 35, 3, mobile=True),
        DwellingSpec(DwellingKind.TOWER, "Tower", 6, 60, 6),
    )
}
