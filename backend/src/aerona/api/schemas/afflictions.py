from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.affliction import ChangeSign, CharmKind, CureKind, ForgetScope, PackageKind, SleepUntil, Transmission, Visibility
from aerona.domain.enums.body import BodyFunction, BodyPlan, ConditionKind
from aerona.domain.enums.material import MaterialKind
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
    changes_body: bool
    lucky: bool
    binds: bool
    fades: bool


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
    fortune_sign: int | None
    fortune_strength: int | None
    transform_plan: BodyPlan | None
    transform_species_id: int | None
    transform_substance: MaterialKind | None
    transform_trigger: ChangeSign | None
    transform_mind_kept: bool | None
    changed_from: BodyPlan | None
    charm_target_id: int | None
    charm_target_name: str | None
    charm_kind: CharmKind | None
    charm_strength: int | None
    ageing_rate_pct: int | None
    forget_scope: ForgetScope | None
    sleep_until: SleepUntil | None


class AfflictionsView(ApiModel):
    node_id: int
    name: str
    bearable: bool
    epoch: int
    afflictions: list[BearerAfflictionView]
