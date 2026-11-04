from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.domain.enums.body import Capacity, ConditionKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, MortalRole
from aerona.domain.enums.mind import (
    ActKind,
    MemoryKind,
    NeedKind,
    OpinionComponent,
    PressureKind,
    Profession,
    SkillFamily,
    SkillKind,
    TraitEffect,
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
N = NeedKind

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
    }
)

DOMAIN_VALUES: MappingProxyType[Domain, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        domain: MappingProxyType(values)
        for domain, values in {
            Domain.SEA: {V.XENOPHILIA: 25, V.NATURE: 15, V.SUPERSTITION: 10},
            Domain.FIRE: {V.MARTIAL: 20, V.PURITY: 20, V.TRADITION: -10},
            Domain.EARTH: {V.TRADITION: 25, V.NATURE: 20, V.KINSHIP: 10},
            Domain.SKY: {V.HIERARCHY: 15, V.PIETY: 15, V.KNOWLEDGE: 10},
            Domain.STORM: {V.MARTIAL: 25, V.SUPERSTITION: 15, V.MERCY: -10},
            Domain.DEATH: {V.DEATH: 40, V.PIETY: 10, V.MERCY: -5},
            Domain.LIFE: {V.MERCY: 25, V.NATURE: 20, V.DEATH: -20},
            Domain.DREAM: {V.SUPERSTITION: 30, V.KNOWLEDGE: 10, V.TRADITION: -5},
            Domain.TIME: {V.TRADITION: 25, V.KNOWLEDGE: 15, V.DEATH: 10},
            Domain.LIGHT: {V.PURITY: 25, V.PIETY: 20, V.MERCY: 10},
            Domain.SHADOW: {V.HONOUR: -20, V.SUPERSTITION: 15, V.XENOPHILIA: -10},
            Domain.WAR: {V.MARTIAL: 40, V.HONOUR: 15, V.MERCY: -15},
            Domain.CRAFT: {V.KNOWLEDGE: 20, V.WEALTH: 15, V.TRADITION: -10},
            Domain.KNOWLEDGE: {V.KNOWLEDGE: 40, V.SUPERSTITION: -15, V.TRADITION: -10},
            Domain.LOVE: {V.MERCY: 25, V.KINSHIP: 20, V.MARTIAL: -15},
            Domain.TRICKERY: {V.HONOUR: -30, V.WEALTH: 15, V.HIERARCHY: -10},
            Domain.HUNT: {V.MARTIAL: 15, V.NATURE: 25, V.KINSHIP: 10},
            Domain.PLANTS: {V.NATURE: 35, V.MERCY: 10, V.MARTIAL: -10},
            Domain.BONE: {V.DEATH: 30, V.TRADITION: 15, V.PURITY: -10},
            Domain.BLOOD: {V.KINSHIP: 25, V.MARTIAL: 15, V.MERCY: -15},
            Domain.SOUND: {V.KNOWLEDGE: 10, V.XENOPHILIA: 15, V.TRADITION: 10},
            Domain.STONE: {V.TRADITION: 30, V.HIERARCHY: 15, V.XENOPHILIA: -10},
            Domain.ICE: {V.PURITY: 20, V.TRADITION: 15, V.MERCY: -10},
            Domain.MADNESS: {V.SUPERSTITION: 30, V.TRADITION: -20, V.HIERARCHY: -10},
            Domain.TRADE: {V.WEALTH: 35, V.XENOPHILIA: 25, V.MARTIAL: -10},
            Domain.ROAD: {V.XENOPHILIA: 30, V.TRADITION: -15, V.KINSHIP: -10},
            Domain.PLAGUE: {V.DEATH: 20, V.PURITY: 25, V.XENOPHILIA: -20},
            Domain.HARVEST: {V.NATURE: 25, V.KINSHIP: 15, V.TRADITION: 15},
            Domain.MOON: {V.SUPERSTITION: 25, V.NATURE: 10, V.DEATH: 10},
            Domain.SUN: {V.HIERARCHY: 25, V.PIETY: 20, V.PURITY: 10},
            Domain.STAR: {V.KNOWLEDGE: 25, V.SUPERSTITION: 20, V.PIETY: 10},
            Domain.LIES: {V.HONOUR: -35, V.KNOWLEDGE: -10, V.WEALTH: 10},
            Domain.OATH: {V.HONOUR: 40, V.TRADITION: 15, V.KINSHIP: 10},
            Domain.MEMORY: {V.TRADITION: 30, V.DEATH: 20, V.KNOWLEDGE: 10},
            Domain.HUNGER: {V.WEALTH: -20, V.MERCY: -15, V.MARTIAL: 15},
            Domain.GLASS: {V.KNOWLEDGE: 20, V.PURITY: 15, V.WEALTH: 10},
            Domain.SALT: {V.PURITY: 20, V.WEALTH: 15, V.TRADITION: 10},
            Domain.ASH: {V.DEATH: 25, V.PURITY: 10, V.TRADITION: -10},
            Domain.BORDER: {V.XENOPHILIA: -25, V.MARTIAL: 15, V.KINSHIP: 15},
            Domain.SLEEP: {V.DEATH: 15, V.MERCY: 15, V.MARTIAL: -20},
        }.items()
    }
)

PEOPLE_STAT_VALUES = MappingProxyType(
    {
        "martiality": MappingProxyType({V.MARTIAL: 70, V.MERCY: -20}),
        "piety": MappingProxyType({V.PIETY: 70, V.SUPERSTITION: 20}),
        "magic": MappingProxyType({V.SUPERSTITION: 50, V.KNOWLEDGE: 20}),
        "craft": MappingProxyType({V.KNOWLEDGE: 40, V.TRADITION: -20}),
        "wealth": MappingProxyType({V.WEALTH: 60, V.XENOPHILIA: 20}),
        "prosperity": MappingProxyType({V.WEALTH: 20, V.HIERARCHY: 15}),
    }
)

PASSION_VALUES = MappingProxyType(
    {
        Passion.MERCY: MappingProxyType({V.MERCY: 80, V.MARTIAL: -20}),
        Passion.WRATH: MappingProxyType({V.MERCY: -50, V.MARTIAL: 50}),
        Passion.AMBITION: MappingProxyType({V.HIERARCHY: 40, V.WEALTH: 25, V.TRADITION: -20}),
        Passion.LOYALTY: MappingProxyType({V.KINSHIP: 45, V.HONOUR: 40, V.TRADITION: 20}),
    }
)

AGENDA_VALUES = MappingProxyType(
    {
        EngineKind.MERCHANT_GUILD: MappingProxyType({V.WEALTH: 60, V.XENOPHILIA: 30, V.MARTIAL: -20}),
        EngineKind.PRIESTS_COUNCIL: MappingProxyType({V.PIETY: 60, V.TRADITION: 30, V.HIERARCHY: 20}),
        EngineKind.WARRIOR_BAND: MappingProxyType({V.MARTIAL: 60, V.HONOUR: 30, V.KINSHIP: 20}),
        EngineKind.REBELS: MappingProxyType({V.HIERARCHY: -60, V.TRADITION: -30, V.MERCY: -10}),
    }
)

DOCTRINE_BASE = MappingProxyType({V.PIETY: 45, V.TRADITION: 15})


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


TRAITS: MappingProxyType[TraitKind, TraitSpec] = MappingProxyType(
    {
        T.BRAVE: _trait(
            T.CRAVEN,
            {V.MARTIAL: 15, V.HONOUR: 10},
            capacities={Capacity.MELEE: 10},
            effects={E.COURAGE: 30, E.WAR_APPETITE: 10},
            heritable=True,
            divine=True,
            label="Brave",
        ),
        T.CRAVEN: _trait(
            T.BRAVE,
            {V.MARTIAL: -15},
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
            {V.MERCY: 10, V.TRADITION: 5},
            capacities={Capacity.CRAFT: 5, Capacity.COMMAND: 5},
            effects={E.WAR_APPETITE: -15, E.LEARNING: 10},
            divine=True,
            label="Patient",
        ),
        T.CRUEL: _trait(T.KIND, {V.MERCY: -30}, effects={E.CRUELTY: 40, E.TRUST: -10}, divine=True, label="Cruel"),
        T.KIND: _trait(T.CRUEL, {V.MERCY: 30}, capacities={Capacity.PRESENCE: 5}, effects={E.CRUELTY: -40, E.TRUST: 10}, divine=True, label="Kind"),
        T.AMBITIOUS: _trait(
            T.CONTENT, {V.HIERARCHY: 15, V.WEALTH: 10}, effects={E.AGENT_WEIGHT: 25, E.BETRAYAL: 20, E.WAR_APPETITE: 10}, divine=True, label="Ambitious"
        ),
        T.CONTENT: _trait(T.AMBITIOUS, {V.TRADITION: 10}, effects={E.AGENT_WEIGHT: -20, E.BETRAYAL: -20}, label="Content"),
        T.GREEDY: _trait(T.GENEROUS, {V.WEALTH: 25, V.MERCY: -10}, effects={E.GREED: 35, E.BETRAYAL: 10}, divine=True, label="Greedy"),
        T.GENEROUS: _trait(
            T.GREEDY, {V.WEALTH: -15, V.MERCY: 15}, capacities={Capacity.PRESENCE: 5}, effects={E.GREED: -35, E.TRUST: 10}, divine=True, label="Generous"
        ),
        T.HONEST: _trait(T.DECEITFUL, {V.HONOUR: 25}, effects={E.DECEIT: -40, E.TRUST: 15, E.BETRAYAL: -15}, divine=True, label="Honest"),
        T.DECEITFUL: _trait(T.HONEST, {V.HONOUR: -25}, effects={E.DECEIT: 40, E.TRUST: -15, E.BETRAYAL: 20}, divine=True, label="Deceitful"),
        T.ZEALOUS: _trait(T.CYNICAL, {V.PIETY: 30, V.SUPERSTITION: 10}, effects={E.ZEAL: 40, E.DRIFT: -15}, divine=True, label="Zealous"),
        T.CYNICAL: _trait(T.ZEALOUS, {V.PIETY: -25, V.SUPERSTITION: -15}, effects={E.ZEAL: -40, E.TRUST: -10}, label="Cynical"),
        T.PARANOID: _trait(T.TRUSTING, {V.XENOPHILIA: -20}, effects={E.TRUST: -30, E.MEMORY_DECAY: -25}, divine=True, label="Paranoid"),
        T.TRUSTING: _trait(T.PARANOID, {V.XENOPHILIA: 15}, effects={E.TRUST: 25}, label="Trusting"),
        T.LUSTFUL: _trait(T.CHASTE, {V.PURITY: -15}, effects={E.FERTILITY: 25}, divine=True, label="Lustful"),
        T.CHASTE: _trait(T.LUSTFUL, {V.PURITY: 20, V.PIETY: 5}, effects={E.FERTILITY: -40}, divine=True, label="Chaste"),
        T.GLUTTONOUS: _trait(T.ASCETIC, {V.WEALTH: 10, V.PURITY: -10}, capacities={Capacity.MOBILITY: -5}, label="Gluttonous"),
        T.ASCETIC: _trait(T.GLUTTONOUS, {V.PIETY: 15, V.WEALTH: -20, V.PURITY: 10}, effects={E.ZEAL: 15}, divine=True, label="Ascetic"),
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
            T.RECLUSIVE, {V.KINSHIP: 10, V.XENOPHILIA: 10}, capacities={Capacity.PRESENCE: 12}, effects={E.TRUST: 10}, heritable=True, label="Gregarious"
        ),
        T.RECLUSIVE: _trait(
            T.GREGARIOUS,
            {V.KINSHIP: -10, V.XENOPHILIA: -10},
            capacities={Capacity.PRESENCE: -12, Capacity.SCHOLARSHIP: 5},
            effects={E.AGENT_WEIGHT: -10},
            divine=True,
            label="Reclusive",
        ),
        T.VENGEFUL: _trait(T.FORGIVING, {V.HONOUR: 10, V.MERCY: -20}, effects={E.MEMORY_DECAY: -50, E.WAR_APPETITE: 10}, divine=True, label="Vengeful"),
        T.FORGIVING: _trait(T.VENGEFUL, {V.MERCY: 20}, effects={E.MEMORY_DECAY: 60, E.TRUST: 5}, divine=True, label="Forgiving"),
        T.STUBBORN: _trait(T.FICKLE, {V.TRADITION: 15}, effects={E.DRIFT: -50}, heritable=True, divine=True, label="Stubborn"),
        T.FICKLE: _trait(T.STUBBORN, {V.TRADITION: -15}, effects={E.DRIFT: 60, E.BETRAYAL: 10}, divine=True, label="Fickle"),
        T.JUST: _trait(
            T.ARBITRARY, {V.HONOUR: 15, V.HIERARCHY: -5}, capacities={Capacity.COMMAND: 5}, effects={E.JUSTICE: 40, E.TRUST: 10}, divine=True, label="Just"
        ),
        T.ARBITRARY: _trait(T.JUST, {V.HONOUR: -10, V.HIERARCHY: 15}, effects={E.JUSTICE: -40, E.CRUELTY: 10}, divine=True, label="Arbitrary"),
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
            None,
            {V.MARTIAL: 10, V.TRADITION: -10},
            capacities={Capacity.MELEE: 8, Capacity.COMMAND: -10},
            effects={E.WAR_APPETITE: 20, E.COURAGE: 25, E.EXPLORATION: 20},
            label="Reckless",
        ),
    }
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
    }
)

PLEASURE_TRAITS = frozenset({T.LUSTFUL, T.GLUTTONOUS})


@dataclass(frozen=True)
class SkillSpec:
    family: SkillFamily
    capacity: Capacity
    stats: tuple[str, ...]
    physical: bool
    label: str


def _skill(family: SkillFamily, capacity: Capacity, stats: tuple[str, ...], label: str, *, physical: bool = False) -> SkillSpec:
    return SkillSpec(family, capacity, stats, physical, label)


C, CM, SO, CR, KN, SU, FA = (
    SkillFamily.COMBAT,
    SkillFamily.COMMAND,
    SkillFamily.SOCIAL,
    SkillFamily.CRAFT,
    SkillFamily.KNOWLEDGE,
    SkillFamily.SURVIVAL,
    SkillFamily.FAITH,
)
STR, AGI, INT, CHA = ("strength",), ("agility",), ("intellect",), ("charisma",)

SKILLS: MappingProxyType[SkillKind, SkillSpec] = MappingProxyType(
    {
        S.BLADE: _skill(C, Capacity.MELEE, ("agility", "strength"), "Blade", physical=True),
        S.SPEAR: _skill(C, Capacity.MELEE, ("strength", "agility"), "Spear", physical=True),
        S.AXE: _skill(C, Capacity.MELEE, STR, "Axe", physical=True),
        S.BLUNT: _skill(C, Capacity.MELEE, STR, "Mace and hammer", physical=True),
        S.BOW: _skill(C, Capacity.MISSILE, AGI, "Bow", physical=True),
        S.SLING: _skill(C, Capacity.MISSILE, AGI, "Sling", physical=True),
        S.THROWING: _skill(C, Capacity.MISSILE, ("agility", "strength"), "Throwing", physical=True),
        S.SHIELD: _skill(C, Capacity.MELEE, STR, "Shield", physical=True),
        S.UNARMED: _skill(C, Capacity.MELEE, ("strength", "agility"), "Unarmed fighting", physical=True),
        S.RIDING: _skill(C, Capacity.MOBILITY, AGI, "Riding", physical=True),
        S.MOUNTED_COMBAT: _skill(C, Capacity.MELEE, ("agility", "strength"), "Mounted combat", physical=True),
        S.SIEGECRAFT: _skill(C, Capacity.COMMAND, INT, "Siegecraft"),
        S.NAVAL_COMBAT: _skill(C, Capacity.MELEE, ("agility", "intellect"), "Naval combat", physical=True),
        S.BEAST_HANDLING: _skill(C, Capacity.PRESENCE, ("charisma", "agility"), "Beast handling"),
        S.TACTICS: _skill(CM, Capacity.COMMAND, INT, "Tactics"),
        S.STRATEGY: _skill(CM, Capacity.COMMAND, INT, "Strategy"),
        S.LOGISTICS: _skill(CM, Capacity.COMMAND, INT, "Logistics"),
        S.LEADERSHIP: _skill(CM, Capacity.COMMAND, CHA, "Leadership"),
        S.INTIMIDATION: _skill(CM, Capacity.PRESENCE, ("strength", "charisma"), "Intimidation"),
        S.ORATORY: _skill(SO, Capacity.PRESENCE, CHA, "Oratory"),
        S.NEGOTIATION: _skill(SO, Capacity.PRESENCE, ("charisma", "intellect"), "Negotiation"),
        S.INTRIGUE: _skill(SO, Capacity.SCHOLARSHIP, ("intellect", "charisma"), "Intrigue"),
        S.ETIQUETTE: _skill(SO, Capacity.PRESENCE, CHA, "Etiquette"),
        S.DECEPTION: _skill(SO, Capacity.PRESENCE, ("charisma", "intellect"), "Deception"),
        S.TEACHING: _skill(SO, Capacity.PRESENCE, ("intellect", "charisma"), "Teaching"),
        S.SMITHING: _skill(CR, Capacity.CRAFT, ("strength", "intellect"), "Smithing", physical=True),
        S.CARPENTRY: _skill(CR, Capacity.CRAFT, ("strength", "agility"), "Carpentry", physical=True),
        S.MASONRY: _skill(CR, Capacity.CRAFT, STR, "Masonry", physical=True),
        S.WEAVING: _skill(CR, Capacity.CRAFT, AGI, "Weaving"),
        S.POTTERY: _skill(CR, Capacity.CRAFT, AGI, "Pottery"),
        S.JEWELLING: _skill(CR, Capacity.CRAFT, ("agility", "intellect"), "Jewelling"),
        S.SHIPWRIGHT: _skill(CR, Capacity.CRAFT, ("strength", "intellect"), "Shipwright", physical=True),
        S.ENGINEERING: _skill(CR, Capacity.SCHOLARSHIP, INT, "Engineering"),
        S.ALCHEMY: _skill(CR, Capacity.SCHOLARSHIP, INT, "Alchemy"),
        S.LORE: _skill(KN, Capacity.SCHOLARSHIP, INT, "Lore"),
        S.MEDICINE: _skill(KN, Capacity.CRAFT, INT, "Medicine"),
        S.SURGERY: _skill(KN, Capacity.CRAFT, ("intellect", "agility"), "Surgery"),
        S.ASTRONOMY: _skill(KN, Capacity.SCHOLARSHIP, INT, "Astronomy"),
        S.LAW: _skill(KN, Capacity.SCHOLARSHIP, INT, "Law"),
        S.THEOLOGY: _skill(KN, Capacity.SCHOLARSHIP, INT, "Theology"),
        S.LANGUAGES: _skill(KN, Capacity.SCHOLARSHIP, INT, "Languages"),
        S.WRITING: _skill(KN, Capacity.SCHOLARSHIP, INT, "Writing"),
        S.ACCOUNTING: _skill(KN, Capacity.SCHOLARSHIP, INT, "Accounting"),
        S.HUNTING: _skill(SU, Capacity.MISSILE, AGI, "Hunting", physical=True),
        S.TRACKING: _skill(SU, Capacity.MOBILITY, ("intellect", "agility"), "Tracking"),
        S.FORAGING: _skill(SU, Capacity.MOBILITY, INT, "Foraging"),
        S.SAILING: _skill(SU, Capacity.MOBILITY, ("agility", "strength"), "Sailing", physical=True),
        S.NAVIGATION: _skill(SU, Capacity.SCHOLARSHIP, INT, "Navigation"),
        S.MOUNTAINEERING: _skill(SU, Capacity.MOBILITY, ("strength", "agility"), "Mountaineering", physical=True),
        S.SWIMMING: _skill(SU, Capacity.MOBILITY, ("strength", "agility"), "Swimming", physical=True),
        S.RITUAL: _skill(FA, Capacity.PRESENCE, CHA, "Ritual"),
        S.PROPHECY: _skill(FA, Capacity.SCHOLARSHIP, ("intellect", "charisma"), "Prophecy"),
        S.SPELLCRAFT: _skill(FA, Capacity.SCHOLARSHIP, INT, "Spellcraft"),
        S.SPIRIT_SPEAKING: _skill(FA, Capacity.PRESENCE, CHA, "Spirit-speaking"),
    }
)

COMBAT_SKILLS = tuple(kind for kind, spec in SKILLS.items() if spec.family is SkillFamily.COMBAT)
CRAFT_SKILLS = tuple(kind for kind, spec in SKILLS.items() if spec.family is SkillFamily.CRAFT)
MELEE_SKILLS = (S.BLADE, S.SPEAR, S.AXE, S.BLUNT, S.SHIELD, S.UNARMED, S.MOUNTED_COMBAT)
MISSILE_SKILLS = (S.BOW, S.SLING, S.THROWING, S.HUNTING)
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
            MortalRole.KNIGHT: {S.MOUNTED_COMBAT: 50, S.RIDING: 50, S.BLADE: 40, S.SHIELD: 35, S.ETIQUETTE: 25},
            MortalRole.HUNTER: {S.BOW: 50, S.HUNTING: 50, S.TRACKING: 45, S.FORAGING: 30, S.THROWING: 25},
            MortalRole.CHOSEN: {S.RITUAL: 35, S.BLADE: 30, S.PROPHECY: 25, S.ORATORY: 25},
            MortalRole.SEER: {S.PROPHECY: 50, S.SPIRIT_SPEAKING: 40, S.RITUAL: 30, S.LORE: 25},
            MortalRole.PRIEST: {S.RITUAL: 50, S.THEOLOGY: 45, S.ORATORY: 35, S.WRITING: 20},
            MortalRole.SAGE: {S.LORE: 50, S.WRITING: 40, S.ASTRONOMY: 30, S.TEACHING: 35, S.LAW: 25},
            MortalRole.HEALER: {S.MEDICINE: 50, S.SURGERY: 35, S.FORAGING: 25, S.TEACHING: 15},
            MortalRole.ARTISAN: {S.SMITHING: 40, S.CARPENTRY: 35, S.MASONRY: 30, S.JEWELLING: 25, S.POTTERY: 25},
            MortalRole.MERCHANT: {S.NEGOTIATION: 50, S.ACCOUNTING: 45, S.LANGUAGES: 30, S.ETIQUETTE: 20, S.SAILING: 15},
            MortalRole.SCRIBE: {S.WRITING: 55, S.ACCOUNTING: 35, S.LAW: 30, S.LANGUAGES: 25},
            MortalRole.FARMER: {S.FORAGING: 40, S.BEAST_HANDLING: 30, S.CARPENTRY: 15, S.WEAVING: 15},
            MortalRole.EXPLORER: {S.NAVIGATION: 50, S.SAILING: 40, S.TRACKING: 40, S.MOUNTAINEERING: 35, S.LANGUAGES: 25},
            MortalRole.CAPTAIN: {S.TACTICS: 50, S.LEADERSHIP: 45, S.STRATEGY: 35, S.LOGISTICS: 30, S.SPEAR: 30},
            MortalRole.BANDIT: {S.BLADE: 35, S.INTIMIDATION: 40, S.TRACKING: 30, S.DECEPTION: 30, S.BOW: 25},
            MortalRole.SAINT: {S.RITUAL: 45, S.THEOLOGY: 40, S.ORATORY: 40, S.MEDICINE: 25},
            MortalRole.APPRENTICE: {S.TEACHING: 5, S.WRITING: 15, S.BLADE: 15},
            MortalRole.COMMONER: {S.FORAGING: 25, S.CARPENTRY: 15, S.WEAVING: 15, S.UNARMED: 10},
        }.items()
    }
)

CAREER_SKILLS: MappingProxyType[MortalRole, tuple[SkillKind, ...]] = MappingProxyType(
    {
        MortalRole.WARRIOR: (S.SPEAR, S.SHIELD, S.BLADE, S.AXE, S.BLUNT, S.UNARMED),
        MortalRole.KNIGHT: (S.MOUNTED_COMBAT, S.RIDING),
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
    }
)

FIXED_ROLES = frozenset({MortalRole.RULER, MortalRole.HERO, MortalRole.CHOSEN, MortalRole.SAINT, MortalRole.APPRENTICE})

CAREER_VALUES: MappingProxyType[MortalRole, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        role: MappingProxyType(values)
        for role, values in {
            MortalRole.WARRIOR: {V.MARTIAL: 30, V.HONOUR: 10},
            MortalRole.KNIGHT: {V.MARTIAL: 25, V.HONOUR: 20, V.HIERARCHY: 15},
            MortalRole.HUNTER: {V.NATURE: 25, V.MARTIAL: 10},
            MortalRole.SEER: {V.SUPERSTITION: 30, V.PIETY: 15},
            MortalRole.PRIEST: {V.PIETY: 35, V.TRADITION: 10},
            MortalRole.SAGE: {V.KNOWLEDGE: 35, V.TRADITION: 10},
            MortalRole.HEALER: {V.MERCY: 30, V.KNOWLEDGE: 10},
            MortalRole.ARTISAN: {V.KNOWLEDGE: 10, V.WEALTH: 15},
            MortalRole.MERCHANT: {V.WEALTH: 35, V.XENOPHILIA: 15},
            MortalRole.SCRIBE: {V.KNOWLEDGE: 25, V.HIERARCHY: 10},
            MortalRole.FARMER: {V.NATURE: 15, V.TRADITION: 15},
            MortalRole.EXPLORER: {V.XENOPHILIA: 30, V.TRADITION: -15},
            MortalRole.CAPTAIN: {V.MARTIAL: 25, V.HIERARCHY: 15},
            MortalRole.BANDIT: {V.HONOUR: -30, V.MERCY: -15},
            MortalRole.COMMONER: {},
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


MEMORIES: MappingProxyType[MemoryKind, MemorySpec] = MappingProxyType(
    {
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
        M.MARRIED_INTO: _memory({OC.AFFECTION: 45, OC.TRUST: 40, OC.RESPECT: 15}, 4, {V.KINSHIP: 40}, "Married into our blood"),
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
        M.GOODWILL: _memory({OC.AFFECTION: 45, OC.TRUST: 35, OC.RESPECT: 20}, 12, {V.XENOPHILIA: 15, V.KINSHIP: 10}, "Showed us goodwill"),
        M.LONG_HISTORY: _memory({OC.TRUST: 40, OC.AFFECTION: 30, OC.GRIEVANCE: 30}, 2, {}, "Long shared history", inherited=False),
        M.ILL_WILL: _memory({OC.GRIEVANCE: 50, OC.TRUST: 35, OC.FEAR: 15}, 12, {V.XENOPHILIA: -15, V.HONOUR: 10}, "Showed us ill will"),
    }
)

ACT_READINGS: MappingProxyType[ActKind, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        act: MappingProxyType(values)
        for act, values in {
            A.EXECUTION: {V.MERCY: -45, V.HIERARCHY: 25, V.HONOUR: 10, V.MARTIAL: 15},
            A.MUTILATION: {V.MERCY: -50, V.PURITY: -30, V.HIERARCHY: 15},
            A.BETRAYAL: {V.HONOUR: -60, V.KINSHIP: -20},
            A.MERCY_TO_ENEMY: {V.MERCY: 50, V.MARTIAL: -25, V.HONOUR: 15},
            A.HUMAN_SACRIFICE: {V.MERCY: -45, V.PIETY: 30, V.SUPERSTITION: 25, V.DEATH: 20},
            A.TRADE_WITH_OUTSIDERS: {V.XENOPHILIA: 50, V.WEALTH: 35, V.TRADITION: -15},
            A.BUILDING_TEMPLES: {V.PIETY: 50, V.TRADITION: 20, V.WEALTH: -10},
            A.BURNING_BOOKS: {V.KNOWLEDGE: -60, V.TRADITION: 20, V.PURITY: 15},
            A.CONQUEST: {V.MARTIAL: 45, V.HIERARCHY: 20, V.MERCY: -20, V.XENOPHILIA: -15},
            A.RAIDING: {V.MARTIAL: 35, V.HONOUR: -15, V.MERCY: -25},
            A.DUELLING: {V.HONOUR: 40, V.MARTIAL: 30},
            A.RANSOM: {V.WEALTH: 30, V.MERCY: 20, V.HONOUR: 10},
            A.TAKING_CAPTIVES: {V.MARTIAL: 25, V.MERCY: -20, V.HIERARCHY: 15},
            A.OATHBREAKING: {V.HONOUR: -55, V.PIETY: -20},
            A.LEARNING: {V.KNOWLEDGE: 50, V.TRADITION: -15},
            A.HOSPITALITY: {V.XENOPHILIA: 35, V.KINSHIP: 20, V.MERCY: 15},
            A.WINTER_FIGHTING: {V.MARTIAL: 30, V.TRADITION: -35, V.MERCY: -15},
            A.GUEST_KILLING: {V.HONOUR: -60, V.XENOPHILIA: -30, V.KINSHIP: -20, V.PIETY: -20},
            A.RITUAL_SCARRING: {V.TRADITION: 45, V.PIETY: 25, V.MARTIAL: 15, V.PURITY: -20},
        }.items()
    }
)

NEED_LABELS = MappingProxyType(
    {
        N.SUSTENANCE: "Sustenance",
        N.SAFETY: "Safety",
        N.BELONGING: "Belonging",
        N.STATUS: "Status",
        N.PURPOSE: "Purpose",
        N.FAITH: "Faith",
        N.PLEASURE: "Pleasure",
    }
)

PRESSURE_LABELS = MappingProxyType(
    {
        P.HUNGER: "Hunger",
        P.INSECURITY: "Insecurity",
        P.OVERCROWDING: "Overcrowding",
        P.POVERTY: "Poverty",
        P.IMPIETY: "Impiety",
        P.HUMILIATION: "Humiliation",
        P.STAGNATION: "Stagnation",
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


PROFESSIONS: MappingProxyType[Profession, ProfessionSpec] = MappingProxyType(
    {
        Profession.SOLDIER: ProfessionSpec("Soldier", (S.SPEAR, S.SHIELD, S.BLADE, S.AXE, S.BOW), MortalRole.WARRIOR),
        Profession.RIDER: ProfessionSpec("Rider", (S.RIDING, S.MOUNTED_COMBAT, S.BEAST_HANDLING), MortalRole.KNIGHT),
        Profession.SMITH: ProfessionSpec("Smith", (S.SMITHING, S.JEWELLING, S.ENGINEERING), MortalRole.ARTISAN),
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
        Profession.COMMANDER: ProfessionSpec("Commander", (S.TACTICS, S.STRATEGY, S.LEADERSHIP, S.LOGISTICS), MortalRole.KNIGHT),
    }
)
BRANCH_SKILLS: MappingProxyType[KnowledgeBranch, SkillKind] = MappingProxyType(
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
    }
)
