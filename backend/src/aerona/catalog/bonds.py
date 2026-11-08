from dataclasses import dataclass

from aerona.domain.enums.bond import ROLE_BOND_KINDS, SYMMETRIC_BOND_KINDS, BondCategory, BondKind, LinkGroup, PseudoLinkKind
from aerona.domain.enums.entity import AGENT_TYPES, COMPANION_TYPES, EntityType

MECHANICAL = BondCategory.MECHANICAL
EVENT = BondCategory.EVENT
NARRATIVE = BondCategory.NARRATIVE


@dataclass(frozen=True)
class BondKindSpec:
    kind: BondKind
    label: str
    category: BondCategory
    subject_types: frozenset[EntityType] | None = None
    object_types: frozenset[EntityType] | None = None
    fate_suggestable: bool = False
    weavable: bool = False

    @property
    def deduplicated(self) -> bool:
        return self.category is not BondCategory.EVENT


@dataclass(frozen=True)
class DirectionRule:
    subject_types: frozenset[EntityType]
    object_types: frozenset[EntityType]


T = EntityType
DWELLING_TARGETS = frozenset({T.REGION, T.PLACE, T.SETTLEMENT, T.PEOPLE, T.FACTION, T.CULT})
RULED_TARGETS = frozenset({T.REGION, T.PLACE, T.SETTLEMENT, T.PEOPLE, T.FACTION, T.CULT, T.LAW, T.ARMY})
WORSHIPPER_TYPES = AGENT_TYPES | {T.SPIRIT}
KIN_TYPES = frozenset({T.MORTAL})

BOND_KINDS: dict[BondKind, BondKindSpec] = {
    spec.kind: spec
    for spec in (
        BondKindSpec(BondKind.INSIDE, "inside", MECHANICAL),
        BondKindSpec(BondKind.LIVES_IN, "lives in", MECHANICAL, AGENT_TYPES, DWELLING_TARGETS),
        BondKindSpec(BondKind.WORSHIPS, "worships", MECHANICAL, WORSHIPPER_TYPES),
        BondKindSpec(BondKind.ENEMY, "enemy of", MECHANICAL),
        BondKindSpec(BondKind.ALLY, "ally of", MECHANICAL),
        BondKindSpec(BondKind.DESCENDS_FROM, "descends from", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.PROTECTS, "protects", MECHANICAL),
        BondKindSpec(BondKind.RULES, "rules", MECHANICAL, AGENT_TYPES, RULED_TARGETS),
        BondKindSpec(BondKind.OWNS, "owner of", MECHANICAL, AGENT_TYPES),
        BondKindSpec(BondKind.BEAT, "beat", EVENT),
        BondKindSpec(BondKind.KILLED, "killed", EVENT),
        BondKindSpec(BondKind.CURSED, "cursed", EVENT),
        BondKindSpec(BondKind.BLESSED, "blessed", EVENT),
        BondKindSpec(BondKind.SOURCE_OF, "source of", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.TELLS_OF, "tells of", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.DESTROYED, "destroyed", EVENT),
        BondKindSpec(BondKind.LOVES, "loves", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.FEARS, "fears", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.HUNTS, "hunts", MECHANICAL),
        BondKindSpec(BondKind.TRADES_WITH, "trades with", MECHANICAL, AGENT_TYPES, AGENT_TYPES),
        BondKindSpec(BondKind.PROPHESIES, "prophesies", EVENT, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.CAUSED, "caused", EVENT, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.CELEBRATES, "celebrates", NARRATIVE, AGENT_TYPES, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.FORBIDS, "forbids", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.SPEAKS, "speaks", MECHANICAL, AGENT_TYPES),
        BondKindSpec(BondKind.PRODUCED, "produced", MECHANICAL),
        BondKindSpec(BondKind.BUILT, "built", MECHANICAL),
        BondKindSpec(BondKind.MIGRATED_TO, "migrated to", EVENT),
        BondKindSpec(BondKind.DISCOVERED, "discovered", EVENT),
        BondKindSpec(BondKind.SOUL_DESCENDED_TO, "soul descended to", MECHANICAL),
        BondKindSpec(BondKind.PARTY_TO, "party to", NARRATIVE, fate_suggestable=True),
        BondKindSpec(BondKind.MEMBER_OF, "member of", MECHANICAL),
        BondKindSpec(BondKind.KNOWS, "knows", MECHANICAL, AGENT_TYPES, frozenset({T.KNOWLEDGE})),
        BondKindSpec(BondKind.PAYS_TRIBUTE, "pays tribute to", MECHANICAL),
        BondKindSpec(BondKind.RELATED, "related to", NARRATIVE, weavable=True),
        BondKindSpec(BondKind.HOLDS_CAPTIVE, "holds captive", MECHANICAL),
        BondKindSpec(BondKind.SPY_NETWORK, "set a spy network in", MECHANICAL),
        BondKindSpec(BondKind.PURSUES, "in pursuit of", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.COMPANION, "companion of", NARRATIVE, COMPANION_TYPES, COMPANION_TYPES, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.RIVAL, "rival of", MECHANICAL),
        BondKindSpec(BondKind.APPRENTICE_OF, "apprentice of", MECHANICAL),
        BondKindSpec(BondKind.COMMANDS, "commands", MECHANICAL),
        BondKindSpec(BondKind.PART_OF, "part of", NARRATIVE, fate_suggestable=True, weavable=True),
        BondKindSpec(BondKind.PASSENGER_OF, "passenger of", MECHANICAL),
        BondKindSpec(BondKind.CAPTAIN_OF, "captain of", MECHANICAL),
        BondKindSpec(BondKind.TAMED, "tamed", MECHANICAL),
        BondKindSpec(BondKind.TRUCE, "made truce with", MECHANICAL),
        BondKindSpec(BondKind.OWES, "owes", MECHANICAL),
        BondKindSpec(BondKind.TREATED_BY, "treated by", MECHANICAL),
        BondKindSpec(BondKind.PARENT_OF, "parent of", MECHANICAL, KIN_TYPES, KIN_TYPES),
        BondKindSpec(BondKind.SPOUSE_OF, "spouse of", MECHANICAL, KIN_TYPES, KIN_TYPES),
        BondKindSpec(BondKind.BETROTHED_TO, "betrothed to", MECHANICAL, KIN_TYPES, KIN_TYPES),
        BondKindSpec(BondKind.CONCUBINE_OF, "concubine of", MECHANICAL, KIN_TYPES, KIN_TYPES),
        BondKindSpec(BondKind.FOSTERED_BY, "fostered by", MECHANICAL, KIN_TYPES, KIN_TYPES),
        BondKindSpec(BondKind.SWORN_KIN, "sworn kin of", MECHANICAL, KIN_TYPES, KIN_TYPES),
        BondKindSpec(BondKind.PET_OF, "pet of", MECHANICAL, frozenset({EntityType.BEAST}), frozenset({EntityType.MORTAL})),
        BondKindSpec(BondKind.TELLS, "tells", MECHANICAL),
        BondKindSpec(BondKind.FIXED_IN, "is fixed in", MECHANICAL),
        BondKindSpec(BondKind.ADHERENT_OF, "adheres to", MECHANICAL),
        BondKindSpec(BondKind.PRACTISES, "practises", MECHANICAL),
    )
}

DIRECTION_RULES: dict[BondKind, DirectionRule] = {
    BondKind.SPEAKS: DirectionRule(AGENT_TYPES, frozenset({T.LANGUAGE})),
    BondKind.OWNS: DirectionRule(AGENT_TYPES, frozenset({T.RESOURCE, T.ITEM, T.STRUCTURE, T.VESSEL})),
    BondKind.CELEBRATES: DirectionRule(AGENT_TYPES, frozenset({T.TRADITION})),
    BondKind.KNOWS: DirectionRule(AGENT_TYPES, frozenset({T.KNOWLEDGE})),
    BondKind.RULES: DirectionRule(frozenset({T.MORTAL, T.PEOPLE, T.FACTION, T.CULT, T.SETTLEMENT}), frozenset({T.REGION, T.PLACE})),
    BondKind.TAMED: DirectionRule(frozenset({T.PEOPLE, T.SETTLEMENT, T.FACTION, T.MORTAL, T.CULT}), frozenset({T.SPECIES})),
    BondKind.LIVES_IN: DirectionRule(frozenset({T.MORTAL, T.PEOPLE, T.FACTION, T.CULT, T.SPECIES, T.ARMY}), frozenset({T.REGION, T.PLACE, T.SETTLEMENT})),
    BondKind.PART_OF: DirectionRule(
        frozenset({T.LANGUAGE, T.SPIRIT, T.TRADITION, T.LAW, T.KNOWLEDGE, T.MORTAL, T.RESOURCE, T.STRUCTURE, T.ITEM, T.SPECIES}),
        frozenset({T.REGION, T.PLACE, T.SETTLEMENT, T.PEOPLE, T.FACTION, T.CULT}),
    ),
}

EVENT_BOND_KINDS = frozenset(kind for kind, spec in BOND_KINDS.items() if spec.category is BondCategory.EVENT)
NARRATIVE_BOND_KINDS = frozenset(kind for kind, spec in BOND_KINDS.items() if spec.category is BondCategory.NARRATIVE)
FATE_SUGGESTABLE_BOND_KINDS = frozenset(kind for kind, spec in BOND_KINDS.items() if spec.fate_suggestable)
WEAVABLE_BOND_KINDS = frozenset(kind for kind, spec in BOND_KINDS.items() if spec.weavable)
SINGULAR_NARRATIVE_KINDS = frozenset(NARRATIVE_BOND_KINDS - ROLE_BOND_KINDS - SYMMETRIC_BOND_KINDS)
UNORDERED_PAIR_KINDS = frozenset(SYMMETRIC_BOND_KINDS | SINGULAR_NARRATIVE_KINDS)


def bond_spec(kind: BondKind) -> BondKindSpec:
    return BOND_KINDS[kind]


def endpoints_valid(kind: BondKind, subject_type: EntityType, object_type: EntityType) -> bool:
    spec = BOND_KINDS[kind]
    subject_ok = spec.subject_types is None or subject_type in spec.subject_types
    object_ok = spec.object_types is None or object_type in spec.object_types
    return subject_ok and object_ok


def should_swap(kind: BondKind, subject_type: EntityType, object_type: EntityType) -> bool:
    rule = DIRECTION_RULES.get(kind)
    if rule is None:
        return False
    reversed_fit = subject_type in rule.object_types and object_type in rule.subject_types
    forward_fit = object_type in rule.object_types and subject_type in rule.subject_types
    return reversed_fit and not forward_fit


B = BondKind
P = PseudoLinkKind
LINK_GROUP_LABELS: dict[LinkGroup, str] = {
    LinkGroup.ALL: "All links",
    LinkGroup.TRAVEL: "Travel and trade network",
    LinkGroup.NO_LOCATION: "Excluding location links",
    LinkGroup.CONFLICT: "Conflict",
    LinkGroup.FAITH: "Faith and narrative",
    LinkGroup.LINEAGE: "Lineage, property and making",
    LinkGroup.KNOWLEDGE: "Knowledge, language and trade",
}
LINEAGE_KINDS = (
    B.DESCENDS_FROM,
    B.PARENT_OF,
    B.SPOUSE_OF,
    B.FOSTERED_BY,
    B.RULES,
    B.OWNS,
    B.PRODUCED,
    B.BUILT,
    B.MIGRATED_TO,
    B.MEMBER_OF,
    B.APPRENTICE_OF,
    B.COMMANDS,
    B.PART_OF,
)
LINK_GROUP_KINDS: dict[LinkGroup, frozenset[str]] = {
    LinkGroup.CONFLICT: frozenset(
        kind.value for kind in (B.ENEMY, B.KILLED, B.CURSED, B.HUNTS, B.DESTROYED, B.CAUSED, B.PARTY_TO, B.BEAT, B.RIVAL, B.PURSUES, B.HOLDS_CAPTIVE)
    ),
    LinkGroup.FAITH: frozenset(kind.value for kind in (B.WORSHIPS, B.BLESSED, B.CELEBRATES, B.TELLS_OF, B.SOUL_DESCENDED_TO, B.PROPHESIES)),
    LinkGroup.LINEAGE: frozenset(
        [
            *(
                kind.value
                for kind in (
                    B.DESCENDS_FROM,
                    B.PARENT_OF,
                    B.SPOUSE_OF,
                    B.BETROTHED_TO,
                    B.CONCUBINE_OF,
                    B.FOSTERED_BY,
                    B.SWORN_KIN,
                    B.PET_OF,
                    B.RULES,
                    B.OWNS,
                    B.PRODUCED,
                    B.BUILT,
                    B.MIGRATED_TO,
                    B.MEMBER_OF,
                    B.APPRENTICE_OF,
                    B.COMMANDS,
                    B.PART_OF,
                )
            ),
            P.CREATED.value,
        ]
    ),
    LinkGroup.KNOWLEDGE: frozenset(kind.value for kind in (B.KNOWS, B.SPEAKS, B.SOURCE_OF, B.TRADES_WITH, B.ALLY, B.TRUCE, B.OWES)),
    LinkGroup.TRAVEL: frozenset(
        [P.ROUTE.value, *(kind.value for kind in (B.TRADES_WITH, B.MIGRATED_TO, B.DISCOVERED, B.PAYS_TRIBUTE, B.PASSENGER_OF, B.CAPTAIN_OF))]
    ),
}
ALL_LINK_KINDS = frozenset([*(kind.value for kind in BondKind), *(kind.value for kind in PseudoLinkKind)])
LINK_GROUP_KINDS[LinkGroup.ALL] = ALL_LINK_KINDS
LINK_GROUP_KINDS[LinkGroup.NO_LOCATION] = ALL_LINK_KINDS - {BondKind.INSIDE.value}


def link_groups_of(kind: str) -> list[LinkGroup]:
    return [group for group in LinkGroup if kind in LINK_GROUP_KINDS[group]]


def ordered_link_groups() -> list[tuple[LinkGroup, frozenset[str]]]:
    return [(group, LINK_GROUP_KINDS[group]) for group in LinkGroup]
