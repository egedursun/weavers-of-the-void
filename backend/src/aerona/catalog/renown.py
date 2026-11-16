from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.relations import ContestKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, Currency, LoreKind, LorePrice, ReputationAxis

A = ActKind
X = ReputationAxis


@dataclass(frozen=True)
class ActRenown:
    approved: ReputationAxis | None
    condemned: ReputationAxis | None
    always: ReputationAxis | None = None


def renown(approved: ReputationAxis | None, condemned: ReputationAxis | None, always: ReputationAxis | None = None) -> ActRenown:
    return ActRenown(approved, condemned, always)


ACT_RENOWN: MappingProxyType[ActKind, ActRenown] = MappingProxyType(
    {
        A.EXECUTION: renown(X.HONOUR, X.CRUELTY),
        A.MUTILATION: renown(X.HONOUR, X.CRUELTY),
        A.BETRAYAL: renown(X.TRICKERY, X.TRICKERY, X.TRICKERY),
        A.MERCY_TO_ENEMY: renown(X.HONOUR, X.TRICKERY),
        A.HUMAN_SACRIFICE: renown(X.PIETY, X.CRUELTY),
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
    }
)

CONTEST_RENOWN: MappingProxyType[ContestKind, tuple[ReputationAxis, SkillKind | None]] = MappingProxyType(
    {
        ContestKind.RIDDLE_GAME: (X.WISDOM, None),
        ContestKind.FLYTING: (X.SKILL_RENOWN, SkillKind.ORATORY),
        ContestKind.DEBATE: (X.WISDOM, None),
        ContestKind.GAME_OF_SKILL: (X.SKILL_RENOWN, SkillKind.TACTICS),
        ContestKind.TRIAL_OF_WISDOM: (X.WISDOM, None),
        ContestKind.SONG_CONTEST: (X.SKILL_RENOWN, SkillKind.RITUAL),
        ContestKind.STORYTELLING: (X.SKILL_RENOWN, SkillKind.LORE),
    }
)

AXIS_LABELS: MappingProxyType[ReputationAxis, str] = MappingProxyType(
    {
        X.HEROISM: "Heroism",
        X.HONOUR: "Honour",
        X.CRUELTY: "Cruelty",
        X.PIETY: "Piety",
        X.GENEROSITY: "Generosity",
        X.WISDOM: "Wisdom",
        X.TRICKERY: "Trickery",
        X.SKILL_RENOWN: "Renown for a skill",
        X.TROUBLEMAKER: "Troublemaking",
    }
)
GLORIOUS = frozenset({X.HEROISM, X.HONOUR, X.PIETY, X.GENEROSITY, X.WISDOM, X.SKILL_RENOWN})
INFAMOUS = frozenset({X.CRUELTY, X.TRICKERY, X.TROUBLEMAKER})

CURRENCY_LABELS: MappingProxyType[Currency, str] = MappingProxyType(
    {Currency.PRESTIGE: "Prestige", Currency.PIETY: "Piety", Currency.DREAD: "Dread", Currency.TYRANNY: "Tyranny"}
)
CLAIM_LABELS: MappingProxyType[ClaimKind, str] = MappingProxyType({ClaimKind.TRUE: "True", ClaimKind.SHARED: "Shared", ClaimKind.FALSE: "False"})
STATUS_LABELS: MappingProxyType[ClaimStatus, str] = MappingProxyType(
    {ClaimStatus.STANDING: "Believed", ClaimStatus.VERIFIED: "Proven", ClaimStatus.EXPOSED: "Exposed"}
)
LORE_LABELS: MappingProxyType[LoreKind, str] = MappingProxyType(
    {
        LoreKind.TECHNIQUE: "A technique",
        LoreKind.SITE: "A hidden site",
        LoreKind.MAP: "Knowledge of a land",
        LoreKind.PROPHECY: "A prophecy",
        LoreKind.TRUE_NAME: "A true name",
        LoreKind.WEAKNESS: "A weakness",
        LoreKind.PATTERN: "A pattern of a made thing",
        LoreKind.SOURCE: "Where a source of power lies",
    }
)
PRICE_LABELS: MappingProxyType[LorePrice, str] = MappingProxyType({LorePrice.WEALTH: "Wealth", LorePrice.FAVOUR: "A favour", LorePrice.RENOWN: "Renown"})

FACTION_LORE: MappingProxyType[FactionKind, frozenset[LoreKind]] = MappingProxyType(
    {
        FactionKind.SCHOLARS_ACADEMY: frozenset({LoreKind.TECHNIQUE, LoreKind.PROPHECY}),
        FactionKind.CRAFT_GUILD: frozenset({LoreKind.TECHNIQUE}),
        FactionKind.MERCHANT_GUILD: frozenset({LoreKind.MAP, LoreKind.SITE}),
        FactionKind.WANDERING_MARKET: frozenset({LoreKind.MAP}),
        FactionKind.SECRET_SOCIETY: frozenset({LoreKind.SITE, LoreKind.PROPHECY, LoreKind.TRUE_NAME}),
        FactionKind.MAGE_ORDER: frozenset({LoreKind.SOURCE, LoreKind.TRUE_NAME}),
        FactionKind.ENGINEERS_SOCIETY: frozenset({LoreKind.PATTERN, LoreKind.TECHNIQUE}),
        FactionKind.CHARTERED_COMPANY: frozenset({LoreKind.PATTERN, LoreKind.MAP}),
        FactionKind.PRIESTHOOD: frozenset({LoreKind.PROPHECY}),
        FactionKind.BANDITS: frozenset({LoreKind.SITE, LoreKind.MAP}),
        FactionKind.PIRATES: frozenset({LoreKind.MAP}),
        FactionKind.REBELS: frozenset({LoreKind.MAP, LoreKind.SITE}),
        FactionKind.ASSASSINS: frozenset({LoreKind.SITE, LoreKind.WEAKNESS}),
        FactionKind.MERCENARY_COMPANY: frozenset({LoreKind.MAP}),
        FactionKind.WARRIOR_ORDER: frozenset({LoreKind.TECHNIQUE}),
    }
)
ENTITY_LORE: MappingProxyType[EntityType, frozenset[LoreKind]] = MappingProxyType(
    {
        EntityType.CULT: frozenset({LoreKind.PROPHECY, LoreKind.SITE}),
        EntityType.BEAST: frozenset({LoreKind.SITE}),
        EntityType.SETTLEMENT: frozenset({LoreKind.TECHNIQUE}),
        EntityType.PEOPLE: frozenset({LoreKind.TECHNIQUE, LoreKind.MAP}),
    }
)
