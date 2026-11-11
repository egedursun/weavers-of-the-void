from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger, FormativeKind, HeraldicCharge, MobTarget, Tincture
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.mind import ValueAxis

A = CollectiveActKind
T = CollectiveTrigger
ANGER = "anger"
ANXIETY = "anxiety"
FERVOUR = "fervour"


@dataclass(frozen=True)
class TriggerSpec:
    act: CollectiveActKind
    mood: str
    target: MobTarget
    text: str


TRIGGERS = total(
    CollectiveTrigger,
    {
        T.PRICE_SPIKE: TriggerSpec(A.RIOT, ANGER, MobTarget.GRANARY, "the price of food"),
        T.EXECUTION: TriggerSpec(A.RIOT, ANGER, MobTarget.PALACE, "an execution"),
        T.SERMON: TriggerSpec(A.REVIVAL, FERVOUR, MobTarget.TEMPLE, "a preacher's call"),
        T.OMEN: TriggerSpec(A.PANIC, ANXIETY, MobTarget.GATE, "an omen"),
        T.RUMOUR: TriggerSpec(A.PANIC, ANXIETY, MobTarget.SCAPEGOAT, "a rumour"),
        T.FIRE: TriggerSpec(A.PANIC, ANXIETY, MobTarget.GATE, "a fire"),
        T.PLAGUE: TriggerSpec(A.PROCESSION, FERVOUR, MobTarget.SCAPEGOAT, "a plague"),
        T.BEAST: TriggerSpec(A.PANIC, ANXIETY, MobTarget.GATE, "a beast at hand"),
        T.ECLIPSE: TriggerSpec(A.PANIC, ANXIETY, MobTarget.TEMPLE, "an eclipse"),
        T.MIRACLE: TriggerSpec(A.CONVERSION, FERVOUR, MobTarget.TEMPLE, "a miracle"),
        T.FAMINE: TriggerSpec(A.RIOT, ANGER, MobTarget.GRANARY, "hunger"),
        T.UNPAID_WAGES: TriggerSpec(A.STRIKE, ANGER, MobTarget.WORKSHOP, "unpaid wages"),
    },
)
ACT_TEXT = total(
    CollectiveActKind,
    {
        A.RIOT: "rioted",
        A.PANIC: "fled in panic",
        A.LYNCHING: "lynched a scapegoat",
        A.CONVERSION: "turned to a new faith",
        A.REVOLT: "rose in revolt",
        A.STRIKE: "laid down their work",
        A.PROCESSION: "marched in procession",
        A.REVIVAL: "rose in a revival",
    },
)
ANGRY_ACTS = frozenset({A.RIOT, A.LYNCHING, A.REVOLT, A.STRIKE})
FAITH_ACTS = frozenset({A.CONVERSION, A.PROCESSION, A.REVIVAL})
ACT_COLLECTION = total(
    CollectiveActKind,
    {
        A.RIOT: CollectionKind.RIOT,
        A.LYNCHING: CollectionKind.RIOT,
        A.STRIKE: CollectionKind.RIOT,
        A.PANIC: CollectionKind.PANIC,
        A.REVOLT: CollectionKind.INSURRECTION,
        A.CONVERSION: CollectionKind.CONVERSION_WAVE,
        A.PROCESSION: CollectionKind.PROCESSION,
        A.REVIVAL: CollectionKind.MOVEMENT,
    },
)

F = FormativeKind
V = ValueAxis
FORMATIVE_SHIFTS = total(
    FormativeKind,
    {
        F.GREAT_WAR: ((V.MARTIAL, 1), (V.MERCY, 1)),
        F.VICTORY: ((V.HONOUR, 1), (V.COMPETITION, 1)),
        F.DEFEAT: ((V.LOYALTY, -1), (V.TRADITION, -1)),
        F.PLAGUE: ((V.PIETY, 1), (V.SUPERSTITION, 1)),
        F.FAMINE: ((V.WEALTH, 1), (V.KINSHIP, 1)),
        F.GOLDEN_AGE: ((V.LEISURE, 1), (V.XENOPHILIA, 1)),
        F.CONQUEST: ((V.HIERARCHY, -1), (V.LOYALTY, 1)),
    },
)
COLLECTION_FORMATIVE = MappingProxyType(
    {
        CollectionKind.WAR: F.GREAT_WAR,
        CollectionKind.SIEGE: F.GREAT_WAR,
        CollectionKind.PLAGUE: F.PLAGUE,
        CollectionKind.FAMINE: F.FAMINE,
        CollectionKind.OCCUPATION: F.CONQUEST,
    }
)
LEGACY_TINCTURES = MappingProxyType(
    {
        "or": Tincture.GOLD,
        "argent": Tincture.SILVER,
        "gules": Tincture.RED,
        "azure": Tincture.BLUE,
        "vert": Tincture.GREEN,
        "sable": Tincture.BLACK,
        "purpure": Tincture.PURPLE,
        "tenne": Tincture.ORANGE,
    }
)
HERALDIC_NAMES = total(
    Tincture,
    {
        Tincture.GOLD: "or",
        Tincture.SILVER: "argent",
        Tincture.RED: "gules",
        Tincture.BLUE: "azure",
        Tincture.GREEN: "vert",
        Tincture.BLACK: "sable",
        Tincture.PURPLE: "purpure",
        Tincture.ORANGE: "tenne",
    },
)
METALS = frozenset({Tincture.GOLD, Tincture.SILVER})
VALUE_CHARGES = total(
    ValueAxis,
    {
        V.HONOUR: HeraldicCharge.HAND,
        V.TRADITION: HeraldicCharge.TOWER,
        V.HIERARCHY: HeraldicCharge.CROWN,
        V.MARTIAL: HeraldicCharge.SWORD,
        V.PIETY: HeraldicCharge.STAR,
        V.PURITY: HeraldicCharge.SUN,
        V.KINSHIP: HeraldicCharge.TREE,
        V.MERCY: HeraldicCharge.HAND,
        V.KNOWLEDGE: HeraldicCharge.EYE,
        V.WEALTH: HeraldicCharge.KEY,
        V.NATURE: HeraldicCharge.TREE,
        V.SUPERSTITION: HeraldicCharge.MOON,
        V.XENOPHILIA: HeraldicCharge.WAVE,
        V.DEATH: HeraldicCharge.MOON,
        V.LAW: HeraldicCharge.KEY,
        V.LOYALTY: HeraldicCharge.HAND,
        V.FAMILY: HeraldicCharge.TREE,
        V.FRIENDSHIP: HeraldicCharge.HAND,
        V.TRUTH: HeraldicCharge.SUN,
        V.CRAFTSMANSHIP: HeraldicCharge.WHEEL,
        V.ARTWORK: HeraldicCharge.STAR,
        V.COMPETITION: HeraldicCharge.BEAST,
        V.PERSEVERANCE: HeraldicCharge.TOWER,
        V.LEISURE: HeraldicCharge.BIRD,
    },
)
