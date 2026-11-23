from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.concealment import ConcealScope, HiddenTruthKind, KeeperRole, SeekerAim, TruthAttitude
from aerona.domain.enums.made import IntrusionAim
from aerona.domain.enums.powers import GiftedAttitude

KIND_SPREAD: Mapping[HiddenTruthKind, int] = total(
    HiddenTruthKind,
    {
        HiddenTruthKind.EXISTENCE: 100,
        HiddenTruthKind.NATURE: 100,
        HiddenTruthKind.PRESENCE: 100,
        HiddenTruthKind.POWER: 110,
        HiddenTruthKind.EVENT: 90,
        HiddenTruthKind.ORIGIN: 80,
        HiddenTruthKind.AWAKENING: 120,
        HiddenTruthKind.PROGRAMME: 70,
        HiddenTruthKind.COSMIC: 60,
        HiddenTruthKind.LOCATION: 90,
        HiddenTruthKind.LINEAGE: 70,
    },
)


KIND_STRAIN: Mapping[HiddenTruthKind, int] = total(
    HiddenTruthKind,
    {
        HiddenTruthKind.EXISTENCE: 100,
        HiddenTruthKind.NATURE: 100,
        HiddenTruthKind.PRESENCE: 100,
        HiddenTruthKind.POWER: 100,
        HiddenTruthKind.EVENT: 100,
        HiddenTruthKind.ORIGIN: 120,
        HiddenTruthKind.AWAKENING: 130,
        HiddenTruthKind.PROGRAMME: 110,
        HiddenTruthKind.COSMIC: 200,
        HiddenTruthKind.LOCATION: 100,
        HiddenTruthKind.LINEAGE: 110,
    },
)


SCOPE_SPREAD: Mapping[ConcealScope, int] = total(
    ConcealScope,
    {
        ConcealScope.EVERYONE: 100,
        ConcealScope.A_PEOPLE: 100,
        ConcealScope.A_POLITY: 100,
        ConcealScope.THE_UNINITIATED: 90,
        ConcealScope.A_WORLD: 80,
        ConcealScope.THE_COSMOS: 50,
        ConcealScope.A_HOUSE: 40,
        ConcealScope.A_FAITH: 70,
    },
)


ROLE_WEIGHT: Mapping[KeeperRole, int] = total(
    KeeperRole,
    {KeeperRole.ENFORCER: 200, KeeperRole.GUARDIAN: 150, KeeperRole.MEMBER: 100, KeeperRole.PATRON: 50, KeeperRole.ARCHIVIST: 120, KeeperRole.GO_BETWEEN: 80},
)


PAYING_ORDER = (KeeperRole.PATRON, KeeperRole.GO_BETWEEN, KeeperRole.GUARDIAN, KeeperRole.ARCHIVIST, KeeperRole.MEMBER, KeeperRole.ENFORCER)


REVEALED_ATTITUDES = {
    TruthAttitude.FEARED: GiftedAttitude.FEARED,
    TruthAttitude.REVERED: GiftedAttitude.HONOURED,
    TruthAttitude.ACCEPTED: GiftedAttitude.ORDINARY,
    TruthAttitude.EXPLOITED: GiftedAttitude.REGULATED,
    TruthAttitude.PROTECTED: GiftedAttitude.REGULATED,
    TruthAttitude.BARGAINED: GiftedAttitude.ORDINARY,
}

LEAKED_INTRUSION_AIMS = (IntrusionAim.READ, IntrusionAim.SEIZE)
POPULATION_FOR_CONCEAL_SCOPES = frozenset({ConcealScope.A_PEOPLE, ConcealScope.A_POLITY, ConcealScope.A_WORLD, ConcealScope.A_HOUSE, ConcealScope.A_FAITH})
RELOCATING_TRUTHS = frozenset({HiddenTruthKind.LOCATION, HiddenTruthKind.PRESENCE})
JOINING_AIMS = frozenset({SeekerAim.JOIN_THE_HIDDEN, SeekerAim.PROTECT})
