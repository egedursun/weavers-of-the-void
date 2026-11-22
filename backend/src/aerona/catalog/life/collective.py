from collections.abc import Mapping
from types import MappingProxyType

from aerona.catalog.collective import ANGER, TRIGGERS
from aerona.core.total import total
from aerona.domain.enums.collective import AccountMedium, CollectiveActKind, RoleKind
from aerona.domain.enums.mind import Facet, ValueAxis
from aerona.domain.enums.mortal import CareerPath
from aerona.domain.enums.relations import InteractionKind
from aerona.domain.enums.vehicles import VehicleSection

MEDIUM_FADE: Mapping[AccountMedium, int] = total(
    AccountMedium,
    {
        AccountMedium.ORAL: 100,
        AccountMedium.BOOK: 0,
        AccountMedium.INSCRIPTION: 0,
        AccountMedium.ARTWORK: 0,
        AccountMedium.RECORD: 0,
        AccountMedium.PERFORMANCE: 50,
        AccountMedium.MIND_STATE: 10,
    },
)


CONFORMING = (Facet.COOPERATION, Facet.POLITENESS, Facet.SENSE_OF_DUTY)


TRIGGER_MOOD: dict[CollectiveActKind, str] = {spec.act: spec.mood for spec in TRIGGERS.values()} | {
    CollectiveActKind.LYNCHING: ANGER,
    CollectiveActKind.REVOLT: ANGER,
}


MOUNT_FALLBACKS = (
    VehicleSection.DECK,
    VehicleSection.PLATFORM,
    VehicleSection.TURRET,
    VehicleSection.HULL,
    VehicleSection.CHASSIS,
    VehicleSection.FRAME,
    VehicleSection.GONDOLA,
    VehicleSection.MOUNT_BODY,
    VehicleSection.CORE,
)


FEARFUL = (ValueAxis.SUPERSTITION, ValueAxis.DEATH, ValueAxis.PIETY)


CAREER_ROLES: MappingProxyType[CareerPath, RoleKind] = MappingProxyType(
    {
        CareerPath.ARMY: RoleKind.COMBAT,
        CareerPath.OFFICE: RoleKind.OFFICE,
        CareerPath.APPRENTICE: RoleKind.PROFESSION,
        CareerPath.TRADE: RoleKind.PROFESSION,
        CareerPath.VOWS: RoleKind.PRIESTHOOD,
        CareerPath.STUDY: RoleKind.PROFESSION,
    }
)

DEEPER_BEHAVIOUR_INTERACTION_KINDS = (InteractionKind.TEACH, InteractionKind.GOSSIP)
