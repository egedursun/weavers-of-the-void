from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.knowledge import KNOWLEDGE
from aerona.core.total import total
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.mind import ActKind, SkillKind, ValueAxis
from aerona.domain.enums.relations import ContestKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, Currency, LorePrice, ReputationAxis

A = ActKind
X = ReputationAxis


@dataclass(frozen=True)
class ActRenown:
    approved: ReputationAxis | None
    condemned: ReputationAxis | None
    always: ReputationAxis | None = None


def renown(approved: ReputationAxis | None, condemned: ReputationAxis | None, always: ReputationAxis | None = None) -> ActRenown:
    return ActRenown(approved, condemned, always)


ACT_RENOWN: Mapping[ActKind, ActRenown] = total(
    ActKind,
    {
        A.EXECUTION: renown(X.JUSTICE, X.CRUELTY),
        A.MUTILATION: renown(X.HONOUR, X.CRUELTY),
        A.BETRAYAL: renown(X.TRICKERY, X.TRICKERY, X.TRICKERY),
        A.MERCY_TO_ENEMY: renown(X.MERCY, X.TRICKERY),
        A.SACRIFICE_OF_PEOPLE: renown(X.PIETY, X.CRUELTY),
        A.TRADE_WITH_OUTSIDERS: renown(X.GENEROSITY, X.TROUBLEMAKER),
        A.BUILDING_TEMPLES: renown(X.PIETY, None, X.PIETY),
        A.BURNING_BOOKS: renown(X.PIETY, X.CRUELTY),
        A.CONQUEST: renown(X.HEROISM, X.CRUELTY),
        A.RAIDING: renown(X.HEROISM, X.CRUELTY),
        A.DUELLING: renown(X.HEROISM, X.TROUBLEMAKER),
        A.RANSOM: renown(X.HONOUR, X.TRICKERY),
        A.TAKING_CAPTIVES: renown(X.HEROISM, X.CRUELTY),
        A.OATHBREAKING: renown(X.TRICKERY, X.TRICKERY, X.TRICKERY),
        A.LEARNING: renown(X.WISDOM, None, X.WISDOM),
        A.HOSPITALITY: renown(X.GENEROSITY, None, X.GENEROSITY),
        A.WINTER_FIGHTING: renown(X.HEROISM, X.TROUBLEMAKER),
        A.GUEST_KILLING: renown(X.TRICKERY, X.CRUELTY),
        A.RITUAL_SCARRING: renown(X.PIETY, X.CRUELTY),
        A.KILLING_KIN: renown(X.HONOUR, X.CRUELTY),
        A.KILLING_OUTSIDER: renown(X.HEROISM, X.CRUELTY),
        A.KILLING_IN_WAR: renown(X.HEROISM, X.CRUELTY),
        A.KILLING_CAPTIVE: renown(X.HONOUR, X.CRUELTY),
        A.REGICIDE: renown(X.HEROISM, X.CRUELTY),
        A.DUEL_TO_DEATH: renown(X.HEROISM, X.CRUELTY),
        A.REVENGE_KILLING: renown(X.HONOUR, X.CRUELTY),
        A.THEFT: renown(X.TRICKERY, X.TROUBLEMAKER),
        A.TREASON: renown(X.TRICKERY, X.TRICKERY, X.TROUBLEMAKER),
        A.COWARDICE: renown(X.WISDOM, X.TROUBLEMAKER),
        A.DESECRATION: renown(X.HEROISM, X.CRUELTY),
        A.BRIBERY: renown(X.TRICKERY, X.TROUBLEMAKER),
        A.SUICIDE: renown(X.HONOUR, None),
        A.TORTURE: renown(X.HONOUR, X.CRUELTY),
        A.EATING_SAPIENTS: renown(X.PIETY, X.CRUELTY),
        A.ICONOCLASM: renown(X.PIETY, X.CRUELTY),
        A.CONVERSION_BY_FORCE: renown(X.PIETY, X.CRUELTY),
        A.POLYGAMY: renown(X.GENEROSITY, X.TROUBLEMAKER),
        A.INCEST: renown(X.PIETY, X.TROUBLEMAKER),
        A.MAGIC_USE: renown(X.WISDOM, X.TROUBLEMAKER),
        A.BLOOD_MAGIC: renown(X.WISDOM, X.CRUELTY),
        A.VOID_MAGIC: renown(X.WISDOM, X.TROUBLEMAKER),
        A.NECROMANCY: renown(X.WISDOM, X.CRUELTY),
        A.HOARDING_IN_FAMINE: renown(X.WISDOM, X.CRUELTY),
        A.SLAVERY: renown(X.HONOUR, X.CRUELTY),
        A.ADULTERY: renown(X.TRICKERY, X.TROUBLEMAKER),
        A.USURY: renown(X.WISDOM, X.CRUELTY),
        A.INFANTICIDE: renown(X.HONOUR, X.CRUELTY),
        A.ABANDONING_ELDERS: renown(X.WISDOM, X.CRUELTY),
        A.FORCED_LABOUR: renown(X.HONOUR, X.CRUELTY),
        A.SELLING_OFFICES: renown(X.WISDOM, X.TROUBLEMAKER),
        A.POACHING: renown(X.TRICKERY, X.TROUBLEMAKER),
        A.ENCLOSING: renown(X.WISDOM, X.CRUELTY),
        A.LYING: renown(X.TRICKERY, X.TRICKERY, X.TRICKERY),
        A.DRUNKENNESS: renown(X.GENEROSITY, X.TROUBLEMAKER),
        A.TOMB_ROBBING: renown(X.TRICKERY, X.CRUELTY),
        A.USING_CHARMS: renown(X.WISDOM, X.TROUBLEMAKER),
        A.FEEDING_ON_HOSTS: renown(None, X.CRUELTY),
        A.KILLING_SACRED_ANIMAL: renown(X.HEROISM, X.CRUELTY),
        A.FIXING_CONTESTS: renown(X.TRICKERY, X.TRICKERY, X.TRICKERY),
    },
)

CONTEST_RENOWN: Mapping[ContestKind, tuple[ReputationAxis, SkillKind | None]] = total(
    ContestKind,
    {
        ContestKind.RIDDLE_GAME: (X.WISDOM, None),
        ContestKind.INSULT_CONTEST: (X.SKILL_RENOWN, SkillKind.ORATORY),
        ContestKind.DEBATE: (X.WISDOM, None),
        ContestKind.GAME_OF_SKILL: (X.SKILL_RENOWN, SkillKind.TACTICS),
        ContestKind.TRIAL_OF_WISDOM: (X.WISDOM, None),
        ContestKind.SONG_CONTEST: (X.SKILL_RENOWN, SkillKind.RITUAL),
        ContestKind.STORYTELLING: (X.SKILL_RENOWN, SkillKind.LORE),
        ContestKind.RACE: (X.SKILL_RENOWN, SkillKind.RIDING),
        ContestKind.CRAFT_CONTEST: (X.SKILL_RENOWN, SkillKind.SMITHING),
    },
)


@dataclass(frozen=True)
class AxisSpec:
    label: str
    glorious: bool
    value: ValueAxis | None = None


AXES: Mapping[ReputationAxis, AxisSpec] = total(
    ReputationAxis,
    {
        X.HEROISM: AxisSpec("Heroism", glorious=True, value=ValueAxis.MARTIAL),
        X.HONOUR: AxisSpec("Honour", glorious=True, value=ValueAxis.HONOUR),
        X.CRUELTY: AxisSpec("Cruelty", glorious=False, value=ValueAxis.MERCY),
        X.PIETY: AxisSpec("Piety", glorious=True, value=ValueAxis.PIETY),
        X.GENEROSITY: AxisSpec("Generosity", glorious=True, value=ValueAxis.FRIENDSHIP),
        X.WISDOM: AxisSpec("Wisdom", glorious=True, value=ValueAxis.KNOWLEDGE),
        X.TRICKERY: AxisSpec("Trickery", glorious=False, value=ValueAxis.TRUTH),
        X.SKILL_RENOWN: AxisSpec("Renown for a skill", glorious=True, value=ValueAxis.CRAFTSMANSHIP),
        X.TROUBLEMAKER: AxisSpec("Troublemaking", glorious=False, value=ValueAxis.LAW),
        X.MERCY: AxisSpec("Mercy", glorious=True, value=ValueAxis.MERCY),
        X.JUSTICE: AxisSpec("Justice", glorious=True, value=ValueAxis.LAW),
    },
)
AXIS_LABELS: Mapping[ReputationAxis, str] = {axis: spec.label for axis, spec in AXES.items()}
GLORIOUS = frozenset(axis for axis, spec in AXES.items() if spec.glorious)
INFAMOUS = frozenset(axis for axis, spec in AXES.items() if not spec.glorious)

CURRENCY_LABELS: MappingProxyType[Currency, str] = MappingProxyType(
    {Currency.PRESTIGE: "Prestige", Currency.PIETY: "Piety", Currency.DREAD: "Dread", Currency.TYRANNY: "Tyranny"}
)
CLAIM_LABELS: MappingProxyType[ClaimKind, str] = MappingProxyType({ClaimKind.TRUE: "True", ClaimKind.SHARED: "Shared", ClaimKind.FALSE: "False"})
STATUS_LABELS: MappingProxyType[ClaimStatus, str] = MappingProxyType(
    {ClaimStatus.STANDING: "Believed", ClaimStatus.VERIFIED: "Proven", ClaimStatus.EXPOSED: "Exposed"}
)
LORE_LABELS: Mapping[KnowledgeKind, str] = {kind: spec.label for kind, spec in KNOWLEDGE.items()}
PRICE_LABELS: MappingProxyType[LorePrice, str] = MappingProxyType({LorePrice.WEALTH: "Wealth", LorePrice.FAVOUR: "A favour", LorePrice.RENOWN: "Renown"})

FACTION_LORE: MappingProxyType[FactionKind, frozenset[KnowledgeKind]] = MappingProxyType(
    {
        FactionKind.SCHOLARS_ACADEMY: frozenset({KnowledgeKind.TECHNIQUE, KnowledgeKind.PROPHECY}),
        FactionKind.CRAFT_GUILD: frozenset({KnowledgeKind.TECHNIQUE}),
        FactionKind.MERCHANT_GUILD: frozenset({KnowledgeKind.MAP, KnowledgeKind.SITE}),
        FactionKind.WANDERING_MARKET: frozenset({KnowledgeKind.MAP}),
        FactionKind.SECRET_SOCIETY: frozenset({KnowledgeKind.SITE, KnowledgeKind.PROPHECY, KnowledgeKind.TRUE_NAME}),
        FactionKind.MAGE_ORDER: frozenset({KnowledgeKind.SOURCE, KnowledgeKind.TRUE_NAME}),
        FactionKind.ENGINEERS_SOCIETY: frozenset({KnowledgeKind.PATTERN, KnowledgeKind.TECHNIQUE}),
        FactionKind.CHARTERED_COMPANY: frozenset({KnowledgeKind.PATTERN, KnowledgeKind.MAP}),
        FactionKind.PRIESTHOOD: frozenset({KnowledgeKind.PROPHECY}),
        FactionKind.BANDITS: frozenset({KnowledgeKind.SITE, KnowledgeKind.MAP}),
        FactionKind.PIRATES: frozenset({KnowledgeKind.MAP}),
        FactionKind.REBELS: frozenset({KnowledgeKind.MAP, KnowledgeKind.SITE}),
        FactionKind.ASSASSINS: frozenset({KnowledgeKind.SITE, KnowledgeKind.WEAKNESS}),
        FactionKind.MERCENARY_COMPANY: frozenset({KnowledgeKind.MAP}),
        FactionKind.WARRIOR_ORDER: frozenset({KnowledgeKind.TECHNIQUE}),
    }
)
ENTITY_LORE: MappingProxyType[EntityType, frozenset[KnowledgeKind]] = MappingProxyType(
    {
        EntityType.CULT: frozenset({KnowledgeKind.PROPHECY, KnowledgeKind.SITE}),
        EntityType.BEAST: frozenset({KnowledgeKind.SITE}),
        EntityType.SETTLEMENT: frozenset({KnowledgeKind.TECHNIQUE}),
        EntityType.PEOPLE: frozenset({KnowledgeKind.TECHNIQUE, KnowledgeKind.MAP}),
    }
)
