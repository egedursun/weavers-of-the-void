from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.ecology import Temperament
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.living import (
    CultivationMethod,
    Fertility,
    GrowthStage,
    HostPlacement,
    HostRelation,
    LineOutcome,
    LineTrait,
    LivingCraftStance,
    Metabolism,
)


class LivingProfileView(ApiModel):
    line_id: int | None
    line_name: str | None
    metabolism: Metabolism
    feed_commodity: CommodityKind | None
    feed_per_season: int
    growth_stage: GrowthStage
    size_pct: int
    regeneration: int
    health: int
    temperament: Temperament | None
    bonded_to: NodeRef | None
    bond: int
    fertility: Fertility
    lifespan_years: int
    age_seasons: int
    designed_by: NodeRef | None
    planted_epoch: int
    locked: list[str]


class LineTraitView(ApiModel):
    id: int
    trait: LineTrait
    strength: int
    side_effect: bool
    locked: list[str]


class LineSourceView(ApiModel):
    id: int
    organism: NodeRef
    locked: list[str]


class LivingLineView(ApiModel):
    id: int
    name: str
    method: CultivationMethod
    outcome: LineOutcome
    stability: int
    generation: int
    drift_pct: int
    fertility: Fertility
    metabolism: Metabolism
    owner: NodeRef | None
    maker: NodeRef | None
    species: NodeRef | None
    drifted_from_id: int | None
    drifted_from_name: str | None
    licensed: bool
    escaped: bool
    founded_epoch: int
    living_count: int
    locked: list[str]
    traits: list[LineTraitView]
    sources: list[LineSourceView]


class BankSampleView(ApiModel):
    id: int
    organism: NodeRef
    quality: int
    taken_epoch: int
    locked: list[str]


class GeneBankView(ApiModel):
    structure: NodeRef
    holder: NodeRef | None
    upkeep: int
    unpaid_epochs: int
    locked: list[str]
    samples: list[BankSampleView]


class SymbiontView(ApiModel):
    id: int
    host: NodeRef
    line_id: int | None
    line_name: str | None
    mind: NodeRef | None
    placement: HostPlacement
    relation: HostRelation
    strength: int
    since_epoch: int
    locked: list[str]


class LivingStancesView(ApiModel):
    living_craft_stance: LivingCraftStance
    germline_stance: LivingCraftStance
    clone_stance: LivingCraftStance


class LineChoice(ApiModel):
    id: int
    name: str


class LivingNodeView(ApiModel):
    node: NodeRef
    alive_reason: str | None
    clone_reason: str | None
    profile: LivingProfileView | None
    lines: list[LivingLineView]
    symbionts: list[SymbiontView]
    banks: list[GeneBankView]
    clone_of: list[NodeRef]
    clones: list[NodeRef]
    stances: LivingStancesView | None
    every_line: list[LineChoice]
