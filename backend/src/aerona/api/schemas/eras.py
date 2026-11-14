from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.eras import EraChannel, ProgrammeStage
from aerona.domain.enums.world import TechnologyEra


class EraEffectView(ApiModel):
    channel: EraChannel
    value: int


class EraTechniqueView(ApiModel):
    technique: Technique
    label: str
    effect: str
    era: TechnologyEra
    held: bool
    kept: bool
    programme: bool
    requires: list[Technique]
    effects: list[EraEffectView]


class TechProgrammeView(ApiModel):
    id: int
    polity: NodeRef
    technique: Technique
    label: str
    progress: int
    stage: ProgrammeStage
    visibility: int
    sabotaged: int
    started_epoch: int
    finished_epoch: int | None
    locked: list[str]


class ErasNodeView(ApiModel):
    node: NodeRef
    realm: NodeRef | None
    keeper: NodeRef | None
    era: TechnologyEra
    starting_era: TechnologyEra
    no_gunpowder: bool
    channels: list[EraEffectView]
    techniques: list[EraTechniqueView]
    programmes: list[TechProgrammeView]
