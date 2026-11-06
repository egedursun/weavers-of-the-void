from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.catalog.mind_split import fac, lean
from aerona.domain.enums.mind import (
    ActKind,
    DreamKind,
    DreamReading,
    Emotion,
    Facet,
    MemoryKind,
    MoodState,
    NeedGroup,
    NeedKind,
    ThoughtKind,
    ValueAxis,
)

E = Emotion
F = Facet
T = ThoughtKind
N = NeedKind
G = NeedGroup


@dataclass(frozen=True)
class EmotionSpec:
    label: str
    valence: int
    amplifiers: MappingProxyType[Facet, int]


def amp(**values: int) -> MappingProxyType[Facet, int]:
    return fac(**values)


EMOTIONS: MappingProxyType[Emotion, EmotionSpec] = MappingProxyType(
    {
        E.JOY: EmotionSpec("Joy", 1, amp(cheerfulness=1)),
        E.CONTENTMENT: EmotionSpec("Contentment", 1, amp(emotional_stability=1)),
        E.PRIDE: EmotionSpec("Pride", 1, amp(vanity=1, modesty=-1)),
        E.LOVE: EmotionSpec("Love", 1, amp(friendliness=1)),
        E.GRATITUDE: EmotionSpec("Gratitude", 1, amp(gratitude=1)),
        E.RELIEF: EmotionSpec("Relief", 1, amp(anxiety=1)),
        E.HOPE: EmotionSpec("Hope", 1, amp(cheerfulness=1, depression=-1)),
        E.AWE: EmotionSpec("Awe", 1, amp(imagination=1, artistic_inclination=1)),
        E.AMUSEMENT: EmotionSpec("Amusement", 1, amp(humour=1)),
        E.FEAR: EmotionSpec("Fear", -1, amp(anxiety=1, vulnerability=1)),
        E.ANXIETY: EmotionSpec("Anxiety", -1, amp(anxiety=1, emotional_stability=-1)),
        E.ANGER: EmotionSpec("Anger", -1, amp(anger=1)),
        E.RAGE: EmotionSpec("Rage", -1, amp(anger=1, emotional_stability=-1)),
        E.GRIEF: EmotionSpec("Grief", -1, amp(depression=1, emotional_stability=-1)),
        E.SADNESS: EmotionSpec("Sadness", -1, amp(depression=1, cheerfulness=-1)),
        E.SHAME: EmotionSpec("Shame", -1, amp(self_consciousness=1)),
        E.GUILT: EmotionSpec("Guilt", -1, amp(self_consciousness=1, sense_of_duty=1)),
        E.ENVY: EmotionSpec("Envy", -1, amp(envy=1)),
        E.JEALOUSY: EmotionSpec("Jealousy", -1, amp(envy=1, trust=-1)),
        E.DISGUST: EmotionSpec("Disgust", -1, amp(tolerance_of_strangeness=-1)),
        E.LONELINESS: EmotionSpec("Loneliness", -1, amp(gregariousness=1)),
        E.BOREDOM: EmotionSpec("Boredom", -1, amp(excitement_seeking=1, activity_level=1)),
        E.DESPAIR: EmotionSpec("Despair", -1, amp(depression=1, vulnerability=1)),
        E.LONGING: EmotionSpec("Longing", -1, amp(imagination=1)),
    }
)


@dataclass(frozen=True)
class ThoughtSpec:
    emotion: Emotion
    intensity: int
    label: str
    beliefs: MappingProxyType[ValueAxis, int] = field(default_factory=lambda: MappingProxyType({}))
    facets: MappingProxyType[Facet, int] = field(default_factory=lambda: MappingProxyType({}))


def th(emotion: Emotion, intensity: int, label: str, beliefs: dict[str, int] | None = None, facets: dict[str, int] | None = None) -> ThoughtSpec:
    return ThoughtSpec(emotion, intensity, label, lean(**(beliefs or {})), fac(**(facets or {})))


THOUGHTS: MappingProxyType[ThoughtKind, ThoughtSpec] = MappingProxyType(
    {
        T.MARRIED: th(E.JOY, 60, "Married", {"family": 8}, {"cheerfulness": 3}),
        T.CHILD_BORN: th(E.LOVE, 70, "A child was born to them", {"family": 10}, {"altruism": 3}),
        T.SAW_KIN_DIE: th(E.GRIEF, 75, "Saw kin die", {"family": 6}, {"depression": 4}),
        T.LOST_SPOUSE: th(E.GRIEF, 85, "Lost their spouse", {"family": 5}, {"depression": 6, "cheerfulness": -4}),
        T.LOST_CHILD: th(E.DESPAIR, 90, "Lost a child", {"family": 6}, {"depression": 8, "vulnerability": 4}),
        T.BETRAYED: th(E.ANGER, 70, "Was betrayed", {"loyalty": 6}, {"trust": -8}),
        T.WAS_INSULTED: th(E.SHAME, 40, "Was insulted", {}, {"self_consciousness": 3}),
        T.WAS_GIFTED: th(E.GRATITUDE, 35, "Received a gift"),
        T.WAS_SAVED: th(E.GRATITUDE, 75, "Was saved from harm", {"loyalty": 6}, {"gratitude": 6, "trust": 3}),
        T.WAS_CHEATED: th(E.ANGER, 45, "Was cheated", {"truth": 4}, {"trust": -4}),
        T.WON_BATTLE: th(E.PRIDE, 60, "Won a battle", {"martial": 6}, {"assertiveness": 4}),
        T.DEFEATED: th(E.SHAME, 60, "Was defeated", {}, {"caution": 4, "assertiveness": -3}),
        T.WON_DUEL: th(E.PRIDE, 55, "Won a duel", {"competition": 5}, {"assertiveness": 3}),
        T.LOST_DUEL: th(E.SHAME, 50, "Lost a duel", {}, {"self_consciousness": 3}),
        T.WAS_WOUNDED: th(E.FEAR, 45, "Was wounded", {}, {"caution": 3}),
        T.WAS_MAIMED: th(E.DESPAIR, 80, "Was maimed", {"death": 6}, {"caution": 6, "vulnerability": 5}),
        T.LOST_LIMB_BUT_LIVED: th(E.RELIEF, 70, "Lost a limb but lived", {"perseverance_value": 8}, {"perseverance": 5}),
        T.WAS_HEALED: th(E.RELIEF, 40, "Was healed"),
        T.FELL_ILL: th(E.FEAR, 50, "Fell ill", {}, {"anxiety": 3}),
        T.WITNESSED_ATROCITY: th(E.DISGUST, 80, "Witnessed an atrocity", {"mercy": 8}, {"anxiety": 5, "trust": -4}),
        T.WAS_CAPTURED: th(E.FEAR, 70, "Was taken captive", {}, {"trust": -5, "anxiety": 4}),
        T.WAS_FREED: th(E.RELIEF, 70, "Was set free", {"loyalty": 4}, {"gratitude": 4}),
        T.KILLED_FOE: th(E.PRIDE, 50, "Killed a foe", {"martial": 4}, {"anger": 2}),
        T.ROSE_IN_RANK: th(E.PRIDE, 55, "Rose in rank", {"hierarchy": 4}, {"ambition": 3}),
        T.FELL_IN_RANK: th(E.SHAME, 55, "Fell in rank", {}, {"self_consciousness": 3}),
        T.GAINED_RENOWN: th(E.PRIDE, 45, "Gained renown", {}, {"vanity": 3}),
        T.WAS_SHAMED: th(E.SHAME, 55, "Was shamed before others", {"honour": 4}, {"self_consciousness": 4}),
        T.WAS_PUNISHED: th(E.SHAME, 60, "Was punished", {"law": -4}, {"anger": 3}),
        T.WAS_CONQUERED: th(E.ANGER, 65, "Their home was conquered", {"loyalty": 4}, {"trust": -3}),
        T.PRAYED_ANSWERED: th(E.AWE, 70, "A prayer was answered", {"piety": 10}, {"cheerfulness": 3}),
        T.PRAYER_IGNORED: th(E.SADNESS, 40, "A prayer went unanswered", {"piety": -5}),
        T.SAW_MIRACLE: th(E.AWE, 80, "Saw a miracle", {"piety": 10, "superstition": 6}, {"imagination": 4}),
        T.LOST_FAITH: th(E.DESPAIR, 65, "Lost their faith", {"piety": -10}),
        T.FOUND_FAITH: th(E.HOPE, 60, "Found faith", {"piety": 10}),
        T.SAW_DESECRATION: th(E.ANGER, 70, "Saw something holy desecrated", {"piety": 6, "purity": 4}),
        T.TOUCHED_BY_A_GOD: th(E.AWE, 75, "Felt the touch of a god", {"piety": 8}),
        T.ADMIRED_GREAT_WORK: th(E.AWE, 45, "Admired a great work", {"artwork": 6}, {"artistic_inclination": 3}),
        T.HEARD_GREAT_MUSIC: th(E.JOY, 40, "Heard great music", {"artwork": 4}, {"artistic_inclination": 2}),
        T.ATTENDED_FEAST: th(E.JOY, 35, "Attended a feast", {"leisure": 3}, {"gregariousness": 2}),
        T.MADE_MASTERWORK: th(E.PRIDE, 80, "Made a masterwork", {"craftsmanship": 8}, {"perseverance": 4}),
        T.LEARNED_SOMETHING: th(E.JOY, 30, "Learned something new", {"knowledge": 3}, {"curiosity": 2}),
        T.TAUGHT_APPRENTICE: th(E.PRIDE, 30, "Taught an apprentice", {"knowledge": 2}),
        T.TOOK_IDEA_TO_HEART: th(E.HOPE, 45, "Took an idea to heart"),
        T.ATE_FINE_FOOD: th(E.CONTENTMENT, 20, "Ate well"),
        T.WENT_HUNGRY: th(E.DESPAIR, 45, "Went hungry"),
        T.WENT_THIRSTY: th(E.DESPAIR, 50, "Went thirsty"),
        T.DRANK_WELL: th(E.CONTENTMENT, 15, "Drank their fill"),
        T.SLEPT_WELL: th(E.CONTENTMENT, 20, "Slept well"),
        T.EXHAUSTED: th(E.SADNESS, 35, "Was worn out"),
        T.LIVED_IN_COMFORT: th(E.CONTENTMENT, 25, "Lived in comfort"),
        T.LIVED_IN_SQUALOR: th(E.DISGUST, 35, "Lived in squalor"),
        T.FELT_HALE: th(E.JOY, 20, "Felt hale"),
        T.FELT_UNWELL: th(E.ANXIETY, 35, "Felt unwell"),
        T.FELT_SAFE: th(E.RELIEF, 20, "Felt safe"),
        T.FELT_UNSAFE: th(E.FEAR, 40, "Felt unsafe"),
        T.AMONG_KIN: th(E.LOVE, 25, "Was among kin"),
        T.MISSED_KIN: th(E.LONGING, 30, "Missed their kin"),
        T.AMONG_FRIENDS: th(E.JOY, 25, "Was among friends"),
        T.FELT_LONELY: th(E.LONELINESS, 35, "Felt lonely"),
        T.LOVED: th(E.LOVE, 30, "Felt loved"),
        T.LONGED_FOR_LOVE: th(E.LONGING, 30, "Longed for love"),
        T.HAD_PEACE_AND_QUIET: th(E.CONTENTMENT, 20, "Had peace and quiet"),
        T.CROWDED: th(E.ANXIETY, 25, "Felt crowded"),
        T.RESPECTED: th(E.PRIDE, 25, "Was respected"),
        T.OVERLOOKED: th(E.ENVY, 30, "Felt overlooked"),
        T.BELONGED: th(E.CONTENTMENT, 25, "Felt they belonged"),
        T.ADRIFT: th(E.LONELINESS, 35, "Felt adrift"),
        T.FELT_PURPOSE: th(E.PRIDE, 25, "Felt their life had purpose"),
        T.LACKED_PURPOSE: th(E.SADNESS, 35, "Felt their life lacked purpose"),
        T.PRAYED_IN_PEACE: th(E.CONTENTMENT, 20, "Prayed in peace"),
        T.FAITH_UNMET: th(E.LONGING, 30, "Longed for something to believe"),
        T.LEARNED_NOTHING: th(E.BOREDOM, 25, "Learned nothing new"),
        T.MADE_SOMETHING: th(E.PRIDE, 25, "Made something"),
        T.NOTHING_MADE: th(E.BOREDOM, 25, "Made nothing"),
        T.SAW_BEAUTY: th(E.AWE, 25, "Saw something beautiful"),
        T.SURROUNDED_BY_UGLINESS: th(E.SADNESS, 25, "Saw nothing beautiful"),
        T.WALKED_IN_NATURE: th(E.CONTENTMENT, 20, "Walked in the wild"),
        T.CUT_OFF_FROM_NATURE: th(E.LONGING, 25, "Was cut off from the wild"),
        T.HAD_ADVENTURE: th(E.JOY, 30, "Had an adventure"),
        T.RESTLESS: th(E.BOREDOM, 30, "Felt restless"),
        T.TESTED_IN_COMBAT: th(E.PRIDE, 30, "Was tested in combat"),
        T.BLADE_RUSTING: th(E.BOREDOM, 25, "Felt their blade rusting"),
        T.PROSPERED: th(E.CONTENTMENT, 25, "Prospered"),
        T.WANTED_FOR_MONEY: th(E.ANXIETY, 35, "Wanted for money"),
        T.ENJOYED_LEISURE: th(E.AMUSEMENT, 20, "Enjoyed some leisure"),
        T.BORED: th(E.BOREDOM, 25, "Was bored"),
        T.LIVED_IN_ORDER: th(E.CONTENTMENT, 20, "Lived in good order"),
        T.LIVED_IN_DISORDER: th(E.ANXIETY, 35, "Lived amid disorder"),
        T.RELIVED_MEMORY: th(E.SADNESS, 50, "Relived a memory"),
        T.MOURNED: th(E.GRIEF, 55, "Mourned"),
        T.MADE_PEACE_WITH_LOSS: th(E.RELIEF, 40, "Made peace with a loss", {}, {"emotional_stability": 3}),
        T.HAD_NIGHTMARE: th(E.FEAR, 45, "Had a nightmare"),
        T.HAD_GOOD_DREAM: th(E.HOPE, 30, "Had a good dream"),
        T.DREAMED_OF_LONGING: th(E.LONGING, 40, "Dreamed of what they long for"),
        T.RECEIVED_VISITATION: th(E.AWE, 70, "Was visited in a dream", {"piety": 6, "superstition": 4}),
        T.SENT_BY_THE_CREATOR: th(E.AWE, 50, "Felt something the Creator sent"),
    }
)


@dataclass(frozen=True)
class NeedSpec:
    group: NeedGroup
    label: str
    met: ThoughtKind
    unmet: ThoughtKind
    facets: MappingProxyType[Facet, int] = field(default_factory=lambda: MappingProxyType({}))
    beliefs: MappingProxyType[ValueAxis, int] = field(default_factory=lambda: MappingProxyType({}))


def need(
    group: NeedGroup, label: str, met: ThoughtKind, unmet: ThoughtKind, facets: dict[str, int] | None = None, *, beliefs: dict[str, int] | None = None
) -> NeedSpec:
    return NeedSpec(group, label, met, unmet, fac(**(facets or {})), lean(**(beliefs or {})))


NEEDS: MappingProxyType[NeedKind, NeedSpec] = MappingProxyType(
    {
        N.SUSTENANCE: need(G.BODY, "Food", T.ATE_FINE_FOOD, T.WENT_HUNGRY, {"discipline": -20}),
        N.DRINK: need(G.BODY, "Drink", T.DRANK_WELL, T.WENT_THIRSTY),
        N.REST: need(G.BODY, "Rest", T.SLEPT_WELL, T.EXHAUSTED, {"activity_level": -30}),
        N.COMFORT: need(G.BODY, "Comfort", T.LIVED_IN_COMFORT, T.LIVED_IN_SQUALOR, {"discipline": -30}, beliefs={"leisure": 20, "wealth": 15}),
        N.HEALTH: need(G.BODY, "Health", T.FELT_HALE, T.FELT_UNWELL, {"anxiety": 20}),
        N.SAFETY: need(G.BODY, "Safety", T.FELT_SAFE, T.FELT_UNSAFE, {"anxiety": 40, "caution": 20}),
        N.FAMILY: need(G.SOCIAL, "Family", T.AMONG_KIN, T.MISSED_KIN, {"friendliness": 20}, beliefs={"family": 40, "kinship": 20}),
        N.FRIENDS: need(G.SOCIAL, "Friends", T.AMONG_FRIENDS, T.FELT_LONELY, {"gregariousness": 40, "friendliness": 20}, beliefs={"friendship": 40}),
        N.ROMANCE: need(G.SOCIAL, "Romance", T.LOVED, T.LONGED_FOR_LOVE, {"friendliness": 20, "imagination": 10}),
        N.SOLITUDE: need(G.SOCIAL, "Solitude", T.HAD_PEACE_AND_QUIET, T.CROWDED, {"gregariousness": -50, "abstraction": 15}),
        N.STATUS: need(G.SOCIAL, "Status", T.RESPECTED, T.OVERLOOKED, {"ambition": 30, "vanity": 30, "modesty": -20}, beliefs={"hierarchy": 20, "honour": 15}),
        N.BELONGING: need(G.SOCIAL, "Belonging", T.BELONGED, T.ADRIFT, {"cooperation": 20}, beliefs={"kinship": 20, "loyalty": 15}),
        N.FAITH: need(G.SPIRIT, "Faith", T.PRAYED_IN_PEACE, T.FAITH_UNMET, {}, beliefs={"piety": 60, "superstition": 15}),
        N.PURPOSE: need(G.SPIRIT, "Purpose", T.FELT_PURPOSE, T.LACKED_PURPOSE, {"ambition": 20, "sense_of_duty": 20}, beliefs={"perseverance_value": 15}),
        N.LEARNING: need(G.SPIRIT, "Learning", T.LEARNED_SOMETHING, T.LEARNED_NOTHING, {"curiosity": 50, "abstraction": 20}, beliefs={"knowledge": 40}),
        N.CREATING: need(
            G.SPIRIT, "Creation", T.MADE_SOMETHING, T.NOTHING_MADE, {"imagination": 30, "artistic_inclination": 30}, beliefs={"craftsmanship": 30}
        ),
        N.BEAUTY: need(G.SPIRIT, "Beauty", T.SAW_BEAUTY, T.SURROUNDED_BY_UGLINESS, {"artistic_inclination": 50}, beliefs={"artwork": 40}),
        N.NATURE: need(G.SPIRIT, "Nature", T.WALKED_IN_NATURE, T.CUT_OFF_FROM_NATURE, {"tolerance_of_strangeness": 10}, beliefs={"nature": 50}),
        N.ADVENTURE: need(G.ACTION, "Adventure", T.HAD_ADVENTURE, T.RESTLESS, {"excitement_seeking": 50, "caution": -20}, beliefs={"xenophilia": 20}),
        N.FIGHTING: need(
            G.ACTION, "Combat", T.TESTED_IN_COMBAT, T.BLADE_RUSTING, {"anger": 20, "assertiveness": 20, "excitement_seeking": 20}, beliefs={"martial": 40}
        ),
        N.WEALTH: need(G.ACTION, "Wealth", T.PROSPERED, T.WANTED_FOR_MONEY, {"greed": 50}, beliefs={"wealth": 40}),
        N.PLEASURE: need(G.ACTION, "Leisure", T.ENJOYED_LEISURE, T.BORED, {"excitement_seeking": 20, "discipline": -30, "humour": 15}, beliefs={"leisure": 40}),
        N.ORDER: need(G.ACTION, "Order", T.LIVED_IN_ORDER, T.LIVED_IN_DISORDER, {"orderliness": 50}, beliefs={"law": 40, "tradition": 15}),
    }
)

MEMORY_THOUGHTS: MappingProxyType[MemoryKind, ThoughtKind] = MappingProxyType(
    {
        MemoryKind.HARMED_ME: T.WAS_WOUNDED,
        MemoryKind.MAIMED_ME: T.WAS_MAIMED,
        MemoryKind.SAVED_ME: T.WAS_SAVED,
        MemoryKind.BETRAYED_ME: T.BETRAYED,
        MemoryKind.BROKE_OATH: T.BETRAYED,
        MemoryKind.HUMILIATED_ME: T.WAS_INSULTED,
        MemoryKind.GIFTED_ME: T.WAS_GIFTED,
        MemoryKind.CONVERTED_ME: T.FOUND_FAITH,
        MemoryKind.CONQUERED_US: T.WAS_CONQUERED,
        MemoryKind.FREED_US: T.WAS_FREED,
        MemoryKind.CHEATED_US: T.WAS_CHEATED,
        MemoryKind.TAUGHT_ME: T.LEARNED_SOMETHING,
        MemoryKind.HELD_CAPTIVE: T.WAS_CAPTURED,
        MemoryKind.DESECRATED_HOLY: T.SAW_DESECRATION,
        MemoryKind.DIVINE_WILL: T.TOUCHED_BY_A_GOD,
    }
)

ATROCITIES = frozenset({ActKind.EXECUTION, ActKind.MUTILATION, ActKind.HUMAN_SACRIFICE, ActKind.GUEST_KILLING})

MOOD_ORDER: tuple[MoodState, ...] = (
    MoodState.ELATED,
    MoodState.CONTENT,
    MoodState.FINE,
    MoodState.UNEASY,
    MoodState.UNHAPPY,
    MoodState.MISERABLE,
    MoodState.BROKEN,
)

DREAM_LABELS: MappingProxyType[DreamKind, str] = MappingProxyType(
    {
        DreamKind.ORDINARY: "An ordinary dream",
        DreamKind.NIGHTMARE: "A nightmare",
        DreamKind.LONGING: "A dream of longing",
        DreamKind.PROPHETIC: "A prophetic dream",
        DreamKind.VISITATION: "A visitation",
        DreamKind.SHARED: "A shared dream",
    }
)

READING_LABELS: MappingProxyType[DreamReading, str] = MappingProxyType(
    {
        DreamReading.UNREAD: "Not read",
        DreamReading.OMEN_OF_WAR: "An omen of war",
        DreamReading.OMEN_OF_PLENTY: "An omen of plenty",
        DreamReading.OMEN_OF_DEATH: "An omen of death",
        DreamReading.OMEN_OF_FAVOUR: "An omen of favour",
        DreamReading.WARNING: "A warning",
        DreamReading.CALL_TO_JOURNEY: "A call to journey",
        DreamReading.CALL_TO_LOVE: "A call to love",
    }
)


@dataclass(frozen=True)
class ReadingSpec:
    thought: ThoughtKind
    beliefs: MappingProxyType[ValueAxis, int]
    facets: MappingProxyType[Facet, int]


READINGS: MappingProxyType[DreamReading, ReadingSpec] = MappingProxyType(
    {
        DreamReading.OMEN_OF_WAR: ReadingSpec(T.HAD_NIGHTMARE, lean(martial=8), fac(assertiveness=3)),
        DreamReading.OMEN_OF_PLENTY: ReadingSpec(T.HAD_GOOD_DREAM, lean(leisure=4), fac(cheerfulness=3)),
        DreamReading.OMEN_OF_DEATH: ReadingSpec(T.HAD_NIGHTMARE, lean(death=6), fac(anxiety=4)),
        DreamReading.OMEN_OF_FAVOUR: ReadingSpec(T.HAD_GOOD_DREAM, lean(piety=6), fac(cheerfulness=2)),
        DreamReading.WARNING: ReadingSpec(T.HAD_NIGHTMARE, lean(tradition=4), fac(caution=5)),
        DreamReading.CALL_TO_JOURNEY: ReadingSpec(T.DREAMED_OF_LONGING, lean(xenophilia=6), fac(excitement_seeking=4)),
        DreamReading.CALL_TO_LOVE: ReadingSpec(T.DREAMED_OF_LONGING, lean(family=4, friendship=4), fac(friendliness=3)),
    }
)

NEED_READINGS: MappingProxyType[NeedGroup, DreamReading] = MappingProxyType(
    {
        G.BODY: DreamReading.OMEN_OF_PLENTY,
        G.SOCIAL: DreamReading.CALL_TO_LOVE,
        G.SPIRIT: DreamReading.OMEN_OF_FAVOUR,
        G.ACTION: DreamReading.CALL_TO_JOURNEY,
    }
)
