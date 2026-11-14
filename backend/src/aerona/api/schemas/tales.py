from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.ages import (
    AgeCycle,
    ArcOutcome,
    ArcRole,
    ArcStage,
    ArcTemplate,
    FormationZone,
    GiantMigration,
    PayoffKind,
    SeasonCause,
    SeasonSpell,
    SetupKind,
)
from aerona.domain.enums.cosmography import ApocalypseVariant


class FormationView(ApiModel):
    world: NodeRef
    zone: FormationZone
    migration: GiantMigration
    bombardment: int
    craters: int
    core_share: int
    mantle_heat: int
    water_delivered: int
    exotic_delivered: int
    shaped: bool
    formed_epoch: int
    locked: list[str]


class LongSeasonView(ApiModel):
    world: NodeRef
    cause: SeasonCause
    spell: SeasonSpell
    spell_started_epoch: int
    spell_length: int
    severity: int
    by_node: NodeRef | None
    locked: list[str]


class ForecastView(ApiModel):
    id: int
    world: NodeRef
    people: NodeRef
    scholar: NodeRef | None
    predicted_end_epoch: int
    heeded: bool
    made_epoch: int
    locked: list[str]


class TransformationView(ApiModel):
    plan_id: int
    plan_name: str
    holder: NodeRef | None
    target: NodeRef | None
    progress: int
    steps: int
    target_moisture: int
    target_forest: int
    target_fertility: int
    regions_changed: int
    resistance: int
    sabotage: int
    last_epoch: int
    locked: list[str]


class AgeView(ApiModel):
    id: int
    number: int
    began_epoch: int
    ended_epoch: int | None
    variant: ApocalypseVariant | None
    carried: int
    locked: list[str]


class EchoView(ApiModel):
    id: int
    age_id: int
    template: ArcTemplate
    role: ArcRole | None
    source: NodeRef | None
    echo: NodeRef | None
    weight: int
    locked: list[str]


class ArcFigureView(ApiModel):
    node: NodeRef
    role: ArcRole
    locked: list[str]


class ArcBeatView(ApiModel):
    id: int
    stage: ArcStage
    text: str
    epoch: int
    locked: list[str]


class ArcView(ApiModel):
    id: int
    subject: NodeRef
    template: ArcTemplate
    stage: ArcStage
    outcome: ArcOutcome
    beats: int
    drama: int
    echo_id: int | None
    started_epoch: int
    last_beat_epoch: int
    ended_epoch: int | None
    figures: list[ArcFigureView]
    history: list[ArcBeatView]
    locked: list[str]


class SetupView(ApiModel):
    id: int
    kind: SetupKind
    source_id: int
    subject: NodeRef | None
    payoff: PayoffKind
    opened_epoch: int
    paid_epoch: int | None
    payoff_text: str
    locked: list[str]


class TalesNodeView(ApiModel):
    node: NodeRef
    formation: FormationView | None
    season: LongSeasonView | None
    forecasts: list[ForecastView]
    transformations: list[TransformationView]
    cycle: AgeCycle
    ages: list[AgeView]
    echoes: list[EchoView]
    arcs: list[ArcView]
    setups: list[SetupView]
