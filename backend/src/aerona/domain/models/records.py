from pydantic import Field

from aerona.domain.enums.agent import CouncilCaller, CouncilVote
from aerona.domain.enums.chronicle import ChronicleAuditKind
from aerona.domain.enums.creator import CreatorMoodAxis
from aerona.domain.enums.divine import CouncilMotion
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import SoilKind, TemperatureBand, TerrainKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.meta import ScoreComponent
from aerona.domain.enums.region import DangerSource
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.travel import JourneyEventKind
from aerona.domain.models.base import ValueObject


class JourneyEvent(ValueObject):
    epoch: int = Field(ge=1)
    kind: JourneyEventKind
    text: str
    loss: int = Field(default=0, ge=0)


class CargoLine(ValueObject):
    commodity: CommodityKind
    material: MaterialKind | None = None
    amount: int = Field(ge=0)
    item_entity_id: int | None = None


class PassengerLine(ValueObject):
    community_entity_id: int | None = None
    social_class: SocialClass
    count: int = Field(ge=0)
    condition: int = Field(default=100, ge=0, le=100)
    sick: bool = False


class CouncilSpeech(ValueObject):
    son_id: int
    name: str
    words: str


class CouncilBallot(ValueObject):
    son_id: int
    name: str
    vote: CouncilVote
    reason: str = ""


class CouncilMinutes(ValueObject):
    topic: str
    convened_by: CouncilCaller
    speeches: tuple[CouncilSpeech, ...] = ()
    motion: str = ""
    ballots: tuple[CouncilBallot, ...] = ()
    passed: bool = False
    decision: CouncilMotion = CouncilMotion.NONE
    notes: tuple[str, ...] = ()
    summary: str = ""


class MoodContribution(ValueObject):
    axis: CreatorMoodAxis
    item: str
    delta: float


class ScoreBreakdown(ValueObject):
    parts: dict[ScoreComponent, int] = Field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.parts.values())


class RegionControl(ValueObject):
    ruler_id: int
    ruler_name: str
    ruler_type: EntityType
    share: float = Field(ge=0)
    contested: bool = False


class GroundSnapshot(ValueObject):
    terrain: TerrainKind
    soil: SoilKind
    climate: TemperatureBand
    land_use: str
    ley_lines: int = 0
    nexus: bool = False
    rainfall: int = 0
    danger: int = 0
    danger_source: DangerSource | None = None
    sacredness: int = 0
    scar: str | None = None
    scar_depth: int = 0


class MapSnapshotData(ValueObject):
    living_ids: tuple[int, ...] = ()
    population: dict[int, int] = Field(default_factory=dict)
    political: dict[int, RegionControl] = Field(default_factory=dict)
    ongoing_war_ids: tuple[int, ...] = ()
    ground: dict[int, GroundSnapshot] = Field(default_factory=dict)


class SonEpochStats(ValueObject):
    faith: int = 0
    fame: int = 0
    existence: int = 0
    level: int = 1


class LedgerItem(ValueObject):
    item: str
    delta: float


class EpochStatsData(ValueObject):
    population: int = 0
    followers: int = 0
    entities: int = 0
    words: int = 0
    knowledge: int = 0
    languages: int = 0
    wars: int = 0
    trade_routes: int = 0
    alliances: int = 0
    structures: int = 0
    items: int = 0
    dead: int = 0
    godless: int = 0
    doom: int = 0
    sons: dict[int, SonEpochStats] = Field(default_factory=dict)
    doom_items: tuple[LedgerItem, ...] = ()
    leak_items: dict[int, tuple[LedgerItem, ...]] = Field(default_factory=dict)
    population_items: tuple[LedgerItem, ...] = ()
    essence_items: tuple[LedgerItem, ...] = ()
    soldiers: int | None = None
    travelling: int | None = None
    flow_items: tuple[LedgerItem, ...] = ()


class ChronicleAuditFinding(ValueObject):
    kind: ChronicleAuditKind
    ref: str | None = None
    name: str | None = None
    world_id: int | None = None
    sentence: str | None = None
    detail: str | None = None
    stated: str | None = None
    actual: str | None = None


class ChronicleOutcomeClaim(ValueObject):
    ref: str
    winner_id: int


class ChronicleCreditClaim(ValueObject):
    entity_id: int
    actor_id: int


class ChronicleCountClaim(ValueObject):
    ref: str
    value: int


class ChronicleCoverage(ValueObject):
    covered: tuple[str, ...] = ()
    entity_ids: tuple[int, ...] = ()
    outcomes: tuple[ChronicleOutcomeClaim, ...] = ()
    credits: tuple[ChronicleCreditClaim, ...] = ()
    idle_actor_ids: tuple[int, ...] = ()
    counts: tuple[ChronicleCountClaim, ...] = ()


class ChronicleAuditReport(ValueObject):
    found: int = Field(default=0, ge=0)
    remaining: tuple[ChronicleAuditFinding, ...] = ()
    rewritten: bool = False
    repaired_sentences: int = Field(default=0, ge=0)
    coverage: ChronicleCoverage = Field(default_factory=ChronicleCoverage)
