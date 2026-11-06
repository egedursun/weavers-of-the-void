from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import Attribute, Facet, FacetGroup, IdeaKind, SkillKind, TraitKind, ValueAxis
from aerona.domain.enums.mortal import StressBreak
from aerona.domain.enums.society import KnowledgeBranch

A = Attribute
F = Facet
V = ValueAxis
S = SkillKind
T = TraitKind


@dataclass(frozen=True)
class AttributeSpec:
    label: str
    physical: bool
    seeds: tuple[str, ...]


ATTRIBUTES: MappingProxyType[Attribute, AttributeSpec] = MappingProxyType(
    {
        A.STRENGTH: AttributeSpec("Strength", True, ("strength",)),
        A.AGILITY: AttributeSpec("Agility", True, ("agility",)),
        A.TOUGHNESS: AttributeSpec("Toughness", True, ("endurance", "strength")),
        A.ENDURANCE: AttributeSpec("Endurance", True, ("endurance",)),
        A.RECUPERATION: AttributeSpec("Recuperation", True, ("endurance",)),
        A.DISEASE_RESISTANCE: AttributeSpec("Disease resistance", True, ("endurance", "willpower")),
        A.ANALYTICAL_ABILITY: AttributeSpec("Analytical ability", False, ("intellect",)),
        A.FOCUS: AttributeSpec("Focus", False, ("perception", "willpower")),
        A.WILLPOWER: AttributeSpec("Willpower", False, ("willpower",)),
        A.CREATIVITY: AttributeSpec("Creativity", False, ("creativity",)),
        A.INTUITION: AttributeSpec("Intuition", False, ("perception", "wisdom")),
        A.PATIENCE: AttributeSpec("Patience", False, ("wisdom",)),
        A.MEMORY: AttributeSpec("Memory", False, ("intellect",)),
        A.LINGUISTIC_ABILITY: AttributeSpec("Linguistic ability", False, ("charisma", "intellect")),
        A.SPATIAL_SENSE: AttributeSpec("Spatial sense", False, ("perception", "intellect")),
        A.MUSICALITY: AttributeSpec("Musicality", False, ("creativity", "perception")),
        A.KINAESTHETIC_SENSE: AttributeSpec("Kinaesthetic sense", False, ("agility",)),
        A.EMPATHY: AttributeSpec("Empathy", False, ("charisma", "wisdom")),
        A.SOCIAL_AWARENESS: AttributeSpec("Social awareness", False, ("charisma",)),
    }
)

SUMMARIES: MappingProxyType[str, tuple[Attribute, ...]] = MappingProxyType(
    {
        "strength": (A.STRENGTH,),
        "agility": (A.AGILITY,),
        "endurance": (A.ENDURANCE, A.TOUGHNESS),
        "willpower": (A.WILLPOWER,),
        "creativity": (A.CREATIVITY,),
        "intellect": (A.ANALYTICAL_ABILITY, A.MEMORY),
        "charisma": (A.SOCIAL_AWARENESS, A.EMPATHY, A.LINGUISTIC_ABILITY),
        "perception": (A.INTUITION, A.FOCUS),
        "wisdom": (A.PATIENCE, A.INTUITION, A.EMPATHY),
    }
)

SKILL_ATTRIBUTES: MappingProxyType[SkillKind, tuple[Attribute, ...]] = MappingProxyType(
    {
        S.BLADE: (A.STRENGTH, A.AGILITY, A.KINAESTHETIC_SENSE),
        S.SPEAR: (A.STRENGTH, A.AGILITY, A.KINAESTHETIC_SENSE),
        S.AXE: (A.STRENGTH, A.TOUGHNESS, A.KINAESTHETIC_SENSE),
        S.BLUNT: (A.STRENGTH, A.TOUGHNESS),
        S.BOW: (A.AGILITY, A.FOCUS, A.SPATIAL_SENSE),
        S.SLING: (A.AGILITY, A.SPATIAL_SENSE),
        S.THROWING: (A.AGILITY, A.SPATIAL_SENSE, A.KINAESTHETIC_SENSE),
        S.SHIELD: (A.STRENGTH, A.TOUGHNESS),
        S.UNARMED: (A.STRENGTH, A.AGILITY, A.KINAESTHETIC_SENSE),
        S.RIDING: (A.AGILITY, A.KINAESTHETIC_SENSE, A.EMPATHY),
        S.MOUNTED_COMBAT: (A.AGILITY, A.KINAESTHETIC_SENSE, A.STRENGTH),
        S.SIEGECRAFT: (A.ANALYTICAL_ABILITY, A.SPATIAL_SENSE),
        S.NAVAL_COMBAT: (A.AGILITY, A.SPATIAL_SENSE, A.FOCUS),
        S.BEAST_HANDLING: (A.EMPATHY, A.PATIENCE),
        S.TACTICS: (A.ANALYTICAL_ABILITY, A.INTUITION, A.SPATIAL_SENSE),
        S.STRATEGY: (A.ANALYTICAL_ABILITY, A.PATIENCE, A.MEMORY),
        S.LOGISTICS: (A.ANALYTICAL_ABILITY, A.MEMORY),
        S.LEADERSHIP: (A.WILLPOWER, A.SOCIAL_AWARENESS),
        S.INTIMIDATION: (A.STRENGTH, A.WILLPOWER),
        S.ORATORY: (A.LINGUISTIC_ABILITY, A.SOCIAL_AWARENESS, A.MUSICALITY),
        S.NEGOTIATION: (A.SOCIAL_AWARENESS, A.EMPATHY, A.PATIENCE),
        S.INTRIGUE: (A.SOCIAL_AWARENESS, A.INTUITION, A.MEMORY),
        S.ETIQUETTE: (A.SOCIAL_AWARENESS, A.MEMORY),
        S.DECEPTION: (A.SOCIAL_AWARENESS, A.LINGUISTIC_ABILITY, A.INTUITION),
        S.TEACHING: (A.PATIENCE, A.EMPATHY, A.LINGUISTIC_ABILITY),
        S.SMITHING: (A.STRENGTH, A.FOCUS, A.SPATIAL_SENSE),
        S.CARPENTRY: (A.SPATIAL_SENSE, A.FOCUS),
        S.MASONRY: (A.STRENGTH, A.SPATIAL_SENSE),
        S.WEAVING: (A.FOCUS, A.PATIENCE, A.KINAESTHETIC_SENSE),
        S.POTTERY: (A.KINAESTHETIC_SENSE, A.CREATIVITY),
        S.JEWELLING: (A.FOCUS, A.CREATIVITY, A.KINAESTHETIC_SENSE),
        S.SHIPWRIGHT: (A.SPATIAL_SENSE, A.ANALYTICAL_ABILITY),
        S.ENGINEERING: (A.ANALYTICAL_ABILITY, A.SPATIAL_SENSE),
        S.ALCHEMY: (A.ANALYTICAL_ABILITY, A.MEMORY, A.FOCUS),
        S.LORE: (A.MEMORY, A.ANALYTICAL_ABILITY),
        S.MEDICINE: (A.EMPATHY, A.MEMORY, A.FOCUS),
        S.SURGERY: (A.FOCUS, A.KINAESTHETIC_SENSE, A.ANALYTICAL_ABILITY),
        S.ASTRONOMY: (A.ANALYTICAL_ABILITY, A.SPATIAL_SENSE, A.PATIENCE),
        S.LAW: (A.MEMORY, A.ANALYTICAL_ABILITY),
        S.THEOLOGY: (A.MEMORY, A.INTUITION, A.WILLPOWER),
        S.LANGUAGES: (A.LINGUISTIC_ABILITY, A.MEMORY),
        S.WRITING: (A.LINGUISTIC_ABILITY, A.CREATIVITY, A.MUSICALITY),
        S.ACCOUNTING: (A.ANALYTICAL_ABILITY, A.MEMORY),
        S.HUNTING: (A.INTUITION, A.PATIENCE, A.AGILITY),
        S.TRACKING: (A.INTUITION, A.FOCUS),
        S.FORAGING: (A.INTUITION, A.MEMORY),
        S.SAILING: (A.SPATIAL_SENSE, A.ENDURANCE),
        S.NAVIGATION: (A.SPATIAL_SENSE, A.ANALYTICAL_ABILITY),
        S.MOUNTAINEERING: (A.ENDURANCE, A.STRENGTH, A.TOUGHNESS),
        S.SWIMMING: (A.ENDURANCE, A.STRENGTH, A.RECUPERATION),
        S.RITUAL: (A.MEMORY, A.SOCIAL_AWARENESS, A.MUSICALITY),
        S.PROPHECY: (A.INTUITION, A.CREATIVITY),
        S.SPELLCRAFT: (A.ANALYTICAL_ABILITY, A.FOCUS, A.WILLPOWER),
        S.SPIRIT_SPEAKING: (A.INTUITION, A.EMPATHY, A.WILLPOWER),
    }
)


@dataclass(frozen=True)
class FacetSpec:
    label: str
    group: FacetGroup
    leanings: MappingProxyType[ValueAxis, int] = field(default_factory=lambda: MappingProxyType({}))
    high: TraitKind | None = None
    low: TraitKind | None = None


def lean(**values: int) -> MappingProxyType[ValueAxis, int]:
    return MappingProxyType({ValueAxis(key if key != "perseverance" else "perseverance_value"): value for key, value in values.items()})


G = FacetGroup
FACETS: MappingProxyType[Facet, FacetSpec] = MappingProxyType(
    {
        F.ANXIETY: FacetSpec("Anxiety", G.EMOTIONAL, lean(superstition=20, xenophilia=-10), T.CRAVEN, T.BRAVE),
        F.ANGER: FacetSpec("Anger", G.EMOTIONAL, lean(martial=20, mercy=-15), T.WRATHFUL, T.PATIENT),
        F.DEPRESSION: FacetSpec("Depression", G.EMOTIONAL, lean(death=15, leisure=-10), T.MELANCHOLIC),
        F.SELF_CONSCIOUSNESS: FacetSpec("Self-consciousness", G.EMOTIONAL, lean(honour=15, hierarchy=10)),
        F.VULNERABILITY: FacetSpec("Vulnerability", G.EMOTIONAL, lean(martial=-15, perseverance=-10), T.IMPRESSIONABLE),
        F.CHEERFULNESS: FacetSpec("Cheerfulness", G.EMOTIONAL, lean(leisure=20, death=-10), T.SANGUINE, T.MELANCHOLIC),
        F.EXCITEMENT_SEEKING: FacetSpec("Excitement-seeking", G.EMOTIONAL, lean(competition=15, tradition=-15), T.RECKLESS),
        F.EMOTIONAL_STABILITY: FacetSpec("Emotional stability", G.EMOTIONAL, lean(perseverance=15, tradition=10), T.IRON_WILLED, T.FICKLE),
        F.FRIENDLINESS: FacetSpec("Friendliness", G.SOCIAL, lean(friendship=20, xenophilia=10)),
        F.GREGARIOUSNESS: FacetSpec("Gregariousness", G.SOCIAL, lean(friendship=15, leisure=10), T.GREGARIOUS, T.RECLUSIVE),
        F.ASSERTIVENESS: FacetSpec("Assertiveness", G.SOCIAL, lean(martial=15, competition=15)),
        F.TRUST: FacetSpec("Trust", G.SOCIAL, lean(truth=15, xenophilia=10), T.TRUSTING, T.PARANOID),
        F.ALTRUISM: FacetSpec("Altruism", G.SOCIAL, lean(mercy=20, wealth=-10), T.KIND, T.CRUEL),
        F.MODESTY: FacetSpec("Modesty", G.SOCIAL, lean(piety=10, hierarchy=-10), T.HUMBLE, T.PROUD),
        F.POLITENESS: FacetSpec("Politeness", G.SOCIAL, lean(tradition=15, hierarchy=10)),
        F.COOPERATION: FacetSpec("Cooperation", G.SOCIAL, lean(kinship=15, competition=-15)),
        F.VANITY: FacetSpec("Vanity", G.SOCIAL, lean(honour=10, artwork=10), T.PROUD),
        F.ENVY: FacetSpec("Envy", G.SOCIAL, lean(wealth=15, competition=10)),
        F.GRATITUDE: FacetSpec("Gratitude", G.SOCIAL, lean(loyalty=15, piety=10), T.FORGIVING, T.VENGEFUL),
        F.AMBITION: FacetSpec("Ambition", G.DRIVE, lean(wealth=15, competition=15, hierarchy=10), T.AMBITIOUS, T.CONTENT),
        F.PERSEVERANCE: FacetSpec("Perseverance", G.DRIVE, lean(perseverance=25), T.STUBBORN, T.FICKLE),
        F.ORDERLINESS: FacetSpec("Orderliness", G.DRIVE, lean(law=20, tradition=10)),
        F.DISCIPLINE: FacetSpec("Discipline", G.DRIVE, lean(martial=10, purity=15), T.ASCETIC, T.GLUTTONOUS),
        F.THOROUGHNESS: FacetSpec("Thoroughness", G.DRIVE, lean(craftsmanship=20, knowledge=10)),
        F.ACTIVITY_LEVEL: FacetSpec("Activity level", G.DRIVE, lean(competition=10, leisure=-15)),
        F.CAUTION: FacetSpec("Caution", G.DRIVE, lean(tradition=15, martial=-10), None, T.RECKLESS),
        F.IMAGINATION: FacetSpec("Imagination", G.MIND, lean(artwork=20, superstition=10)),
        F.CURIOSITY: FacetSpec("Curiosity", G.MIND, lean(knowledge=25, xenophilia=10), T.CURIOUS, T.INCURIOUS),
        F.ABSTRACTION: FacetSpec("Abstraction", G.MIND, lean(knowledge=20, tradition=-10), T.SCHOLARLY, T.ILLITERATE_PROUD),
        F.ARTISTIC_INCLINATION: FacetSpec("Artistic inclination", G.MIND, lean(artwork=25, craftsmanship=10)),
        F.TOLERANCE_OF_STRANGENESS: FacetSpec("Tolerance of strangeness", G.MIND, lean(xenophilia=20, purity=-15)),
        F.HUMOUR: FacetSpec("Humour", G.MIND, lean(leisure=15, piety=-10)),
        F.SENSE_OF_DUTY: FacetSpec("Sense of duty", G.MIND, lean(loyalty=15, law=15, honour=10), T.JUST, T.ARBITRARY),
        F.GREED: FacetSpec("Greed", G.MIND, lean(wealth=25, mercy=-10), T.GREEDY, T.GENEROUS),
    }
)


@dataclass(frozen=True)
class IdeaSpec:
    label: str
    beliefs: MappingProxyType[ValueAxis, int]
    gains: MappingProxyType[Attribute, int]
    costs: MappingProxyType[Attribute, int]
    facets: MappingProxyType[Facet, int]
    distraction: int = 5


def att(**values: int) -> MappingProxyType[Attribute, int]:
    return MappingProxyType({Attribute(key): value for key, value in values.items()})


def fac(**values: int) -> MappingProxyType[Facet, int]:
    return MappingProxyType({Facet(key): value for key, value in values.items()})


IK = IdeaKind
IDEAS: MappingProxyType[IdeaKind, IdeaSpec] = MappingProxyType(
    {
        IK.RATIONALISM: IdeaSpec("Rationalism", lean(knowledge=20, superstition=-20), att(analytical_ability=6), att(intuition=3), fac(curiosity=8)),
        IK.MYSTICISM: IdeaSpec("Mysticism", lean(superstition=20, piety=10, knowledge=-10), att(intuition=6), att(analytical_ability=3), fac(imagination=8)),
        IK.ASCETICISM: IdeaSpec(
            "Asceticism", lean(purity=20, wealth=-15, leisure=-15), att(willpower=6), att(social_awareness=3), fac(discipline=10, greed=-8)
        ),
        IK.MERCY_FOR_ALL: IdeaSpec("Mercy for all", lean(mercy=25, martial=-10), att(empathy=6), att(strength=2), fac(altruism=10, anger=-6)),
        IK.MARTIAL_CREED: IdeaSpec(
            "Martial creed", lean(martial=25, honour=10), att(strength=4, toughness=3), att(empathy=3), fac(assertiveness=8, caution=-6)
        ),
        IK.RULE_OF_LAW: IdeaSpec("Rule of law", lean(law=25, tradition=10), att(memory=4), att(creativity=3), fac(orderliness=10, sense_of_duty=6)),
        IK.FREE_SPIRIT: IdeaSpec(
            "Free spirit", lean(law=-20, leisure=10, xenophilia=10), att(creativity=6), att(patience=3), fac(excitement_seeking=8, orderliness=-8)
        ),
        IK.KIN_FIRST: IdeaSpec(
            "Kin first", lean(family=25, kinship=15, xenophilia=-10), att(willpower=3), att(social_awareness=2), fac(cooperation=6, trust=-4)
        ),
        IK.HONOUR_CODE: IdeaSpec("Honour code", lean(honour=25, truth=15), att(willpower=4), att(intuition=2), fac(sense_of_duty=8, self_consciousness=6)),
        IK.WANDERLUST: IdeaSpec(
            "Wanderlust", lean(xenophilia=20, tradition=-15), att(spatial_sense=6), att(patience=3), fac(curiosity=6, excitement_seeking=6)
        ),
        IK.MATERIALISM: IdeaSpec(
            "Materialism", lean(wealth=25, piety=-10), att(analytical_ability=3, social_awareness=3), att(empathy=3), fac(greed=10, ambition=6)
        ),
        IK.REVERENCE_FOR_NATURE: IdeaSpec(
            "Reverence for nature", lean(nature=25, wealth=-10), att(intuition=4, endurance=2), att(analytical_ability=2), fac(tolerance_of_strangeness=6)
        ),
        IK.CRAFT_DEVOTION: IdeaSpec(
            "Devotion to craft", lean(craftsmanship=25, perseverance=10), att(focus=6), att(social_awareness=3), fac(thoroughness=10, perseverance=6)
        ),
        IK.BEAUTY_ABOVE_ALL: IdeaSpec(
            "Beauty above all", lean(artwork=25, wealth=-5), att(creativity=4, musicality=4), att(analytical_ability=3), fac(artistic_inclination=10, vanity=4)
        ),
        IK.EGALITARIANISM: IdeaSpec("Equality of all", lean(hierarchy=-25, mercy=10), att(empathy=4), att(memory=2), fac(modesty=8, assertiveness=-4)),
        IK.DIVINE_ORDER: IdeaSpec(
            "Divine order", lean(piety=25, hierarchy=10, law=10), att(willpower=4), att(creativity=3), fac(sense_of_duty=8, tolerance_of_strangeness=-6)
        ),
    }
)

IT = IdeologyTenet
IDEOLOGY_IDEAS: MappingProxyType[IdeologyTenet, IdeaKind] = MappingProxyType(
    {
        IT.LEGALISM: IK.RULE_OF_LAW,
        IT.RESTRAINT: IK.MERCY_FOR_ALL,
        IT.EGALITARIANISM: IK.EGALITARIANISM,
        IT.DIVINE_RIGHT: IK.DIVINE_ORDER,
        IT.MERCANTILISM: IK.MATERIALISM,
        IT.MILITARISM: IK.MARTIAL_CREED,
        IT.ASCETICISM: IK.ASCETICISM,
        IT.RATIONALISM: IK.RATIONALISM,
        IT.NATURE_HARMONY: IK.REVERENCE_FOR_NATURE,
        IT.XENOPHOBIA: IK.KIN_FIRST,
        IT.COSMOPOLITANISM: IK.WANDERLUST,
        IT.ANTI_GOD: IK.FREE_SPIRIT,
        IT.CREATORISM: IK.DIVINE_ORDER,
    }
)

TK = TenetKind
TENET_IDEAS: MappingProxyType[TenetKind, IdeaKind] = MappingProxyType(
    {
        TK.PACIFISM: IK.MERCY_FOR_ALL,
        TK.HOLY_WAR: IK.MARTIAL_CREED,
        TK.ASCETICISM: IK.ASCETICISM,
        TK.SACRED_SUFFERING: IK.ASCETICISM,
        TK.PURITY_OF_BODY: IK.ASCETICISM,
        TK.ANCESTOR_VENERATION: IK.KIN_FIRST,
        TK.HUMAN_SACRIFICE: IK.DIVINE_ORDER,
        TK.ANIMAL_SACRIFICE: IK.DIVINE_ORDER,
        TK.CELIBATE_CLERGY: IK.ASCETICISM,
        TK.PROSELYTISM: IK.DIVINE_ORDER,
        TK.EXCLUSIVITY: IK.KIN_FIRST,
        TK.SYNCRETIC_OPENNESS: IK.WANDERLUST,
        TK.MONASTIC_LEARNING: IK.RATIONALISM,
        TK.ANTI_MAGIC: IK.RATIONALISM,
        TK.SANCTIFIED_MAGIC: IK.MYSTICISM,
        TK.JUDGEMENT_BY_DEEDS: IK.HONOUR_CODE,
        TK.JUDGEMENT_BY_FAITH: IK.MYSTICISM,
        TK.REINCARNATION: IK.MYSTICISM,
        TK.MARTYRDOM_GLORY: IK.HONOUR_CODE,
        TK.DIVINE_KINGSHIP: IK.DIVINE_ORDER,
        TK.DIETARY_LAW: IK.RULE_OF_LAW,
        TK.SACRED_SPECIES: IK.REVERENCE_FOR_NATURE,
        TK.PILGRIMAGE_DUTY: IK.WANDERLUST,
        TK.SOULS_REST: IK.MERCY_FOR_ALL,
    }
)

KB = KnowledgeBranch
BRANCH_IDEAS: MappingProxyType[KnowledgeBranch, IdeaKind] = MappingProxyType(
    {
        KB.AGRICULTURE: IK.REVERENCE_FOR_NATURE,
        KB.METALLURGY: IK.CRAFT_DEVOTION,
        KB.SEAFARING: IK.WANDERLUST,
        KB.WRITING: IK.BEAUTY_ABOVE_ALL,
        KB.ARCHITECTURE: IK.CRAFT_DEVOTION,
        KB.MEDICINE: IK.MERCY_FOR_ALL,
        KB.MAGIC: IK.MYSTICISM,
        KB.WARFARE: IK.MARTIAL_CREED,
        KB.ASTRONOMY: IK.RATIONALISM,
        KB.TRADE: IK.MATERIALISM,
        KB.SKY_NAVIGATION: IK.WANDERLUST,
        KB.SHIPBUILDING: IK.CRAFT_DEVOTION,
        KB.GATE_LORE: IK.MYSTICISM,
        KB.PATHFINDING: IK.WANDERLUST,
        KB.VOID_LIVING: IK.FREE_SPIRIT,
        KB.IMMORTALITY: IK.MYSTICISM,
        KB.BIOMANCY: IK.RATIONALISM,
        KB.FORBIDDEN: IK.FREE_SPIRIT,
    }
)

C = ConditionKind
CONDITION_ATTRIBUTES: MappingProxyType[ConditionKind, tuple[Attribute, ...]] = MappingProxyType(
    {
        C.CHRONIC_ILLNESS: (A.ENDURANCE, A.RECUPERATION, A.DISEASE_RESISTANCE),
        C.PARANOIA: (A.EMPATHY, A.SOCIAL_AWARENESS),
        C.VISIONS: (A.FOCUS, A.ANALYTICAL_ABILITY),
        C.RAGE: (A.PATIENCE, A.EMPATHY),
        C.MELANCHOLY: (A.FOCUS, A.WILLPOWER),
        C.ADDICTION: (A.WILLPOWER, A.RECUPERATION),
        C.AGE_BLINDNESS: (A.SPATIAL_SENSE, A.FOCUS),
        C.AGE_DEAFNESS: (A.MUSICALITY, A.LINGUISTIC_ABILITY),
        C.WITHERED_LIMB: (A.STRENGTH, A.AGILITY, A.KINAESTHETIC_SENSE),
        C.ENDLESS_HUNGER: (A.ENDURANCE, A.PATIENCE),
        C.POSSESSION: (A.WILLPOWER, A.MEMORY),
        C.VOID_TAINT: (A.EMPATHY, A.MEMORY),
        C.CHOSEN_MARK: (),
        C.DIVINE_BRAND: (),
    }
)

SB = StressBreak
BREAK_FACETS: MappingProxyType[StressBreak, tuple[Facet, ...]] = MappingProxyType(
    {
        SB.RAGE: (F.ANGER,),
        SB.FLIGHT: (F.ANXIETY, F.VULNERABILITY),
        SB.DESPAIR: (F.DEPRESSION,),
        SB.ZEAL: (F.SENSE_OF_DUTY,),
        SB.VICE: (F.EXCITEMENT_SEEKING, F.GREED),
        SB.REVELATION: (F.CURIOSITY, F.ABSTRACTION),
    }
)

STRESS_FACETS: MappingProxyType[Facet, int] = MappingProxyType(
    {F.ANXIETY: 1, F.VULNERABILITY: 1, F.DEPRESSION: 1, F.EMOTIONAL_STABILITY: -1, F.CHEERFULNESS: -1}
)
BOLD_FACETS: MappingProxyType[Facet, int] = MappingProxyType({F.ASSERTIVENESS: 1, F.EXCITEMENT_SEEKING: 1, F.CAUTION: -1, F.ANXIETY: -1})

NEW_AXES: MappingProxyType[ValueAxis, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        V.LAW: lean(tradition=40, hierarchy=30),
        V.LOYALTY: lean(honour=40, kinship=30),
        V.FAMILY: lean(kinship=60, death=10),
        V.FRIENDSHIP: lean(xenophilia=30, mercy=30),
        V.TRUTH: lean(honour=50, knowledge=10),
        V.CRAFTSMANSHIP: lean(tradition=20, wealth=20, knowledge=20),
        V.ARTWORK: lean(wealth=20, knowledge=20),
        V.COMPETITION: lean(martial=40, wealth=20, mercy=-10),
        V.PERSEVERANCE: lean(tradition=30, honour=20, martial=10),
        V.LEISURE: lean(wealth=30, martial=-20, purity=-20),
    }
)


def derived_axes(values: dict[ValueAxis, int]) -> dict[ValueAxis, int]:
    return {
        axis: max(-100, min(100, round(sum(values.get(source, 0) * weight for source, weight in weights.items()) / 100))) for axis, weights in NEW_AXES.items()
    }


def idea_for_beliefs(beliefs: dict[ValueAxis, int]) -> IdeaKind | None:
    best: tuple[float, IdeaKind] | None = None
    for kind, spec in IDEAS.items():
        fit = sum(beliefs.get(axis, 0) * weight for axis, weight in spec.beliefs.items())
        if fit > 0 and (best is None or fit > best[0]):
            best = (fit, kind)
    return best[1] if best else None
