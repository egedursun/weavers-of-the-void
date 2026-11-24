from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.catalog.art_modes import ART_MODES
from aerona.core.total import total
from aerona.domain.enums.culture import (
    CalendarSlot,
    IdeologyTenet,
    ItemClass,
    LegendArchetype,
    MagicSchool,
    MagicSource,
    RiteEffectKind,
    RiteStage,
    SayingKind,
    TraditionFunction,
)
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.rules.registry import Rules

V = ValueAxis
A = LegendArchetype
K = TraditionFunction
IT = IdeologyTenet
S = MagicSchool
D = Domain
E = RiteEffectKind
SC = SocialClass

LEGEND_MORALS = MappingProxyType(
    {
        A.HERO_QUEST: {V.HONOUR: 10, V.MARTIAL: 5},
        A.MONSTER: {V.MARTIAL: 5, V.XENOPHILIA: -5},
        A.TRICKSTER: {V.TRADITION: -5, V.HIERARCHY: -5},
        A.CREATION: {V.PIETY: 10, V.TRADITION: 5},
        A.WORLD_DISASTER: {V.PIETY: 10, V.NATURE: 5},
        A.BETRAYAL: {V.HONOUR: 10, V.KINSHIP: 5, V.XENOPHILIA: -5},
        A.LOST_GOLDEN_AGE: {V.TRADITION: 10, V.PURITY: 5},
        A.CHOSEN_ONE: {V.PIETY: 5, V.HIERARCHY: 5},
        A.CURSED_LINE: {V.SUPERSTITION: 10, V.KINSHIP: -5},
        A.RETURN_OF_A_RULER: {V.HIERARCHY: 10, V.TRADITION: 5},
        A.HAUNTED_PLACE: {V.SUPERSTITION: 10, V.DEATH: 5},
        A.FOUNDING: {V.TRADITION: 5, V.KINSHIP: 5},
        A.EXILE: {V.XENOPHILIA: 5, V.KINSHIP: -5},
        A.TRANSFORMATION: {V.TRADITION: -5, V.NATURE: 5},
        A.BARGAIN: {V.HONOUR: 5, V.SUPERSTITION: 5},
        A.SACRIFICE: {V.PIETY: 10, V.KINSHIP: 5},
        A.RIVALRY: {V.COMPETITION: 10, V.HONOUR: 5},
        A.DISCOVERY: {V.XENOPHILIA: 5, V.TRADITION: -5},
        A.DECEPTION: {V.HONOUR: 10, V.SUPERSTITION: 5},
        A.UNION: {V.KINSHIP: 10, V.XENOPHILIA: 5},
        A.ASCENT: {V.HIERARCHY: 5, V.COMPETITION: 5},
        A.FALL: {V.HIERARCHY: -5, V.TRADITION: 5},
    }
)

DISTORTED = MappingProxyType(
    {
        V.HONOUR: A.BETRAYAL,
        V.PIETY: A.CHOSEN_ONE,
        V.SUPERSTITION: A.CURSED_LINE,
        V.MARTIAL: A.HERO_QUEST,
        V.TRADITION: A.LOST_GOLDEN_AGE,
        V.HIERARCHY: A.RETURN_OF_A_RULER,
        V.DEATH: A.HAUNTED_PLACE,
    }
)


@dataclass(frozen=True)
class TraditionSpec:
    kind: TraditionFunction
    cost: dict[str, int] = field(default_factory=dict)
    effects: dict[str, int] = field(default_factory=dict)
    values: dict[ValueAxis, int] = field(default_factory=dict)


TRADITIONS = MappingProxyType(
    {
        spec.kind: spec
        for spec in (
            TraditionSpec(K.FESTIVAL, {"food": 2}, {"cohesion": 4, "satisfaction": 3}),
            TraditionSpec(K.FAST, {}, {"piety": 2, "food_saved": 1}, {V.PIETY: 1, V.PURITY: 1}),
            TraditionSpec(K.RITE_OF_PASSAGE, {"food": 1}, {"cohesion": 2}, {V.TRADITION: 1}),
            TraditionSpec(K.TABOO, {}, {"taboo": 1}, {V.PURITY: 1, V.TRADITION: 1}),
            TraditionSpec(K.OFFERING, {"goods": 1}, {"piety": 2}, {V.PIETY: 1}),
            TraditionSpec(K.PILGRIMAGE, {"food": 1}, {"piety": 3}, {V.PIETY: 1}),
            TraditionSpec(K.HOSPITALITY, {}, {"hospitality": 1}, {V.XENOPHILIA: 2, V.HONOUR: 1}),
            TraditionSpec(K.DUEL_CUSTOM, {}, {"duels": 1}, {V.HONOUR: 2, V.MARTIAL: 1}),
            TraditionSpec(K.MOURNING, {}, {"cohesion": 2}, {V.DEATH: 1, V.KINSHIP: 1}),
            TraditionSpec(K.SEASONAL_RITE, {"food": 1}, {"harvest": 1, "cohesion": 2}, {V.NATURE: 1}),
            TraditionSpec(K.MARTIAL_DISPLAY, {}, {"martial": 2}, {V.MARTIAL: 2}),
            TraditionSpec(K.BODY_MARKING, {}, {"scar": 1}, {V.MARTIAL: 1, V.PURITY: -1}),
            TraditionSpec(K.ANCESTRAL_RITE, {"food": 2}, {"placation": 1}, {V.KINSHIP: 1, V.DEATH: 1}),
            TraditionSpec(K.REST_CUSTOM, {}, {"rest": 1}, {V.TRADITION: 1}),
            TraditionSpec(K.VIGIL, {}, {"vigil": 1}, {V.PIETY: 1, V.DEATH: 1}),
            TraditionSpec(K.GIFT_CUSTOM, {"goods": 1}, {"cohesion": 2, "hospitality": 1}, {V.KINSHIP: 1, V.XENOPHILIA: 1}),
            TraditionSpec(K.PURIFICATION, {}, {"piety": 2}, {V.PURITY: 2}),
            TraditionSpec(K.COMMEMORATION, {"food": 1}, {"cohesion": 3}, {V.TRADITION: 2}),
            TraditionSpec(K.COMPETITION, {"food": 1}, {"satisfaction": 2, "martial": 1}, {V.COMPETITION: 2}),
            TraditionSpec(K.FAIR, {"goods": 1}, {"trade": 2, "satisfaction": 1}, {V.WEALTH: 1}),
            TraditionSpec(K.WELCOME, {"food": 1}, {"hospitality": 1, "bonding": 1}, {V.HOSPITALITY: 2, V.XENOPHILIA: 1}),
            TraditionSpec(K.RECONCILIATION, {"goods": 1}, {"bonding": 2, "cohesion": 1}, {V.MERCY: 1, V.KINSHIP: 1}),
            TraditionSpec(K.THANKSGIVING, {"food": 2}, {"satisfaction": 2, "piety": 1, "healing": 1}, {V.PIETY: 1}),
        )
    }
)


@dataclass(frozen=True)
class FunctionSpec:
    slot: CalendarSlot | None
    cost: Callable[[Rules], int]
    festive: bool = False
    absorbable: bool = False
    seer: bool = False
    sleep: bool = False
    defied_by: LawKind | None = None
    tenets: frozenset[IdeologyTenet] = frozenset()


FUNCTIONS: Mapping[TraditionFunction, FunctionSpec] = total(
    TraditionFunction,
    {
        K.FESTIVAL: FunctionSpec(
            CalendarSlot.HARVEST,
            lambda rules: rules.traditions.festival_cost,
            festive=True,
            absorbable=True,
            defied_by=LawKind.SUMPTUARY,
            tenets=frozenset({IT.ASCETICISM}),
        ),
        K.FAST: FunctionSpec(CalendarSlot.HOLY_DAY, lambda rules: rules.traditions.fast_cost, tenets=frozenset({IT.RATIONALISM})),
        K.RITE_OF_PASSAGE: FunctionSpec(None, lambda rules: rules.traditions.rite_of_passage_cost, absorbable=True, seer=True, tenets=frozenset({IT.ANTI_GOD})),
        K.TABOO: FunctionSpec(None, lambda rules: rules.traditions.taboo_cost, tenets=frozenset({IT.COSMOPOLITANISM})),
        K.OFFERING: FunctionSpec(
            CalendarSlot.HOLY_DAY,
            lambda rules: rules.traditions.offering_cost,
            seer=True,
            defied_by=LawKind.WORSHIP_BAN,
            tenets=frozenset({IT.RATIONALISM, IT.ANTI_GOD, IT.CREATORISM}),
        ),
        K.PILGRIMAGE: FunctionSpec(
            CalendarSlot.PILGRIMAGE,
            lambda rules: rules.traditions.pilgrimage_cost,
            defied_by=LawKind.WORSHIP_BAN,
            tenets=frozenset({IT.RATIONALISM, IT.ANTI_GOD}),
        ),
        K.HOSPITALITY: FunctionSpec(
            None, lambda rules: rules.traditions.hospitality_cost, defied_by=LawKind.FOREIGNER_RIGHTS, tenets=frozenset({IT.COSMOPOLITANISM})
        ),
        K.DUEL_CUSTOM: FunctionSpec(
            None, lambda rules: rules.traditions.duel_custom_cost, defied_by=LawKind.PENAL_CODE, tenets=frozenset({IT.EGALITARIANISM, IT.RESTRAINT})
        ),
        K.MOURNING: FunctionSpec(CalendarSlot.REMEMBRANCE, lambda rules: rules.traditions.mourning_cost),
        K.SEASONAL_RITE: FunctionSpec(CalendarSlot.SOWING, lambda rules: rules.traditions.seasonal_rite_cost, festive=True, absorbable=True),
        K.MARTIAL_DISPLAY: FunctionSpec(CalendarSlot.CAMPAIGN, lambda rules: rules.traditions.martial_display_cost, tenets=frozenset({IT.RESTRAINT})),
        K.BODY_MARKING: FunctionSpec(
            None, lambda rules: rules.traditions.body_marking_cost, seer=True, defied_by=LawKind.PENAL_CODE, tenets=frozenset({IT.EGALITARIANISM})
        ),
        K.ANCESTRAL_RITE: FunctionSpec(
            CalendarSlot.REMEMBRANCE,
            lambda rules: rules.traditions.ancestral_rite_cost,
            festive=True,
            absorbable=True,
            defied_by=LawKind.WORSHIP_BAN,
            tenets=frozenset({IT.RATIONALISM, IT.ASCETICISM, IT.CREATORISM}),
        ),
        K.REST_CUSTOM: FunctionSpec(CalendarSlot.NEW_YEAR, lambda rules: rules.traditions.rest_custom_cost, sleep=True),
        K.VIGIL: FunctionSpec(CalendarSlot.HOLY_DAY, lambda rules: rules.traditions.vigil_cost, sleep=True),
        K.GIFT_CUSTOM: FunctionSpec(CalendarSlot.MIDWINTER, lambda rules: rules.traditions.gift_custom_cost),
        K.PURIFICATION: FunctionSpec(CalendarSlot.HOLY_DAY, lambda rules: rules.traditions.purification_cost),
        K.COMMEMORATION: FunctionSpec(CalendarSlot.REMEMBRANCE, lambda rules: rules.traditions.commemoration_cost),
        K.COMPETITION: FunctionSpec(CalendarSlot.MIDSUMMER, lambda rules: rules.traditions.competition_cost),
        K.FAIR: FunctionSpec(CalendarSlot.MARKET, lambda rules: rules.traditions.fair_cost),
        K.WELCOME: FunctionSpec(None, lambda rules: rules.traditions.welcome_cost, absorbable=True),
        K.RECONCILIATION: FunctionSpec(None, lambda rules: rules.traditions.reconciliation_cost),
        K.THANKSGIVING: FunctionSpec(CalendarSlot.HARVEST, lambda rules: rules.traditions.thanksgiving_cost, festive=True, absorbable=True),
    },
)
FESTIVE = frozenset(kind for kind, spec in FUNCTIONS.items() if spec.festive)
ABSORBABLE = frozenset(kind for kind, spec in FUNCTIONS.items() if spec.absorbable)
SEER_RITES = frozenset(kind for kind, spec in FUNCTIONS.items() if spec.seer)
SLEEP_CUSTOMS = frozenset(kind for kind, spec in FUNCTIONS.items() if spec.sleep)
DEFIED_BY: Mapping[TraditionFunction, LawKind] = MappingProxyType({kind: spec.defied_by for kind, spec in FUNCTIONS.items() if spec.defied_by is not None})
CREED_DEFIES: Mapping[IdeologyTenet, frozenset[TraditionFunction]] = MappingProxyType(
    {tenet: frozenset(kind for kind, spec in FUNCTIONS.items() if tenet in spec.tenets) for tenet in IdeologyTenet}
)
SLEEP_TEXTS: Mapping[TraditionFunction, tuple[str, str]] = MappingProxyType(
    {
        K.REST_CUSTOM: ("The Midday Rest of {name}", "Under a day of {hours:hour|hours} the work stops in the middle of the day and the folk rest."),
        K.VIGIL: ("The Long Night Vigil of {name}", "Through a night of {hours:hour|hours} some keep watch while the rest sleep in turns."),
    }
)
SLOT_NAMED = (K.COMMEMORATION, K.FAIR)
STAGE_SLOTS: Mapping[RiteStage, CalendarSlot | None] = total(
    RiteStage,
    {
        RiteStage.BIRTH: None,
        RiteStage.NAMING: CalendarSlot.NEW_YEAR,
        RiteStage.COMING_OF_AGE: None,
        RiteStage.UNION: None,
        RiteStage.ELDERHOOD: None,
        RiteStage.DEATH: CalendarSlot.REMEMBRANCE,
        RiteStage.INITIATION: None,
        RiteStage.DEPARTURE: None,
    },
)


def slot_fit(kind: TraditionFunction, stage: RiteStage | None) -> CalendarSlot | None:
    return STAGE_SLOTS[stage] if kind is TraditionFunction.RITE_OF_PASSAGE and stage is not None else FUNCTIONS[kind].slot


STAGES = total(
    RiteStage,
    {
        RiteStage.BIRTH: TraditionSpec(K.RITE_OF_PASSAGE, {"food": 1}, {"cohesion": 2}, {V.KINSHIP: 1}),
        RiteStage.NAMING: TraditionSpec(K.RITE_OF_PASSAGE, {}, {"cohesion": 1}, {V.TRADITION: 1}),
        RiteStage.COMING_OF_AGE: TraditionSpec(K.RITE_OF_PASSAGE, {"food": 1}, {"cohesion": 2}, {V.TRADITION: 1, V.MARTIAL: 1}),
        RiteStage.UNION: TraditionSpec(K.RITE_OF_PASSAGE, {"food": 1}, {"fertility": 5}, {V.KINSHIP: 1}),
        RiteStage.ELDERHOOD: TraditionSpec(K.RITE_OF_PASSAGE, {"food": 1}, {"cohesion": 1}, {V.TRADITION: 1, V.KINSHIP: 1}),
        RiteStage.DEATH: TraditionSpec(K.RITE_OF_PASSAGE, {"goods": 1}, {"rite": 1}, {V.DEATH: 1}),
        RiteStage.INITIATION: TraditionSpec(K.RITE_OF_PASSAGE, {"food": 1}, {"cohesion": 2}, {V.LOYALTY: 1}),
        RiteStage.DEPARTURE: TraditionSpec(K.RITE_OF_PASSAGE, {"goods": 1}, {"cohesion": 1}, {V.KINSHIP: 1, V.XENOPHILIA: 1}),
    },
)


def tradition_spec(kind: TraditionFunction, stage: RiteStage | None) -> TraditionSpec:
    return STAGES[stage] if kind is TraditionFunction.RITE_OF_PASSAGE and stage is not None else TRADITIONS[kind]


IDEOLOGY_VALUES = MappingProxyType(
    {
        IT.LEGALISM: {V.HIERARCHY: 5, V.TRADITION: 3},
        IT.RESTRAINT: {V.PURITY: 3, V.MERCY: 2},
        IT.EGALITARIANISM: {V.HIERARCHY: -8, V.MERCY: 3},
        IT.DIVINE_RIGHT: {V.HIERARCHY: 8, V.PIETY: 5},
        IT.MERCANTILISM: {V.WEALTH: 8, V.XENOPHILIA: 3},
        IT.MILITARISM: {V.MARTIAL: 8, V.HONOUR: 3},
        IT.ASCETICISM: {V.WEALTH: -6, V.PURITY: 4},
        IT.RATIONALISM: {V.KNOWLEDGE: 8, V.SUPERSTITION: -6},
        IT.NATURE_HARMONY: {V.NATURE: 8, V.WEALTH: -3},
        IT.XENOPHOBIA: {V.XENOPHILIA: -8, V.KINSHIP: 4},
        IT.COSMOPOLITANISM: {V.XENOPHILIA: 8, V.TRADITION: -3},
        IT.ANTI_GOD: {V.PIETY: -10, V.KNOWLEDGE: 4},
        IT.CREATORISM: {V.PIETY: 8, V.TRADITION: 3},
    }
)

IDEOLOGY_APPEAL = MappingProxyType(
    {
        IT.LEGALISM: {SC.SCRIBE: 60, SC.NOBLE: 40, SC.OFFICIAL: 70},
        IT.RESTRAINT: {SC.PRIEST: 40, SC.SCRIBE: 40},
        IT.EGALITARIANISM: {SC.FARMER: 60, SC.SERF_OR_SLAVE: 80, SC.OUTCAST: 70, SC.ARTISAN: 40, SC.WORKER: 70, SC.UNEMPLOYED: 70, SC.CITIZEN: 50},
        IT.DIVINE_RIGHT: {SC.NOBLE: 80, SC.PRIEST: 60},
        IT.MERCANTILISM: {SC.MERCHANT: 80, SC.ARTISAN: 50},
        IT.MILITARISM: {SC.WARRIOR: 80, SC.NOBLE: 50},
        IT.ASCETICISM: {SC.MONASTIC: 80, SC.PRIEST: 40},
        IT.RATIONALISM: {SC.SCRIBE: 70, SC.MERCHANT: 30, SC.PROFESSIONAL: 70},
        IT.NATURE_HARMONY: {SC.FARMER: 50, SC.OUTCAST: 30},
        IT.XENOPHOBIA: {SC.FARMER: 40, SC.WARRIOR: 40},
        IT.COSMOPOLITANISM: {SC.MERCHANT: 60, SC.SCRIBE: 40, SC.CITIZEN: 40, SC.PROFESSIONAL: 40},
        IT.ANTI_GOD: {SC.SCRIBE: 40, SC.OUTCAST: 50},
        IT.CREATORISM: {SC.PRIEST: 50, SC.MONASTIC: 50},
    }
)

VALUE_IDEOLOGY: MappingProxyType[ValueAxis, tuple[IdeologyTenet, IdeologyTenet]] = MappingProxyType(
    {
        V.HIERARCHY: (IT.DIVINE_RIGHT, IT.EGALITARIANISM),
        V.WEALTH: (IT.MERCANTILISM, IT.ASCETICISM),
        V.MARTIAL: (IT.MILITARISM, IT.RESTRAINT),
        V.KNOWLEDGE: (IT.RATIONALISM, IT.ASCETICISM),
        V.NATURE: (IT.NATURE_HARMONY, IT.MERCANTILISM),
        V.XENOPHILIA: (IT.COSMOPOLITANISM, IT.XENOPHOBIA),
        V.PIETY: (IT.CREATORISM, IT.ANTI_GOD),
        V.TRADITION: (IT.LEGALISM, IT.COSMOPOLITANISM),
    }
)

DOMAIN_SCHOOLS = MappingProxyType(
    {
        D.SEA: (S.ELEMENTAL_WATER,),
        D.FIRE: (S.ELEMENTAL_FIRE,),
        D.EARTH: (S.EARTH,),
        D.SKY: (S.STORM, S.DIVINATION),
        D.STORM: (S.STORM,),
        D.DEATH: (S.DEATH,),
        D.LIFE: (S.LIFE,),
        D.DREAM: (S.MIND, S.ILLUSION),
        D.TIME: (S.DIVINATION,),
        D.LIGHT: (S.LIFE, S.WARDING),
        D.SHADOW: (S.ILLUSION,),
        D.WAR: (S.ELEMENTAL_FIRE, S.WARDING),
        D.CRAFT: (S.BINDING, S.EARTH),
        D.KNOWLEDGE: (S.DIVINATION, S.MIND),
        D.LOVE: (S.MIND, S.LIFE),
        D.TRICKERY: (S.ILLUSION,),
        D.HUNT: (S.SUMMONING,),
        D.PLANTS: (S.LIFE, S.EARTH),
        D.BONE: (S.DEATH, S.BINDING),
        D.BLOOD: (S.BLOOD,),
        D.SOUND: (S.MIND,),
        D.STONE: (S.EARTH, S.WARDING),
        D.ICE: (S.ELEMENTAL_WATER,),
        D.MADNESS: (S.MIND, S.VOID),
        D.TRADE: (S.DIVINATION,),
        D.ROAD: (S.SUMMONING, S.DIVINATION),
        D.PLAGUE: (S.DEATH, S.BLOOD),
        D.HARVEST: (S.LIFE, S.EARTH),
        D.MOON: (S.ILLUSION, S.DIVINATION),
        D.SUN: (S.ELEMENTAL_FIRE, S.LIFE),
        D.STAR: (S.DIVINATION, S.VOID),
        D.LIES: (S.ILLUSION, S.MIND),
        D.OATH: (S.BINDING, S.WARDING),
        D.MEMORY: (S.MIND, S.DEATH),
        D.HUNGER: (S.BLOOD, S.VOID),
        D.GLASS: (S.WARDING, S.DIVINATION),
        D.SALT: (S.WARDING, S.ELEMENTAL_WATER),
        D.ASH: (S.ELEMENTAL_FIRE, S.DEATH),
        D.BORDER: (S.WARDING, S.BINDING),
        D.SLEEP: (S.MIND, S.ILLUSION),
    }
)


@dataclass(frozen=True)
class RiteTemplate:
    school: MagicSchool
    name: str
    source: MagicSource
    effects: tuple[tuple[RiteEffectKind, int], ...]
    power: int


RITE_TEMPLATES = MappingProxyType(
    {
        S.ELEMENTAL_FIRE: RiteTemplate(S.ELEMENTAL_FIRE, "Rite of Fire", MagicSource.LEY, ((E.DAMAGE, 3),), 3),
        S.ELEMENTAL_WATER: RiteTemplate(S.ELEMENTAL_WATER, "Rite of Rain", MagicSource.LEY, ((E.WEATHER_CHANGE, 4), (E.HARVEST_BLESSING, 2)), 4),
        S.EARTH: RiteTemplate(S.EARTH, "Rite of the Harvest", MagicSource.REAGENT, ((E.HARVEST_BLESSING, 3),), 2),
        S.STORM: RiteTemplate(S.STORM, "Rite of the Storm", MagicSource.LEY, ((E.WEATHER_CHANGE, 5), (E.DAMAGE, 2)), 5),
        S.LIFE: RiteTemplate(S.LIFE, "Rite of Healing", MagicSource.DIVINE, ((E.HEAL, 4), (E.FERTILITY, 2)), 3),
        S.DEATH: RiteTemplate(S.DEATH, "Rite of Raising the Dead", MagicSource.SOUL, ((E.RAISE_DEAD, 4), (E.UNSEAL_SOUL, 3)), 6),
        S.MIND: RiteTemplate(S.MIND, "Rite of the Will", MagicSource.LEY, ((E.CURSE, 3),), 3),
        S.ILLUSION: RiteTemplate(S.ILLUSION, "Rite of Illusion", MagicSource.LEY, ((E.WEATHER_CHANGE, 4),), 4),
        S.DIVINATION: RiteTemplate(S.DIVINATION, "Rite of Reading", MagicSource.REAGENT, ((E.SCRY, 4),), 2),
        S.WARDING: RiteTemplate(S.WARDING, "Rite of Warding", MagicSource.LEY, ((E.WARD, 4), (E.BLESS, 2), (E.EXORCISE, 3)), 3),
        S.BINDING: RiteTemplate(S.BINDING, "Rite of Binding", MagicSource.SOUL, ((E.BIND, 4), (E.SEAL_SOUL, 3)), 4),
        S.SUMMONING: RiteTemplate(S.SUMMONING, "Rite of Summoning", MagicSource.REAGENT, ((E.SUMMON, 4),), 5),
        S.BLOOD: RiteTemplate(S.BLOOD, "Rite of Blood", MagicSource.BLOOD, ((E.BLESS, 4), (E.DAMAGE, 3)), 5),
        S.VOID: RiteTemplate(S.VOID, "Rite of the Void", MagicSource.VOID, ((E.DAMAGE, 6), (E.CURSE, 4)), 8),
    }
)

DESPERATE_SCHOOLS = frozenset({S.BLOOD, S.VOID})


@dataclass(frozen=True)
class ItemSpec:
    item_class: ItemClass
    reach: int = 0
    coverage: int = 0
    weight: int = 0
    damage_type: str | None = None


ITEM_CLASSES = total(
    ItemClass,
    {
        spec.item_class: spec
        for spec in (
            ItemSpec(ItemClass.BLADE, reach=1, weight=2, damage_type="cut"),
            ItemSpec(ItemClass.LONGBLADE, reach=2, weight=3, damage_type="cut"),
            ItemSpec(ItemClass.AXE, reach=1, weight=3, damage_type="cut"),
            ItemSpec(ItemClass.SPEAR, reach=3, weight=2, damage_type="pierce"),
            ItemSpec(ItemClass.POLEARM, reach=3, weight=4, damage_type="cut"),
            ItemSpec(ItemClass.MACE, reach=1, weight=4, damage_type="blunt"),
            ItemSpec(ItemClass.BOW, reach=5, weight=1, damage_type="pierce"),
            ItemSpec(ItemClass.CROSSBOW, reach=5, weight=3, damage_type="pierce"),
            ItemSpec(ItemClass.SLING, reach=4, weight=1, damage_type="blunt"),
            ItemSpec(ItemClass.THROWING, reach=3, weight=1, damage_type="pierce"),
            ItemSpec(ItemClass.STAFF, reach=2, weight=2, damage_type="blunt"),
            ItemSpec(ItemClass.ARMOUR, coverage=60, weight=8),
            ItemSpec(ItemClass.SHIELD, coverage=30, weight=4),
            ItemSpec(ItemClass.HELMET, coverage=10, weight=2),
            ItemSpec(ItemClass.PADDING, coverage=50, weight=2),
            ItemSpec(ItemClass.CLOAK, coverage=20, weight=1),
            ItemSpec(ItemClass.FIREARM, reach=5, weight=3, damage_type="ballistic"),
            ItemSpec(ItemClass.IMPLANT, coverage=5, weight=1),
            *(
                ItemSpec(kind)
                for kind in (
                    ItemClass.CROWN,
                    ItemClass.SCEPTRE,
                    ItemClass.SEAL,
                    ItemClass.RING,
                    ItemClass.STANDARD,
                    ItemClass.HOLY_RELIC,
                    ItemClass.IDOL,
                    ItemClass.PRAYER_BOOK,
                    ItemClass.BOOK,
                    ItemClass.SCROLL,
                    ItemClass.MAP,
                    ItemClass.ASTROLABE,
                    ItemClass.TOOL,
                    ItemClass.INSTRUMENT,
                    ItemClass.MIRROR,
                    ItemClass.VESSEL_OBJECT,
                    ItemClass.PROSTHESIS,
                    ItemClass.KEY,
                    ItemClass.JEWEL,
                    ItemClass.CURRENCY,
                    ItemClass.DEVICE,
                    ItemClass.COMPUTER,
                    ItemClass.DRUG,
                    ItemClass.VEHICLE_PART,
                    ItemClass.COMMUNICATOR,
                )
            ),
        )
    },
)
WEAPONS = frozenset(
    {
        ItemClass.BLADE,
        ItemClass.LONGBLADE,
        ItemClass.AXE,
        ItemClass.SPEAR,
        ItemClass.POLEARM,
        ItemClass.MACE,
        ItemClass.BOW,
        ItemClass.CROSSBOW,
        ItemClass.SLING,
        ItemClass.THROWING,
        ItemClass.STAFF,
        ItemClass.FIREARM,
    }
)
REGALIA = frozenset({ItemClass.CROWN, ItemClass.SCEPTRE, ItemClass.SEAL, ItemClass.RING})
KNOWLEDGE_ITEMS = frozenset({ItemClass.BOOK, ItemClass.SCROLL, ItemClass.PRAYER_BOOK, ItemClass.COMPUTER})

ITEM_WORDS = MappingProxyType(
    {
        ItemClass.LONGBLADE: ("longsword", "greatsword", "claymore"),
        ItemClass.BLADE: ("sword", "blade", "dagger", "knife", "sabre", "scimitar"),
        ItemClass.AXE: ("axe",),
        ItemClass.SPEAR: ("spear", "lance", "javelin", "trident"),
        ItemClass.POLEARM: ("halberd", "glaive", "pike", "polearm"),
        ItemClass.MACE: ("mace", "hammer", "club", "flail"),
        ItemClass.CROSSBOW: ("crossbow",),
        ItemClass.BOW: ("bow",),
        ItemClass.SLING: ("sling",),
        ItemClass.STAFF: ("staff", "wand", "rod"),
        ItemClass.ARMOUR: ("armour", "armor", "mail", "plate", "cuirass", "hauberk"),
        ItemClass.SHIELD: ("shield", "buckler"),
        ItemClass.HELMET: ("helm", "helmet"),
        ItemClass.CROWN: ("crown", "diadem", "circlet", "tiara"),
        ItemClass.SCEPTRE: ("sceptre", "scepter"),
        ItemClass.SEAL: ("seal", "signet"),
        ItemClass.RING: ("ring",),
        ItemClass.STANDARD: ("banner", "standard", "flag"),
        ItemClass.HOLY_RELIC: ("relic", "bone", "reliquary"),
        ItemClass.IDOL: ("idol", "statuette", "figurine"),
        ItemClass.PRAYER_BOOK: ("psalter", "hymnal", "prayer"),
        ItemClass.BOOK: ("book", "tome", "codex", "grimoire", "chronicle"),
        ItemClass.SCROLL: ("scroll",),
        ItemClass.MAP: ("map", "chart"),
        ItemClass.ASTROLABE: ("astrolabe", "orrery"),
        ItemClass.INSTRUMENT: ("harp", "lyre", "drum", "horn", "flute", "lute"),
        ItemClass.MIRROR: ("mirror",),
        ItemClass.VESSEL_OBJECT: ("cup", "urn", "chalice", "grail", "bowl", "goblet"),
        ItemClass.KEY: ("key",),
        ItemClass.JEWEL: ("jewel", "gem", "pearl", "amulet", "necklace", "stone"),
        ItemClass.FIREARM: ("gun", "rifle", "pistol", "musket", "carbine", "revolver"),
        ItemClass.COMPUTER: ("computer", "terminal", "datapad"),
        ItemClass.COMMUNICATOR: ("radio", "phone", "communicator", "transmitter"),
        ItemClass.DRUG: ("drug", "pill", "serum", "stimulant"),
        ItemClass.IMPLANT: ("implant", "cybernetic"),
        ItemClass.DEVICE: ("device", "machine", "gadget"),
        ItemClass.VEHICLE_PART: ("engine", "thruster", "wheel"),
    }
)

ART_MESSAGES = MappingProxyType({mode: spec.message for mode, spec in ART_MODES.items()})
COURT_MESSAGE = MappingProxyType({ValueAxis.HIERARCHY.value: 5, ValueAxis.HONOUR.value: 2})

ART_WORDS = MappingProxyType({mode: spec.words for mode, spec in ART_MODES.items()})

SAYING_KIND_LABELS = total(
    SayingKind,
    {
        SayingKind.PROVERB: "Proverb",
        SayingKind.LULLABY: "Lullaby",
        SayingKind.PRAYER: "Prayer",
        SayingKind.MALEDICTION: "Malediction",
        SayingKind.FOLK_SONG: "Folk song",
        SayingKind.OATH: "Oath",
        SayingKind.TONGUE_TWISTER: "Tongue twister",
        SayingKind.HYMN: "Hymn",
    },
)
