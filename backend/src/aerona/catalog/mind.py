from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.catalog.thoughts import NEEDS
from aerona.core.total import total
from aerona.domain.enums.body import Capacity, ConditionKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, MortalRole
from aerona.domain.enums.mind import (
    ActKind,
    MemoryKind,
    OpinionComponent,
    PressureKind,
    Profession,
    SkillFamily,
    SkillKind,
    TraitEffect,
    TraitFamily,
    TraitKind,
    ValueAxis,
)
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import Passion

V = ValueAxis
T = TraitKind
S = SkillKind
E = TraitEffect
M = MemoryKind
OC = OpinionComponent
A = ActKind
P = PressureKind

VALUE_LABELS = MappingProxyType(
    {
        V.HONOUR: ("Pragmatism", "Honour"),
        V.TRADITION: ("Innovation", "Tradition"),
        V.HIERARCHY: ("Equality", "Hierarchy"),
        V.MARTIAL: ("Peace", "Martial glory"),
        V.PIETY: ("Worldliness", "Piety"),
        V.PURITY: ("Tolerance of the unclean", "Purity"),
        V.KINSHIP: ("Individualism", "Clan loyalty"),
        V.MERCY: ("Cruelty", "Mercy"),
        V.KNOWLEDGE: ("Scorn of learning", "Learning"),
        V.WEALTH: ("Austerity", "Commerce and display"),
        V.NATURE: ("Mastery over nature", "Harmony with nature"),
        V.SUPERSTITION: ("Rationalism", "Omen-reading"),
        V.XENOPHILIA: ("Xenophobia", "Openness to strangers"),
        V.DEATH: ("Fear of death", "Veneration of the dead"),
        V.LAW: ("Independence", "Law"),
        V.LOYALTY: ("Opportunism", "Loyalty"),
        V.FAMILY: ("Self", "Family"),
        V.FRIENDSHIP: ("Self-reliance", "Friendship"),
        V.TRUTH: ("Expedience", "Honesty"),
        V.CRAFTSMANSHIP: ("Indifference to craft", "Craftsmanship"),
        V.ARTWORK: ("Indifference to art", "Artwork"),
        V.COMPETITION: ("Harmony", "Competition"),
        V.PERSEVERANCE: ("Ease", "Perseverance"),
        V.LEISURE: ("Industry", "Leisure"),
    }
)

DOMAIN_VALUES: MappingProxyType[Domain, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        domain: MappingProxyType(values)
        for domain, values in {
            Domain.SEA: {V.XENOPHILIA: 25, V.NATURE: 15, V.SUPERSTITION: 10, V.PERSEVERANCE: 10},
            Domain.FIRE: {V.MARTIAL: 20, V.PURITY: 20, V.TRADITION: -10, V.CRAFTSMANSHIP: 15},
            Domain.EARTH: {V.TRADITION: 25, V.NATURE: 20, V.KINSHIP: 10, V.FAMILY: 10, V.PERSEVERANCE: 10},
            Domain.SKY: {V.HIERARCHY: 15, V.PIETY: 15, V.KNOWLEDGE: 10, V.LAW: 10},
            Domain.STORM: {V.MARTIAL: 25, V.SUPERSTITION: 15, V.MERCY: -10, V.COMPETITION: 10},
            Domain.DEATH: {V.DEATH: 40, V.PIETY: 10, V.MERCY: -5, V.FAMILY: 10},
            Domain.LIFE: {V.MERCY: 25, V.NATURE: 20, V.DEATH: -20, V.FAMILY: 10, V.LEISURE: 10},
            Domain.DREAM: {V.SUPERSTITION: 30, V.KNOWLEDGE: 10, V.TRADITION: -5, V.LEISURE: 10, V.ARTWORK: 10},
            Domain.TIME: {V.TRADITION: 25, V.KNOWLEDGE: 15, V.PERSEVERANCE: 15},
            Domain.LIGHT: {V.PURITY: 25, V.PIETY: 20, V.MERCY: 10, V.TRUTH: 20},
            Domain.SHADOW: {V.HONOUR: -20, V.SUPERSTITION: 15, V.XENOPHILIA: -10, V.TRUTH: -15},
            Domain.WAR: {V.MARTIAL: 40, V.HONOUR: 15, V.MERCY: -15, V.COMPETITION: 20, V.LOYALTY: 10},
            Domain.CRAFT: {V.KNOWLEDGE: 20, V.WEALTH: 15, V.TRADITION: -10, V.CRAFTSMANSHIP: 30},
            Domain.KNOWLEDGE: {V.KNOWLEDGE: 40, V.SUPERSTITION: -15, V.TRADITION: -10, V.TRUTH: 15},
            Domain.LOVE: {V.MERCY: 25, V.KINSHIP: 20, V.MARTIAL: -15, V.FAMILY: 20, V.FRIENDSHIP: 20},
            Domain.TRICKERY: {V.HONOUR: -30, V.WEALTH: 15, V.HIERARCHY: -10, V.TRUTH: -25, V.LAW: -15},
            Domain.HUNT: {V.MARTIAL: 15, V.NATURE: 25, V.KINSHIP: 10, V.COMPETITION: 10, V.PERSEVERANCE: 10},
            Domain.PLANTS: {V.NATURE: 35, V.MERCY: 10, V.MARTIAL: -10, V.LEISURE: 10},
            Domain.BONE: {V.TRADITION: 15, V.PURITY: -10, V.CRAFTSMANSHIP: 10},
            Domain.BLOOD: {V.KINSHIP: 25, V.MARTIAL: 15, V.MERCY: -15, V.FAMILY: 20, V.LOYALTY: 10},
            Domain.SOUND: {V.KNOWLEDGE: 10, V.XENOPHILIA: 15, V.TRADITION: 10, V.ARTWORK: 20},
            Domain.STONE: {V.TRADITION: 30, V.HIERARCHY: 15, V.XENOPHILIA: -10, V.PERSEVERANCE: 20, V.LAW: 10},
            Domain.ICE: {V.PURITY: 20, V.TRADITION: 15, V.MERCY: -10, V.PERSEVERANCE: 15},
            Domain.MADNESS: {V.SUPERSTITION: 30, V.TRADITION: -20, V.HIERARCHY: -10, V.LAW: -20, V.ARTWORK: 10},
            Domain.TRADE: {V.WEALTH: 35, V.XENOPHILIA: 25, V.MARTIAL: -10, V.COMPETITION: 15},
            Domain.ROAD: {V.XENOPHILIA: 30, V.TRADITION: -15, V.KINSHIP: -10, V.FRIENDSHIP: 10},
            Domain.PLAGUE: {V.PURITY: 25, V.XENOPHILIA: -20, V.LAW: 10},
            Domain.HARVEST: {V.NATURE: 25, V.KINSHIP: 15, V.TRADITION: 15, V.FAMILY: 15, V.PERSEVERANCE: 10},
            Domain.MOON: {V.SUPERSTITION: 25, V.NATURE: 10, V.ARTWORK: 10},
            Domain.SUN: {V.HIERARCHY: 25, V.PIETY: 20, V.PURITY: 10, V.LAW: 15},
            Domain.STAR: {V.KNOWLEDGE: 25, V.SUPERSTITION: 20, V.PIETY: 10, V.ARTWORK: 10},
            Domain.LIES: {V.HONOUR: -35, V.KNOWLEDGE: -10, V.WEALTH: 10, V.TRUTH: -35},
            Domain.OATH: {V.HONOUR: 40, V.TRADITION: 15, V.KINSHIP: 10, V.LOYALTY: 25, V.TRUTH: 20},
            Domain.MEMORY: {V.TRADITION: 30, V.KNOWLEDGE: 10, V.FAMILY: 15},
            Domain.HUNGER: {V.WEALTH: -20, V.MERCY: -15, V.MARTIAL: 15, V.PERSEVERANCE: 15, V.LEISURE: -15},
            Domain.GLASS: {V.KNOWLEDGE: 20, V.PURITY: 15, V.WEALTH: 10, V.ARTWORK: 15, V.CRAFTSMANSHIP: 10},
            Domain.SALT: {V.PURITY: 20, V.WEALTH: 15, V.TRADITION: 10, V.PERSEVERANCE: 10},
            Domain.ASH: {V.PURITY: 10, V.TRADITION: -10, V.PERSEVERANCE: 10},
            Domain.BORDER: {V.XENOPHILIA: -25, V.MARTIAL: 15, V.KINSHIP: 15, V.LOYALTY: 15},
            Domain.SLEEP: {V.MERCY: 15, V.MARTIAL: -20, V.LEISURE: 25},
            Domain.TECHNOLOGY: {V.KNOWLEDGE: 25, V.CRAFTSMANSHIP: 20, V.TRADITION: -15},
            Domain.MACHINES: {V.CRAFTSMANSHIP: 30, V.KNOWLEDGE: 15, V.NATURE: -15},
            Domain.CITIES: {V.LAW: 15, V.WEALTH: 15, V.XENOPHILIA: 10, V.NATURE: -10},
            Domain.INDUSTRY: {V.WEALTH: 20, V.PERSEVERANCE: 20, V.CRAFTSMANSHIP: 15, V.NATURE: -20},
            Domain.INFORMATION: {V.KNOWLEDGE: 25, V.TRUTH: 15},
            Domain.SPACE: {V.XENOPHILIA: 25, V.KNOWLEDGE: 15},
            Domain.SCIENCE: {V.KNOWLEDGE: 35, V.TRUTH: 25, V.SUPERSTITION: -25},
        }.items()
    }
)

PEOPLE_STAT_VALUES = MappingProxyType(
    {
        "martiality": MappingProxyType({V.MARTIAL: 70, V.MERCY: -20, V.COMPETITION: 20}),
        "piety": MappingProxyType({V.PIETY: 70, V.SUPERSTITION: 20, V.LAW: 10}),
        "magic": MappingProxyType({V.SUPERSTITION: 50, V.KNOWLEDGE: 20}),
        "craft": MappingProxyType({V.KNOWLEDGE: 40, V.TRADITION: -20, V.CRAFTSMANSHIP: 50, V.ARTWORK: 15}),
        "wealth": MappingProxyType({V.WEALTH: 60, V.XENOPHILIA: 20, V.COMPETITION: 15}),
        "prosperity": MappingProxyType({V.WEALTH: 20, V.HIERARCHY: 15, V.LEISURE: 20}),
    }
)

PASSION_VALUES = MappingProxyType(
    {
        Passion.MERCY: MappingProxyType({V.MERCY: 80, V.MARTIAL: -20, V.FRIENDSHIP: 20}),
        Passion.WRATH: MappingProxyType({V.MERCY: -50, V.MARTIAL: 50, V.COMPETITION: 15}),
        Passion.AMBITION: MappingProxyType({V.HIERARCHY: 40, V.WEALTH: 25, V.TRADITION: -20, V.COMPETITION: 40}),
        Passion.LOYALTY: MappingProxyType({V.KINSHIP: 45, V.HONOUR: 40, V.TRADITION: 20, V.LOYALTY: 60, V.FRIENDSHIP: 20}),
    }
)

AGENDA_VALUES = MappingProxyType(
    {
        EngineKind.MERCHANT_GUILD: MappingProxyType({V.WEALTH: 60, V.XENOPHILIA: 30, V.MARTIAL: -20, V.COMPETITION: 30}),
        EngineKind.PRIESTS_COUNCIL: MappingProxyType({V.PIETY: 60, V.TRADITION: 30, V.HIERARCHY: 20, V.LAW: 20}),
        EngineKind.WARRIOR_BAND: MappingProxyType({V.MARTIAL: 60, V.HONOUR: 30, V.KINSHIP: 20, V.LOYALTY: 30}),
        EngineKind.REBELS: MappingProxyType({V.HIERARCHY: -60, V.TRADITION: -30, V.MERCY: -10, V.LAW: -50}),
    }
)

DOCTRINE_BASE = MappingProxyType({V.PIETY: 45, V.TRADITION: 15, V.LAW: 15, V.TRUTH: 10})


@dataclass(frozen=True)
class TraitSpec:
    opposite: TraitKind | None
    values: MappingProxyType[ValueAxis, int]
    capacities: MappingProxyType[Capacity, int] = field(default_factory=lambda: MappingProxyType({}))
    effects: MappingProxyType[TraitEffect, int] = field(default_factory=lambda: MappingProxyType({}))
    heritable: bool = False
    divine: bool = False
    label: str = ""


def _trait(
    opposite: TraitKind | None,
    values: dict[ValueAxis, int],
    *,
    capacities: dict[Capacity, int] | None = None,
    effects: dict[TraitEffect, int] | None = None,
    heritable: bool = False,
    divine: bool = False,
    label: str,
) -> TraitSpec:
    return TraitSpec(opposite, MappingProxyType(values), MappingProxyType(capacities or {}), MappingProxyType(effects or {}), heritable, divine, label)


TRAITS: MappingProxyType[TraitKind, TraitSpec] = total(
    TraitKind,
    {
        T.BRAVE: _trait(
            T.CRAVEN,
            {V.MARTIAL: 15, V.HONOUR: 10, V.PERSEVERANCE: 10},
            capacities={Capacity.MELEE: 10},
            effects={E.COURAGE: 30, E.WAR_APPETITE: 10},
            heritable=True,
            divine=True,
            label="Brave",
        ),
        T.CRAVEN: _trait(
            T.BRAVE,
            {V.MARTIAL: -15, V.LEISURE: 10},
            capacities={Capacity.MELEE: -15, Capacity.COMMAND: -10},
            effects={E.COURAGE: -40, E.WAR_APPETITE: -20},
            heritable=True,
            label="Craven",
        ),
        T.WRATHFUL: _trait(
            T.PATIENT,
            {V.MERCY: -15, V.MARTIAL: 10},
            capacities={Capacity.MELEE: 5},
            effects={E.WAR_APPETITE: 25, E.CRUELTY: 15, E.MEMORY_DECAY: -20},
            divine=True,
            label="Wrathful",
        ),
        T.PATIENT: _trait(
            T.WRATHFUL,
            {V.MERCY: 10, V.TRADITION: 5, V.PERSEVERANCE: 10},
            capacities={Capacity.CRAFT: 5, Capacity.COMMAND: 5},
            effects={E.WAR_APPETITE: -15, E.LEARNING: 10},
            divine=True,
            label="Patient",
        ),
        T.CRUEL: _trait(T.KIND, {V.MERCY: -30}, effects={E.CRUELTY: 40, E.TRUST: -10}, divine=True, label="Cruel"),
        T.KIND: _trait(T.CRUEL, {V.MERCY: 30}, capacities={Capacity.PRESENCE: 5}, effects={E.CRUELTY: -40, E.TRUST: 10}, divine=True, label="Kind"),
        T.AMBITIOUS: _trait(
            T.CONTENT,
            {V.HIERARCHY: 15, V.WEALTH: 10, V.COMPETITION: 25},
            effects={E.AGENT_WEIGHT: 25, E.BETRAYAL: 20, E.WAR_APPETITE: 10},
            divine=True,
            label="Ambitious",
        ),
        T.CONTENT: _trait(T.AMBITIOUS, {V.TRADITION: 10, V.LEISURE: 20, V.COMPETITION: -15}, effects={E.AGENT_WEIGHT: -20, E.BETRAYAL: -20}, label="Content"),
        T.GREEDY: _trait(T.GENEROUS, {V.WEALTH: 25, V.MERCY: -10}, effects={E.GREED: 35, E.BETRAYAL: 10}, divine=True, label="Greedy"),
        T.GENEROUS: _trait(
            T.GREEDY, {V.WEALTH: -15, V.MERCY: 15}, capacities={Capacity.PRESENCE: 5}, effects={E.GREED: -35, E.TRUST: 10}, divine=True, label="Generous"
        ),
        T.HONEST: _trait(T.DECEITFUL, {V.HONOUR: 25, V.TRUTH: 35}, effects={E.DECEIT: -40, E.TRUST: 15, E.BETRAYAL: -15}, divine=True, label="Honest"),
        T.DECEITFUL: _trait(T.HONEST, {V.HONOUR: -25, V.TRUTH: -35}, effects={E.DECEIT: 40, E.TRUST: -15, E.BETRAYAL: 20}, divine=True, label="Deceitful"),
        T.ZEALOUS: _trait(T.CYNICAL, {V.PIETY: 30, V.SUPERSTITION: 10}, effects={E.ZEAL: 40, E.DRIFT: -15}, divine=True, label="Zealous"),
        T.CYNICAL: _trait(T.ZEALOUS, {V.PIETY: -25, V.SUPERSTITION: -15}, effects={E.ZEAL: -40, E.TRUST: -10}, label="Cynical"),
        T.PARANOID: _trait(T.TRUSTING, {V.XENOPHILIA: -20}, effects={E.TRUST: -30, E.MEMORY_DECAY: -25}, divine=True, label="Paranoid"),
        T.TRUSTING: _trait(T.PARANOID, {V.XENOPHILIA: 15, V.FRIENDSHIP: 15}, effects={E.TRUST: 25}, label="Trusting"),
        T.LUSTFUL: _trait(T.CHASTE, {V.PURITY: -15}, effects={E.FERTILITY: 25}, divine=True, label="Lustful"),
        T.CHASTE: _trait(T.LUSTFUL, {V.PURITY: 20, V.PIETY: 5}, effects={E.FERTILITY: -40}, divine=True, label="Chaste"),
        T.GLUTTONOUS: _trait(T.ASCETIC, {V.WEALTH: 10, V.PURITY: -10, V.LEISURE: 20}, capacities={Capacity.MOBILITY: -5}, label="Gluttonous"),
        T.ASCETIC: _trait(T.GLUTTONOUS, {V.PIETY: 15, V.WEALTH: -20, V.PURITY: 10, V.LEISURE: -25}, effects={E.ZEAL: 15}, divine=True, label="Ascetic"),
        T.SCHOLARLY: _trait(
            T.ILLITERATE_PROUD,
            {V.KNOWLEDGE: 30},
            capacities={Capacity.SCHOLARSHIP: 15},
            effects={E.LEARNING: 25},
            heritable=True,
            divine=True,
            label="Scholarly",
        ),
        T.ILLITERATE_PROUD: _trait(
            T.SCHOLARLY, {V.KNOWLEDGE: -30, V.TRADITION: 10}, capacities={Capacity.SCHOLARSHIP: -20}, effects={E.LEARNING: -15}, label="Proudly unlettered"
        ),
        T.GREGARIOUS: _trait(
            T.RECLUSIVE,
            {V.KINSHIP: 10, V.XENOPHILIA: 10, V.FRIENDSHIP: 25},
            capacities={Capacity.PRESENCE: 12},
            effects={E.TRUST: 10},
            heritable=True,
            label="Gregarious",
        ),
        T.RECLUSIVE: _trait(
            T.GREGARIOUS,
            {V.KINSHIP: -10, V.XENOPHILIA: -10, V.FRIENDSHIP: -20},
            capacities={Capacity.PRESENCE: -12, Capacity.SCHOLARSHIP: 5},
            effects={E.AGENT_WEIGHT: -10},
            divine=True,
            label="Reclusive",
        ),
        T.VENGEFUL: _trait(T.FORGIVING, {V.HONOUR: 10, V.MERCY: -20}, effects={E.MEMORY_DECAY: -50, E.WAR_APPETITE: 10}, divine=True, label="Vengeful"),
        T.FORGIVING: _trait(T.VENGEFUL, {V.MERCY: 20}, effects={E.MEMORY_DECAY: 60, E.TRUST: 5}, divine=True, label="Forgiving"),
        T.STUBBORN: _trait(T.FICKLE, {V.TRADITION: 15, V.PERSEVERANCE: 25}, effects={E.DRIFT: -50}, heritable=True, divine=True, label="Stubborn"),
        T.FICKLE: _trait(
            T.STUBBORN, {V.TRADITION: -15, V.PERSEVERANCE: -25, V.LOYALTY: -15}, effects={E.DRIFT: 60, E.BETRAYAL: 10}, divine=True, label="Fickle"
        ),
        T.JUST: _trait(
            T.ARBITRARY,
            {V.HONOUR: 15, V.HIERARCHY: -5, V.LAW: 25},
            capacities={Capacity.COMMAND: 5},
            effects={E.JUSTICE: 40, E.TRUST: 10},
            divine=True,
            label="Just",
        ),
        T.ARBITRARY: _trait(T.JUST, {V.HONOUR: -10, V.HIERARCHY: 15, V.LAW: -20}, effects={E.JUSTICE: -40, E.CRUELTY: 10}, divine=True, label="Arbitrary"),
        T.HUMBLE: _trait(T.PROUD, {V.HIERARCHY: -15, V.PIETY: 5}, effects={E.TRUST: 5, E.AGENT_WEIGHT: -5}, label="Humble"),
        T.PROUD: _trait(
            T.HUMBLE,
            {V.HIERARCHY: 15, V.HONOUR: 10},
            capacities={Capacity.PRESENCE: 8},
            effects={E.AGENT_WEIGHT: 10, E.WAR_APPETITE: 5},
            divine=True,
            label="Proud",
        ),
        T.CURIOUS: _trait(
            T.INCURIOUS,
            {V.KNOWLEDGE: 20, V.XENOPHILIA: 15, V.TRADITION: -10},
            capacities={Capacity.SCHOLARSHIP: 5},
            effects={E.LEARNING: 20, E.EXPLORATION: 40, E.AGENT_WEIGHT: 10},
            heritable=True,
            divine=True,
            label="Curious",
        ),
        T.INCURIOUS: _trait(T.CURIOUS, {V.KNOWLEDGE: -15, V.TRADITION: 10}, effects={E.LEARNING: -20, E.EXPLORATION: -40}, label="Incurious"),
        T.MELANCHOLIC: _trait(
            T.SANGUINE,
            {V.DEATH: 15},
            capacities={Capacity.PRESENCE: -8, Capacity.SCHOLARSHIP: 5},
            effects={E.AGENT_WEIGHT: -10},
            heritable=True,
            divine=True,
            label="Melancholic",
        ),
        T.SANGUINE: _trait(
            T.MELANCHOLIC, {V.DEATH: -10, V.XENOPHILIA: 5}, capacities={Capacity.PRESENCE: 8}, effects={E.TRUST: 5}, heritable=True, label="Sanguine"
        ),
        T.IRON_WILLED: _trait(
            T.IMPRESSIONABLE, {V.HONOUR: 10}, capacities={Capacity.COMMAND: 8}, effects={E.DRIFT: -40, E.COURAGE: 20}, divine=True, label="Iron-willed"
        ),
        T.IMPRESSIONABLE: _trait(T.IRON_WILLED, {V.TRADITION: -5}, effects={E.DRIFT: 60, E.LEARNING: 10}, label="Impressionable"),
        T.CUNNING_TACTICIAN: _trait(
            None, {V.MARTIAL: 10, V.KNOWLEDGE: 5}, capacities={Capacity.COMMAND: 15}, effects={E.DECEIT: 10}, divine=True, label="Cunning tactician"
        ),
        T.RECKLESS: _trait(
            T.CAUTIOUS,
            {V.MARTIAL: 10, V.TRADITION: -10},
            capacities={Capacity.MELEE: 8, Capacity.COMMAND: -10},
            effects={E.WAR_APPETITE: 20, E.COURAGE: 25, E.EXPLORATION: 20},
            label="Reckless",
        ),
        T.CAUTIOUS: _trait(
            T.RECKLESS,
            {V.TRADITION: 10, V.PERSEVERANCE: 5},
            capacities={Capacity.COMMAND: 8},
            effects={E.WAR_APPETITE: -15, E.COURAGE: -10, E.EXPLORATION: -15},
            heritable=True,
            divine=True,
            label="Cautious",
        ),
        T.DILIGENT: _trait(
            T.SLOTHFUL,
            {V.PERSEVERANCE: 20, V.LEISURE: -15},
            capacities={Capacity.CRAFT: 10, Capacity.SCHOLARSHIP: 5},
            effects={E.LEARNING: 15, E.AGENT_WEIGHT: 10},
            heritable=True,
            divine=True,
            label="Diligent",
        ),
        T.SLOTHFUL: _trait(
            T.DILIGENT,
            {V.PERSEVERANCE: -20, V.LEISURE: 25},
            capacities={Capacity.CRAFT: -10},
            effects={E.LEARNING: -10, E.AGENT_WEIGHT: -15},
            label="Slothful",
        ),
        T.LOYAL: _trait(T.DISLOYAL, {V.LOYALTY: 30, V.HONOUR: 10}, effects={E.BETRAYAL: -40, E.TRUST: 10}, divine=True, label="Loyal"),
        T.DISLOYAL: _trait(T.LOYAL, {V.LOYALTY: -30}, effects={E.BETRAYAL: 35, E.TRUST: -10}, divine=True, label="Disloyal"),
        T.OBEDIENT: _trait(T.DEFIANT, {V.HIERARCHY: 20, V.LAW: 15}, effects={E.DRIFT: 20, E.AGENT_WEIGHT: -10, E.JUSTICE: 10}, label="Obedient"),
        T.DEFIANT: _trait(
            T.OBEDIENT,
            {V.HIERARCHY: -20, V.LAW: -15, V.TRADITION: -10},
            capacities={Capacity.PRESENCE: 5},
            effects={E.DRIFT: -20, E.AGENT_WEIGHT: 10, E.BETRAYAL: 10},
            divine=True,
            label="Defiant",
        ),
        T.PLAYFUL: _trait(
            T.DOUR,
            {V.LEISURE: 15, V.FRIENDSHIP: 10},
            capacities={Capacity.PRESENCE: 8},
            effects={E.TRUST: 5, E.EXPLORATION: 10},
            heritable=True,
            divine=True,
            label="Playful",
        ),
        T.DOUR: _trait(T.PLAYFUL, {V.LEISURE: -10, V.TRADITION: 10}, capacities={Capacity.PRESENCE: -6}, effects={E.TRUST: -5}, divine=True, label="Dour"),
        T.CHARMING: _trait(
            T.AWKWARD, {V.FRIENDSHIP: 10}, capacities={Capacity.PRESENCE: 12}, effects={E.CHARM: 35}, heritable=True, divine=True, label="Charming"
        ),
        T.AWKWARD: _trait(T.CHARMING, {V.FRIENDSHIP: -5}, capacities={Capacity.PRESENCE: -10}, effects={E.CHARM: -30}, heritable=True, label="Awkward"),
        T.ELOQUENT: _trait(
            T.TONGUE_TIED,
            {V.TRUTH: 5, V.KNOWLEDGE: 5},
            capacities={Capacity.PRESENCE: 10, Capacity.COMMAND: 5},
            effects={E.CHARM: 20, E.AGENT_WEIGHT: 5},
            heritable=True,
            divine=True,
            label="Eloquent",
        ),
        T.TONGUE_TIED: _trait(T.ELOQUENT, {}, capacities={Capacity.PRESENCE: -10}, effects={E.CHARM: -15}, heritable=True, label="Tongue-tied"),
        T.TACTFUL: _trait(
            T.BLUNT, {V.FRIENDSHIP: 10, V.TRUTH: -5}, capacities={Capacity.PRESENCE: 5}, effects={E.CHARM: 15, E.TRUST: 5}, divine=True, label="Tactful"
        ),
        T.BLUNT: _trait(T.TACTFUL, {V.TRUTH: 15}, effects={E.CHARM: -15, E.DECEIT: -15}, divine=True, label="Blunt"),
        T.DISCREET: _trait(T.GOSSIPING, {V.TRUTH: 5, V.LOYALTY: 10}, effects={E.TRUST: 10, E.BETRAYAL: -10}, divine=True, label="Discreet"),
        T.GOSSIPING: _trait(T.DISCREET, {V.FRIENDSHIP: 10, V.LOYALTY: -10}, effects={E.SOCIABILITY: 15, E.BETRAYAL: 10, E.TRUST: -5}, label="Gossiping"),
        T.HOSPITABLE: _trait(
            T.INHOSPITABLE,
            {V.KINSHIP: 10, V.XENOPHILIA: 15, V.MERCY: 5},
            capacities={Capacity.PRESENCE: 5},
            effects={E.SOCIABILITY: 20, E.TRUST: 5},
            divine=True,
            label="Hospitable",
        ),
        T.INHOSPITABLE: _trait(T.HOSPITABLE, {V.XENOPHILIA: -15}, effects={E.SOCIABILITY: -20}, divine=True, label="Inhospitable"),
        T.COOPERATIVE: _trait(
            T.COMPETITIVE, {V.COMPETITION: -20, V.FRIENDSHIP: 10}, effects={E.SOCIABILITY: 15, E.TRUST: 10}, heritable=True, divine=True, label="Cooperative"
        ),
        T.COMPETITIVE: _trait(
            T.COOPERATIVE,
            {V.COMPETITION: 25},
            capacities={Capacity.MELEE: 5},
            effects={E.AGENT_WEIGHT: 10, E.WAR_APPETITE: 5},
            heritable=True,
            divine=True,
            label="Competitive",
        ),
        T.AFFECTIONATE: _trait(
            T.ALOOF,
            {V.FAMILY: 15, V.FRIENDSHIP: 15},
            capacities={Capacity.PRESENCE: 5},
            effects={E.SOCIABILITY: 20, E.FERTILITY: 10},
            heritable=True,
            divine=True,
            label="Affectionate",
        ),
        T.ALOOF: _trait(T.AFFECTIONATE, {V.FAMILY: -10, V.FRIENDSHIP: -10}, effects={E.SOCIABILITY: -20}, heritable=True, divine=True, label="Aloof"),
        T.COURTEOUS: _trait(T.RUDE, {V.TRADITION: 10, V.HONOUR: 5}, capacities={Capacity.PRESENCE: 5}, effects={E.CHARM: 15}, divine=True, label="Courteous"),
        T.RUDE: _trait(T.COURTEOUS, {V.TRADITION: -10}, effects={E.CHARM: -20}, divine=True, label="Rude"),
        T.SHREWD: _trait(
            T.GULLIBLE,
            {V.KNOWLEDGE: 5, V.TRUTH: 5},
            capacities={Capacity.SCHOLARSHIP: 5, Capacity.COMMAND: 5},
            effects={E.DRIFT: -15, E.TRUST: -5},
            heritable=True,
            divine=True,
            label="Shrewd",
        ),
        T.GULLIBLE: _trait(T.SHREWD, {}, effects={E.DRIFT: 30, E.TRUST: 15}, heritable=True, label="Gullible"),
        T.IMAGINATIVE: _trait(
            T.LITERAL_MINDED,
            {V.ARTWORK: 20, V.KNOWLEDGE: 5},
            capacities={Capacity.CRAFT: 5, Capacity.SCHOLARSHIP: 5},
            effects={E.LEARNING: 10, E.EXPLORATION: 15},
            heritable=True,
            divine=True,
            label="Imaginative",
        ),
        T.LITERAL_MINDED: _trait(T.IMAGINATIVE, {V.ARTWORK: -15, V.TRADITION: 10}, effects={E.EXPLORATION: -10}, heritable=True, label="Literal-minded"),
        T.METHODICAL: _trait(
            T.SCATTERBRAINED,
            {V.PERSEVERANCE: 10, V.CRAFTSMANSHIP: 10},
            capacities={Capacity.CRAFT: 10, Capacity.SCHOLARSHIP: 5},
            effects={E.LEARNING: 10},
            heritable=True,
            divine=True,
            label="Methodical",
        ),
        T.SCATTERBRAINED: _trait(
            T.METHODICAL,
            {V.PERSEVERANCE: -10},
            capacities={Capacity.CRAFT: -8},
            effects={E.LEARNING: -10, E.MEMORY_DECAY: 20},
            heritable=True,
            label="Scatterbrained",
        ),
        T.PERCEPTIVE: _trait(
            T.OBLIVIOUS,
            {V.KNOWLEDGE: 5},
            capacities={Capacity.SCHOLARSHIP: 5, Capacity.MISSILE: 5},
            effects={E.TRUST: -5, E.LEARNING: 5},
            heritable=True,
            divine=True,
            label="Perceptive",
        ),
        T.OBLIVIOUS: _trait(T.PERCEPTIVE, {}, capacities={Capacity.MISSILE: -5}, effects={E.TRUST: 10}, heritable=True, label="Oblivious"),
        T.WISE: _trait(
            T.FOOLISH,
            {V.KNOWLEDGE: 15, V.MERCY: 5, V.LAW: 5},
            capacities={Capacity.SCHOLARSHIP: 10, Capacity.COMMAND: 5},
            effects={E.LEARNING: 15, E.JUSTICE: 10, E.DRIFT: -10},
            divine=True,
            label="Wise",
        ),
        T.FOOLISH: _trait(
            T.WISE, {V.KNOWLEDGE: -10}, capacities={Capacity.SCHOLARSHIP: -10}, effects={E.LEARNING: -10, E.DRIFT: 15}, divine=True, label="Foolish"
        ),
        T.SCEPTICAL: _trait(
            T.CREDULOUS,
            {V.SUPERSTITION: -20, V.TRUTH: 10},
            capacities={Capacity.SCHOLARSHIP: 5},
            effects={E.ZEAL: -15, E.DRIFT: -10},
            divine=True,
            label="Sceptical",
        ),
        T.CREDULOUS: _trait(T.SCEPTICAL, {V.SUPERSTITION: 20}, effects={E.ZEAL: 10, E.DRIFT: 20}, label="Credulous"),
        T.CONTEMPLATIVE: _trait(
            T.IMPULSIVE,
            {V.KNOWLEDGE: 10, V.LEISURE: 5},
            capacities={Capacity.SCHOLARSHIP: 8},
            effects={E.WAR_APPETITE: -10, E.LEARNING: 5},
            divine=True,
            label="Contemplative",
        ),
        T.IMPULSIVE: _trait(
            T.CONTEMPLATIVE,
            {V.PERSEVERANCE: -10},
            capacities={Capacity.MELEE: 5},
            effects={E.WAR_APPETITE: 15, E.EXPLORATION: 10, E.MEMORY_DECAY: 10},
            divine=True,
            label="Impulsive",
        ),
        T.DISCIPLINED: _trait(
            T.UNDISCIPLINED,
            {V.PERSEVERANCE: 15, V.LAW: 10},
            capacities={Capacity.COMMAND: 10, Capacity.MELEE: 5},
            effects={E.COURAGE: 10, E.DRIFT: -10},
            divine=True,
            label="Disciplined",
        ),
        T.UNDISCIPLINED: _trait(
            T.DISCIPLINED, {V.PERSEVERANCE: -15, V.LEISURE: 10}, capacities={Capacity.COMMAND: -10}, effects={E.DRIFT: 10}, label="Undisciplined"
        ),
        T.FRUGAL: _trait(T.SPENDTHRIFT, {V.WEALTH: 10, V.LEISURE: -10}, effects={E.GREED: 10}, heritable=True, divine=True, label="Frugal"),
        T.SPENDTHRIFT: _trait(
            T.FRUGAL,
            {V.WEALTH: -5, V.LEISURE: 20},
            capacities={Capacity.PRESENCE: 5},
            effects={E.GREED: -10, E.SOCIABILITY: 10},
            heritable=True,
            label="Spendthrift",
        ),
        T.ORDERLY: _trait(T.DISORDERLY, {V.LAW: 15, V.TRADITION: 10}, capacities={Capacity.CRAFT: 5}, effects={E.JUSTICE: 10}, divine=True, label="Orderly"),
        T.DISORDERLY: _trait(T.ORDERLY, {V.LAW: -15, V.TRADITION: -10}, effects={E.JUSTICE: -10, E.DRIFT: 10}, divine=True, label="Disorderly"),
        T.HONOURABLE: _trait(
            T.UNSCRUPULOUS, {V.HONOUR: 30, V.TRUTH: 10}, effects={E.BETRAYAL: -30, E.DECEIT: -20, E.TRUST: 10}, divine=True, label="Honourable"
        ),
        T.UNSCRUPULOUS: _trait(
            T.HONOURABLE, {V.HONOUR: -30, V.WEALTH: 10}, effects={E.BETRAYAL: 25, E.DECEIT: 25, E.GREED: 10}, divine=True, label="Unscrupulous"
        ),
        T.MODEST: _trait(T.VAIN, {V.HIERARCHY: -10}, effects={E.CHARM: 5, E.AGENT_WEIGHT: -5}, divine=True, label="Modest"),
        T.VAIN: _trait(
            T.MODEST, {V.HIERARCHY: 10, V.ARTWORK: 5}, capacities={Capacity.PRESENCE: 8}, effects={E.AGENT_WEIGHT: 10, E.CHARM: -5}, divine=True, label="Vain"
        ),
        T.COMPASSIONATE: _trait(
            T.CALLOUS,
            {V.MERCY: 25, V.FAMILY: 5},
            capacities={Capacity.PRESENCE: 5},
            effects={E.CRUELTY: -30, E.SOCIABILITY: 10},
            heritable=True,
            divine=True,
            label="Compassionate",
        ),
        T.CALLOUS: _trait(T.COMPASSIONATE, {V.MERCY: -25}, effects={E.CRUELTY: 25, E.SOCIABILITY: -10}, heritable=True, divine=True, label="Callous"),
        T.CALM: _trait(
            T.ANXIOUS,
            {V.PERSEVERANCE: 5},
            capacities={Capacity.COMMAND: 5},
            effects={E.RESILIENCE: 30, E.COURAGE: 10},
            heritable=True,
            divine=True,
            label="Calm",
        ),
        T.ANXIOUS: _trait(
            T.CALM,
            {V.SUPERSTITION: 5},
            capacities={Capacity.COMMAND: -5},
            effects={E.RESILIENCE: -30, E.COURAGE: -10, E.TRUST: -5},
            heritable=True,
            label="Anxious",
        ),
        T.OPTIMISTIC: _trait(
            T.PESSIMISTIC,
            {V.DEATH: -10},
            capacities={Capacity.PRESENCE: 5},
            effects={E.RESILIENCE: 20, E.AGENT_WEIGHT: 5, E.EXPLORATION: 5},
            heritable=True,
            divine=True,
            label="Optimistic",
        ),
        T.PESSIMISTIC: _trait(T.OPTIMISTIC, {V.DEATH: 10}, effects={E.RESILIENCE: -20, E.AGENT_WEIGHT: -5}, heritable=True, divine=True, label="Pessimistic"),
        T.PASSIONATE: _trait(
            T.DETACHED,
            {V.ARTWORK: 10, V.FRIENDSHIP: 5},
            capacities={Capacity.PRESENCE: 8},
            effects={E.AGENT_WEIGHT: 10, E.FERTILITY: 10, E.MEMORY_DECAY: -10},
            heritable=True,
            divine=True,
            label="Passionate",
        ),
        T.DETACHED: _trait(T.PASSIONATE, {V.LEISURE: 5}, effects={E.AGENT_WEIGHT: -10, E.RESILIENCE: 10}, heritable=True, divine=True, label="Detached"),
        T.JEALOUS: _trait(
            T.SECURE, {V.FAMILY: 10, V.COMPETITION: 10}, effects={E.TRUST: -20, E.CRUELTY: 10, E.MEMORY_DECAY: -15}, divine=True, label="Jealous"
        ),
        T.SECURE: _trait(T.JEALOUS, {V.FRIENDSHIP: 5}, effects={E.TRUST: 10, E.RESILIENCE: 10}, divine=True, label="Secure"),
        T.SENTIMENTAL: _trait(
            T.UNSENTIMENTAL, {V.FAMILY: 15, V.TRADITION: 10}, effects={E.MEMORY_DECAY: -30}, heritable=True, divine=True, label="Sentimental"
        ),
        T.UNSENTIMENTAL: _trait(T.SENTIMENTAL, {V.TRADITION: -10}, effects={E.MEMORY_DECAY: 30, E.RESILIENCE: 5}, heritable=True, label="Unsentimental"),
        T.MYSTIC: _trait(
            T.WORLDLY,
            {V.PIETY: 20, V.SUPERSTITION: 15, V.KNOWLEDGE: 5},
            capacities={Capacity.SCHOLARSHIP: 5},
            effects={E.ZEAL: 20, E.LEARNING: 5},
            heritable=True,
            divine=True,
            label="Mystic",
        ),
        T.WORLDLY: _trait(
            T.MYSTIC, {V.PIETY: -10, V.WEALTH: 10, V.LEISURE: 10}, capacities={Capacity.PRESENCE: 5}, effects={E.ZEAL: -15}, divine=True, label="Worldly"
        ),
        T.TOLERANT: _trait(T.INTOLERANT, {V.XENOPHILIA: 20, V.MERCY: 5}, effects={E.ZEAL: -10, E.TRUST: 10, E.CRUELTY: -10}, divine=True, label="Tolerant"),
        T.INTOLERANT: _trait(T.TOLERANT, {V.XENOPHILIA: -20, V.PURITY: 15}, effects={E.ZEAL: 20, E.CRUELTY: 15, E.TRUST: -10}, divine=True, label="Intolerant"),
        T.REVERENT: _trait(T.IRREVERENT, {V.PIETY: 15, V.TRADITION: 15}, effects={E.ZEAL: 10, E.DRIFT: -10}, divine=True, label="Reverent"),
        T.IRREVERENT: _trait(
            T.REVERENT, {V.PIETY: -15, V.TRADITION: -15}, capacities={Capacity.PRESENCE: 5}, effects={E.ZEAL: -15, E.DRIFT: 10}, divine=True, label="Irreverent"
        ),
        T.ADVENTUROUS: _trait(
            T.HOMEBOUND,
            {V.XENOPHILIA: 15, V.KINSHIP: -5},
            capacities={Capacity.MOBILITY: 5},
            effects={E.EXPLORATION: 40, E.COURAGE: 10},
            heritable=True,
            divine=True,
            label="Adventurous",
        ),
        T.HOMEBOUND: _trait(T.ADVENTUROUS, {V.KINSHIP: 15, V.TRADITION: 10}, effects={E.EXPLORATION: -40}, heritable=True, label="Homebound"),
        T.IDEALISTIC: _trait(T.PRAGMATIC, {V.HONOUR: 15, V.TRUTH: 15, V.LAW: 10}, effects={E.JUSTICE: 20, E.GREED: -15}, divine=True, label="Idealistic"),
        T.PRAGMATIC: _trait(
            T.IDEALISTIC,
            {V.WEALTH: 10, V.TRADITION: -5},
            capacities={Capacity.COMMAND: 5},
            effects={E.JUSTICE: -5, E.DRIFT: 10},
            divine=True,
            label="Pragmatic",
        ),
        T.PERFECTIONIST: _trait(
            T.CARELESS,
            {V.CRAFTSMANSHIP: 25, V.PERSEVERANCE: 10},
            capacities={Capacity.CRAFT: 12},
            effects={E.LEARNING: 5, E.RESILIENCE: -10},
            heritable=True,
            divine=True,
            label="Perfectionist",
        ),
        T.CARELESS: _trait(
            T.PERFECTIONIST, {V.CRAFTSMANSHIP: -15}, capacities={Capacity.CRAFT: -10}, effects={E.RESILIENCE: 10}, heritable=True, label="Careless"
        ),
        T.GLORY_SEEKING: _trait(
            T.UNASSUMING,
            {V.COMPETITION: 15, V.MARTIAL: 10, V.HONOUR: 10},
            capacities={Capacity.PRESENCE: 5},
            effects={E.AGENT_WEIGHT: 15, E.WAR_APPETITE: 15, E.COURAGE: 10},
            divine=True,
            label="Glory-seeking",
        ),
        T.UNASSUMING: _trait(T.GLORY_SEEKING, {V.COMPETITION: -10}, effects={E.AGENT_WEIGHT: -10, E.WAR_APPETITE: -10}, divine=True, label="Unassuming"),
        T.DUTIFUL: _trait(T.SELF_SERVING, {V.LOYALTY: 20, V.LAW: 10, V.FAMILY: 5}, effects={E.BETRAYAL: -25, E.JUSTICE: 10}, divine=True, label="Dutiful"),
        T.SELF_SERVING: _trait(T.DUTIFUL, {V.LOYALTY: -15, V.WEALTH: 15}, effects={E.BETRAYAL: 20, E.GREED: 15}, divine=True, label="Self-serving"),
        T.RESILIENT: _trait(T.FRAGILE, {V.PERSEVERANCE: 15}, effects={E.RESILIENCE: 40, E.COURAGE: 5}, heritable=True, divine=True, label="Resilient"),
        T.FRAGILE: _trait(T.RESILIENT, {V.PERSEVERANCE: -10}, effects={E.RESILIENCE: -40}, heritable=True, label="Fragile"),
        T.STOIC: _trait(
            T.VOLATILE,
            {V.PERSEVERANCE: 10, V.HONOUR: 5},
            capacities={Capacity.COMMAND: 5},
            effects={E.RESILIENCE: 20, E.WAR_APPETITE: -5},
            divine=True,
            label="Stoic",
        ),
        T.VOLATILE: _trait(
            T.STOIC, {V.MERCY: -5}, capacities={Capacity.MELEE: 5}, effects={E.RESILIENCE: -15, E.WAR_APPETITE: 15, E.CRUELTY: 5}, divine=True, label="Volatile"
        ),
        T.BROODING: _trait(
            T.CAREFREE,
            {V.DEATH: 10},
            capacities={Capacity.SCHOLARSHIP: 5},
            effects={E.MEMORY_DECAY: -25, E.RESILIENCE: -10},
            heritable=True,
            divine=True,
            label="Brooding",
        ),
        T.CAREFREE: _trait(
            T.BROODING,
            {V.LEISURE: 15, V.DEATH: -10},
            capacities={Capacity.PRESENCE: 5},
            effects={E.MEMORY_DECAY: 25, E.RESILIENCE: 15},
            heritable=True,
            divine=True,
            label="Carefree",
        ),
        T.BLOODTHIRSTY: _trait(
            T.PEACEABLE,
            {V.MARTIAL: 25, V.MERCY: -20},
            capacities={Capacity.MELEE: 10},
            effects={E.WAR_APPETITE: 40, E.CRUELTY: 25},
            divine=True,
            label="Bloodthirsty",
        ),
        T.PEACEABLE: _trait(
            T.BLOODTHIRSTY, {V.MARTIAL: -20, V.MERCY: 15}, capacities={Capacity.MELEE: -5}, effects={E.WAR_APPETITE: -40}, divine=True, label="Peaceable"
        ),
        T.GALLANT: _trait(
            T.RUTHLESS,
            {V.HONOUR: 20, V.MERCY: 10, V.MARTIAL: 5},
            capacities={Capacity.PRESENCE: 5},
            effects={E.CRUELTY: -20, E.COURAGE: 15},
            divine=True,
            label="Gallant",
        ),
        T.RUTHLESS: _trait(
            T.GALLANT,
            {V.HONOUR: -10, V.MERCY: -15, V.MARTIAL: 10},
            capacities={Capacity.COMMAND: 5},
            effects={E.CRUELTY: 25, E.WAR_APPETITE: 10},
            divine=True,
            label="Ruthless",
        ),
        T.VIGILANT: _trait(
            T.COMPLACENT,
            {V.MARTIAL: 5},
            capacities={Capacity.COMMAND: 5, Capacity.MISSILE: 5},
            effects={E.TRUST: -10, E.COURAGE: 5},
            heritable=True,
            divine=True,
            label="Vigilant",
        ),
        T.COMPLACENT: _trait(T.VIGILANT, {V.LEISURE: 10}, capacities={Capacity.COMMAND: -5}, effects={E.TRUST: 10}, label="Complacent"),
        T.HARDY: _trait(
            None,
            {V.PERSEVERANCE: 10},
            capacities={Capacity.MELEE: 5, Capacity.MOBILITY: 5},
            effects={E.RESILIENCE: 15},
            heritable=True,
            label="Hardy",
        ),
        T.NIMBLE: _trait(None, {}, capacities={Capacity.MOBILITY: 10, Capacity.CRAFT: 5}, heritable=True, label="Nimble"),
        T.SHARP_SIGHTED: _trait(None, {}, capacities={Capacity.MISSILE: 10}, effects={E.EXPLORATION: 10}, heritable=True, label="Sharp-sighted"),
        T.RETENTIVE: _trait(
            None,
            {V.KNOWLEDGE: 5},
            capacities={Capacity.SCHOLARSHIP: 10},
            effects={E.LEARNING: 15, E.MEMORY_DECAY: -20},
            heritable=True,
            label="Retentive",
        ),
        T.NUMERATE: _trait(
            None, {V.KNOWLEDGE: 5}, capacities={Capacity.SCHOLARSHIP: 5, Capacity.CRAFT: 5}, effects={E.LEARNING: 10}, heritable=True, label="Numerate"
        ),
        T.MUSICAL: _trait(None, {V.ARTWORK: 10}, capacities={Capacity.PRESENCE: 5}, effects={E.CHARM: 10}, heritable=True, label="Musical"),
    },
)
TF = TraitFamily
TRAIT_FAMILY: Mapping[TraitKind, TraitFamily] = total(
    TraitKind,
    {
        T.BRAVE: TF.MARTIAL,
        T.CRAVEN: TF.MARTIAL,
        T.WRATHFUL: TF.VICE,
        T.PATIENT: TF.VIRTUE,
        T.CRUEL: TF.VICE,
        T.KIND: TF.VIRTUE,
        T.AMBITIOUS: TF.DRIVE,
        T.CONTENT: TF.DRIVE,
        T.GREEDY: TF.VICE,
        T.GENEROUS: TF.VIRTUE,
        T.HONEST: TF.VIRTUE,
        T.DECEITFUL: TF.VICE,
        T.ZEALOUS: TF.FAITH,
        T.CYNICAL: TF.FAITH,
        T.PARANOID: TF.FEELING,
        T.TRUSTING: TF.FEELING,
        T.LUSTFUL: TF.VICE,
        T.CHASTE: TF.VIRTUE,
        T.GLUTTONOUS: TF.VICE,
        T.ASCETIC: TF.VIRTUE,
        T.SCHOLARLY: TF.INTELLECT,
        T.ILLITERATE_PROUD: TF.INTELLECT,
        T.GREGARIOUS: TF.SOCIAL,
        T.RECLUSIVE: TF.SOCIAL,
        T.VENGEFUL: TF.VICE,
        T.FORGIVING: TF.VIRTUE,
        T.STUBBORN: TF.CONDUCT,
        T.FICKLE: TF.CONDUCT,
        T.JUST: TF.VIRTUE,
        T.ARBITRARY: TF.VICE,
        T.HUMBLE: TF.VIRTUE,
        T.PROUD: TF.VICE,
        T.CURIOUS: TF.INTELLECT,
        T.INCURIOUS: TF.INTELLECT,
        T.MELANCHOLIC: TF.TEMPERAMENT,
        T.SANGUINE: TF.TEMPERAMENT,
        T.IRON_WILLED: TF.COPING,
        T.IMPRESSIONABLE: TF.COPING,
        T.CUNNING_TACTICIAN: TF.MARTIAL,
        T.RECKLESS: TF.CONDUCT,
        T.CAUTIOUS: TF.CONDUCT,
        T.DILIGENT: TF.VIRTUE,
        T.SLOTHFUL: TF.VICE,
        T.LOYAL: TF.VIRTUE,
        T.DISLOYAL: TF.VICE,
        T.OBEDIENT: TF.CONDUCT,
        T.DEFIANT: TF.CONDUCT,
        T.PLAYFUL: TF.TEMPERAMENT,
        T.DOUR: TF.TEMPERAMENT,
        T.CHARMING: TF.SOCIAL,
        T.AWKWARD: TF.SOCIAL,
        T.ELOQUENT: TF.SOCIAL,
        T.TONGUE_TIED: TF.SOCIAL,
        T.TACTFUL: TF.SOCIAL,
        T.BLUNT: TF.SOCIAL,
        T.DISCREET: TF.SOCIAL,
        T.GOSSIPING: TF.SOCIAL,
        T.HOSPITABLE: TF.SOCIAL,
        T.INHOSPITABLE: TF.SOCIAL,
        T.COOPERATIVE: TF.SOCIAL,
        T.COMPETITIVE: TF.SOCIAL,
        T.AFFECTIONATE: TF.SOCIAL,
        T.ALOOF: TF.SOCIAL,
        T.COURTEOUS: TF.SOCIAL,
        T.RUDE: TF.SOCIAL,
        T.SHREWD: TF.INTELLECT,
        T.GULLIBLE: TF.INTELLECT,
        T.IMAGINATIVE: TF.INTELLECT,
        T.LITERAL_MINDED: TF.INTELLECT,
        T.METHODICAL: TF.INTELLECT,
        T.SCATTERBRAINED: TF.INTELLECT,
        T.PERCEPTIVE: TF.INTELLECT,
        T.OBLIVIOUS: TF.INTELLECT,
        T.WISE: TF.INTELLECT,
        T.FOOLISH: TF.INTELLECT,
        T.SCEPTICAL: TF.INTELLECT,
        T.CREDULOUS: TF.INTELLECT,
        T.CONTEMPLATIVE: TF.INTELLECT,
        T.IMPULSIVE: TF.INTELLECT,
        T.DISCIPLINED: TF.CONDUCT,
        T.UNDISCIPLINED: TF.CONDUCT,
        T.FRUGAL: TF.CONDUCT,
        T.SPENDTHRIFT: TF.CONDUCT,
        T.ORDERLY: TF.CONDUCT,
        T.DISORDERLY: TF.CONDUCT,
        T.HONOURABLE: TF.CONDUCT,
        T.UNSCRUPULOUS: TF.CONDUCT,
        T.MODEST: TF.CONDUCT,
        T.VAIN: TF.CONDUCT,
        T.COMPASSIONATE: TF.FEELING,
        T.CALLOUS: TF.FEELING,
        T.CALM: TF.FEELING,
        T.ANXIOUS: TF.FEELING,
        T.OPTIMISTIC: TF.FEELING,
        T.PESSIMISTIC: TF.FEELING,
        T.PASSIONATE: TF.FEELING,
        T.DETACHED: TF.FEELING,
        T.JEALOUS: TF.FEELING,
        T.SECURE: TF.FEELING,
        T.SENTIMENTAL: TF.FEELING,
        T.UNSENTIMENTAL: TF.FEELING,
        T.MYSTIC: TF.FAITH,
        T.WORLDLY: TF.FAITH,
        T.TOLERANT: TF.FAITH,
        T.INTOLERANT: TF.FAITH,
        T.REVERENT: TF.FAITH,
        T.IRREVERENT: TF.FAITH,
        T.ADVENTUROUS: TF.DRIVE,
        T.HOMEBOUND: TF.DRIVE,
        T.IDEALISTIC: TF.DRIVE,
        T.PRAGMATIC: TF.DRIVE,
        T.PERFECTIONIST: TF.DRIVE,
        T.CARELESS: TF.DRIVE,
        T.GLORY_SEEKING: TF.DRIVE,
        T.UNASSUMING: TF.DRIVE,
        T.DUTIFUL: TF.DRIVE,
        T.SELF_SERVING: TF.DRIVE,
        T.RESILIENT: TF.COPING,
        T.FRAGILE: TF.COPING,
        T.STOIC: TF.COPING,
        T.VOLATILE: TF.COPING,
        T.BROODING: TF.COPING,
        T.CAREFREE: TF.COPING,
        T.BLOODTHIRSTY: TF.MARTIAL,
        T.PEACEABLE: TF.MARTIAL,
        T.GALLANT: TF.MARTIAL,
        T.RUTHLESS: TF.MARTIAL,
        T.VIGILANT: TF.MARTIAL,
        T.COMPLACENT: TF.MARTIAL,
        T.HARDY: TF.COPING,
        T.NIMBLE: TF.CONDUCT,
        T.SHARP_SIGHTED: TF.INTELLECT,
        T.RETENTIVE: TF.INTELLECT,
        T.NUMERATE: TF.INTELLECT,
        T.MUSICAL: TF.FEELING,
    },
)
FAMILY_LIMIT: Mapping[TraitFamily, int] = total(
    TraitFamily,
    {
        TF.TEMPERAMENT: 1,
        TF.VIRTUE: 3,
        TF.VICE: 3,
        TF.SOCIAL: 2,
        TF.INTELLECT: 2,
        TF.CONDUCT: 2,
        TF.FEELING: 2,
        TF.FAITH: 1,
        TF.DRIVE: 2,
        TF.COPING: 1,
        TF.MARTIAL: 2,
    },
)

DIVINE_TRAITS = tuple(kind for kind, spec in TRAITS.items() if spec.divine)

CONDITION_TRAITS = MappingProxyType(
    {
        ConditionKind.PARANOIA: T.PARANOID,
        ConditionKind.RAGE: T.WRATHFUL,
        ConditionKind.MELANCHOLY: T.MELANCHOLIC,
        ConditionKind.VISIONS: T.ZEALOUS,
        ConditionKind.ADDICTION: T.GLUTTONOUS,
        ConditionKind.CHOSEN_MARK: T.PROUD,
        ConditionKind.POSSESSION: T.FICKLE,
        ConditionKind.NIGHTMARES: T.MELANCHOLIC,
    }
)

PLEASURE_TRAITS = frozenset({T.LUSTFUL, T.GLUTTONOUS})


@dataclass(frozen=True)
class SkillSpec:
    family: SkillFamily
    capacity: Capacity
    physical: bool
    label: str


def _skill(family: SkillFamily, capacity: Capacity, label: str, *, physical: bool = False) -> SkillSpec:
    return SkillSpec(family, capacity, physical, label)


C, CM, SO, CR, KN, SU, FA = (
    SkillFamily.COMBAT,
    SkillFamily.COMMAND,
    SkillFamily.SOCIAL,
    SkillFamily.CRAFT,
    SkillFamily.KNOWLEDGE,
    SkillFamily.SURVIVAL,
    SkillFamily.FAITH,
)

SKILLS: MappingProxyType[SkillKind, SkillSpec] = total(
    SkillKind,
    {
        S.BLADE: _skill(C, Capacity.MELEE, "Blade", physical=True),
        S.SPEAR: _skill(C, Capacity.MELEE, "Spear", physical=True),
        S.AXE: _skill(C, Capacity.MELEE, "Axe", physical=True),
        S.BLUNT: _skill(C, Capacity.MELEE, "Mace and hammer", physical=True),
        S.BOW: _skill(C, Capacity.MISSILE, "Bow", physical=True),
        S.SLING: _skill(C, Capacity.MISSILE, "Sling", physical=True),
        S.THROWING: _skill(C, Capacity.MISSILE, "Throwing", physical=True),
        S.SHIELD: _skill(C, Capacity.MELEE, "Shield", physical=True),
        S.UNARMED: _skill(C, Capacity.MELEE, "Unarmed fighting", physical=True),
        S.RIDING: _skill(C, Capacity.MOBILITY, "Riding", physical=True),
        S.MOUNTED_COMBAT: _skill(C, Capacity.MELEE, "Mounted combat", physical=True),
        S.SIEGECRAFT: _skill(C, Capacity.COMMAND, "Siegecraft"),
        S.NAVAL_COMBAT: _skill(C, Capacity.MELEE, "Naval combat", physical=True),
        S.BEAST_HANDLING: _skill(C, Capacity.PRESENCE, "Beast handling"),
        S.TACTICS: _skill(CM, Capacity.COMMAND, "Tactics"),
        S.STRATEGY: _skill(CM, Capacity.COMMAND, "Strategy"),
        S.LOGISTICS: _skill(CM, Capacity.COMMAND, "Logistics"),
        S.LEADERSHIP: _skill(CM, Capacity.COMMAND, "Leadership"),
        S.INTIMIDATION: _skill(CM, Capacity.PRESENCE, "Intimidation"),
        S.ORATORY: _skill(SO, Capacity.PRESENCE, "Oratory"),
        S.NEGOTIATION: _skill(SO, Capacity.PRESENCE, "Negotiation"),
        S.INTRIGUE: _skill(SO, Capacity.SCHOLARSHIP, "Intrigue"),
        S.ETIQUETTE: _skill(SO, Capacity.PRESENCE, "Etiquette"),
        S.DECEPTION: _skill(SO, Capacity.PRESENCE, "Deception"),
        S.TEACHING: _skill(SO, Capacity.PRESENCE, "Teaching"),
        S.SMITHING: _skill(CR, Capacity.CRAFT, "Metalworking", physical=True),
        S.CARPENTRY: _skill(CR, Capacity.CRAFT, "Carpentry", physical=True),
        S.MASONRY: _skill(CR, Capacity.CRAFT, "Masonry", physical=True),
        S.WEAVING: _skill(CR, Capacity.CRAFT, "Weaving"),
        S.POTTERY: _skill(CR, Capacity.CRAFT, "Pottery"),
        S.JEWELLING: _skill(CR, Capacity.CRAFT, "Jewelling"),
        S.SHIPWRIGHT: _skill(CR, Capacity.CRAFT, "Shipwright", physical=True),
        S.ENGINEERING: _skill(CR, Capacity.SCHOLARSHIP, "Engineering"),
        S.ALCHEMY: _skill(CR, Capacity.SCHOLARSHIP, "Alchemy"),
        S.LORE: _skill(KN, Capacity.SCHOLARSHIP, "Lore"),
        S.MEDICINE: _skill(KN, Capacity.CRAFT, "Medicine"),
        S.SURGERY: _skill(KN, Capacity.CRAFT, "Surgery"),
        S.ASTRONOMY: _skill(KN, Capacity.SCHOLARSHIP, "Astronomy"),
        S.LAW: _skill(KN, Capacity.SCHOLARSHIP, "Law"),
        S.THEOLOGY: _skill(KN, Capacity.SCHOLARSHIP, "Theology"),
        S.LANGUAGES: _skill(KN, Capacity.SCHOLARSHIP, "Languages"),
        S.WRITING: _skill(KN, Capacity.SCHOLARSHIP, "Writing"),
        S.CRYPTOGRAPHY: _skill(KN, Capacity.SCHOLARSHIP, "Cryptography"),
        S.ACCOUNTING: _skill(KN, Capacity.SCHOLARSHIP, "Accounting"),
        S.HUNTING: _skill(SU, Capacity.MISSILE, "Hunting", physical=True),
        S.TRACKING: _skill(SU, Capacity.MOBILITY, "Tracking"),
        S.FORAGING: _skill(SU, Capacity.MOBILITY, "Foraging"),
        S.SAILING: _skill(SU, Capacity.MOBILITY, "Sailing", physical=True),
        S.NAVIGATION: _skill(SU, Capacity.SCHOLARSHIP, "Navigation"),
        S.MOUNTAINEERING: _skill(SU, Capacity.MOBILITY, "Mountaineering", physical=True),
        S.SWIMMING: _skill(SU, Capacity.MOBILITY, "Swimming", physical=True),
        S.RITUAL: _skill(FA, Capacity.PRESENCE, "Ritual"),
        S.PROPHECY: _skill(FA, Capacity.SCHOLARSHIP, "Prophecy"),
        S.SPELLCRAFT: _skill(FA, Capacity.SCHOLARSHIP, "Spellcraft"),
        S.SPIRIT_SPEAKING: _skill(FA, Capacity.PRESENCE, "Spirit-speaking"),
        S.FIREARMS: _skill(C, Capacity.MISSILE, "Firearms", physical=True),
        S.PILOTING: _skill(SU, Capacity.MOBILITY, "Piloting"),
        S.DRIVING: _skill(SU, Capacity.MOBILITY, "Driving"),
        S.MECHANICS: _skill(CR, Capacity.CRAFT, "Mechanics", physical=True),
        S.ELECTRONICS: _skill(CR, Capacity.SCHOLARSHIP, "Electronics"),
        S.COMPUTING: _skill(KN, Capacity.SCHOLARSHIP, "Computing"),
        S.SCIENCE: _skill(KN, Capacity.SCHOLARSHIP, "Science"),
        S.ADMINISTRATION: _skill(CM, Capacity.COMMAND, "Administration"),
    },
)

COMBAT_SKILLS = tuple(kind for kind, spec in SKILLS.items() if spec.family is SkillFamily.COMBAT)
CRAFT_SKILLS = tuple(kind for kind, spec in SKILLS.items() if spec.family is SkillFamily.CRAFT)
MELEE_SKILLS = (S.BLADE, S.SPEAR, S.AXE, S.BLUNT, S.SHIELD, S.UNARMED, S.MOUNTED_COMBAT)
MISSILE_SKILLS = (S.BOW, S.SLING, S.THROWING, S.HUNTING, S.FIREARMS)
COMMAND_SKILLS = (S.TACTICS, S.STRATEGY, S.LOGISTICS, S.LEADERSHIP)
HEALING_SKILLS = (S.MEDICINE, S.SURGERY)
PREACHING_SKILLS = (S.ORATORY, S.THEOLOGY, S.RITUAL)
LEARNED_SKILLS = (S.LORE, S.WRITING, S.ASTRONOMY, S.LAW, S.THEOLOGY)

ROLE_SKILLS: MappingProxyType[MortalRole, MappingProxyType[SkillKind, int]] = MappingProxyType(
    {
        role: MappingProxyType(skills)
        for role, skills in {
            MortalRole.RULER: {S.LEADERSHIP: 45, S.STRATEGY: 30, S.LAW: 30, S.ETIQUETTE: 35, S.NEGOTIATION: 30, S.BLADE: 20},
            MortalRole.HERO: {S.BLADE: 50, S.SHIELD: 40, S.UNARMED: 35, S.LEADERSHIP: 25, S.TRACKING: 20},
            MortalRole.WARRIOR: {S.SPEAR: 45, S.SHIELD: 40, S.BLADE: 30, S.AXE: 25, S.UNARMED: 25},
            MortalRole.SWORN_WARRIOR: {S.MOUNTED_COMBAT: 50, S.RIDING: 50, S.BLADE: 40, S.SHIELD: 35, S.ETIQUETTE: 25},
            MortalRole.HUNTER: {S.BOW: 50, S.HUNTING: 50, S.TRACKING: 45, S.FORAGING: 30, S.THROWING: 25},
            MortalRole.CHOSEN: {S.RITUAL: 35, S.BLADE: 30, S.PROPHECY: 25, S.ORATORY: 25},
            MortalRole.SEER: {S.PROPHECY: 50, S.SPIRIT_SPEAKING: 40, S.RITUAL: 30, S.LORE: 25},
            MortalRole.PRIEST: {S.RITUAL: 50, S.THEOLOGY: 45, S.ORATORY: 35, S.WRITING: 20},
            MortalRole.SAGE: {S.LORE: 50, S.WRITING: 40, S.ASTRONOMY: 30, S.TEACHING: 35, S.LAW: 25},
            MortalRole.HEALER: {S.MEDICINE: 50, S.SURGERY: 35, S.FORAGING: 25, S.TEACHING: 15},
            MortalRole.ARTISAN: {S.SMITHING: 40, S.CARPENTRY: 35, S.MASONRY: 30, S.JEWELLING: 25, S.POTTERY: 25},
            MortalRole.MERCHANT: {S.NEGOTIATION: 50, S.ACCOUNTING: 45, S.LANGUAGES: 30, S.ETIQUETTE: 20, S.SAILING: 15},
            MortalRole.SCRIBE: {S.WRITING: 55, S.ACCOUNTING: 35, S.LAW: 30, S.LANGUAGES: 25, S.CRYPTOGRAPHY: 15},
            MortalRole.FARMER: {S.FORAGING: 40, S.BEAST_HANDLING: 30, S.CARPENTRY: 15, S.WEAVING: 15},
            MortalRole.EXPLORER: {S.NAVIGATION: 50, S.SAILING: 40, S.TRACKING: 40, S.MOUNTAINEERING: 35, S.LANGUAGES: 25},
            MortalRole.CAPTAIN: {S.TACTICS: 50, S.LEADERSHIP: 45, S.STRATEGY: 35, S.LOGISTICS: 30, S.SPEAR: 30},
            MortalRole.BANDIT: {S.BLADE: 35, S.INTIMIDATION: 40, S.TRACKING: 30, S.DECEPTION: 30, S.BOW: 25},
            MortalRole.SAINT: {S.RITUAL: 45, S.THEOLOGY: 40, S.ORATORY: 40, S.MEDICINE: 25},
            MortalRole.APPRENTICE: {S.TEACHING: 5, S.WRITING: 15, S.BLADE: 15},
            MortalRole.COMMONER: {S.FORAGING: 25, S.CARPENTRY: 15, S.WEAVING: 15, S.UNARMED: 10},
            MortalRole.OFFICER: {S.TACTICS: 45, S.LEADERSHIP: 40, S.FIREARMS: 35, S.LOGISTICS: 30, S.STRATEGY: 25},
            MortalRole.SPY: {S.INTRIGUE: 50, S.DECEPTION: 45, S.CRYPTOGRAPHY: 30, S.LANGUAGES: 30, S.FIREARMS: 15},
            MortalRole.SCIENTIST: {S.SCIENCE: 55, S.COMPUTING: 35, S.WRITING: 30, S.TEACHING: 20},
            MortalRole.ENGINEER: {S.ENGINEERING: 50, S.MECHANICS: 45, S.ELECTRONICS: 35, S.COMPUTING: 20},
            MortalRole.PILOT: {S.PILOTING: 55, S.NAVIGATION: 40, S.ELECTRONICS: 20, S.FIREARMS: 15},
            MortalRole.PHYSICIAN: {S.MEDICINE: 55, S.SURGERY: 45, S.SCIENCE: 25, S.TEACHING: 15},
            MortalRole.JOURNALIST: {S.WRITING: 45, S.ORATORY: 35, S.INTRIGUE: 25, S.LANGUAGES: 25},
            MortalRole.EXECUTIVE: {S.ADMINISTRATION: 45, S.NEGOTIATION: 45, S.ACCOUNTING: 40, S.LEADERSHIP: 25},
        }.items()
    }
)

CAREER_SKILLS: MappingProxyType[MortalRole, tuple[SkillKind, ...]] = MappingProxyType(
    {
        MortalRole.WARRIOR: (S.SPEAR, S.SHIELD, S.BLADE, S.AXE, S.BLUNT, S.UNARMED),
        MortalRole.SWORN_WARRIOR: (S.MOUNTED_COMBAT, S.RIDING),
        MortalRole.HUNTER: (S.HUNTING, S.BOW, S.TRACKING),
        MortalRole.SEER: (S.PROPHECY, S.SPIRIT_SPEAKING),
        MortalRole.PRIEST: (S.RITUAL, S.THEOLOGY),
        MortalRole.SAGE: (S.LORE, S.ASTRONOMY, S.TEACHING, S.LAW),
        MortalRole.HEALER: (S.MEDICINE, S.SURGERY),
        MortalRole.ARTISAN: CRAFT_SKILLS,
        MortalRole.MERCHANT: (S.NEGOTIATION, S.ACCOUNTING),
        MortalRole.SCRIBE: (S.WRITING, S.ACCOUNTING),
        MortalRole.FARMER: (S.FORAGING, S.BEAST_HANDLING),
        MortalRole.EXPLORER: (S.NAVIGATION, S.SAILING, S.MOUNTAINEERING),
        MortalRole.CAPTAIN: COMMAND_SKILLS,
        MortalRole.BANDIT: (S.INTIMIDATION, S.DECEPTION),
        MortalRole.OFFICER: (S.TACTICS, S.FIREARMS, S.LOGISTICS),
        MortalRole.SPY: (S.INTRIGUE, S.DECEPTION, S.CRYPTOGRAPHY),
        MortalRole.SCIENTIST: (S.SCIENCE, S.COMPUTING),
        MortalRole.ENGINEER: (S.ENGINEERING, S.MECHANICS, S.ELECTRONICS),
        MortalRole.PILOT: (S.PILOTING, S.NAVIGATION),
        MortalRole.PHYSICIAN: (S.MEDICINE, S.SURGERY),
        MortalRole.JOURNALIST: (S.WRITING, S.ORATORY),
        MortalRole.EXECUTIVE: (S.ADMINISTRATION, S.NEGOTIATION, S.ACCOUNTING),
    }
)

FIXED_ROLES = frozenset({MortalRole.RULER, MortalRole.HERO, MortalRole.CHOSEN, MortalRole.SAINT, MortalRole.APPRENTICE})

CAREER_VALUES: MappingProxyType[MortalRole, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        role: MappingProxyType(values)
        for role, values in {
            MortalRole.WARRIOR: {V.MARTIAL: 30, V.HONOUR: 10, V.COMPETITION: 10},
            MortalRole.SWORN_WARRIOR: {V.MARTIAL: 25, V.HONOUR: 20, V.HIERARCHY: 15, V.LOYALTY: 15},
            MortalRole.HUNTER: {V.NATURE: 25, V.MARTIAL: 10},
            MortalRole.SEER: {V.SUPERSTITION: 30, V.PIETY: 15},
            MortalRole.PRIEST: {V.PIETY: 35, V.TRADITION: 10},
            MortalRole.SAGE: {V.KNOWLEDGE: 35, V.TRADITION: 10, V.TRUTH: 15},
            MortalRole.HEALER: {V.MERCY: 30, V.KNOWLEDGE: 10, V.FRIENDSHIP: 10},
            MortalRole.ARTISAN: {V.KNOWLEDGE: 10, V.WEALTH: 15, V.CRAFTSMANSHIP: 30, V.ARTWORK: 10},
            MortalRole.MERCHANT: {V.WEALTH: 35, V.XENOPHILIA: 15, V.COMPETITION: 15},
            MortalRole.SCRIBE: {V.KNOWLEDGE: 25, V.HIERARCHY: 10, V.LAW: 10, V.TRUTH: 5},
            MortalRole.FARMER: {V.NATURE: 15, V.TRADITION: 15, V.FAMILY: 10, V.PERSEVERANCE: 10},
            MortalRole.EXPLORER: {V.XENOPHILIA: 30, V.TRADITION: -15, V.PERSEVERANCE: 10},
            MortalRole.CAPTAIN: {V.MARTIAL: 25, V.HIERARCHY: 15, V.LOYALTY: 10},
            MortalRole.BANDIT: {V.HONOUR: -30, V.MERCY: -15, V.LAW: -30, V.LOYALTY: -10},
            MortalRole.COMMONER: {},
            MortalRole.OFFICER: {V.MARTIAL: 20, V.HIERARCHY: 20, V.LOYALTY: 15},
            MortalRole.SPY: {V.LOYALTY: 15, V.TRUTH: -20, V.KNOWLEDGE: 10},
            MortalRole.SCIENTIST: {V.KNOWLEDGE: 35, V.TRUTH: 20, V.TRADITION: -10},
            MortalRole.ENGINEER: {V.KNOWLEDGE: 15, V.CRAFTSMANSHIP: 30},
            MortalRole.PILOT: {V.XENOPHILIA: 15, V.PERSEVERANCE: 15, V.COMPETITION: 10},
            MortalRole.PHYSICIAN: {V.MERCY: 30, V.KNOWLEDGE: 20},
            MortalRole.JOURNALIST: {V.TRUTH: 30, V.KNOWLEDGE: 10, V.HIERARCHY: -10},
            MortalRole.EXECUTIVE: {V.WEALTH: 30, V.COMPETITION: 20, V.HIERARCHY: 10},
        }.items()
    }
)


@dataclass(frozen=True)
class MemorySpec:
    components: MappingProxyType[OpinionComponent, int]
    decay_pct: int
    cares: MappingProxyType[ValueAxis, int]
    label: str
    act: ActKind | None = None
    inherited: bool = True


def _memory(
    components: dict[OpinionComponent, int], decay_pct: int, cares: dict[ValueAxis, int], label: str, act: ActKind | None = None, *, inherited: bool = True
) -> MemorySpec:
    return MemorySpec(MappingProxyType(components), decay_pct, MappingProxyType(cares), label, act, inherited)


MEMORIES: MappingProxyType[MemoryKind, MemorySpec] = total(
    MemoryKind,
    {
        M.MEMORY_GAP: _memory({OC.TRUST: 100}, 10, {}, "A gap in memory", inherited=False),
        M.COMPELLED_ME: _memory({OC.GRIEVANCE: 50, OC.TRUST: 30, OC.FEAR: 20}, 8, {V.HONOUR: 25, V.LAW: 10}, "Bent our minds"),
        M.HARMED_ME: _memory({OC.GRIEVANCE: 60, OC.TRUST: 25, OC.FEAR: 15}, 12, {V.HONOUR: 20, V.MERCY: 15}, "Harmed us", A.RAIDING),
        M.KILLED_KIN: _memory({OC.GRIEVANCE: 75, OC.TRUST: 15, OC.FEAR: 10}, 2, {V.KINSHIP: 40, V.HONOUR: 25}, "Killed our kin", A.EXECUTION),
        M.SAVED_ME: _memory({OC.AFFECTION: 45, OC.TRUST: 35, OC.RESPECT: 20}, 6, {V.MERCY: 20, V.KINSHIP: 15}, "Saved us"),
        M.BETRAYED_ME: _memory({OC.GRIEVANCE: 50, OC.TRUST: 50}, 5, {V.HONOUR: 40, V.KINSHIP: 15}, "Betrayed us", A.BETRAYAL),
        M.KEPT_OATH: _memory({OC.TRUST: 60, OC.RESPECT: 40}, 8, {V.HONOUR: 35}, "Kept an oath"),
        M.BROKE_OATH: _memory({OC.TRUST: 60, OC.GRIEVANCE: 25, OC.RESPECT: 15}, 6, {V.HONOUR: 40, V.PIETY: 10}, "Broke an oath", A.OATHBREAKING),
        M.MAIMED_ME: _memory({OC.GRIEVANCE: 65, OC.FEAR: 25, OC.TRUST: 10}, 4, {V.PURITY: 25, V.HONOUR: 20}, "Maimed us", A.MUTILATION),
        M.HUMILIATED_ME: _memory({OC.GRIEVANCE: 55, OC.RESPECT: 25, OC.FEAR: 20}, 7, {V.HONOUR: 35, V.HIERARCHY: 15}, "Humiliated us"),
        M.GIFTED_ME: _memory({OC.AFFECTION: 55, OC.TRUST: 30, OC.RESPECT: 15}, 15, {V.WEALTH: 15, V.KINSHIP: 10}, "Gave us gifts", A.HOSPITALITY),
        M.CONVERTED_ME: _memory({OC.AFFECTION: 40, OC.RESPECT: 40, OC.TRUST: 20}, 6, {V.PIETY: 35}, "Converted us"),
        M.CONQUERED_US: _memory(
            {OC.GRIEVANCE: 50, OC.FEAR: 35, OC.RESPECT: 15}, 3, {V.HONOUR: 25, V.XENOPHILIA: -25, V.KINSHIP: 15}, "Conquered us", A.CONQUEST
        ),
        M.FREED_US: _memory({OC.AFFECTION: 50, OC.TRUST: 30, OC.RESPECT: 20}, 4, {V.HONOUR: 20, V.KINSHIP: 15}, "Freed us"),
        M.FAMINE_AID: _memory({OC.AFFECTION: 55, OC.TRUST: 35, OC.RESPECT: 10}, 6, {V.MERCY: 25, V.KINSHIP: 15}, "Fed us in famine", A.HOSPITALITY),
        M.DESECRATED_HOLY: _memory({OC.GRIEVANCE: 70, OC.TRUST: 20, OC.RESPECT: 10}, 3, {V.PIETY: 45, V.PURITY: 20}, "Desecrated our holy places"),
        M.MARRIED_INTO: _memory({OC.AFFECTION: 45, OC.TRUST: 40, OC.RESPECT: 15}, 4, {V.KINSHIP: 40}, "Married into our line"),
        M.FOUGHT_US: _memory({OC.GRIEVANCE: 45, OC.FEAR: 25, OC.RESPECT: 15, OC.TRUST: 15}, 10, {V.MARTIAL: -15, V.HONOUR: 15}, "Fought us", A.RAIDING),
        M.TRADED_WITH: _memory(
            {OC.TRUST: 50, OC.AFFECTION: 30, OC.RESPECT: 20}, 15, {V.WEALTH: 25, V.XENOPHILIA: 20}, "Traded with us", A.TRADE_WITH_OUTSIDERS
        ),
        M.ALLIED_WITH: _memory({OC.TRUST: 50, OC.AFFECTION: 35, OC.RESPECT: 15}, 8, {V.HONOUR: 20, V.KINSHIP: 10}, "Stood with us"),
        M.MADE_PEACE: _memory({OC.TRUST: 45, OC.RESPECT: 35, OC.AFFECTION: 20}, 10, {V.MERCY: 20, V.MARTIAL: -15}, "Made peace with us", A.MERCY_TO_ENEMY),
        M.DEMANDED_TRIBUTE: _memory({OC.GRIEVANCE: 45, OC.FEAR: 40, OC.RESPECT: 15}, 8, {V.HONOUR: 25, V.HIERARCHY: -15}, "Took tribute from us"),
        M.CHEATED_US: _memory({OC.TRUST: 55, OC.GRIEVANCE: 45}, 10, {V.HONOUR: 25, V.WEALTH: 20}, "Cheated us"),
        M.SPIED_ON_US: _memory({OC.TRUST: 60, OC.GRIEVANCE: 30, OC.FEAR: 10}, 12, {V.XENOPHILIA: -20, V.HONOUR: 15}, "Spied on us"),
        M.ENVIED: _memory({OC.GRIEVANCE: 40, OC.RESPECT: 40, OC.AFFECTION: 20}, 15, {V.WEALTH: 20, V.HIERARCHY: 10}, "Outshone us"),
        M.FAILED_TO_HEAL: _memory(
            {OC.TRUST: 55, OC.GRIEVANCE: 35, OC.RESPECT: 10}, 10, {V.KINSHIP: 20, V.KNOWLEDGE: 15}, "Failed to heal our own", inherited=False
        ),
        M.TAUGHT_ME: _memory({OC.RESPECT: 50, OC.AFFECTION: 30, OC.TRUST: 20}, 5, {V.KNOWLEDGE: 30, V.TRADITION: 15}, "Taught us", A.LEARNING),
        M.HELD_CAPTIVE: _memory({OC.GRIEVANCE: 50, OC.FEAR: 35, OC.TRUST: 15}, 6, {V.HONOUR: 20, V.KINSHIP: 20}, "Held our own captive", A.TAKING_CAPTIVES),
        M.LAMENTED: _memory({OC.GRIEVANCE: 60, OC.AFFECTION: 20, OC.RESPECT: 20}, 5, {V.DEATH: 30, V.KINSHIP: 20}, "Is mourned in our laments"),
        M.DIVINE_WILL: _memory({OC.TRUST: 34, OC.AFFECTION: 33, OC.RESPECT: 33}, 0, {}, "The gods willed it", inherited=False),
        M.DREADS: _memory({OC.FEAR: 70, OC.RESPECT: 30}, 0, {}, "Dreads the power that touched them", inherited=False),
        M.GOODWILL: _memory({OC.AFFECTION: 45, OC.TRUST: 35, OC.RESPECT: 20}, 12, {V.XENOPHILIA: 15, V.KINSHIP: 10}, "Showed us goodwill"),
        M.LONG_HISTORY: _memory({OC.TRUST: 40, OC.AFFECTION: 30, OC.GRIEVANCE: 30}, 2, {}, "Long shared history", inherited=False),
        M.FORMATIVE: _memory({}, 1, {}, "A formative experience", inherited=False),
        M.ILL_WILL: _memory({OC.GRIEVANCE: 50, OC.TRUST: 35, OC.FEAR: 15}, 12, {V.XENOPHILIA: -15, V.HONOUR: 10}, "Showed us ill will"),
        M.STOLE_FAITHFUL: _memory({OC.GRIEVANCE: 60, OC.TRUST: 40}, 8, {V.LOYALTY: 15, V.COMPETITION: 15}, "Took our faithful"),
        M.AIDED_CHOSEN: _memory({OC.AFFECTION: 50, OC.TRUST: 50}, 10, {V.FRIENDSHIP: 15, V.LOYALTY: 10}, "Aided our chosen"),
    },
)

ACT_READINGS: MappingProxyType[ActKind, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        act: MappingProxyType(values)
        for act, values in {
            A.EXECUTION: {V.MERCY: -45, V.HIERARCHY: 25, V.HONOUR: 10, V.MARTIAL: 15, V.LAW: 20},
            A.MUTILATION: {V.MERCY: -50, V.PURITY: -30, V.HIERARCHY: 15},
            A.BETRAYAL: {V.HONOUR: -60, V.KINSHIP: -20, V.LOYALTY: -40, V.TRUTH: -20},
            A.MERCY_TO_ENEMY: {V.MERCY: 50, V.MARTIAL: -25, V.HONOUR: 15},
            A.SACRIFICE_OF_PEOPLE: {V.MERCY: -45, V.PIETY: 30, V.SUPERSTITION: 25, V.DEATH: 20},
            A.TRADE_WITH_OUTSIDERS: {V.XENOPHILIA: 50, V.WEALTH: 35, V.TRADITION: -15},
            A.BUILDING_TEMPLES: {V.PIETY: 50, V.TRADITION: 20, V.WEALTH: -10, V.CRAFTSMANSHIP: 10},
            A.BURNING_BOOKS: {V.KNOWLEDGE: -60, V.TRADITION: 20, V.PURITY: 15, V.ARTWORK: -20},
            A.CONQUEST: {V.MARTIAL: 45, V.HIERARCHY: 20, V.MERCY: -20, V.XENOPHILIA: -15, V.COMPETITION: 15},
            A.RAIDING: {V.MARTIAL: 35, V.HONOUR: -15, V.MERCY: -25},
            A.DUELLING: {V.HONOUR: 40, V.MARTIAL: 30, V.COMPETITION: 30},
            A.RANSOM: {V.WEALTH: 30, V.MERCY: 20, V.HONOUR: 10},
            A.TAKING_CAPTIVES: {V.MARTIAL: 25, V.MERCY: -20, V.HIERARCHY: 15},
            A.OATHBREAKING: {V.HONOUR: -55, V.PIETY: -20, V.TRUTH: -30, V.LOYALTY: -30},
            A.LEARNING: {V.KNOWLEDGE: 50, V.TRADITION: -15},
            A.HOSPITALITY: {V.XENOPHILIA: 35, V.KINSHIP: 20, V.MERCY: 15, V.FRIENDSHIP: 25},
            A.WINTER_FIGHTING: {V.MARTIAL: 30, V.TRADITION: -35, V.MERCY: -15},
            A.GUEST_KILLING: {V.HONOUR: -60, V.XENOPHILIA: -30, V.KINSHIP: -20, V.PIETY: -20, V.FRIENDSHIP: -30},
            A.RITUAL_SCARRING: {V.TRADITION: 45, V.PIETY: 25, V.MARTIAL: 15, V.PURITY: -20},
            A.KILLING_KIN: {V.FAMILY: -60, V.KINSHIP: -40, V.MERCY: -20},
            A.KILLING_OUTSIDER: {V.MERCY: -40, V.LAW: -30, V.XENOPHILIA: -15},
            A.KILLING_IN_WAR: {V.MARTIAL: 45, V.MERCY: -20, V.HONOUR: 10},
            A.KILLING_CAPTIVE: {V.MERCY: -55, V.HONOUR: -25, V.MARTIAL: 10},
            A.REGICIDE: {V.HIERARCHY: -55, V.LOYALTY: -40, V.LAW: -20},
            A.DUEL_TO_DEATH: {V.HONOUR: 45, V.MARTIAL: 30, V.MERCY: -20},
            A.REVENGE_KILLING: {V.FAMILY: 35, V.HONOUR: 30, V.LAW: -35, V.MERCY: -20},
            A.THEFT: {V.LAW: -50, V.TRUTH: -20, V.WEALTH: 10},
            A.TREASON: {V.LOYALTY: -60, V.HIERARCHY: -25, V.LAW: -20},
            A.COWARDICE: {V.MARTIAL: -45, V.HONOUR: -35, V.PERSEVERANCE: -20},
            A.DESECRATION: {V.PIETY: -60, V.PURITY: -25, V.TRADITION: -15},
            A.BRIBERY: {V.LAW: -40, V.TRUTH: -30, V.WEALTH: 25},
            A.SUICIDE: {V.DEATH: 30, V.PERSEVERANCE: -45, V.PIETY: -20, V.FAMILY: -20},
            A.TORTURE: {V.MERCY: -60, V.MARTIAL: 15, V.HIERARCHY: 15},
            A.EATING_SAPIENTS: {V.PURITY: -60, V.MERCY: -40, V.TRADITION: -20},
            A.ICONOCLASM: {V.ARTWORK: -45, V.PIETY: 25, V.PURITY: 25, V.TRADITION: -20},
            A.CONVERSION_BY_FORCE: {V.PIETY: 40, V.MERCY: -35, V.XENOPHILIA: -30},
            A.POLYGAMY: {V.HIERARCHY: 25, V.TRADITION: 15, V.FAMILY: 20, V.PURITY: -15},
            A.INCEST: {V.PURITY: -50, V.TRADITION: -20, V.KINSHIP: 15},
            A.MAGIC_USE: {V.SUPERSTITION: 40, V.KNOWLEDGE: 20, V.TRADITION: -10},
            A.BLOOD_MAGIC: {V.SUPERSTITION: 35, V.MERCY: -35, V.PURITY: -30},
            A.VOID_MAGIC: {V.SUPERSTITION: 30, V.PURITY: -45, V.TRADITION: -25},
            A.NECROMANCY: {V.DEATH: -40, V.PIETY: -30, V.SUPERSTITION: 30},
            A.HOARDING_IN_FAMINE: {V.MERCY: -45, V.WEALTH: 30, V.KINSHIP: -20},
            A.SLAVERY: {V.HIERARCHY: 40, V.MERCY: -40, V.WEALTH: 15},
            A.ADULTERY: {V.FAMILY: -40, V.LAW: -20, V.LOYALTY: -30},
            A.USURY: {V.WEALTH: 35, V.MERCY: -30, V.KINSHIP: -10},
            A.INFANTICIDE: {V.MERCY: -55, V.FAMILY: -40, V.TRADITION: -10},
            A.ABANDONING_ELDERS: {V.MERCY: -40, V.FAMILY: -35, V.TRADITION: -20},
            A.FORCED_LABOUR: {V.HIERARCHY: 35, V.MERCY: -30, V.LAW: 15},
            A.SELLING_OFFICES: {V.WEALTH: 35, V.LAW: -30, V.HONOUR: -20},
            A.POACHING: {V.LAW: -30, V.HIERARCHY: -20, V.KINSHIP: 10},
            A.ENCLOSING: {V.WEALTH: 35, V.HIERARCHY: 25, V.MERCY: -30, V.TRADITION: -20},
        }.items()
    }
)

NEED_LABELS = MappingProxyType({kind: spec.label for kind, spec in NEEDS.items()})

PRESSURE_LABELS = MappingProxyType(
    {
        P.HUNGER: "Hunger",
        P.INSECURITY: "Insecurity",
        P.OVERCROWDING: "Overcrowding",
        P.POVERTY: "Poverty",
        P.IMPIETY: "Impiety",
        P.HUMILIATION: "Humiliation",
        P.STAGNATION: "Stagnation",
        P.POLLUTION: "Pollution",
        P.UNEMPLOYMENT: "Unemployment",
        P.OPPRESSION: "Oppression",
        P.DISEASE_BURDEN: "Burden of disease",
        P.PURPOSELESSNESS: "Want of purpose",
    }
)

HUMILIATING_MEMORIES = frozenset({M.CONQUERED_US, M.HUMILIATED_ME, M.DEMANDED_TRIBUTE, M.CHEATED_US})
THREAT_MEMORIES = frozenset({M.FOUGHT_US, M.HARMED_ME, M.CONQUERED_US, M.KILLED_KIN, M.SPIED_ON_US})

RELATION_EVENT_MEMORIES = MappingProxyType(
    {
        "battle": M.FOUGHT_US,
        "muharebe": M.FOUGHT_US,
        "invasion": M.FOUGHT_US,
        "istila": M.FOUGHT_US,
        "tribute revolt": M.FOUGHT_US,
        "debt war": M.FOUGHT_US,
        "conquest": M.CONQUERED_US,
        "fetih": M.CONQUERED_US,
        "victory": M.HUMILIATED_ME,
        "trade": M.TRADED_WITH,
        "ticaret": M.TRADED_WITH,
        "barter": M.TRADED_WITH,
        "first contact": M.TRADED_WITH,
        "uneasy first contact": M.ILL_WILL,
        "distance from the homeland": M.ILL_WILL,
        "peace": M.MADE_PEACE,
        "exhaustion peace": M.MADE_PEACE,
        "white peace": M.MADE_PEACE,
        "peace miracle": M.DIVINE_WILL,
        "alliance": M.ALLIED_WITH,
        "ittifak": M.ALLIED_WITH,
        "interworld alliance": M.ALLIED_WITH,
        "interworld treaty": M.ALLIED_WITH,
        "marriage": M.MARRIED_INTO,
        "evlilik": M.MARRIED_INTO,
        "tribute": M.DEMANDED_TRIBUTE,
        "debt turned to tribute": M.DEMANDED_TRIBUTE,
        "tribute ended": M.FREED_US,
        "ransom": M.FREED_US,
        "tribute forgiven": M.GIFTED_ME,
        "debt forgiven": M.GIFTED_ME,
        "debt written off": M.GIFTED_ME,
        "loan": M.GIFTED_ME,
        "debt paid": M.KEPT_OATH,
        "unpaid debt": M.CHEATED_US,
        "broke an oath": M.BROKE_OATH,
        "betrayal": M.BETRAYED_ME,
        "caught spies": M.SPIED_ON_US,
        "resource seized": M.HARMED_ME,
        "adoption": M.GOODWILL,
    }
)


def memory_for_event(event: str, delta: int) -> MemoryKind:
    return RELATION_EVENT_MEMORIES.get(event.strip().lower(), M.GOODWILL if delta >= 0 else M.ILL_WILL)


T_ = TraitKind
DEPTH_WORDS: MappingProxyType[TraitKind, tuple[str, ...]] = MappingProxyType(
    {
        T_.BRAVE: ("brave", "bold", "fearless", "daring", "valiant", "courageous"),
        T_.CRAVEN: ("coward", "cowardly", "craven", "timid", "fearful"),
        T_.WRATHFUL: ("wrathful", "angry", "furious", "hot-tempered", "temper", "rage"),
        T_.PATIENT: ("patient", "calm", "unhurried", "serene"),
        T_.CRUEL: ("cruel", "sadistic", "merciless", "ruthless", "brutal"),
        T_.KIND: ("kind-hearted", "gentle", "compassionate", "tender", "caring"),
        T_.AMBITIOUS: ("ambitious", "driven", "hungry for power", "aspiring"),
        T_.CONTENT: ("contented", "satisfied", "easygoing"),
        T_.GREEDY: ("greedy", "miser", "miserly", "avaricious", "grasping"),
        T_.GENEROUS: ("generous", "giving", "open-handed", "charitable"),
        T_.HONEST: ("honest", "truthful", "candid", "sincere"),
        T_.DECEITFUL: ("deceitful", "liar", "lying", "treacherous", "sly", "two-faced"),
        T_.ZEALOUS: ("zealous", "devout", "fanatic", "fanatical", "pious"),
        T_.CYNICAL: ("cynical", "sceptical", "skeptical", "doubting", "faithless"),
        T_.PARANOID: ("paranoid", "suspicious", "distrustful"),
        T_.TRUSTING: ("trusting", "naive", "credulous"),
        T_.LUSTFUL: ("lustful", "lecherous", "amorous", "seductive"),
        T_.CHASTE: ("chaste", "celibate", "pure-hearted"),
        T_.GLUTTONOUS: ("glutton", "gluttonous", "greedy eater", "drunkard"),
        T_.ASCETIC: ("ascetic", "austere", "frugal", "abstinent"),
        T_.SCHOLARLY: ("scholarly", "learned", "bookish", "studious", "wise"),
        T_.ILLITERATE_PROUD: ("illiterate", "unlettered", "scorns books"),
        T_.GREGARIOUS: ("gregarious", "sociable", "jovial", "talkative", "merry"),
        T_.RECLUSIVE: ("reclusive", "hermit", "solitary", "withdrawn", "shy"),
        T_.VENGEFUL: ("vengeful", "grudge", "spiteful", "vindictive"),
        T_.FORGIVING: ("forgiving", "merciful", "lenient"),
        T_.STUBBORN: ("stubborn", "obstinate", "headstrong", "mulish"),
        T_.FICKLE: ("fickle", "capricious", "flighty", "inconstant"),
        T_.JUST: ("fair-minded", "righteous", "even-handed", "upright"),
        T_.ARBITRARY: ("arbitrary", "whimsical", "unfair", "tyrannical"),
        T_.HUMBLE: ("humble", "modest", "meek"),
        T_.PROUD: ("proud", "arrogant", "haughty", "vain"),
        T_.CURIOUS: ("curious", "inquisitive", "questioning", "wondering"),
        T_.INCURIOUS: ("incurious", "dull", "indifferent"),
        T_.MELANCHOLIC: ("melancholic", "melancholy", "sad", "gloomy", "brooding", "sorrowful"),
        T_.SANGUINE: ("sanguine", "cheerful", "hopeful", "optimistic"),
        T_.IRON_WILLED: ("iron-willed", "resolute", "unbending", "steadfast", "determined"),
        T_.IMPRESSIONABLE: ("impressionable", "gullible", "easily swayed"),
        T_.CUNNING_TACTICIAN: ("tactician", "strategist", "cunning", "shrewd", "wily"),
        T_.RECKLESS: ("reckless", "rash", "impulsive", "foolhardy"),
    }
)


@dataclass(frozen=True)
class ProfessionSpec:
    label: str
    skills: tuple[SkillKind, ...]
    role: MortalRole


PROFESSIONS: MappingProxyType[Profession, ProfessionSpec] = total(
    Profession,
    {
        Profession.SOLDIER: ProfessionSpec("Soldier", (S.SPEAR, S.SHIELD, S.BLADE, S.AXE, S.BOW), MortalRole.WARRIOR),
        Profession.RIDER: ProfessionSpec("Rider", (S.RIDING, S.MOUNTED_COMBAT, S.BEAST_HANDLING), MortalRole.SWORN_WARRIOR),
        Profession.SMITH: ProfessionSpec("Metalworker", (S.SMITHING, S.JEWELLING, S.ENGINEERING), MortalRole.ARTISAN),
        Profession.BUILDER: ProfessionSpec("Builder", (S.MASONRY, S.CARPENTRY, S.ENGINEERING), MortalRole.ARTISAN),
        Profession.WEAVER: ProfessionSpec("Weaver", (S.WEAVING, S.POTTERY), MortalRole.ARTISAN),
        Profession.HEALER: ProfessionSpec("Healer", (S.MEDICINE, S.SURGERY, S.FORAGING), MortalRole.HEALER),
        Profession.SCHOLAR: ProfessionSpec("Scholar", (S.LORE, S.WRITING, S.ASTRONOMY, S.LANGUAGES), MortalRole.SAGE),
        Profession.PRIEST: ProfessionSpec("Priest", (S.THEOLOGY, S.RITUAL, S.ORATORY), MortalRole.PRIEST),
        Profession.SORCERER: ProfessionSpec("Sorcerer", (S.SPELLCRAFT, S.ALCHEMY, S.SPIRIT_SPEAKING), MortalRole.SAGE),
        Profession.MERCHANT: ProfessionSpec("Merchant", (S.ACCOUNTING, S.NEGOTIATION, S.SAILING), MortalRole.MERCHANT),
        Profession.DIPLOMAT: ProfessionSpec("Diplomat", (S.NEGOTIATION, S.ETIQUETTE, S.LANGUAGES, S.ORATORY), MortalRole.SCRIBE),
        Profession.HUNTER: ProfessionSpec("Hunter", (S.HUNTING, S.TRACKING, S.BOW), MortalRole.HUNTER),
        Profession.SAILOR: ProfessionSpec("Sailor", (S.SAILING, S.NAVIGATION, S.SWIMMING), MortalRole.CAPTAIN),
        Profession.COMMANDER: ProfessionSpec("Commander", (S.TACTICS, S.STRATEGY, S.LEADERSHIP, S.LOGISTICS), MortalRole.SWORN_WARRIOR),
        Profession.ENGINEER: ProfessionSpec("Engineer", (S.ENGINEERING, S.MECHANICS, S.ELECTRONICS), MortalRole.ENGINEER),
        Profession.SCIENTIST: ProfessionSpec("Scientist", (S.SCIENCE, S.COMPUTING, S.WRITING), MortalRole.SCIENTIST),
        Profession.PILOT: ProfessionSpec("Pilot", (S.PILOTING, S.NAVIGATION, S.ELECTRONICS), MortalRole.PILOT),
        Profession.TECHNICIAN: ProfessionSpec("Technician", (S.ELECTRONICS, S.MECHANICS), MortalRole.ENGINEER),
        Profession.PROGRAMMER: ProfessionSpec("Programmer", (S.COMPUTING, S.CRYPTOGRAPHY, S.SCIENCE), MortalRole.SCIENTIST),
        Profession.MECHANIC: ProfessionSpec("Mechanic", (S.MECHANICS, S.DRIVING, S.SMITHING), MortalRole.ARTISAN),
        Profession.MINER: ProfessionSpec("Miner", (S.MASONRY, S.ENGINEERING, S.MOUNTAINEERING), MortalRole.COMMONER),
        Profession.FARMER: ProfessionSpec("Farmer", (S.FORAGING, S.BEAST_HANDLING, S.DRIVING), MortalRole.FARMER),
        Profession.ARTIST: ProfessionSpec("Artist", (S.WEAVING, S.POTTERY, S.JEWELLING, S.ORATORY), MortalRole.ARTISAN),
        Profession.ADMINISTRATOR: ProfessionSpec("Administrator", (S.ADMINISTRATION, S.LAW, S.ACCOUNTING), MortalRole.SCRIBE),
        Profession.SPACER: ProfessionSpec("Spacer", (S.PILOTING, S.NAVIGATION, S.MECHANICS), MortalRole.PILOT),
        Profession.DEATH_WORKER: ProfessionSpec("Death worker", (S.RITUAL, S.MEDICINE), MortalRole.COMMONER),
    },
)
BRANCH_SKILLS: MappingProxyType[KnowledgeBranch, SkillKind] = total(
    KnowledgeBranch,
    {
        KnowledgeBranch.AGRICULTURE: S.FORAGING,
        KnowledgeBranch.METALLURGY: S.SMITHING,
        KnowledgeBranch.SEAFARING: S.SAILING,
        KnowledgeBranch.WRITING: S.WRITING,
        KnowledgeBranch.ARCHITECTURE: S.MASONRY,
        KnowledgeBranch.MEDICINE: S.MEDICINE,
        KnowledgeBranch.MAGIC: S.SPELLCRAFT,
        KnowledgeBranch.WARFARE: S.TACTICS,
        KnowledgeBranch.ASTRONOMY: S.ASTRONOMY,
        KnowledgeBranch.TRADE: S.ACCOUNTING,
        KnowledgeBranch.SKY_NAVIGATION: S.NAVIGATION,
        KnowledgeBranch.SHIPBUILDING: S.SHIPWRIGHT,
        KnowledgeBranch.GATE_LORE: S.LORE,
        KnowledgeBranch.PATHFINDING: S.TRACKING,
        KnowledgeBranch.VOID_LIVING: S.LORE,
        KnowledgeBranch.IMMORTALITY: S.ALCHEMY,
        KnowledgeBranch.BIOMANCY: S.MEDICINE,
        KnowledgeBranch.FORBIDDEN: S.SPELLCRAFT,
        KnowledgeBranch.CIVICS: S.LAW,
    },
)
