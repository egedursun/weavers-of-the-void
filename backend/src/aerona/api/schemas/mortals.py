from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import KindFamily, Profession
from aerona.domain.enums.mortal import (
    Ability,
    CareerPath,
    DeathCause,
    EquipmentSlot,
    LifeStage,
    MarriageEnd,
    MarriageKind,
    MortalSex,
    StressBreak,
)
from aerona.domain.enums.society import SocialClass


class AbilityView(ApiModel):
    ability: Ability
    value: int
    held: bool


class MarriageView(ApiModel):
    id: int
    spouse: NodeRef | None
    kind: MarriageKind
    treaty: NodeRef | None
    start_epoch: int
    end_epoch: int | None
    cause_end: MarriageEnd | None
    forced: bool


class KinLink(ApiModel):
    bond_id: int
    kind: BondKind
    other: NodeRef
    outgoing: bool
    living: bool


class SlotView(ApiModel):
    slot: EquipmentSlot
    item: NodeRef | None
    held: bool


class MortalProfileView(ApiModel):
    mortal: NodeRef
    sex: MortalSex
    abilities: list[AbilityView]
    life_stage: LifeStage
    fertility: int
    health: int
    stress: int
    wealth: int
    renown: int
    honour: int
    infamy: int
    legitimacy: int | None
    education: int
    polity: NodeRef | None
    loyalty_liege: int
    loyalty_community: int
    loyalty_god: int
    career: CareerPath | None
    profession: Profession | None
    last_break: StressBreak | None
    last_break_epoch: int | None
    cause_of_death: DeathCause | None
    death_place: NodeRef | None
    social_class: SocialClass | None
    held: list[str]
    marriages: list[MarriageView]
    kin: list[KinLink]
    equipment: list[SlotView]
    stress_threshold: int


class VariantView(ApiModel):
    id: int
    family: KindFamily
    base: str
    name: str
    description: str | None
    strength_pct: int
    learning_pct: int
    held: list[str]


class TreePerson(ApiModel):
    id: int
    name: str
    living: bool
    sex: MortalSex | None
    parents: list[int]
    spouses: list[int]
    generation: int


class FamilyTreeView(ApiModel):
    root: int
    people: list[TreePerson]
