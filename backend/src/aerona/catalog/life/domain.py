from types import MappingProxyType

from aerona.catalog.war_w52 import STANCES
from aerona.domain.enums.body import MedicineTier
from aerona.domain.enums.ecology import SpeciesClass
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.labour import ContractStatus
from aerona.domain.enums.mass_weapons import ProgrammeStage
from aerona.domain.enums.physics import CosmicFeatureKind
from aerona.domain.enums.structure import ConstructionState
from aerona.domain.enums.war import WarCause

CRIME_KINDS = frozenset(
    {
        FactionKind.CRIME_FAMILY,
        FactionKind.PIRATE_CONFEDERACY,
        FactionKind.SMUGGLING_RING,
        FactionKind.THIEVES_GUILD,
        FactionKind.STREET_GANG,
        FactionKind.TRAFFICKING_RING,
    }
)

GANG_KINDS = (FactionKind.STREET_GANG, FactionKind.TRAFFICKING_RING)

LICENSABLE_KINDS = frozenset({FactionKind.PIRATE_CONFEDERACY, FactionKind.SMUGGLING_RING, FactionKind.THIEVES_GUILD})

OUTLAW_KINDS = frozenset({FactionKind.REBELS, FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.ROUTE_RAIDERS, FactionKind.ASSASSINS, *CRIME_KINDS})

ROBBER_KINDS = frozenset({FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.PIRATE_CONFEDERACY, FactionKind.REBELS, FactionKind.ROUTE_RAIDERS})

LENDER_KINDS = frozenset({FactionKind.FINANCIERS, FactionKind.MERCHANT_GUILD})

GUILD_KINDS = frozenset({FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD, FactionKind.WANDERING_MARKET})

ARMED_KINDS = frozenset(
    {
        FactionKind.BANDITS,
        FactionKind.CRIME_FAMILY,
        FactionKind.MERCENARY_COMPANY,
        FactionKind.PIRATES,
        FactionKind.PIRATE_CONFEDERACY,
        FactionKind.REBELS,
        FactionKind.ROUTE_RAIDERS,
        FactionKind.WARRIOR_ORDER,
    }
)

SECRET_KINDS = frozenset({FactionKind.ASSASSINS, FactionKind.SECRET_SOCIETY, FactionKind.SMUGGLING_RING, FactionKind.THIEVES_GUILD})

ENGINE_OF_KIND = MappingProxyType(
    {
        FactionKind.MERCHANT_GUILD: EngineKind.MERCHANT_GUILD,
        FactionKind.PRIESTHOOD: EngineKind.PRIESTS_COUNCIL,
        FactionKind.WARRIOR_ORDER: EngineKind.WARRIOR_BAND,
        FactionKind.REBELS: EngineKind.REBELS,
        FactionKind.ROUTE_RAIDERS: EngineKind.ROUTE_RAIDERS,
        FactionKind.INTERWORLD_FEDERATION: EngineKind.INTERWORLD_FEDERATION,
        FactionKind.WANDERING_MARKET: EngineKind.WANDERING_MARKET,
    }
)

OPEN_CONTRACTS = frozenset({ContractStatus.AGREED, ContractStatus.BARGAINING, ContractStatus.PROPOSED})

ARMED_STAGES = frozenset({ProgrammeStage.READY, ProgrammeStage.TESTED})

RESTING = frozenset(stance for stance, spec in STANCES.items() if spec.resting)

PERIODIC_BODIES = frozenset({CosmicFeatureKind.PERIODIC_COMET, CosmicFeatureKind.WANDERING_STAR})

STANDING_STATES = frozenset({ConstructionState.COMPLETE, ConstructionState.DAMAGED})

UNFINISHED_STATES = frozenset({ConstructionState.BUILDING, ConstructionState.PLANNED})

GONE_STATES = frozenset({ConstructionState.RUINED, ConstructionState.ABANDONED, ConstructionState.DISMANTLED})

REVOLT_CAUSES = frozenset({WarCause.INDEPENDENCE, WarCause.LIBERATION, WarCause.TRIBUTE_REVOLT, WarCause.UPRISING})

GROWN = frozenset({SpeciesClass.FUNGUS, SpeciesClass.PLANT})

MEDICINE_ORDER = (
    MedicineTier.NONE,
    MedicineTier.HERBS,
    MedicineTier.SURGERY,
    MedicineTier.ANATOMY,
    MedicineTier.ANTISEPSIS,
    MedicineTier.ANAESTHESIA,
    MedicineTier.PROSTHETICS,
    MedicineTier.IMMUNISATION,
    MedicineTier.ANTIMICROBIALS,
    MedicineTier.REATTACHMENT,
    MedicineTier.TRANSPLANTATION,
    MedicineTier.MIND_MEDICINE,
    MedicineTier.REGENERATION,
    MedicineTier.GENOME_REPAIR,
    MedicineTier.CELLULAR_MACHINES,
)
