from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.nature import Dormancy, FermentKind, PlantDefence, SenseKind, SymbiosisKind, Thermoregulation


class KindNatureView(ApiModel):
    dormancy: Dormancy
    thermoregulation: Thermoregulation
    woken_epoch: int | None
    endemic: bool
    relict: bool
    island_epochs: int
    range_peak: int
    asleep_now: bool
    activity_pct: int
    locked: list[str]


class FolkNatureView(ApiModel):
    thermoregulation: Thermoregulation
    activity_pct: int
    locked: list[str]


class PlantNatureView(ApiModel):
    defence: PlantDefence
    defence_potency: int
    locked: list[str]


class SenseView(ApiModel):
    sense: SenseKind
    acuity: int
    locked: list[str]


class KindBondView(ApiModel):
    id: int
    first: NodeRef
    second: NodeRef
    kind: SymbiosisKind
    strength: int
    since_epoch: int
    locked: list[str]


class SoilLifeView(ApiModel):
    life: int
    sterile_epochs: int
    updated_epoch: int
    recycling_pct: int
    locked: list[str]


class DefenceCoverView(ApiModel):
    defence: PlantDefence
    cover_pct: int


class FermentCultureView(ApiModel):
    id: int
    holder: NodeRef
    kind: FermentKind
    quality: int
    since_epoch: int
    lost_epoch: int | None
    locked: list[str]


class NatureNodeView(ApiModel):
    node: NodeRef
    region: NodeRef | None
    season_band: TemperatureBand | None
    kind_profile: KindNatureView | None
    folk_profile: FolkNatureView | None
    plant: PlantNatureView | None
    sense_holder: NodeRef | None
    senses: list[SenseView]
    bonds: list[KindBondView]
    soil: SoilLifeView | None
    defences: list[DefenceCoverView]
    cultures: list[FermentCultureView]
