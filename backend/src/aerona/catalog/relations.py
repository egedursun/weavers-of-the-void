from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from aerona.catalog.mind_split import fac
from aerona.core.total import total
from aerona.domain.enums.mind import Attribute, Facet, PreferenceKind, SkillKind, ThoughtKind, ValueAxis, WantKind
from aerona.domain.enums.relations import (
    AppealKind,
    CircleKind,
    ContestKind,
    ContestStake,
    GroupKind,
    InteractionKind,
    PassionKind,
    PassionSource,
    PersuasionAim,
    RelationType,
)
from aerona.rules.registry import Rules

K = InteractionKind
T = ThoughtKind
R = RelationType


@dataclass(frozen=True)
class InteractionSpec:
    label: str
    facets: MappingProxyType[Facet, int]
    mood: int = 0
    warmth: int = 0
    friendship: int = 0
    romance: int = 0
    familiarity: int = 2
    rivalry: int = 0
    thought: ThoughtKind | None = None
    mutual: bool = False
    romantic: bool = False
    hostile: bool = False
    min_familiarity: int = 0
    min_romance: int = 0
    skill: SkillKind | None = None
    wants: frozenset[WantKind] = field(default_factory=frozenset)
    notable: bool = False


def act(label: str, facets: dict[str, int], **rest: Any) -> InteractionSpec:
    return InteractionSpec(label, fac(**facets), **rest)


INTERACTIONS: Mapping[InteractionKind, InteractionSpec] = total(
    K,
    {
        K.CONVERSE: act("Talked", {"gregariousness": 40, "friendliness": 20}, friendship=2, familiarity=5, skill=SkillKind.ETIQUETTE),
        K.BEFRIEND: act("Sought friendship", {"friendliness": 50, "trust": 20}, warmth=10, friendship=6, familiarity=4, skill=SkillKind.ETIQUETTE),
        K.GOSSIP: act("Gossiped", {"gregariousness": 30, "politeness": -30}, friendship=3, familiarity=3),
        K.JOKE: act("Shared a joke", {"humour": 50, "cheerfulness": 30}, mood=2, friendship=4, familiarity=3, thought=T.LAUGHED_TOGETHER, mutual=True),
        K.COMFORT: act("Gave comfort", {"altruism": 50, "friendliness": 30}, warmth=10, friendship=6, familiarity=3, thought=T.WAS_COMFORTED),
        K.FLATTER: act("Flattered", {"politeness": 40, "ambition": 20}, friendship=3, familiarity=2, thought=T.WAS_FLATTERED, skill=SkillKind.ETIQUETTE),
        K.BOAST: act("Boasted", {"vanity": 50, "assertiveness": 30, "modesty": -40}, friendship=-1, rivalry=3, wants=frozenset({WantKind.WIN_GLORY})),
        K.INSULT: act("Insulted", {"anger": 50, "politeness": -50}, mood=-2, warmth=-10, friendship=-8, rivalry=6, thought=T.WAS_INSULTED, hostile=True),
        K.ARGUE: act("Argued", {"assertiveness": 40, "abstraction": 30}, friendship=-3, familiarity=2, rivalry=3, skill=SkillKind.ORATORY),
        K.FLIRT: act(
            "Flirted",
            {"excitement_seeking": 40, "friendliness": 20},
            mood=1,
            friendship=2,
            romance=6,
            romantic=True,
            skill=SkillKind.ETIQUETTE,
            wants=frozenset({WantKind.MARRY}),
        ),
        K.COURT: act(
            "Courted",
            {"friendliness": 30, "perseverance": 20},
            friendship=3,
            romance=8,
            romantic=True,
            min_romance=20,
            skill=SkillKind.ETIQUETTE,
            wants=frozenset({WantKind.MARRY}),
        ),
        K.PROPOSE: act(
            "Proposed", {"assertiveness": 20, "sense_of_duty": 20}, romance=4, romantic=True, min_romance=60, wants=frozenset({WantKind.MARRY}), notable=True
        ),
        K.SEDUCE: act(
            "Seduced",
            {"excitement_seeking": 50, "sense_of_duty": -40},
            romance=10,
            friendship=1,
            romantic=True,
            min_romance=40,
            skill=SkillKind.DECEPTION,
        ),
        K.QUARREL: act(
            "Quarrelled",
            {"anger": 50, "cooperation": -30},
            mood=-2,
            warmth=-5,
            friendship=-6,
            romance=-4,
            thought=T.QUARRELLED,
            mutual=True,
            hostile=True,
            min_familiarity=30,
        ),
        K.RECONCILE: act(
            "Reconciled",
            {"gratitude": 30, "cooperation": 40},
            friendship=8,
            rivalry=-4,
            thought=T.RECONCILED,
            mutual=True,
            min_familiarity=30,
            wants=frozenset({WantKind.MAKE_PEACE}),
            notable=True,
        ),
        K.TEACH: act(
            "Taught", {"altruism": 30, "orderliness": 20}, friendship=3, familiarity=3, skill=SkillKind.TEACHING, wants=frozenset({WantKind.FIND_A_TEACHER})
        ),
        K.GIFT: act("Gave a gift", {"altruism": 40, "greed": -40}, warmth=5, friendship=6, familiarity=2, thought=T.WAS_GIFTED),
        K.ASK_FAVOUR: act("Asked a favour", {"trust": 30, "modesty": -20}, warmth=15, friendship=-1, familiarity=2, skill=SkillKind.NEGOTIATION),
        K.CONFIDE_SECRET: act(
            "Confided", {"trust": 50, "friendliness": 20}, warmth=30, friendship=5, familiarity=4, thought=T.CONFIDED_IN, mutual=True, min_familiarity=40
        ),
        K.THREATEN: act(
            "Threatened",
            {"assertiveness": 40, "anger": 30, "politeness": -30},
            warmth=-10,
            friendship=-6,
            rivalry=4,
            thought=T.WAS_THREATENED,
            hostile=True,
            skill=SkillKind.INTIMIDATION,
        ),
        K.BRAWL: act(
            "Came to blows",
            {"anger": 60, "excitement_seeking": 20},
            mood=-1,
            warmth=-20,
            friendship=-4,
            rivalry=6,
            thought=T.BRAWLED,
            mutual=True,
            hostile=True,
            notable=True,
        ),
        K.APOLOGISE: act(
            "Apologised",
            {"modesty": 40, "cooperation": 30, "vanity": -30},
            warmth=5,
            friendship=4,
            rivalry=-3,
            thought=T.RECONCILED,
            min_familiarity=10,
            skill=SkillKind.ETIQUETTE,
            wants=frozenset({WantKind.MAKE_PEACE}),
            notable=True,
        ),
        K.SHARE_MEAL: act(
            "Shared a meal",
            {"gregariousness": 40, "altruism": 20},
            mood=1,
            warmth=10,
            friendship=5,
            familiarity=4,
            thought=T.ATTENDED_FEAST,
            mutual=True,
            notable=True,
        ),
        K.ASK_COUNSEL: act(
            "Asked counsel", {"trust": 30, "modesty": 20, "curiosity": 20}, warmth=10, friendship=3, familiarity=3, skill=SkillKind.NEGOTIATION, notable=True
        ),
    },
)


@dataclass(frozen=True)
class RelationSpec:
    label: str
    opinion_floor: int
    duties: bool
    inherits: bool
    ends: str
    hostile: bool = False
    hates: bool = False
    intimate: bool = False


RELATIONS: Mapping[RelationType, RelationSpec] = total(
    R,
    {
        R.ACQUAINTANCE: RelationSpec("Acquaintance", 0, duties=False, inherits=False, ends="when they stop meeting"),
        R.FRIEND: RelationSpec("Friend", 0, duties=False, inherits=False, ends="when friendship cools"),
        R.CLOSE_FRIEND: RelationSpec("Close friend", 5, duties=False, inherits=False, ends="when friendship cools"),
        R.BEST_FRIEND: RelationSpec("Best friend", 10, duties=False, inherits=False, ends="when another friend grows closer"),
        R.CONFIDANT: RelationSpec("Confidant", 10, duties=False, inherits=False, ends="when trust fades"),
        R.CRUSH: RelationSpec("Crush", 0, duties=False, inherits=False, ends="when the longing fades"),
        R.LOVER: RelationSpec("Lover", 10, duties=False, inherits=False, ends="when love fades on either side", intimate=True),
        R.EX_LOVER: RelationSpec("Former lover", 0, duties=False, inherits=False, ends="never; it is what remains of love"),
        R.SPOUSE: RelationSpec("Spouse", 15, duties=True, inherits=True, ends="at death or the end of the union", intimate=True),
        R.RIVAL: RelationSpec("Rival", 0, duties=False, inherits=False, ends="when rivalry fades", hostile=True),
        R.NEMESIS: RelationSpec("Nemesis", 0, duties=False, inherits=False, ends="when one of them falls", hostile=True, hates=True),
        R.ENEMY: RelationSpec("Enemy", 0, duties=False, inherits=False, ends="when hatred fades", hostile=True, hates=True),
        R.MENTOR: RelationSpec("Mentor", 5, duties=False, inherits=False, ends="when the teaching is done"),
        R.PROTEGE: RelationSpec("Protégé", 5, duties=False, inherits=False, ends="when the teaching is done"),
        R.COMRADE_IN_ARMS: RelationSpec("Comrade in arms", 10, duties=True, inherits=False, ends="when they no longer serve together"),
        R.DRINKING_COMPANION: RelationSpec("Drinking companion", 0, duties=False, inherits=False, ends="when they leave the hall"),
        R.PATRON: RelationSpec("Patron", 5, duties=True, inherits=False, ends="when the gap in wealth closes"),
        R.CLIENT: RelationSpec("Client", 5, duties=True, inherits=False, ends="when the gap in wealth closes"),
        R.BETROTHED: RelationSpec("Betrothed", 10, duties=True, inherits=False, ends="at the union, or by breaking the promise"),
        R.SWORN_KIN: RelationSpec("Sworn kin", 20, duties=True, inherits=True, ends="only by oathbreaking"),
        R.FOSTER: RelationSpec("Foster kin", 15, duties=True, inherits=True, ends="never; the raising stays"),
    },
)
RELATION_LABELS = MappingProxyType({kind: spec.label for kind, spec in RELATIONS.items()})
HOSTILE_KEYS = frozenset(kind.value for kind, spec in RELATIONS.items() if spec.hostile)
HATING_KEYS = frozenset(kind.value for kind, spec in RELATIONS.items() if spec.hates)
INTIMATE_KEYS = frozenset(kind.value for kind, spec in RELATIONS.items() if spec.intimate)
DUTY_RELATIONS = frozenset(kind for kind, spec in RELATIONS.items() if spec.duties)
INHERITING_RELATIONS = frozenset(kind for kind, spec in RELATIONS.items() if spec.inherits)


@dataclass(frozen=True)
class CircleSpec:
    label: str
    tastes: frozenset[PreferenceKind]
    axes: frozenset[ValueAxis]
    secret: bool = False
    fields: bool = False
    wagers: bool = False


CIRCLES: Mapping[CircleKind, CircleSpec] = total(
    CircleKind,
    {
        CircleKind.DRINKING_CIRCLE: CircleSpec("Drinking hall", frozenset({PreferenceKind.DRINK, PreferenceKind.FOOD}), frozenset({ValueAxis.LEISURE})),
        CircleKind.POETS_CIRCLE: CircleSpec(
            "Poets' circle", frozenset({PreferenceKind.ART_FORM, PreferenceKind.ARTWORK_SUBJECT}), frozenset({ValueAxis.ARTWORK})
        ),
        CircleKind.HUNTING_CIRCLE: CircleSpec("Hunting lodge", frozenset({PreferenceKind.CREATURE, PreferenceKind.TERRAIN}), frozenset({ValueAxis.NATURE})),
        CircleKind.SECRET_SOCIETY: CircleSpec("Secret society", frozenset(), frozenset({ValueAxis.TRUTH, ValueAxis.SUPERSTITION}), secret=True),
        CircleKind.STUDY_CIRCLE: CircleSpec("Study circle", frozenset(), frozenset({ValueAxis.KNOWLEDGE})),
        CircleKind.PRAYER_CIRCLE: CircleSpec("Prayer circle", frozenset({PreferenceKind.DEITY_ASPECT}), frozenset({ValueAxis.PIETY})),
        CircleKind.MUSIC_CIRCLE: CircleSpec("Music circle", frozenset({PreferenceKind.SEASON, PreferenceKind.WEATHER}), frozenset({ValueAxis.COMPETITION})),
        CircleKind.CRAFT_CIRCLE: CircleSpec(
            "Craft circle", frozenset({PreferenceKind.CRAFT, PreferenceKind.MATERIAL, PreferenceKind.ACTIVITY}), frozenset({ValueAxis.CRAFTSMANSHIP})
        ),
        CircleKind.SPORT_CLUB: CircleSpec("Sport club", frozenset({PreferenceKind.GAME}), frozenset(), fields=True),
        CircleKind.GAMING_CIRCLE: CircleSpec("Gaming circle", frozenset(), frozenset({ValueAxis.WEALTH}), wagers=True),
    },
)

PASSION_LABELS: MappingProxyType[PassionKind, str] = MappingProxyType(
    {
        PassionKind.LOVE: "Love",
        PassionKind.LOYALTY: "Loyalty",
        PassionKind.HATRED: "Hatred",
        PassionKind.DEVOTION: "Devotion",
        PassionKind.AMBITION: "Ambition",
        PassionKind.ENVY: "Envy",
        PassionKind.GRIEF: "Grief",
        PassionKind.CURIOSITY: "Curiosity",
        PassionKind.FEAR: "Fear",
        PassionKind.SHAME: "Shame",
        PassionKind.PRIDE: "Pride",
        PassionKind.JEALOUSY: "Jealousy",
        PassionKind.ADMIRATION: "Admiration",
        PassionKind.OBSESSION: "Obsession",
    }
)
PASSION_SOURCE_LABELS: MappingProxyType[PassionSource, str] = MappingProxyType(
    {
        PassionSource.RELATIONSHIP: "A bond with them",
        PassionSource.OATH: "An oath",
        PassionSource.MEMORY: "A memory that shaped them",
        PassionSource.UPBRINGING: "Their upbringing",
        PassionSource.DIVINE: "A god's touch",
    }
)


@dataclass(frozen=True)
class AppealSpec:
    label: str
    facets: MappingProxyType[Facet, int]


APPEALS: Mapping[AppealKind, AppealSpec] = total(
    AppealKind,
    {
        AppealKind.BELIEF: AppealSpec("An appeal to a belief", fac(abstraction=20)),
        AppealKind.SELF_INTEREST: AppealSpec("An appeal to self-interest", fac(greed=40, ambition=30)),
        AppealKind.AUTHORITY: AppealSpec("An appeal to authority", fac(sense_of_duty=30, orderliness=20, assertiveness=-30)),
        AppealKind.EVIDENCE: AppealSpec("An appeal to evidence", fac(curiosity=30, abstraction=30)),
        AppealKind.FEAR: AppealSpec("An appeal to fear", fac(anxiety=40, vulnerability=30, emotional_stability=-20)),
        AppealKind.FEELING: AppealSpec("An appeal to feeling", fac(altruism=30, vulnerability=30, gratitude=20)),
        AppealKind.BOND: AppealSpec("An appeal to a bond", fac(trust=30, sense_of_duty=30, cooperation=20)),
    },
)
AIM_LABELS: Mapping[PersuasionAim, str] = total(
    PersuasionAim,
    {
        PersuasionAim.BELIEF: "A belief",
        PersuasionAim.DECISION: "A ruler's decision",
        PersuasionAim.FAITH: "A faith",
        PersuasionAim.VOTE: "A vote in council",
        PersuasionAim.TREATY: "A treaty",
        PersuasionAim.SURRENDER: "A surrender",
        PersuasionAim.CONFESSION: "A confession",
    },
)
GROUP_LABELS: MappingProxyType[GroupKind, str] = total(
    GroupKind,
    {
        GroupKind.HOUSEHOLD: "Household",
        GroupKind.COURT: "Court",
        GroupKind.CIRCLE: "Circle",
        GroupKind.WARBAND: "Warband",
        GroupKind.CREW: "Crew",
        GroupKind.CELL: "Cell",
        GroupKind.BAND: "Band",
        GroupKind.TEAM: "Team",
    },
)


@dataclass(frozen=True)
class ContestSpec:
    label: str
    skills: tuple[SkillKind, ...]
    attributes: tuple[Attribute, ...]
    work: str | None = None
    races: bool = False
    crafted: bool = False


CONTESTS: Mapping[ContestKind, ContestSpec] = total(
    ContestKind,
    {
        ContestKind.RIDDLE_GAME: ContestSpec("Riddle game", (SkillKind.LORE,), (Attribute.MEMORY, Attribute.INTUITION)),
        ContestKind.INSULT_CONTEST: ContestSpec(
            "Insult contest", (SkillKind.ORATORY, SkillKind.WRITING), (Attribute.LINGUISTIC_ABILITY, Attribute.CREATIVITY), "verbal"
        ),
        ContestKind.DEBATE: ContestSpec("Debate", (SkillKind.ORATORY, SkillKind.LAW), (Attribute.ANALYTICAL_ABILITY, Attribute.SOCIAL_AWARENESS)),
        ContestKind.GAME_OF_SKILL: ContestSpec("Game of skill", (SkillKind.TACTICS, SkillKind.STRATEGY), (Attribute.SPATIAL_SENSE, Attribute.FOCUS)),
        ContestKind.TRIAL_OF_WISDOM: ContestSpec("Trial of wisdom", (SkillKind.LAW, SkillKind.THEOLOGY), (Attribute.INTUITION, Attribute.EMPATHY)),
        ContestKind.SONG_CONTEST: ContestSpec("Song contest", (SkillKind.ORATORY, SkillKind.RITUAL), (Attribute.MUSICALITY, Attribute.CREATIVITY), "musical"),
        ContestKind.STORYTELLING: ContestSpec(
            "Storytelling", (SkillKind.LORE, SkillKind.ORATORY), (Attribute.CREATIVITY, Attribute.LINGUISTIC_ABILITY), "verbal"
        ),
        ContestKind.RACE: ContestSpec("Race", (SkillKind.RIDING, SkillKind.SAILING, SkillKind.SWIMMING), (Attribute.ENDURANCE, Attribute.AGILITY), races=True),
        ContestKind.CRAFT_CONTEST: ContestSpec(
            "Craft contest", (SkillKind.SMITHING, SkillKind.WEAVING, SkillKind.JEWELLING), (Attribute.CREATIVITY, Attribute.KINAESTHETIC_SENSE), crafted=True
        ),
    },
)
STAKE_LABELS: Mapping[ContestStake, str] = total(
    ContestStake,
    {
        ContestStake.HONOUR: "Honour",
        ContestStake.UNION: "A union",
        ContestStake.WAGER: "A wager",
        ContestStake.OFFICE: "A place at court",
        ContestStake.CAPTIVE: "A captive's freedom",
        ContestStake.DIVINE_FAVOUR: "A god's favour",
        ContestStake.LAND: "A holding of land",
        ContestStake.FREEDOM: "The contestant's own freedom",
        ContestStake.KNOWLEDGE: "A kind of knowledge",
    },
)


@dataclass(frozen=True)
class Tuning:
    weight: Callable[[Rules], int]
    effect: Callable[[Rules], int]


TUNING: Mapping[InteractionKind, Tuning] = total(
    K,
    {
        K.CONVERSE: Tuning(lambda rules: rules.interactions.converse_weight, lambda rules: rules.interactions.converse_effect),
        K.BEFRIEND: Tuning(lambda rules: rules.interactions.befriend_weight, lambda rules: rules.interactions.befriend_effect),
        K.GOSSIP: Tuning(lambda rules: rules.interactions.gossip_weight, lambda rules: rules.interactions.gossip_effect),
        K.JOKE: Tuning(lambda rules: rules.interactions.joke_weight, lambda rules: rules.interactions.joke_effect),
        K.COMFORT: Tuning(lambda rules: rules.interactions.comfort_weight, lambda rules: rules.interactions.comfort_effect),
        K.FLATTER: Tuning(lambda rules: rules.interactions.flatter_weight, lambda rules: rules.interactions.flatter_effect),
        K.BOAST: Tuning(lambda rules: rules.interactions.boast_weight, lambda rules: rules.interactions.boast_effect),
        K.INSULT: Tuning(lambda rules: rules.interactions.insult_weight, lambda rules: rules.interactions.insult_effect),
        K.ARGUE: Tuning(lambda rules: rules.interactions.argue_weight, lambda rules: rules.interactions.argue_effect),
        K.FLIRT: Tuning(lambda rules: rules.interactions.flirt_weight, lambda rules: rules.interactions.flirt_effect),
        K.COURT: Tuning(lambda rules: rules.interactions.court_weight, lambda rules: rules.interactions.court_effect),
        K.PROPOSE: Tuning(lambda rules: rules.interactions.propose_weight, lambda rules: rules.interactions.propose_effect),
        K.SEDUCE: Tuning(lambda rules: rules.interactions.seduce_weight, lambda rules: rules.interactions.seduce_effect),
        K.QUARREL: Tuning(lambda rules: rules.interactions.quarrel_weight, lambda rules: rules.interactions.quarrel_effect),
        K.RECONCILE: Tuning(lambda rules: rules.interactions.reconcile_weight, lambda rules: rules.interactions.reconcile_effect),
        K.TEACH: Tuning(lambda rules: rules.interactions.teach_weight, lambda rules: rules.interactions.teach_effect),
        K.GIFT: Tuning(lambda rules: rules.interactions.gift_weight, lambda rules: rules.interactions.gift_effect),
        K.ASK_FAVOUR: Tuning(lambda rules: rules.interactions.ask_favour_weight, lambda rules: rules.interactions.ask_favour_effect),
        K.CONFIDE_SECRET: Tuning(lambda rules: rules.interactions.confide_secret_weight, lambda rules: rules.interactions.confide_secret_effect),
        K.THREATEN: Tuning(lambda rules: rules.interactions.threaten_weight, lambda rules: rules.interactions.threaten_effect),
        K.BRAWL: Tuning(lambda rules: rules.interactions.brawl_weight, lambda rules: rules.interactions.brawl_effect),
        K.APOLOGISE: Tuning(lambda rules: rules.interactions.apologise_weight, lambda rules: rules.interactions.apologise_effect),
        K.SHARE_MEAL: Tuning(lambda rules: rules.interactions.share_meal_weight, lambda rules: rules.interactions.share_meal_effect),
        K.ASK_COUNSEL: Tuning(lambda rules: rules.interactions.ask_counsel_weight, lambda rules: rules.interactions.ask_counsel_effect),
    },
)
NOTABLE_INTERACTIONS = frozenset(kind for kind, spec in INTERACTIONS.items() if spec.notable)
