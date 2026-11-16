from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.catalog.mind_split import fac, lean
from aerona.domain.enums.mind import (
    Facet,
    FearKind,
    FocusKind,
    InspirationKind,
    LifeGoal,
    NeedKind,
    PerkKind,
    SkillFamily,
    ValueAxis,
    WantKind,
)

G = LifeGoal
W = WantKind
F = FearKind
K = FocusKind
P = PerkKind
N = NeedKind


@dataclass(frozen=True)
class GoalSpec:
    label: str
    beliefs: MappingProxyType[ValueAxis, int]
    facets: MappingProxyType[Facet, int]
    milestones: tuple[str, str, str]
    physical: bool = False


def goal(label: str, beliefs: dict[str, int], facets: dict[str, int], milestones: tuple[str, str, str], *, physical: bool = False) -> GoalSpec:
    return GoalSpec(label, lean(**beliefs), fac(**facets), milestones, physical)


GOALS: MappingProxyType[LifeGoal, GoalSpec] = MappingProxyType(
    {
        G.RULE_A_REALM: goal(
            "Rule a realm", {"hierarchy": 40, "competition": 20}, {"ambition": 50, "assertiveness": 30}, ("Hold an office", "Rule a town", "Rule a realm")
        ),
        G.FOUND_A_HOUSE: goal(
            "Found a house", {"family": 40, "hierarchy": 20}, {"ambition": 40}, ("Rise among the notable", "Lead a household", "Found a house")
        ),
        G.MASTER_A_CRAFT: goal(
            "Master a craft",
            {"craftsmanship": 50},
            {"thoroughness": 40, "perseverance": 30},
            ("Learn the craft", "Become a fellow of the craft", "Become a master"),
            physical=True,
        ),
        G.CREATE_A_MASTERWORK: goal(
            "Create a masterwork",
            {"artwork": 40, "craftsmanship": 30},
            {"artistic_inclination": 50, "imagination": 30},
            ("Find the craft", "Hone the hand", "Make a masterwork"),
        ),
        G.BECOME_A_LEGEND: goal(
            "Become a legend", {"honour": 30, "competition": 30}, {"vanity": 40, "excitement_seeking": 30}, ("Be noticed", "Be renowned", "Be a legend")
        ),
        G.RAISE_A_FAMILY: goal("Raise a large family", {"family": 60}, {"friendliness": 30}, ("A first child", "A growing family", "A large family")),
        G.SEE_THE_WORLD: goal("See the world", {"xenophilia": 50}, {"curiosity": 40, "excitement_seeking": 40}, ("Leave home", "Travel far", "See the world")),
        G.ACHIEVE_HOLINESS: goal(
            "Achieve holiness", {"piety": 60, "purity": 20}, {"sense_of_duty": 30, "discipline": 30}, ("Keep the faith", "Serve the faith", "Be held holy")
        ),
        G.GAIN_WEALTH: goal("Gain wealth", {"wealth": 60}, {"greed": 50}, ("Be comfortable", "Be rich", "Be very rich")),
        G.AVENGE_KIN: goal(
            "Avenge kin", {"family": 40, "honour": 30}, {"anger": 40, "gratitude": -20}, ("Remember the wrong", "Seek the killer", "See the killer dead")
        ),
        G.KNOW_A_TRUTH: goal(
            "Know a truth", {"knowledge": 60, "truth": 20}, {"curiosity": 50, "abstraction": 40}, ("Begin to study", "Learn deeply", "Know the truth")
        ),
        G.DEFEAT_A_BEAST: goal(
            "Defeat a great beast",
            {"martial": 40, "honour": 20},
            {"excitement_seeking": 40, "caution": -30},
            ("Train for the hunt", "Hunt the wild", "Defeat a great beast"),
            physical=True,
        ),
        G.SERVE_A_GOD: goal("Serve a god", {"piety": 50, "loyalty": 30}, {"sense_of_duty": 40}, ("Worship", "Serve", "Be chosen")),
        G.LIVE_IN_PEACE: goal(
            "Live in peace", {"leisure": 40, "mercy": 20, "martial": -30}, {"anxiety": 20, "cooperation": 30}, ("Find calm", "Keep calm", "Live in peace")
        ),
        G.FIND_LOVE: goal("Find love", {"family": 30, "friendship": 30}, {"friendliness": 40, "imagination": 20}, ("Long for love", "Be courted", "Find love")),
    }
)


@dataclass(frozen=True)
class WantSpec:
    label: str
    needs: tuple[NeedKind, ...]


WANTS: MappingProxyType[WantKind, WantSpec] = MappingProxyType(
    {
        W.MARRY: WantSpec("Marry", (N.ROMANCE, N.FAMILY)),
        W.GAIN_OFFICE: WantSpec("Gain an office", (N.STATUS,)),
        W.FINE_WEAPON: WantSpec("Own a fine weapon", (N.FIGHTING,)),
        W.VISIT_A_SHRINE: WantSpec("Visit a shrine", (N.FAITH,)),
        W.LEARN_A_SKILL: WantSpec("Learn a skill", (N.LEARNING, N.CREATING)),
        W.GAIN_WEALTH: WantSpec("Gain wealth", (N.WEALTH, N.COMFORT)),
        W.HAVE_A_CHILD: WantSpec("Have a child", (N.FAMILY,)),
        W.TRAVEL: WantSpec("Travel", (N.ADVENTURE, N.NATURE)),
        W.WIN_GLORY: WantSpec("Win glory", (N.FIGHTING, N.STATUS)),
        W.MAKE_PEACE: WantSpec("See peace made", (N.SAFETY, N.ORDER)),
        W.AVENGE: WantSpec("Take revenge", ()),
        W.FIND_A_TEACHER: WantSpec("Find a teacher", (N.PURPOSE, N.LEARNING)),
    }
)


@dataclass(frozen=True)
class FearSpec:
    label: str
    facets: MappingProxyType[Facet, int]


FEARS: MappingProxyType[FearKind, FearSpec] = MappingProxyType(
    {
        F.DEATH: FearSpec("Death", fac(anxiety=40, vulnerability=30)),
        F.WAR: FearSpec("War", fac(anxiety=30, caution=30, assertiveness=-20)),
        F.PLAGUE: FearSpec("Plague", fac(anxiety=40, tolerance_of_difference=-20)),
        F.BEASTS: FearSpec("Beasts", fac(anxiety=30, caution=30)),
        F.LOSING_A_CHILD: FearSpec("Losing a child", fac(anxiety=30, friendliness=20)),
        F.POVERTY: FearSpec("Poverty", fac(anxiety=20, greed=30)),
        F.SHAME: FearSpec("Shame", fac(self_consciousness=50, vanity=20)),
        F.DARK: FearSpec("The dark", fac(anxiety=30, imagination=30)),
    }
)


@dataclass(frozen=True)
class PerkSpec:
    focus: FocusKind
    label: str
    stat: str
    amount: int
    level: int


@dataclass(frozen=True)
class FocusSpec:
    label: str
    families: tuple[SkillFamily, ...]
    perks: tuple[PerkKind, ...] = field(default=())


SF = SkillFamily
FOCUSES: MappingProxyType[FocusKind, FocusSpec] = MappingProxyType(
    {
        K.DIPLOMACY: FocusSpec("Diplomacy", (SF.SOCIAL,), (P.SILVER_TONGUE, P.PEACEMAKER, P.WELL_CONNECTED, P.ENVOYS_PATIENCE, P.BELOVED)),
        K.MARTIAL: FocusSpec("Martial", (SF.COMBAT, SF.COMMAND), (P.HARDENED, P.SWIFT_BLADE, P.IRON_NERVE, P.BATTLE_EYE, P.WARLORD)),
        K.STEWARDSHIP: FocusSpec("Stewardship", (SF.SURVIVAL,), (P.LEDGER_MIND, P.STEADY_HAND, P.PRUDENT, P.BUILDER, P.GRANARY_KEEPER)),
        K.INTRIGUE: FocusSpec("Intrigue", (SF.SOCIAL,), (P.SHADOW_STEP, P.KEEN_EAR, P.MASK, P.NETWORK_BUILDER, P.COLD_EYE)),
        K.LEARNING: FocusSpec("Learning", (SF.KNOWLEDGE,), (P.QUICK_STUDY, P.DEEP_MEMORY, P.LUCID, P.SAGES_INSIGHT, P.POLYMATH)),
        K.PIETY: FocusSpec("Piety", (SF.FAITH,), (P.DEVOUT, P.SERENE, P.FAITHFUL_VOICE, P.VISIONARY, P.HALLOWED)),
        K.CRAFT: FocusSpec("Craft", (SF.CRAFT,), (P.SURE_HANDS, P.INVENTIVE, P.TIRELESS, P.EYE_FOR_BEAUTY, P.MASTERS_TOUCH)),
        K.LEISURE: FocusSpec("Leisure", (), (P.GOOD_COMPANY, P.CAREFREE, P.REVELLER, P.CHARMING, P.JOYFUL_SPIRIT)),
    }
)

PERK_LEVELS = (20, 35, 50, 65, 80)
PERK_STATS: MappingProxyType[PerkKind, tuple[str, str, int]] = MappingProxyType(
    {
        P.SILVER_TONGUE: ("Silver tongue", "charisma", 4),
        P.PEACEMAKER: ("Peacemaker", "wisdom", 3),
        P.WELL_CONNECTED: ("Well connected", "charisma", 3),
        P.ENVOYS_PATIENCE: ("Envoy's patience", "willpower", 3),
        P.BELOVED: ("Beloved", "charisma", 5),
        P.HARDENED: ("Hardened", "endurance", 4),
        P.SWIFT_BLADE: ("Swift blade", "agility", 4),
        P.IRON_NERVE: ("Iron nerve", "willpower", 4),
        P.BATTLE_EYE: ("Battle eye", "perception", 4),
        P.WARLORD: ("Warlord", "strength", 5),
        P.LEDGER_MIND: ("Ledger mind", "intellect", 3),
        P.STEADY_HAND: ("Steady hand", "willpower", 3),
        P.PRUDENT: ("Prudent", "wisdom", 4),
        P.BUILDER: ("Builder", "endurance", 3),
        P.GRANARY_KEEPER: ("Granary keeper", "wisdom", 5),
        P.SHADOW_STEP: ("Shadow step", "agility", 3),
        P.KEEN_EAR: ("Keen ear", "perception", 4),
        P.MASK: ("Mask", "charisma", 3),
        P.NETWORK_BUILDER: ("Network builder", "intellect", 4),
        P.COLD_EYE: ("Cold eye", "willpower", 5),
        P.QUICK_STUDY: ("Quick study", "intellect", 3),
        P.DEEP_MEMORY: ("Deep memory", "intellect", 3),
        P.LUCID: ("Lucid", "wisdom", 4),
        P.SAGES_INSIGHT: ("Sage's insight", "perception", 4),
        P.POLYMATH: ("Polymath", "intellect", 5),
        P.DEVOUT: ("Devout", "willpower", 3),
        P.SERENE: ("Serene", "wisdom", 3),
        P.FAITHFUL_VOICE: ("Faithful voice", "charisma", 4),
        P.VISIONARY: ("Visionary", "perception", 4),
        P.HALLOWED: ("Hallowed", "charisma", 5),
        P.SURE_HANDS: ("Sure hands", "agility", 3),
        P.INVENTIVE: ("Inventive", "creativity", 3),
        P.TIRELESS: ("Tireless", "endurance", 4),
        P.EYE_FOR_BEAUTY: ("Eye for beauty", "creativity", 4),
        P.MASTERS_TOUCH: ("Master's touch", "creativity", 5),
        P.GOOD_COMPANY: ("Good company", "charisma", 3),
        P.CAREFREE: ("Carefree", "willpower", 3),
        P.REVELLER: ("Reveller", "endurance", 3),
        P.CHARMING: ("Charming", "charisma", 4),
        P.JOYFUL_SPIRIT: ("Joyful spirit", "creativity", 4),
    }
)

PERKS: MappingProxyType[PerkKind, PerkSpec] = MappingProxyType(
    {
        perk: PerkSpec(focus, PERK_STATS[perk][0], PERK_STATS[perk][1], PERK_STATS[perk][2], PERK_LEVELS[index])
        for focus, spec in FOCUSES.items()
        for index, perk in enumerate(spec.perks)
    }
)

INSPIRATION_LABELS: MappingProxyType[InspirationKind, str] = MappingProxyType(
    {
        InspirationKind.MASTERWORK_FEVER: "A fever to make a masterwork",
        InspirationKind.RESEARCH_INSIGHT: "A flash of insight",
        InspirationKind.HEROIC_RESOLVE: "A heroic resolve",
        InspirationKind.ARTISTIC_VISION: "A vision of a work to make",
        InspirationKind.TECHNICAL_BREAKTHROUGH: "A way through a hard problem",
        InspirationKind.SPIRITUAL_INSIGHT: "An insight of the spirit",
    }
)


WANT_VALUES: MappingProxyType[WantKind, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        W.GAIN_OFFICE: lean(hierarchy=40),
        W.WIN_GLORY: lean(martial=40),
        W.LEARN_A_SKILL: lean(knowledge=40),
        W.GAIN_WEALTH: lean(wealth=40),
        W.TRAVEL: lean(xenophilia=40),
        W.VISIT_A_SHRINE: lean(piety=40),
        W.FINE_WEAPON: lean(martial=20, craftsmanship=20),
    }
)
