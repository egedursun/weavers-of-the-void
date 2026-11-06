from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission, Visibility
from aerona.domain.enums.body import BodyFunction, ConditionKind
from aerona.domain.enums.mind import NeedKind, ValueAxis


class StageView(ApiModel):
    number: int
    label: str
    epochs: int | None
    condition: ConditionKind | None
    severity: int
    stats: dict[str, int]
    values: dict[ValueAxis, int]
    needs: list[NeedKind]
    quenches: list[NeedKind]
    grants: list[BodyFunction]
    sanity_loss: int
    ageless: bool
    sunlight_harm: bool
    transforms: bool
    recruits: bool
    fears_source: bool


class PackageView(ApiModel):
    kind: PackageKind
    label: str
    description: str
    transmissions: list[Transmission]
    onset: int
    stages: list[StageView]
    cures: list[CureKind]
    visibility: Visibility
    contagion: list[Transmission]
    cure_level: int
    hereditary: bool


class BearerAfflictionView(ApiModel):
    id: int
    package: PackageKind
    label: str
    stage: int
    stage_label: str | None
    stage_count: int
    since_epoch: int
    stage_since_epoch: int
    next_stage_epoch: int | None
    transmission: Transmission
    source_node_id: int | None
    source_name: str | None
    source_link: str | None
    visibility: Visibility
    cured_epoch: int | None
    applied: dict[str, int]
    held: bool


class AfflictionsView(ApiModel):
    node_id: int
    name: str
    bearable: bool
    epoch: int
    afflictions: list[BearerAfflictionView]
