from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.made import DataContent, IntrusionTarget
from aerona.domain.enums.networks import NetworkAccess, NetworkCarrier, NetworkRole, OutageCause

ACCESS_REACH: Mapping[NetworkAccess, int] = total(
    NetworkAccess,
    {NetworkAccess.CLOSED: 50, NetworkAccess.MEMBERS: 100, NetworkAccess.LICENSED: 120, NetworkAccess.OPEN: 150},
)
ACCESS_GUARD: Mapping[NetworkAccess, int] = total(
    NetworkAccess,
    {NetworkAccess.CLOSED: 25, NetworkAccess.MEMBERS: 10, NetworkAccess.LICENSED: 5, NetworkAccess.OPEN: 0},
)
ROLE_SHOCK: Mapping[NetworkRole, int] = total(
    NetworkRole,
    {NetworkRole.HUB: 200, NetworkRole.STATION: 100, NetworkRole.END: 60, NetworkRole.RELAY: 80, NetworkRole.ARCHIVE: 40},
)
CARRIER_FAILURE: Mapping[NetworkCarrier, OutageCause] = total(
    NetworkCarrier,
    {
        NetworkCarrier.RELAY: OutageCause.STORM,
        NetworkCarrier.WIRED: OutageCause.POWER,
        NetworkCarrier.BROADCAST: OutageCause.FLARE,
        NetworkCarrier.MESH: OutageCause.POWER,
        NetworkCarrier.MIND_LINK: OutageCause.RITE,
        NetworkCarrier.RITE_LINK: OutageCause.RITE,
        NetworkCarrier.GROWN_LINK: OutageCause.DECAY,
    },
)
CAUSE_EPOCHS: Mapping[OutageCause, int] = total(
    OutageCause,
    {
        OutageCause.STORM: 100,
        OutageCause.FLARE: 150,
        OutageCause.WAR: 200,
        OutageCause.SABOTAGE: 150,
        OutageCause.INTRUSION: 100,
        OutageCause.DECAY: 200,
        OutageCause.RITE: 100,
        OutageCause.POWER: 100,
        OutageCause.SHORTAGE: 150,
        OutageCause.DIVINE: 300,
    },
)
TARGET_GUARD: Mapping[IntrusionTarget, int] = total(
    IntrusionTarget,
    {
        IntrusionTarget.NETWORK: 0,
        IntrusionTarget.DATA_STORE: 0,
        IntrusionTarget.MADE_MIND: 10,
        IntrusionTarget.AUGMENT: 5,
        IntrusionTarget.CONSTRUCT: 10,
        IntrusionTarget.VEHICLE: 15,
        IntrusionTarget.STRUCTURE: 20,
        IntrusionTarget.LEDGER: 25,
        IntrusionTarget.SAVED_STATE: 15,
    },
)
CONTENT_WORTH: Mapping[DataContent, int] = total(
    DataContent,
    {
        DataContent.SECRET: 0,
        DataContent.MIND_STATE: 0,
        DataContent.KNOWLEDGE: 0,
        DataContent.ACCOUNT: 5,
        DataContent.LEDGER: 10,
        DataContent.IDENTITY: 0,
        DataContent.ORDERS: 0,
    },
)
TAKEN_CONTENT = frozenset(DataContent)
