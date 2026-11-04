from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.demography import AgeBand, Sex
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.environment import RiverClass, SoilKind, TerrainKind
from aerona.domain.enums.happening import EventPhase, RiverShiftCause
from aerona.domain.enums.society import SocialClass


class SeasonRef(ApiModel):
    position: int
    name: str


class RegionRef(ApiModel):
    region_id: int
    region: str


class FootprintView(ApiModel):
    region_id: int
    region: str
    joined_epoch: int


class CasualtyView(ApiModel):
    community_id: int
    community: str
    age_band: AgeBand
    sex: Sex
    social_class: SocialClass
    phase: EventPhase
    count: int


class PhaseStepView(ApiModel):
    phase: EventPhase
    reached: bool
    current: bool
    since_epoch: int | None


class EventView(ApiModel):
    entity_id: int
    name: str
    kind: EngineKind | None
    severity: int | None
    world_id: int | None
    location_id: int | None
    location: str | None
    start_epoch: int
    start_year: int | None
    start_season: SeasonRef | None
    end_epoch: int | None
    end_year: int | None
    end_season: SeasonRef | None
    phase: EventPhase
    phase_epoch: int
    multi_season: bool
    ended: bool
    locked: list[str]
    incident_id: int | None
    incident_text: str | None
    siege_id: int | None
    footprint: list[FootprintView]
    casualties: list[CasualtyView]
    toll: int
    steps: list[PhaseStepView]
    seasons: list[SeasonRef]
    kinds: list[EngineKind]


class EventSummaryView(ApiModel):
    entity_id: int
    name: str
    kind: EngineKind | None
    phase: EventPhase
    ended: bool
    start_year: int | None
    end_year: int | None
    toll: int
    severity: int | None


class RiverShiftView(ApiModel):
    id: int
    from_region_id: int
    from_region: str
    to_region_id: int
    to_region: str
    epoch: int
    year: int | None
    river_class: RiverClass
    cause: RiverShiftCause


class LandShapeView(ApiModel):
    region_id: int
    region: str
    soil: SoilKind | None
    terrain: TerrainKind | None
    river_class: RiverClass | None
    rainfall: int | None
    grazed: int | None
    desertification: int
    desertified: bool
    desert_since_epoch: int | None
    river_course: RiverClass | None
    course_changed_epoch: int | None
    volcanic: bool
    volcanic_pressure: int
    eruption_chance: float
    last_eruption_epoch: int | None
    ash_since_epoch: int | None
    ash_weathering_epochs: int
    desertified_at: int
    locked: list[str]
    soil_locked: bool
    shifts: list[RiverShiftView]
    neighbours: list[RegionRef]


class HappeningsHereView(ApiModel):
    location_id: int
    world_id: int | None
    region_id: int | None
    events: list[EventSummaryView]
    kinds: list[EngineKind]
    seasons: list[SeasonRef]
