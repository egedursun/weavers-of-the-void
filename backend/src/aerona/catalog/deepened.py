from aerona.domain.enums.belonging import FugitiveKind
from aerona.domain.enums.communication import DispatchContent, SignalKind
from aerona.domain.enums.crafts import AssistiveAid
from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.customs import CoopPurpose
from aerona.domain.enums.faction import EstatePrivilege, FactionGoalKind
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.military import UnitFamily
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.structure import BuildingForm, StructureSection

NEW_QUARTERS = frozenset({DistrictKind.PILGRIM_QUARTER, DistrictKind.CARAVAN_QUARTER, DistrictKind.FLOATING})
DENSE = frozenset({SizeTier.CITY, SizeTier.METROPOLIS, SizeTier.MEGALOPOLIS, SizeTier.WORLD_CITY})
LIVING_GARDENS = frozenset({GardenKind.KITCHEN_GARDEN, GardenKind.ROOF_GARDEN})
SHAPED_FORMS = frozenset({BuildingForm.STILT, BuildingForm.VAULT})
HELD_SECTIONS = frozenset({StructureSection.CISTERN, StructureSection.CHIMNEY})
SENSE_AIDS = frozenset({AssistiveAid.HEARING_AID, AssistiveAid.TACTILE_SCRIPT})
HEAVY_CURSES = frozenset({CurseKind.ISOLATION, CurseKind.WEAKNESS})
SOCIAL_COOPS = frozenset({CoopPurpose.SCHOOL, CoopPurpose.HOUSING})
KIN_GOALS = frozenset({FactionGoalKind.PROTECT_MEMBERS, FactionGoalKind.FOUND_SETTLEMENT})
MARKED_PRIVILEGES = frozenset({EstatePrivilege.SERVICE_EXEMPTION, EstatePrivilege.DRESS})
CLOSED_CASES = frozenset({CaseStage.CLOSED})
OPEN_CASES = frozenset(stage for stage in CaseStage if stage is not CaseStage.CLOSED)
PERSECUTED = frozenset({FugitiveKind.HERETIC, FugitiveKind.OUTLAW})
SEEN_FROM_FOREST = frozenset({SignalKind.BEACON_CHAIN})
REFUSABLE = frozenset({DispatchContent.PROPOSAL, DispatchContent.DEMAND, DispatchContent.PLEA})
RIDERS = frozenset({UnitFamily.MOUNTED, UnitFamily.BEAST})
RINGED = frozenset({UnitFamily.INFANTRY, UnitFamily.MISSILE, UnitFamily.VEHICLE})
