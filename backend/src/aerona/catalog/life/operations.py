from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.military import ArmyRole
from aerona.domain.enums.operations import ExpeditionEvent
from aerona.domain.enums.records import StepAction, StepState
from aerona.domain.enums.vehicles import VehicleSection

STAFF_ROLES = (ArmyRole.SUB_COMMANDER, ArmyRole.QUARTERMASTER)


EXPEDITION_STEPS: Mapping[ExpeditionEvent, StepAction] = MappingProxyType(
    {
        ExpeditionEvent.SETOUT: StepAction.DEPART,
        ExpeditionEvent.LEG: StepAction.TRAVEL,
        ExpeditionEvent.ROOM: StepAction.ENTER,
        ExpeditionEvent.CAMP: StepAction.REST,
        ExpeditionEvent.AMBUSH: StepAction.MEET_DANGER,
        ExpeditionEvent.EXPOSURE: StepAction.WORSEN,
        ExpeditionEvent.AFFLICTION: StepAction.WORSEN,
        ExpeditionEvent.VIRTUE: StepAction.RALLY,
        ExpeditionEvent.QUIRK: StepAction.LEARN,
        ExpeditionEvent.FALLEN: StepAction.DIE,
        ExpeditionEvent.RETURN: StepAction.RETURN,
        ExpeditionEvent.LOSS: StepAction.LOSE_WAY,
    }
)


EXPEDITION_STATES: Mapping[ExpeditionEvent, StepState] = MappingProxyType(
    {
        ExpeditionEvent.EXPOSURE: StepState.EXHAUSTED,
        ExpeditionEvent.AFFLICTION: StepState.EXHAUSTED,
        ExpeditionEvent.VIRTUE: StepState.RALLIED,
        ExpeditionEvent.FALLEN: StepState.UNCONSCIOUS,
    }
)

HOLED_SECTIONS = frozenset({VehicleSection.HULL, VehicleSection.KEEL, VehicleSection.BOW, VehicleSection.STERN, VehicleSection.HOLD})
