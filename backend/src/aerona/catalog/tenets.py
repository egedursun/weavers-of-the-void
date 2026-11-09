from types import MappingProxyType

from aerona.domain.enums.domain import Domain
from aerona.domain.enums.faith import JudgementDoctrine, StratumKind, TenetKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.son import Passion

T = TenetKind
D = Domain
J = JudgementDoctrine

DOMAIN_TENETS = MappingProxyType(
    {
        D.SEA: (T.PILGRIMAGE_DUTY, T.SYNCRETIC_OPENNESS),
        D.FIRE: (T.PURITY_OF_BODY, T.HOLY_WAR),
        D.EARTH: (T.ANCESTOR_VENERATION, T.ASCETICISM),
        D.SKY: (T.DIVINE_KINGSHIP, T.PROSELYTISM),
        D.STORM: (T.HOLY_WAR, T.ANIMAL_SACRIFICE),
        D.DEATH: (T.ANCESTOR_VENERATION, T.JUDGEMENT_BY_DEEDS, T.SOULS_REST),
        D.LIFE: (T.PACIFISM, T.SACRED_SPECIES),
        D.DREAM: (T.REINCARNATION, T.SYNCRETIC_OPENNESS),
        D.TIME: (T.REINCARNATION, T.MONASTIC_LEARNING),
        D.LIGHT: (T.PURITY_OF_BODY, T.JUDGEMENT_BY_FAITH, T.PROSELYTISM),
        D.SHADOW: (T.EXCLUSIVITY, T.SANCTIFIED_MAGIC),
        D.WAR: (T.HOLY_WAR, T.MARTYRDOM_GLORY),
        D.CRAFT: (T.MONASTIC_LEARNING, T.ASCETICISM),
        D.KNOWLEDGE: (T.MONASTIC_LEARNING, T.SANCTIFIED_MAGIC),
        D.LOVE: (T.PACIFISM, T.SYNCRETIC_OPENNESS),
        D.TRICKERY: (T.SYNCRETIC_OPENNESS, T.SANCTIFIED_MAGIC),
        D.HUNT: (T.ANIMAL_SACRIFICE, T.SACRED_SPECIES),
        D.PLANTS: (T.DIETARY_LAW, T.PACIFISM),
        D.BONE: (T.ANCESTOR_VENERATION, T.SACRED_SUFFERING),
        D.BLOOD: (T.HUMAN_SACRIFICE, T.MARTYRDOM_GLORY),
        D.SOUND: (T.PROSELYTISM, T.MONASTIC_LEARNING),
        D.STONE: (T.ANCESTOR_VENERATION, T.EXCLUSIVITY),
        D.ICE: (T.ASCETICISM, T.SACRED_SUFFERING),
        D.MADNESS: (T.SACRED_SUFFERING, T.HUMAN_SACRIFICE),
        D.TRADE: (T.SYNCRETIC_OPENNESS, T.PILGRIMAGE_DUTY),
        D.ROAD: (T.PILGRIMAGE_DUTY, T.PROSELYTISM),
        D.PLAGUE: (T.SACRED_SUFFERING, T.ANTI_MAGIC),
        D.HARVEST: (T.DIETARY_LAW, T.ANIMAL_SACRIFICE),
        D.MOON: (T.CELIBATE_CLERGY, T.REINCARNATION),
        D.SUN: (T.DIVINE_KINGSHIP, T.JUDGEMENT_BY_FAITH),
        D.STAR: (T.MONASTIC_LEARNING, T.PILGRIMAGE_DUTY),
        D.LIES: (T.SANCTIFIED_MAGIC, T.EXCLUSIVITY),
        D.OATH: (T.JUDGEMENT_BY_DEEDS, T.EXCLUSIVITY),
        D.MEMORY: (T.ANCESTOR_VENERATION, T.REINCARNATION),
        D.HUNGER: (T.ASCETICISM, T.HUMAN_SACRIFICE),
        D.GLASS: (T.ANTI_MAGIC, T.PURITY_OF_BODY),
        D.SALT: (T.DIETARY_LAW, T.PURITY_OF_BODY),
        D.ASH: (T.SOULS_REST, T.ASCETICISM),
        D.BORDER: (T.EXCLUSIVITY, T.HOLY_WAR),
        D.SLEEP: (T.SOULS_REST, T.PACIFISM),
    }
)

DOMAIN_JUDGEMENT = MappingProxyType(
    {
        **dict.fromkeys((D.DEATH, D.OATH, D.WAR, D.BONE, D.BORDER, D.STONE, D.CRAFT), J.DEEDS),
        **dict.fromkeys((D.LIGHT, D.SUN, D.SKY, D.STAR, D.SOUND, D.KNOWLEDGE, D.TIME), J.FAITH),
        **dict.fromkeys((D.MEMORY, D.ASH, D.SALT, D.HARVEST, D.EARTH, D.PLANTS, D.ICE), J.RITE),
        **dict.fromkeys((D.LOVE, D.TRICKERY, D.LIES, D.MOON, D.DREAM, D.SEA, D.TRADE, D.ROAD, D.FIRE, D.STORM), J.FAVOUR),
        **dict.fromkeys((D.MADNESS, D.HUNGER, D.PLAGUE, D.SHADOW, D.GLASS, D.SLEEP, D.LIFE, D.HUNT, D.BLOOD), J.NONE),
    }
)

VALUE_TENETS: MappingProxyType[ValueAxis, tuple[TenetKind, TenetKind]] = MappingProxyType(
    {
        ValueAxis.MARTIAL: (T.HOLY_WAR, T.PACIFISM),
        ValueAxis.MERCY: (T.PACIFISM, T.HUMAN_SACRIFICE),
        ValueAxis.PURITY: (T.PURITY_OF_BODY, T.SACRED_SUFFERING),
        ValueAxis.KINSHIP: (T.ANCESTOR_VENERATION, T.CELIBATE_CLERGY),
        ValueAxis.KNOWLEDGE: (T.MONASTIC_LEARNING, T.ANTI_MAGIC),
        ValueAxis.XENOPHILIA: (T.SYNCRETIC_OPENNESS, T.EXCLUSIVITY),
        ValueAxis.WEALTH: (T.PILGRIMAGE_DUTY, T.ASCETICISM),
        ValueAxis.DEATH: (T.MARTYRDOM_GLORY, T.SOULS_REST),
        ValueAxis.HIERARCHY: (T.DIVINE_KINGSHIP, T.PROSELYTISM),
        ValueAxis.NATURE: (T.SACRED_SPECIES, T.ANIMAL_SACRIFICE),
        ValueAxis.PIETY: (T.JUDGEMENT_BY_FAITH, T.JUDGEMENT_BY_DEEDS),
        ValueAxis.TRADITION: (T.DIETARY_LAW, T.SYNCRETIC_OPENNESS),
        ValueAxis.SUPERSTITION: (T.REINCARNATION, T.SANCTIFIED_MAGIC),
        ValueAxis.HONOUR: (T.JUDGEMENT_BY_DEEDS, T.SACRED_SUFFERING),
    }
)

OPPOSED = frozenset(
    {
        frozenset({T.PACIFISM, T.HOLY_WAR}),
        frozenset({T.SACRED_SUFFERING, T.PURITY_OF_BODY}),
        frozenset({T.EXCLUSIVITY, T.SYNCRETIC_OPENNESS}),
        frozenset({T.ANTI_MAGIC, T.SANCTIFIED_MAGIC}),
        frozenset({T.JUDGEMENT_BY_DEEDS, T.JUDGEMENT_BY_FAITH}),
        frozenset({T.REINCARNATION, T.SOULS_REST}),
        frozenset({T.ASCETICISM, T.PILGRIMAGE_DUTY}),
    }
)

TARGETED = frozenset({T.DIETARY_LAW, T.SACRED_SPECIES, T.PILGRIMAGE_DUTY})

TENET_EFFECTS = MappingProxyType(
    {
        T.PACIFISM: "The faithful keep fewer warriors and a devout ruler loses face for every war.",
        T.HOLY_WAR: "Armies fight harder against unbelievers; peace with them costs zeal.",
        T.ASCETICISM: "Comfort does not erode the faith; tithes go to alms, not temples.",
        T.SACRED_SUFFERING: "The maimed are honoured among the faithful.",
        T.PURITY_OF_BODY: "The maimed are unclean among the faithful.",
        T.ANCESTOR_VENERATION: "Ancestor spirits are fed with offerings and guard their people.",
        T.HUMAN_SACRIFICE: "Captives are given to the god; other peoples are appalled.",
        T.ANIMAL_SACRIFICE: "Livestock is offered to the god each epoch.",
        T.CELIBATE_CLERGY: "The clergy found no houses.",
        T.PROSELYTISM: "Missionaries travel the roads and convert harder.",
        T.EXCLUSIVITY: "No other god is revered beside this one.",
        T.SYNCRETIC_OPENNESS: "Other gods are gladly revered beside this one.",
        T.MONASTIC_LEARNING: "Monasteries keep knowledge alive through dark ages.",
        T.ANTI_MAGIC: "Wizards are hunted and magic is shunned.",
        T.SANCTIFIED_MAGIC: "Magic is a holy gift and its users are revered.",
        T.JUDGEMENT_BY_DEEDS: "The dead are judged by what they did.",
        T.JUDGEMENT_BY_FAITH: "The dead are judged by what they believed.",
        T.REINCARNATION: "Exceptional souls may be born again.",
        T.MARTYRDOM_GLORY: "Martyrs stir the faith and the fallen go to a warrior hall.",
        T.DIVINE_KINGSHIP: "Rulers are the god's own and draw legitimacy from the faith.",
        T.DIETARY_LAW: "One food is forbidden to the faithful.",
        T.SACRED_SPECIES: "One beast is sacred; its hunters are hated.",
        T.PILGRIMAGE_DUTY: "The faithful must journey to a holy place.",
        T.SOULS_REST: "Souls are sealed against return.",
        T.VOID_COMMUNION: "The faithful commune with a being from outside; they and their home lose sanity and the world leaks.",
        T.FEEDING_THE_HUNGER: "The faithful make offerings that feed the being they worship.",
        T.WHISPERED_SECRETS: "The being they worship passes forbidden knowledge to their home.",
    }
)

STRATUM_NAMES = MappingProxyType(
    {
        StratumKind.PARADISE: "the Blessed Fields",
        StratumKind.PLAIN: "the Grey Plain",
        StratumKind.TORMENT: "the Pits",
        StratumKind.OBLIVION: "the Forgetting",
        StratumKind.WARRIOR_HALL: "the Hall of the Fallen",
        StratumKind.ANCESTOR_HALL: "the House of the Ancestors",
    }
)

STRATUM_PRIORITY = MappingProxyType(
    {
        StratumKind.OBLIVION: 0,
        StratumKind.WARRIOR_HALL: 10,
        StratumKind.PARADISE: 20,
        StratumKind.TORMENT: 30,
        StratumKind.ANCESTOR_HALL: 40,
        StratumKind.PLAIN: 90,
    }
)

PASSION_TENETS = MappingProxyType(
    {
        Passion.WRATH: (T.HOLY_WAR, T.MARTYRDOM_GLORY),
        Passion.MERCY: (T.PACIFISM, T.ASCETICISM),
        Passion.AMBITION: (T.PROSELYTISM, T.DIVINE_KINGSHIP),
        Passion.LOYALTY: (T.EXCLUSIVITY, T.ANCESTOR_VENERATION),
    }
)
