from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.culture import TraditionKind


class HolyDayDetail(ApiModel):
    index: int
    name: str
    year: int | None
    season_position: int | None
    notable_year_id: int | None
    tradition_id: int | None
    tradition_name: str | None


class CalendarDetail(ApiModel):
    knowledge_id: int
    name: str
    anchor_year: int
    keepers: int
    holy_days: list[HolyDayDetail]


class SeasonTradition(ApiModel):
    id: int
    name: str
    kind: TraditionKind
    season_position: int | None
    calendar_id: int | None
    calendar_name: str | None
    in_season: bool | None
    held: list[str]


class WorldCalendarView(ApiModel):
    world_id: int
    calendar_locked: list[str]
    day_length_hours: int | None
    long_days: bool
    long_day_hours: int
    sleep_customs: int
    calendars: list[CalendarDetail]
    traditions: list[SeasonTradition]


class LeyWorkView(ApiModel):
    structure_id: int
    name: str
    attuned: bool
    on_ley_line: bool
    at_nexus: bool
    function: int | None
    locked: list[str]


class SettlementWorks(ApiModel):
    settlement_id: int
    name: str
    bridges: int
    irrigation: int
    harbour: bool
    locked: list[str]


class RegionWorksView(ApiModel):
    region_id: int
    roads: int
    bridges: int
    harbours: int
    irrigation: int
    irrigation_pct: int
    rainfall: int
    rain_lost_to_clearing: int
    cleared: int
    settlements: list[SettlementWorks]
    ley_works: list[LeyWorkView]
