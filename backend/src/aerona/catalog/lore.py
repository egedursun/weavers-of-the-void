from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.domain.enums.culture import (
    ArtMedium,
    IdeologyTenet,
    ItemClass,
    LegendArchetype,
    MagicSchool,
    MagicSource,
    RiteEffectKind,
    TraditionKind,
)
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass

V = ValueAxis
A = LegendArchetype
K = TraditionKind
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
        A.FLOOD: {V.PIETY: 10, V.NATURE: 5},
        A.BETRAYAL: {V.HONOUR: 10, V.KINSHIP: 5, V.XENOPHILIA: -5},
        A.LOST_PARADISE: {V.TRADITION: 10, V.PURITY: 5},
        A.CHOSEN_ONE: {V.PIETY: 5, V.HIERARCHY: 5},
        A.CURSED_LINE: {V.SUPERSTITION: 10, V.KINSHIP: -5},
        A.RETURN_OF_THE_KING: {V.HIERARCHY: 10, V.TRADITION: 5},
        A.HAUNTED_PLACE: {V.SUPERSTITION: 10, V.DEATH: 5},
    }
)

DISTORTED = MappingProxyType(
    {
        V.HONOUR: A.BETRAYAL,
        V.PIETY: A.CHOSEN_ONE,
        V.SUPERSTITION: A.CURSED_LINE,
        V.MARTIAL: A.HERO_QUEST,
        V.TRADITION: A.LOST_PARADISE,
        V.HIERARCHY: A.RETURN_OF_THE_KING,
        V.DEATH: A.HAUNTED_PLACE,
    }
)


@dataclass(frozen=True)
class TraditionSpec:
    kind: TraditionKind
    cost: dict[str, int] = field(default_factory=dict)
    effects: dict[str, int] = field(default_factory=dict)
    values: dict[ValueAxis, int] = field(default_factory=dict)


TRADITIONS = MappingProxyType(
    {
        spec.kind: spec
        for spec in (
            TraditionSpec(K.FESTIVAL, {"food": 2}, {"cohesion": 4, "satisfaction": 3}),
            TraditionSpec(K.FAST, {}, {"piety": 2, "food_saved": 1}, {V.PIETY: 1, V.PURITY: 1}),
            TraditionSpec(K.FUNERAL_RITE, {"goods": 1}, {"rite": 1}, {V.DEATH: 1}),
            TraditionSpec(K.INITIATION, {}, {"scar": 1, "cohesion": 2}, {V.MARTIAL: 1}),
            TraditionSpec(K.MARRIAGE_RITE, {"food": 1}, {"fertility": 5}, {V.KINSHIP: 1}),
            TraditionSpec(K.COMING_OF_AGE, {"food": 1}, {"cohesion": 2}, {V.TRADITION: 1}),
            TraditionSpec(K.TABOO, {}, {"taboo": 1}, {V.PURITY: 1, V.TRADITION: 1}),
            TraditionSpec(K.OFFERING, {"goods": 1}, {"piety": 2}, {V.PIETY: 1}),
            TraditionSpec(K.PILGRIMAGE, {"food": 1}, {"piety": 3}, {V.PIETY: 1}),
            TraditionSpec(K.HOSPITALITY_LAW, {}, {"hospitality": 1}, {V.XENOPHILIA: 2, V.HONOUR: 1}),
            TraditionSpec(K.DUEL_CUSTOM, {}, {"duels": 1}, {V.HONOUR: 2, V.MARTIAL: 1}),
            TraditionSpec(K.MOURNING, {}, {"cohesion": 2}, {V.DEATH: 1, V.KINSHIP: 1}),
            TraditionSpec(K.HARVEST_RITE, {"food": 1}, {"harvest": 1, "cohesion": 2}, {V.NATURE: 1}),
            TraditionSpec(K.WAR_DANCE, {}, {"martial": 2}, {V.MARTIAL: 2}),
            TraditionSpec(K.SCAR_RITE, {}, {"scar": 1}, {V.MARTIAL: 1, V.PURITY: -1}),
            TraditionSpec(K.ANCESTOR_FEAST, {"food": 2}, {"placation": 1}, {V.KINSHIP: 1, V.DEATH: 1}),
        )
    }
)

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
        IT.LEGALISM: {SC.SCRIBE: 60, SC.NOBLE: 40},
        IT.RESTRAINT: {SC.PRIEST: 40, SC.SCRIBE: 40},
        IT.EGALITARIANISM: {SC.FARMER: 60, SC.SERF_OR_SLAVE: 80, SC.OUTCAST: 70, SC.ARTISAN: 40},
        IT.DIVINE_RIGHT: {SC.NOBLE: 80, SC.PRIEST: 60},
        IT.MERCANTILISM: {SC.MERCHANT: 80, SC.ARTISAN: 50},
        IT.MILITARISM: {SC.WARRIOR: 80, SC.NOBLE: 50},
        IT.ASCETICISM: {SC.MONASTIC: 80, SC.PRIEST: 40},
        IT.RATIONALISM: {SC.SCRIBE: 70, SC.MERCHANT: 30},
        IT.NATURE_HARMONY: {SC.FARMER: 50, SC.OUTCAST: 30},
        IT.XENOPHOBIA: {SC.FARMER: 40, SC.WARRIOR: 40},
        IT.COSMOPOLITANISM: {SC.MERCHANT: 60, SC.SCRIBE: 40},
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
        S.ELEMENTAL_FIRE: RiteTemplate(S.ELEMENTAL_FIRE, "Calling of Flame", MagicSource.LEY, ((E.DAMAGE, 3),), 3),
        S.ELEMENTAL_WATER: RiteTemplate(S.ELEMENTAL_WATER, "Rain Summoning", MagicSource.LEY, ((E.WEATHER_CHANGE, 4), (E.HARVEST_BLESSING, 2)), 4),
        S.EARTH: RiteTemplate(S.EARTH, "Blessing of the Furrow", MagicSource.REAGENT, ((E.HARVEST_BLESSING, 3),), 2),
        S.STORM: RiteTemplate(S.STORM, "Raising of the Storm", MagicSource.LEY, ((E.WEATHER_CHANGE, 5), (E.DAMAGE, 2)), 5),
        S.LIFE: RiteTemplate(S.LIFE, "Laying on of Hands", MagicSource.DIVINE, ((E.HEAL, 4), (E.FERTILITY, 2)), 3),
        S.DEATH: RiteTemplate(S.DEATH, "Raising of the Fallen", MagicSource.SOUL, ((E.RAISE_DEAD, 4),), 6),
        S.MIND: RiteTemplate(S.MIND, "Bending of the Will", MagicSource.LEY, ((E.CURSE, 3),), 3),
        S.ILLUSION: RiteTemplate(S.ILLUSION, "Veil of Fog", MagicSource.LEY, ((E.WEATHER_CHANGE, 4),), 4),
        S.DIVINATION: RiteTemplate(S.DIVINATION, "Reading of Omens", MagicSource.REAGENT, ((E.SCRY, 4),), 2),
        S.WARDING: RiteTemplate(S.WARDING, "Warding of the Walls", MagicSource.LEY, ((E.WARD, 4), (E.BLESS, 2)), 3),
        S.BINDING: RiteTemplate(S.BINDING, "Chain of Spirits", MagicSource.SOUL, ((E.BIND, 4),), 4),
        S.SUMMONING: RiteTemplate(S.SUMMONING, "Calling of the Beast", MagicSource.REAGENT, ((E.SUMMON, 4),), 5),
        S.BLOOD: RiteTemplate(S.BLOOD, "Blood Offering", MagicSource.BLOOD, ((E.BLESS, 4), (E.DAMAGE, 3)), 5),
        S.VOID: RiteTemplate(S.VOID, "Opening of the Void", MagicSource.VOID, ((E.DAMAGE, 6), (E.CURSE, 4)), 8),
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


ITEM_CLASSES = MappingProxyType(
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
                )
            ),
        )
    }
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
    }
)
REGALIA = frozenset({ItemClass.CROWN, ItemClass.SCEPTRE, ItemClass.SEAL, ItemClass.RING})
KNOWLEDGE_ITEMS = frozenset({ItemClass.BOOK, ItemClass.SCROLL, ItemClass.PRAYER_BOOK})

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
    }
)

ART_MESSAGES = MappingProxyType(
    {
        ArtMedium.SONG: {V.KINSHIP: 3},
        ArtMedium.EPIC_POEM: {V.HONOUR: 5, V.MARTIAL: 3},
        ArtMedium.PLAY: {V.MERCY: 3},
        ArtMedium.STATUE: {V.HIERARCHY: 4, V.MARTIAL: 2},
        ArtMedium.FRESCO: {V.PIETY: 4},
        ArtMedium.TAPESTRY: {V.TRADITION: 4},
        ArtMedium.MOSAIC: {V.PIETY: 3},
        ArtMedium.BOOK: {V.KNOWLEDGE: 5},
        ArtMedium.DANCE: {V.KINSHIP: 2, V.MARTIAL: 2},
        ArtMedium.MUSIC: {V.KINSHIP: 3},
        ArtMedium.CARVING: {V.TRADITION: 3},
        ArtMedium.ARCHITECTURE_ORNAMENT: {V.HIERARCHY: 3},
    }
)

ART_WORDS = MappingProxyType(
    {
        ArtMedium.EPIC_POEM: ("epic", "saga", "poem", "ballad", "lay", "verse"),
        ArtMedium.SONG: ("song", "hymn", "chant", "anthem", "lament"),
        ArtMedium.PLAY: ("play", "drama", "tragedy", "comedy"),
        ArtMedium.STATUE: ("statue", "colossus", "bust", "sculpture"),
        ArtMedium.FRESCO: ("fresco", "mural", "painting"),
        ArtMedium.TAPESTRY: ("tapestry", "weaving", "embroidery"),
        ArtMedium.MOSAIC: ("mosaic",),
        ArtMedium.BOOK: ("book", "chronicle", "codex", "treatise", "history", "annals"),
        ArtMedium.DANCE: ("dance",),
        ArtMedium.MUSIC: ("music", "symphony", "melody", "drum"),
        ArtMedium.CARVING: ("carving", "relief", "stele", "totem"),
        ArtMedium.ARCHITECTURE_ORNAMENT: ("frieze", "ornament", "gate", "arch"),
    }
)
