from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.divine import DivineCost, DivineMode, DivineObject, DivineScope, DivineVerb
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.son import PowerEffect


class DivinePowerView(ApiModel):
    id: int
    name: str
    verb: DivineVerb
    object: DivineObject
    object_key: str | None
    scope: DivineScope
    mode: DivineMode
    cost: DivineCost
    cost_amount: int
    cooldown: int
    strength: int
    domains: list[Domain]
    son_preset: PowerEffect | None
    foreign_preset: ForeignGodPowerEffect | None
    last_used_epoch: int | None
    granted_epoch: int
    ready: bool
    locked: list[str]


class DivinePowersNodeView(ApiModel):
    node: NodeRef
    powers: list[DivinePowerView]
