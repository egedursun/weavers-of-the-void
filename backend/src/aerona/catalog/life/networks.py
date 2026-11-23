from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.made import DataContent, IntrusionTarget
from aerona.domain.enums.networks import NetworkCarrier, NetworkRole, OutageCause

CARRIER_DAYS = {
    NetworkCarrier.RELAY: "relay_days",
    NetworkCarrier.WIRED: "wired_days",
    NetworkCarrier.BROADCAST: "broadcast_days",
    NetworkCarrier.MESH: "mesh_days",
    NetworkCarrier.MIND_LINK: "mind_link_days",
    NetworkCarrier.RITE_LINK: "rite_link_days",
    NetworkCarrier.GROWN_LINK: "grown_link_days",
    NetworkCarrier.DREAM_LINK: "dream_link_days",
}


CARRIER_ENERGY = total(
    NetworkCarrier,
    {
        NetworkCarrier.RELAY: EnergyKind.MUSCLE,
        NetworkCarrier.WIRED: EnergyKind.ELECTRIC,
        NetworkCarrier.BROADCAST: EnergyKind.ELECTRIC,
        NetworkCarrier.MESH: EnergyKind.ELECTRIC,
        NetworkCarrier.MIND_LINK: EnergyKind.MAGIC,
        NetworkCarrier.RITE_LINK: EnergyKind.MAGIC,
        NetworkCarrier.GROWN_LINK: EnergyKind.FEED,
        NetworkCarrier.DREAM_LINK: EnergyKind.BELIEF,
    },
)


ROLE_SHOCK: Mapping[NetworkRole, int] = total(
    NetworkRole,
    {NetworkRole.HUB: 200, NetworkRole.STATION: 100, NetworkRole.END: 60, NetworkRole.RELAY: 80, NetworkRole.ARCHIVE: 40, NetworkRole.GATEWAY: 150},
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
        NetworkCarrier.DREAM_LINK: OutageCause.RITE,
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
        OutageCause.ICE_STORM: 100,
        OutageCause.QUAKE: 150,
        OutageCause.SHUTDOWN: 50,
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
        IntrusionTarget.SEAL: 30,
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
        DataContent.LOCATION: 5,
    },
)
JOINING_ROLES = frozenset({NetworkRole.END, NetworkRole.STATION, NetworkRole.RELAY})
