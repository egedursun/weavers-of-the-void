from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, ResourceMechanic
from aerona.rules.registry import Rules

B = KnowledgeBranch


@dataclass(frozen=True)
class KeyedText[K]:
    key: K
    label: str
    effect: str


KNOWLEDGE_BRANCHES: dict[KnowledgeBranch, KeyedText[KnowledgeBranch]] = {
    item.key: item
    for item in (
        KeyedText(B.AGRICULTURE, "Agriculture", "Knowers' population grows faster; famine and drought strike more softly."),
        KeyedText(B.METALLURGY, "Metallurgy", "Weapons and armour they produce are stronger."),
        KeyedText(B.SEAFARING, "Seafaring", "Trade, war and migration with communities beyond the sea."),
        KeyedText(B.WRITING, "Writing", "Their languages grow complex; what they know spreads faster to partners."),
        KeyedText(B.ARCHITECTURE, "Architecture", "Their structures are grander and sturdier, and withstand earthquakes."),
        KeyedText(B.MEDICINE, "Medicine", "Plagues strike more softly; their mortals live longer."),
        KeyedText(B.MAGIC, "Magic", "Their magic grows and the items they produce gain might."),
        KeyedText(B.WARFARE, "Art of War", "Their armies fight harder."),
        KeyedText(B.ASTRONOMY, "Astronomy", "They read the star of the epoch, sense disasters early and suffer them less."),
        KeyedText(B.TRADE, "Trade", "Their trade routes bring more prosperity."),
        KeyedText(B.SKY_NAVIGATION, "Sky Navigation", "Can discover routes between worlds; journeys are less likely to go astray."),
        KeyedText(B.SHIPBUILDING, "Shipbuilding", "Can build ships that sail between worlds."),
        KeyedText(B.GATE_LORE, "Gate Lore", "Can open and close ancient gates; gate journeys are swift."),
        KeyedText(B.PATHFINDING, "Pathfinding", "Can fold space with the cosmic travel resource."),
        KeyedText(B.VOID_LIVING, "Void Living", "Can settle worlds with thin or no air; loses fewer travellers."),
        KeyedText(B.IMMORTALITY, "Pursuit of Immortality", "Their mortals reach for immortality."),
        KeyedText(B.BIOMANCY, "Biomancy", "Combines and alters living things: merges species into new ones and steers mutations."),
        KeyedText(B.FORBIDDEN, "Forbidden Knowledge", "Great power in war and magic, at the price of sanity and a leak into their world."),
        KeyedText(B.CIVICS, "Civics", "Their laws, offices, faith and thought grow into institutions that shape how the realm is run."),
        KeyedText(B.LAW, "Law", "Their courts and codes grow; written and codified law come within reach sooner."),
        KeyedText(B.NATURAL_HISTORY, "Natural History", "They know living kinds better: breeding, anatomy and new materials open to them."),
        KeyedText(B.LANGUAGE_LORE, "Language Lore", "They read and translate other tongues; ciphers and interpreters come easier."),
        KeyedText(B.MATHEMATICS, "Mathematics", "Their reckoning sharpens engineering, navigation and accounts, up to signs for unknowns."),
    )
}

NATURAL_LAWS: dict[NaturalLaw, KeyedText[NaturalLaw]] = {
    item.key: item
    for item in (
        KeyedText(NaturalLaw.NONE, "None", "Narrative only; no mechanical effect."),
        KeyedText(NaturalLaw.IMMORTALITY, "Immortality", "Mortals do not age; population grows more slowly."),
        KeyedText(NaturalLaw.SHORT_LIFE, "Short life", "Mortals age faster; population grows faster."),
        KeyedText(NaturalLaw.DEAD_RETURN, "Return of the dead", "Fallen heroes may return as ghosts."),
        KeyedText(NaturalLaw.MAGIC_PRICE, "Price of magic", "Peoples steeped in magic pay part of their population to it every epoch."),
        KeyedText(NaturalLaw.WAR_BAN, "War ban", "Wars break out less often but are bloodier."),
        KeyedText(NaturalLaw.BOUNTY, "Bounty", "The fertility of every land rises each epoch."),
        KeyedText(NaturalLaw.DROUGHT, "Drought", "The fertility of every land falls each epoch."),
        KeyedText(NaturalLaw.SEA_BAN, "Sea ban", "Seas cannot be crossed; seafaring is useless."),
        KeyedText(NaturalLaw.ONE_LANGUAGE, "One language", "Languages spread faster through conquest and trade."),
        KeyedText(NaturalLaw.DISASTERS, "Disasters", "Natural disasters happen more often."),
        KeyedText(NaturalLaw.SOULS_REINCARNATE, "Souls reincarnate", "Souls that pass judgement may be born again into a new life."),
        KeyedText(NaturalLaw.GIFT_FLOWERING, "Gift flowering", "The magical gift is born more often in every bloodline."),
        KeyedText(NaturalLaw.GIFT_WITHERING, "Gift withering", "The magical gift is born more rarely and fades from bloodlines."),
        KeyedText(NaturalLaw.NO_IRON, "No iron", "Iron cannot be smelted or worked."),
        KeyedText(NaturalLaw.ETERNAL_NIGHT, "Eternal night", "The sun does not rise over its reach; fields yield far less."),
        KeyedText(NaturalLaw.MAGIC_REQUIRES_BLOOD, "Magic requires blood", "Every rite costs the caster's blood as well as its price."),
        KeyedText(NaturalLaw.GRAVITY_SHIFT, "Shifted weight", "Things weigh differently; building and marching are slower."),
        KeyedText(NaturalLaw.SEASONS_REVERSED, "Seasons reversed", "The seasons run backwards; growth comes in the cold half of the year."),
        KeyedText(
            NaturalLaw.LONG_SEASONS,
            "Long seasons",
            "Summers and winters run for years of no set length; scholars forecast their turn and peoples store food against them.",
        ),
        KeyedText(NaturalLaw.DREAMS_ARE_REAL, "Dreams are real", "Dream routes never close and mortals dream more often."),
        KeyedText(NaturalLaw.OATHS_BIND, "Oaths bind", "Whoever breaks an oath is branded at once."),
        KeyedText(
            NaturalLaw.THE_DEAD_SPEAK,
            "The dead speak",
            "Spirits take turns in the world: they speak, send word, foretell and pray, and tell the legends of the places they dwell in.",
        ),
        KeyedText(NaturalLaw.METAL_RUSTS_FAST, "Metal rusts fast", "Metal weapons and tools wear out far faster."),
        KeyedText(NaturalLaw.NO_GUNPOWDER, "No gunpowder", "Powder will not burn: no gunpowder, firearms or cannon can be made."),
    )
}

RESOURCE_MECHANICS: dict[ResourceMechanic, KeyedText[ResourceMechanic]] = {
    item.key: item
    for item in (
        KeyedText(ResourceMechanic.DECAYING, "Decaying", "Rots in storage: its abundance drops each epoch and never regenerates."),
        KeyedText(ResourceMechanic.ADDICTIVE, "Addictive", "Communities that own it become addicted; losing it causes withdrawal."),
        KeyedText(ResourceMechanic.SENTIENT, "Sentient", "Chooses who mines it and makes demands; abandons owners who ignore them."),
        KeyedText(ResourceMechanic.DEPLETION_PRICE, "Depletion price", "When its last drop is drawn a curse falls on its land and doom approaches."),
        KeyedText(ResourceMechanic.FIXED, "Fixed", "A fixed amount in the cosmos that never regenerates."),
        KeyedText(ResourceMechanic.SACRED, "Sacred", "Belongs to a god who is angered when non-worshippers mine it."),
    )
}

ENGINE_UNDISCOVERABLE_BRANCHES: frozenset[KnowledgeBranch] = frozenset({B.FORBIDDEN})


def branch_label(branch: KnowledgeBranch) -> str:
    return KNOWLEDGE_BRANCHES[branch].label


K = KnowledgeKind


@dataclass(frozen=True)
class KnowledgeSpec:
    label: str
    dies: bool
    worth: Callable[[Rules], int]


KNOWLEDGE: Mapping[KnowledgeKind, KnowledgeSpec] = total(
    KnowledgeKind,
    {
        K.SONG: KnowledgeSpec("A song", dies=False, worth=lambda rules: rules.knowledge.song_value),
        K.ART_FORM: KnowledgeSpec("An art form", dies=False, worth=lambda rules: rules.knowledge.art_form_value),
        K.RITE: KnowledgeSpec("A rite", dies=False, worth=lambda rules: rules.knowledge.rite_value),
        K.TECHNIQUE: KnowledgeSpec("A technique", dies=False, worth=lambda rules: rules.knowledge.technique_value),
        K.TRUE_NAME: KnowledgeSpec("A true name", dies=True, worth=lambda rules: rules.knowledge.true_name_value),
        K.PROPHECY: KnowledgeSpec("A prophecy", dies=True, worth=lambda rules: rules.knowledge.prophecy_value),
        K.TREASURE: KnowledgeSpec("Where a treasure lies", dies=True, worth=lambda rules: rules.knowledge.treasure_value),
        K.LANGUAGE: KnowledgeSpec("A language", dies=False, worth=lambda rules: rules.knowledge.language_value),
        K.ACCOUNT: KnowledgeSpec("An account of what happened", dies=False, worth=lambda rules: rules.knowledge.account_value),
        K.SITE: KnowledgeSpec("A hidden site", dies=True, worth=lambda rules: rules.knowledge.site_value),
        K.MAP: KnowledgeSpec("Knowledge of a land", dies=False, worth=lambda rules: rules.knowledge.map_value),
        K.WEAKNESS: KnowledgeSpec("A weakness", dies=True, worth=lambda rules: rules.knowledge.weakness_value),
        K.PATTERN: KnowledgeSpec("A pattern of a made thing", dies=False, worth=lambda rules: rules.knowledge.pattern_value),
        K.SOURCE: KnowledgeSpec("Where a source of power lies", dies=True, worth=lambda rules: rules.knowledge.source_value),
        K.SECRET: KnowledgeSpec("A secret of a person, house or realm", dies=True, worth=lambda rules: rules.knowledge.secret_value),
        K.REMEDY: KnowledgeSpec("A remedy", dies=True, worth=lambda rules: rules.knowledge.remedy_value),
        K.GENEALOGY: KnowledgeSpec("A line of descent", dies=False, worth=lambda rules: rules.knowledge.genealogy_value),
    },
)
DYING_KNOWLEDGE = frozenset(kind for kind, spec in KNOWLEDGE.items() if spec.dies)
