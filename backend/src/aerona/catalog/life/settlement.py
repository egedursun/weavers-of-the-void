from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import DistrictHarm, DistrictKind

DISASTER_TARGETS: Mapping[DistrictHarm, frozenset[DistrictKind]] = MappingProxyType(
    {
        DistrictHarm.FLOOD: frozenset(
            {
                DistrictKind.FARMLAND,
                DistrictKind.HARBOUR,
                DistrictKind.SLUMS,
                DistrictKind.MARKET,
                DistrictKind.NECROPOLIS,
                DistrictKind.TRANSPORT_HUB,
                DistrictKind.SUBURB,
            }
        ),
        DistrictHarm.EARTHQUAKE: frozenset(DistrictKind),
        DistrictHarm.STORM: frozenset({DistrictKind.HARBOUR, DistrictKind.SLUMS, DistrictKind.FARMLAND, DistrictKind.FOREIGN_QUARTER}),
        DistrictHarm.DROUGHT: frozenset({DistrictKind.FARMLAND}),
        DistrictHarm.SACK: frozenset(
            {
                DistrictKind.BUSINESS,
                DistrictKind.INDUSTRIAL,
                DistrictKind.ENTERTAINMENT,
                DistrictKind.SUBURB,
                DistrictKind.MARKET,
                DistrictKind.PALACE,
                DistrictKind.TEMPLE_QUARTER,
                DistrictKind.CRAFT_QUARTER,
                DistrictKind.FOREIGN_QUARTER,
                DistrictKind.HARBOUR,
                DistrictKind.SLUMS,
            }
        ),
    }
)


OFFICE_TIER_RULES: Mapping[OfficeKind, str] = MappingProxyType(
    {
        OfficeKind.CHANCELLOR: "chancellor_tier",
        OfficeKind.MARSHAL: "marshal_tier",
        OfficeKind.TREASURER: "treasurer_tier",
        OfficeKind.HIGH_JUDGE: "high_judge_tier",
        OfficeKind.SPYMASTER: "spymaster_tier",
        OfficeKind.HERALD: "herald_tier",
        OfficeKind.CHAPLAIN: "chaplain_tier",
        OfficeKind.GOVERNOR: "governor_tier",
        OfficeKind.COURT_SCHOLAR: "court_scholar_tier",
        OfficeKind.JESTER: "jester_tier",
    }
)

STARTING_DISTRICTS_DISTRICT_KINDS = (DistrictKind.CRAFT_QUARTER, DistrictKind.TEMPLE_QUARTER)
TOWN_OF_DISTRICT_KINDS = frozenset({DistrictKind.FARMLAND, DistrictKind.MARKET})
BASE_PARAMETERS_DISTRICT_KINDS = (DistrictKind.FARMLAND, DistrictKind.MARKET)
BASE_PARAMETERS_DISTRICT_KINDS_2 = (DistrictKind.MARKET, DistrictKind.CRAFT_QUARTER)
