from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.genetics import GeneticEffect, Locus
from aerona.domain.enums.living import LineTrait
from aerona.domain.enums.mind import Attribute, SkillKind, TraitKind
from aerona.domain.enums.polity import HouseTrait
from aerona.rules.registry import Rules

A = Attribute
S = SkillKind
G = GeneticEffect
T = TraitKind
HIGH = "high"
LOW = "low"


def frozen[K, V](values: Mapping[K, V] | None = None) -> MappingProxyType[K, V]:
    return MappingProxyType(dict(values or {}))


@dataclass(frozen=True)
class LocusEffect:
    stats: MappingProxyType[str, int] = field(default_factory=frozen)
    attributes: MappingProxyType[Attribute, int] = field(default_factory=frozen)
    skills: MappingProxyType[SkillKind, int] = field(default_factory=frozen)
    effects: MappingProxyType[GeneticEffect, int] = field(default_factory=frozen)
    line_trait: LineTrait | None = None
    traits: tuple[tuple[str, TraitKind], ...] = ()


def effect(
    *,
    stats: dict[str, int] | None = None,
    attributes: dict[Attribute, int] | None = None,
    skills: dict[SkillKind, int] | None = None,
    effects: dict[GeneticEffect, int] | None = None,
    line_trait: LineTrait | None = None,
    traits: tuple[tuple[str, TraitKind], ...] = (),
) -> LocusEffect:
    return LocusEffect(frozen(stats), frozen(attributes), frozen(skills), frozen(effects), line_trait, traits)


NONE = effect()
GIFT = effect(line_trait=LineTrait.GIFT)

LOCUS_EFFECTS: Mapping[Locus, LocusEffect] = total(
    Locus,
    {
        Locus.HEIGHT: effect(line_trait=LineTrait.SIZE),
        Locus.BUILD: effect(stats={"strength": 2, "agility": -2}),
        Locus.SKIN: NONE,
        Locus.HAIR_COLOUR: NONE,
        Locus.HAIR_TEXTURE: NONE,
        Locus.EYE_COLOUR: NONE,
        Locus.FACE: NONE,
        Locus.VOICE: NONE,
        Locus.PROPORTIONS: effect(stats={"agility": 2}, attributes={A.KINAESTHETIC_SENSE: 2}),
        Locus.MARKINGS: NONE,
        Locus.MUSCLE: effect(stats={"strength": 5}, attributes={A.STRENGTH: 6}, line_trait=LineTrait.STRENGTH),
        Locus.STAMINA: effect(stats={"endurance": 5}, attributes={A.ENDURANCE: 6}, line_trait=LineTrait.HARDINESS, traits=((HIGH, T.HARDY),)),
        Locus.AGILITY: effect(stats={"agility": 5}, attributes={A.AGILITY: 6, A.KINAESTHETIC_SENSE: 2}, line_trait=LineTrait.SPEED),
        Locus.METABOLISM: effect(attributes={A.ENDURANCE: 2, A.RECUPERATION: 2}, effects={G.LIFESPAN: -1, G.HEALING: 1}),
        Locus.COLD_TOLERANCE: effect(effects={G.COLD: 1}, line_trait=LineTrait.CLIMATE_TOLERANCE),
        Locus.HEAT_TOLERANCE: effect(effects={G.HEAT: 1}, line_trait=LineTrait.CLIMATE_TOLERANCE),
        Locus.LUNG_CAPACITY: effect(attributes={A.ENDURANCE: 2}, skills={S.SWIMMING: 20, S.MOUNTAINEERING: 15, S.SAILING: 5}, line_trait=LineTrait.AQUATIC),
        Locus.BONE_DENSITY: effect(stats={"strength": 1}, attributes={A.TOUGHNESS: 6}, line_trait=LineTrait.HARDINESS),
        Locus.WOUND_HEALING: effect(attributes={A.RECUPERATION: 6}, effects={G.HEALING: 2}, line_trait=LineTrait.REGENERATION),
        Locus.AGEING_PACE: effect(effects={G.LIFESPAN: -2}),
        Locus.PAIN_SENSE: effect(attributes={A.WILLPOWER: -3}, skills={S.MEDICINE: 5}, effects={G.STRESS: 1}),
        Locus.SIGHT: effect(
            stats={"perception": 4},
            attributes={A.FOCUS: 2},
            skills={S.BOW: 15, S.SLING: 10, S.THROWING: 10, S.FIREARMS: 10, S.ASTRONOMY: 10, S.NAVIGATION: 5, S.PILOTING: 5},
            traits=((HIGH, T.SHARP_SIGHTED),),
        ),
        Locus.HEARING: effect(
            stats={"perception": 3}, attributes={A.SOCIAL_AWARENESS: 2, A.MUSICALITY: 2}, skills={S.TRACKING: 10, S.INTRIGUE: 10, S.LANGUAGES: 5}
        ),
        Locus.SMELL: effect(stats={"perception": 2}, skills={S.TRACKING: 15, S.HUNTING: 10, S.FORAGING: 10, S.ALCHEMY: 10, S.MEDICINE: 5}),
        Locus.TASTE: effect(attributes={A.CREATIVITY: 1}, skills={S.FORAGING: 10, S.ALCHEMY: 10}),
        Locus.NIGHT_VISION: effect(stats={"perception": 2}, skills={S.HUNTING: 10, S.TRACKING: 10, S.INTRIGUE: 10, S.NAVIGATION: 5}),
        Locus.EXCITABILITY: effect(
            attributes={A.PATIENCE: -5, A.FOCUS: -2, A.CREATIVITY: 2},
            effects={G.STRESS: 1},
            line_trait=LineTrait.DOCILITY,
            traits=((HIGH, T.PASSIONATE), (LOW, T.CALM)),
        ),
        Locus.SOCIABILITY: effect(
            stats={"charisma": 3},
            attributes={A.SOCIAL_AWARENESS: 4, A.EMPATHY: 2},
            skills={S.ORATORY: 10, S.NEGOTIATION: 10, S.ETIQUETTE: 5},
            traits=((HIGH, T.GREGARIOUS), (LOW, T.ALOOF)),
        ),
        Locus.RISK_APPETITE: effect(attributes={A.WILLPOWER: 2, A.PATIENCE: -2}, traits=((HIGH, T.ADVENTUROUS), (LOW, T.CAUTIOUS))),
        Locus.ATTENTION: effect(attributes={A.FOCUS: 6}, traits=((HIGH, T.VIGILANT), (LOW, T.SCATTERBRAINED))),
        Locus.STRESS_RESPONSE: effect(
            attributes={A.WILLPOWER: -5},
            effects={G.STRESS: 2, G.MADNESS: 1},
            line_trait=LineTrait.NERVOUS_SYSTEM,
            traits=((HIGH, T.ANXIOUS), (LOW, T.RESILIENT)),
        ),
        Locus.MEMORY: effect(
            stats={"intellect": 2},
            attributes={A.MEMORY: 6},
            skills={S.LORE: 10, S.LAW: 10, S.LANGUAGES: 5, S.THEOLOGY: 5},
            line_trait=LineTrait.SAPIENCE,
            traits=((HIGH, T.RETENTIVE),),
        ),
        Locus.SPATIAL_SENSE: effect(
            attributes={A.SPATIAL_SENSE: 6},
            skills={S.NAVIGATION: 10, S.ENGINEERING: 10, S.MASONRY: 10, S.SIEGECRAFT: 5, S.CARPENTRY: 5, S.SHIPWRIGHT: 5},
        ),
        Locus.LANGUAGE_EASE: effect(
            attributes={A.LINGUISTIC_ABILITY: 6},
            skills={S.LANGUAGES: 20, S.WRITING: 10, S.ORATORY: 5},
            traits=((HIGH, T.ELOQUENT), (LOW, T.TONGUE_TIED)),
        ),
        Locus.NUMBER_SENSE: effect(
            stats={"intellect": 2},
            attributes={A.ANALYTICAL_ABILITY: 6},
            skills={S.ACCOUNTING: 20, S.ASTRONOMY: 10, S.ENGINEERING: 10, S.CRYPTOGRAPHY: 10, S.SCIENCE: 10, S.COMPUTING: 10},
            traits=((HIGH, T.NUMERATE),),
        ),
        Locus.MUSICAL_EAR: effect(attributes={A.MUSICALITY: 6}, skills={S.RITUAL: 5, S.ORATORY: 5, S.LANGUAGES: 5}, traits=((HIGH, T.MUSICAL),)),
        Locus.COORDINATION: effect(
            attributes={A.KINAESTHETIC_SENSE: 6, A.AGILITY: 2},
            skills={
                S.SMITHING: 10,
                S.CARPENTRY: 10,
                S.JEWELLING: 10,
                S.SURGERY: 10,
                S.BLADE: 5,
                S.BOW: 5,
                S.RIDING: 5,
                S.WEAVING: 5,
                S.POTTERY: 5,
            },
            traits=((HIGH, T.NIMBLE),),
        ),
        Locus.LONGEVITY: effect(effects={G.LIFESPAN: 1}, line_trait=LineTrait.LIFESPAN),
        Locus.FERTILITY: effect(effects={G.FERTILITY: 1}),
        Locus.TWINNING: NONE,
        Locus.DISEASE_RESISTANCE: effect(effects={G.DISEASE: -1}, line_trait=LineTrait.DISEASE_RESISTANCE),
        Locus.MADNESS: effect(effects={G.MADNESS: 1}),
        Locus.COLOUR_BLINDNESS: effect(skills={S.WEAVING: -30, S.POTTERY: -30, S.JEWELLING: -30}),
        Locus.GIANT_BLOOD: effect(line_trait=LineTrait.SIZE),
        Locus.DIVINE_BLOOD: NONE,
        Locus.CURSE_MARKER: effect(effects={G.LIFESPAN: -1}),
        Locus.GIFT_ELEMENTAL_FIRE: GIFT,
        Locus.GIFT_ELEMENTAL_WATER: GIFT,
        Locus.GIFT_EARTH: GIFT,
        Locus.GIFT_STORM: GIFT,
        Locus.GIFT_LIFE: GIFT,
        Locus.GIFT_DEATH: GIFT,
        Locus.GIFT_MIND: GIFT,
        Locus.GIFT_ILLUSION: GIFT,
        Locus.GIFT_DIVINATION: GIFT,
        Locus.GIFT_WARDING: GIFT,
        Locus.GIFT_BINDING: GIFT,
        Locus.GIFT_SUMMONING: GIFT,
        Locus.GIFT_BLOOD: GIFT,
        Locus.GIFT_VOID: GIFT,
    },
)

EFFECT_SCALES: Mapping[GeneticEffect, Callable[[Rules], int]] = total(
    GeneticEffect,
    {
        G.DISEASE: lambda rules: rules.genetics.disease_pct,
        G.FERTILITY: lambda rules: rules.genetics.fertility_pct,
        G.MADNESS: lambda rules: rules.genetics.madness_pct,
        G.LIFESPAN: lambda rules: rules.genetics.longevity_pct,
        G.HEALING: lambda rules: rules.genetics.healing_pct,
        G.STRESS: lambda rules: rules.genetics.stress_pct,
        G.COLD: lambda rules: rules.genetics.climate_health,
        G.HEAT: lambda rules: rules.genetics.climate_health,
    },
)

GENETIC_EFFECT_LABELS: Mapping[GeneticEffect, str] = total(
    GeneticEffect,
    {
        G.DISEASE: "Chance of catching a sickness",
        G.FERTILITY: "Chance of children",
        G.MADNESS: "Chance a mind breaks under strain",
        G.LIFESPAN: "Lifespan",
        G.HEALING: "Chance a wound heals",
        G.STRESS: "Stress gained",
        G.COLD: "Health in cold lands",
        G.HEAT: "Health in hot lands",
    },
)

HOUSE_TRAIT_ALLELES: Mapping[HouseTrait, tuple[Locus, str]] = total(
    HouseTrait,
    {
        HouseTrait.LONG_LIVED: (Locus.LONGEVITY, "enduring"),
        HouseTrait.GIANT_BLOODED: (Locus.GIANT_BLOOD, "giant"),
        HouseTrait.GOD_BLOODED: (Locus.DIVINE_BLOOD, "divine"),
        HouseTrait.CURSED: (Locus.CURSE_MARKER, "marked"),
        HouseTrait.FERTILE: (Locus.FERTILITY, "fruitful"),
        HouseTrait.SEER_GIFT: (Locus.GIFT_DIVINATION, "gifted"),
        HouseTrait.STRONG_BLOODED: (Locus.MUSCLE, HIGH),
        HouseTrait.SWIFT: (Locus.AGILITY, HIGH),
        HouseTrait.QUICK_HEALING: (Locus.WOUND_HEALING, HIGH),
        HouseTrait.SHARP_SENSED: (Locus.SIGHT, HIGH),
        HouseTrait.STEADY: (Locus.STRESS_RESPONSE, LOW),
        HouseTrait.QUICK_MINDED: (Locus.MEMORY, HIGH),
    },
)

HOUSE_TRAIT_LABELS: Mapping[HouseTrait, str] = total(
    HouseTrait,
    {
        HouseTrait.LONG_LIVED: "long-lived",
        HouseTrait.GIANT_BLOODED: "giant-blooded",
        HouseTrait.GOD_BLOODED: "god-blooded",
        HouseTrait.CURSED: "cursed",
        HouseTrait.FERTILE: "fertile",
        HouseTrait.SEER_GIFT: "gifted with sight",
        HouseTrait.STRONG_BLOODED: "strong-blooded",
        HouseTrait.SWIFT: "swift",
        HouseTrait.QUICK_HEALING: "quick to heal",
        HouseTrait.SHARP_SENSED: "sharp of sense",
        HouseTrait.STEADY: "steady under strain",
        HouseTrait.QUICK_MINDED: "quick of mind",
    },
)

HOUSE_TRAIT_SOURCES: Mapping[HouseTrait, str] = total(
    HouseTrait,
    {
        HouseTrait.SEER_GIFT: "a seer was born to the line",
        HouseTrait.GIANT_BLOODED: "the line bore giants",
        HouseTrait.LONG_LIVED: "its elders lived long",
        HouseTrait.FERTILE: "its line was fertile",
        HouseTrait.CURSED: "a curse fell on the line",
        HouseTrait.GOD_BLOODED: "it carries a god's descent",
        HouseTrait.STRONG_BLOODED: "its members are born strong",
        HouseTrait.SWIFT: "its members are born quick of reflex",
        HouseTrait.QUICK_HEALING: "its members heal quickly",
        HouseTrait.SHARP_SENSED: "its members are born sharp-sighted",
        HouseTrait.STEADY: "its members stay calm under strain",
        HouseTrait.QUICK_MINDED: "its members are born with long memories",
    },
)

EFFECT_POINTS = frozenset({G.COLD, G.HEAT})

ATTRIBUTE_WORDS: Mapping[Attribute, str] = total(
    Attribute,
    {
        A.STRENGTH: "strength",
        A.AGILITY: "agility",
        A.TOUGHNESS: "toughness",
        A.ENDURANCE: "endurance",
        A.RECUPERATION: "recuperation",
        A.DISEASE_RESISTANCE: "resistance to sickness",
        A.ANALYTICAL_ABILITY: "analytical ability",
        A.FOCUS: "focus",
        A.WILLPOWER: "willpower",
        A.CREATIVITY: "creativity",
        A.INTUITION: "intuition",
        A.PATIENCE: "patience",
        A.MEMORY: "memory",
        A.LINGUISTIC_ABILITY: "ease with language",
        A.SPATIAL_SENSE: "spatial sense",
        A.MUSICALITY: "musicality",
        A.KINAESTHETIC_SENSE: "sense of the body",
        A.EMPATHY: "empathy",
        A.SOCIAL_AWARENESS: "social awareness",
    },
)

STAT_WORDS: Mapping[str, str] = MappingProxyType(
    {
        "strength": "Strength",
        "agility": "Agility",
        "endurance": "Endurance",
        "perception": "Perception",
        "intellect": "Intellect",
        "charisma": "Charisma",
    }
)
